"""Entire study plumbing exercised with a labeled deterministic Ollama test double."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from trajyn.agent import AgentContext
from trajyn.delivery_agent import DeliveryReferenceAgent
from trajyn.lesson_protocol import OPTIONS, artifact_hashes, design, read_json, save_json
from trajyn.lesson_report import replay_attempt, replay_demo, replay_study
from trajyn.lesson_study import (
    attempt,
    completed,
    demo,
    main,
    next_attempt,
    prepare,
    run,
    study_lock,
)
from trajyn.models import Observation, PublicTask, Step, ToolAction, ToolParameter, ToolSpec
from trajyn.ollama import LocalModel, OllamaConnection, OllamaError
from trajyn.recording import encode_json


def fixture_api(
    self: OllamaConnection, path: str, payload: dict[str, object] | None = None
) -> dict[str, object]:
    """No inference. Actions follow the public rules-based fixture, labeled by tests."""
    if path == "/api/tags":
        return {
            "models": [
                {"name": name, "digest": char * 64, "size": 1}
                for name, char in [("qwen3:8b", "a"), ("granite4:3b", "b")]
            ]
        }
    if path == "/api/show":
        return {"details": {"family": "deterministic-test-double"}, "capabilities": ["tools"]}
    if path == "/api/version":
        return {"version": "deterministic-test-double"}
    assert payload is not None and path == "/api/chat"
    messages: Any = payload["messages"]
    if payload["format"] == "json":
        # A deterministic TEST learner inspects the provided contrasts. This test
        # supplies no evidence for a real Qwen learning or transfer result.
        from trajyn.lesson import Activation, Exclusion

        contrasts = json.loads(messages[1]["content"])["contrasts"]
        evidence = []
        producers = set()
        for trace in contrasts:
            if not trace["verified"]:
                continue
            for step in trace["steps"]:
                tool = step["action"]["tool"]
                if tool in {"ship_replacement", "locker_replacement"}:
                    consumer = next(
                        s for s in trace["steps"] if s["action"]["tool"] == "close_case"
                    )
                    producers.add(tool)
                    evidence.append(
                        {
                            "trajectory_id": trace["trajectory_id"],
                            "producer_step": step["index"],
                            "consumer_step": consumer["index"],
                        }
                    )
                    break
        proposal = {
            "version": 1,
            "workflow": "delivery-exception-v3",
            "producer_tools": sorted(producers),
            "consumer_tool": "close_case",
            "output_field": "receipt_id",
            "success_codes": ["remedy_exists", "remedy_posted"],
            "activation": list(Activation),
            "exclusions": list(Exclusion),
            "bindings": [
                {"parameter": "ticket_id", "origin": "producer.action", "field": "ticket_id"},
                {
                    "parameter": "receipt_id",
                    "origin": "producer.observation",
                    "field": "receipt_id",
                },
            ],
            "evidence": evidence,
        }
        return {
            "message": {"content": encode_json(proposal)},
            "prompt_eval_count": 11,
            "eval_count": 2,
        }
    content = messages[1]["content"]
    ticket = re.search(r"ticket (case-[a-f0-9]+)", content)
    assert ticket is not None
    tools = json.loads(content.split("Available tools:\n")[1].split("\nPublic tool history")[0])
    history = json.loads(content.split("Public tool history in order:\n")[1].split("\nChoose")[0])
    ctx = AgentContext(
        PublicTask(ticket[1], "fixture", "delivery-exception-v3"),
        tuple(
            ToolSpec(
                t["name"], t["description"], tuple(ToolParameter(**p) for p in t["parameters"])
            )
            for t in tools
        ),
        tuple(
            Step(i, ToolAction(**s["action"]), Observation(**s["observation"]))
            for i, s in enumerate(history, 1)
        ),
        10,
    )
    decision = DeliveryReferenceAgent().decide(ctx)
    assert decision is not None
    return {
        "message": {"content": encode_json({"action": decision.action.tool})},
        "prompt_eval_count": 11,
        "eval_count": 2,
    }


def test_all_96_cells_freeze_resume_and_offline_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(OllamaConnection, "api", fixture_api)
    monkeypatch.setattr("trajyn.lesson_study.committed_freeze", lambda path: "test-fixture")
    connection = OllamaConnection("http://127.0.0.1:11434", OPTIONS)
    root, freeze = tmp_path / "archive", tmp_path / "freeze.json"
    prepared = prepare(root, connection, freeze)
    assert prepared["status"] == "ready_to_freeze"
    manifest = read_json(freeze)
    assert len(manifest["design"]["cases"]) == 24
    assert all(manifest["F_available"].values())
    result = run(root, connection, freeze)
    assert result["completed_cells"] == 96
    before = artifact_hashes(root)
    assert run(root, connection, freeze) == result
    assert artifact_hashes(root) == before

    # Offline rebuild cannot access the inference endpoint.
    def forbidden(*args: object, **kwargs: object) -> dict[str, object]:
        raise AssertionError("offline replay contacted a model")

    monkeypatch.setattr(OllamaConnection, "api", forbidden)
    assert replay_study(root, freeze) == result
    report = read_json(root / "report.json")
    assert report["gate_audits"]["G"]["hint_deliveries"] == 16
    assert report["gate_audits"]["G"]["incorrect_deliveries"] == 0
    assert report["results"]["overall"]["paired"]["G_vs_A"]["difference_pp"] == 0
    # Even a newly sealed wrong audit is rejected by reconstruction of real prompts.
    folder = completed(root / "targets" / "1008-G")
    assert folder is not None
    record = read_json(folder / "result.json")
    record["audit"]["delivered"] = []
    save_json(folder / "result.json", record)
    save_json(folder / "seal.json", artifact_hashes(folder, exclude=("seal.json",)))
    with pytest.raises(ValueError, match="reported decisions"):
        replay_study(root, freeze)


def test_demo_replays_and_rejects_tampering(tmp_path: Path) -> None:
    result = demo(tmp_path)
    assert result["cases_with_offered_hints"] == 16
    assert result["model_attempts"] == 0
    assert result == replay_demo(tmp_path)
    lesson = tmp_path / "lesson.json"
    lesson.write_text(lesson.read_text() + " ")
    with pytest.raises(ValueError, match="changed artifact"):
        replay_demo(tmp_path)


def test_rejected_induction_stops_before_targets_and_all_proposals_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def bad_learner(
        self: OllamaConnection, path: str, payload: dict[str, object] | None = None
    ) -> dict[str, object]:
        if payload is not None and payload.get("format") == "json":
            return {"message": {"content": '{"instruction":"hand authored text"}'}}
        return fixture_api(self, path, payload)

    monkeypatch.setattr(OllamaConnection, "api", bad_learner)
    result = prepare(
        tmp_path / "archive",
        OllamaConnection("http://localhost", OPTIONS),
        tmp_path / "freeze.json",
    )
    assert result["status"] == "no_valid_learned_lesson"
    root = tmp_path / "archive"
    assert len(list((root / "proposals").glob("*.json"))) == 4
    assert not (root / "targets").exists()
    assert not (root / "lesson.json").exists()
    assert replay_study(root, tmp_path / "freeze.json")["status"] == "not_frozen"
    record = read_json(root / "validations/1.json")
    record["reason"] = "invented rejection"
    save_json(root / "validations/1.json", record)
    with pytest.raises(ValueError, match="rejection reason changed"):
        replay_study(root, tmp_path / "freeze.json")


def test_infrastructure_failure_is_sealed_incomplete_and_replayable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from trajyn.benchmark import DELIVERY_V3, generate_delivery_task

    def failed(self: OllamaConnection, path: str, payload: object = None) -> dict[str, object]:
        raise OllamaError("fixture_timeout")

    monkeypatch.setattr(OllamaConnection, "api", failed)
    task = generate_delivery_task(600, workflow=DELIVERY_V3)
    model = LocalModel("qwen3:8b", "a" * 64, "test-double", False)
    folder = next_attempt(tmp_path / "cell")
    record = attempt(folder, task, OllamaConnection("http://localhost", OPTIONS), model)
    assert record["status"] == "incomplete"
    assert completed(tmp_path / "cell") is None
    assert next_attempt(tmp_path / "cell") != folder
    assert replay_attempt(folder, task, model) == json.loads(encode_json(record))
    with pytest.raises(ValueError, match="already exists"):
        attempt(folder, task, OllamaConnection("http://localhost", OPTIONS), model)


def test_manifest_has_distinct_partitions_routes_and_rotated_order() -> None:
    plan: Any = design()
    assert set(plan["train_seeds"]).isdisjoint(plan["dev_seeds"])
    assert set(plan["dev_seeds"]).isdisjoint(c["seed"] for c in plan["cases"])
    counts = {
        kind: sum(c["type"] == kind for c in plan["cases"])
        for kind in ["familiar", "different_route", "look_alike"]
    }
    assert set(counts.values()) == {8}
    assert len({tuple(c["arms"]) for c in plan["cases"]}) == 4
    families = {kind: {c["family"] for c in plan["cases"] if c["type"] == kind} for kind in counts}
    assert families["familiar"].isdisjoint(families["different_route"])
    assert len(families["different_route"]) == 4


def test_os_lock_prevents_concurrent_writers(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    with study_lock(root), pytest.raises(OSError), study_lock(root):
        pass
    with study_lock(root):
        pass


def test_cli_demo_and_replay(tmp_path: Path) -> None:
    assert main(["demo", "--output", str(tmp_path)]) == 0
    assert main(["replay", "--output", str(tmp_path)]) == 0
