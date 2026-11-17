import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trajyn.agent import AgentContext, OfflineReferenceAgent
from trajyn.benchmark import generate_delivery_task
from trajyn.capability import ArgumentBinding, read_capsule
from trajyn.delivery_agent import DeliveryReferenceAgent
from trajyn.environment import generate_task
from trajyn.induction import induce
from trajyn.models import AgentDecision, AgentIdentity, Observation, Split
from trajyn.provenance import read_trajectory
from trajyn.recording import encode_json, trajectory_id, write_jsonl, write_trajectory
from trajyn.runner import run_task

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def test_induction_derives_distinct_guarded_branches_without_instance_ids(tmp_path: Path) -> None:
    source = run_task(generate_delivery_task(0), DeliveryReferenceAgent())
    capsule = induce(source, created_at=CREATED)
    assert capsule == induce(source, created_at=CREATED)
    assert capsule.evidence[0].trajectory_id == source.trajectory_id
    assert capsule.evidence[0].step_indices == (1, 2, 3, 4, 5)
    assert capsule.steps[3].bindings == (
        ArgumentBinding("parcel_id", 1, "parcel_id"),
        ArgumentBinding("product_id", 2, "product_id"),
        ArgumentBinding("ticket_id", 0, "ticket_id"),
    )
    assert encode_json(capsule).find(source.task.ticket_id) == -1
    for step in source.steps:
        for value in step.action.arguments.values():
            assert isinstance(value, str) and value not in encode_json(capsule)
    path = tmp_path / "capsule.json"
    write_jsonl(path, [capsule])
    assert read_capsule(path) == capsule

    delivered = induce(
        run_task(generate_delivery_task(2), DeliveryReferenceAgent()), created_at=CREATED
    )
    assert [step.tool for step in delivered.steps] == [
        "read_case",
        "inspect_parcel",
        "acknowledge_delivery",
        "close_case",
    ]
    retry = induce(
        run_task(generate_delivery_task(4), DeliveryReferenceAgent()), created_at=CREATED
    )
    assert retry.steps[3].expect is not None and retry.steps[3].expect.code == "warehouse_retry"
    assert retry.steps[4].tool == "ship_replacement"


def test_legacy_jsonl_and_measured_runs_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "legacy.jsonl"
    legacy = run_task(generate_task(42), OfflineReferenceAgent())
    write_trajectory(path, legacy)
    assert read_trajectory(path) == legacy
    assert induce(legacy, created_at=CREATED).steps[0].tool == "get_ticket"

    measured = run_task(generate_delivery_task(0), DeliveryReferenceAgent(), measure_time=True)
    write_trajectory(path, measured)
    assert read_trajectory(path) == measured


def test_induction_rejects_held_out_incomplete_and_forged_records(tmp_path: Path) -> None:
    agent = DeliveryReferenceAgent()
    with pytest.raises(ValueError, match="training trajectory"):
        induce(run_task(generate_delivery_task(202, Split.TEST), agent), created_at=CREATED)
    with pytest.raises(ValueError, match="verified successful"):
        induce(run_task(generate_delivery_task(0), agent, max_steps=1), created_at=CREATED)

    original = run_task(generate_delivery_task(0), agent)
    fake_step = replace(original.steps[0], observation=Observation(True, "made_up"))
    fake = replace(original, steps=(fake_step, *original.steps[1:]))
    fake = replace(fake, trajectory_id=trajectory_id(fake))
    with pytest.raises(ValueError, match="cannot be reproduced at step 1"):
        induce(fake, created_at=CREATED)

    path = tmp_path / "forged.jsonl"
    write_trajectory(path, original)
    lines = path.read_text(encoding="utf-8").splitlines()
    event = json.loads(lines[1])
    event["schema_version"] = 50
    lines[1] = json.dumps(event)
    path.write_text("\n".join(lines), encoding="utf-8")
    with pytest.raises(ValueError, match="trajectory schema"):
        read_trajectory(path)


def test_induction_rejects_success_using_unobserved_identifiers() -> None:
    task = generate_delivery_task(0)
    original = run_task(task, DeliveryReferenceAgent())
    actions = tuple(step.action for step in original.steps[3:])

    class UnobservableShortcut:
        identity = AgentIdentity("fixture", "shortcut")

        def decide(self, context: AgentContext) -> AgentDecision | None:
            index = len(context.steps)
            return AgentDecision(actions[index]) if index < len(actions) else None

    shortcut = run_task(task, UnobservableShortcut())
    assert shortcut.verification.passed
    with pytest.raises(ValueError, match="no observed source for parcel_id"):
        induce(shortcut, created_at=CREATED)


def test_capsule_rejects_forward_bindings_and_wrong_schema(tmp_path: Path) -> None:
    capsule = induce(
        run_task(generate_delivery_task(0), DeliveryReferenceAgent()), created_at=CREATED
    )
    first, *rest = capsule.steps
    ungrounded = replace(first, bindings=(ArgumentBinding("ticket_id", 2, "ticket_id"),))
    with pytest.raises(ValueError, match="earlier steps"):
        replace(capsule, steps=(ungrounded, *rest))
    path = tmp_path / "invalid.json"
    record = json.loads(encode_json(capsule))
    record["schema_version"] = 100
    write_jsonl(path, [record])
    with pytest.raises(ValueError, match="unsupported capability schema"):
        read_capsule(path)
