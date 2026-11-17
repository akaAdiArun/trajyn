from dataclasses import replace
from datetime import UTC, datetime

from trajyn.benchmark import generate_delivery_task
from trajyn.delivery_agent import DeliveryReferenceAgent
from trajyn.environment import generate_task
from trajyn.induction import induce
from trajyn.models import Split, public_task
from trajyn.recording import encode_json
from trajyn.runner import environment_for, run_task
from trajyn.target import DeliveryTargetAgent
from trajyn.transfer import TransferStatus, select_capsule


def test_capsule_is_used_with_live_ids_and_source_metadata_stays_outside_context() -> None:
    source = run_task(generate_delivery_task(0), DeliveryReferenceAgent())
    capsule = induce(source, created_at=datetime(2026, 1, 1, tzinfo=UTC))
    task = generate_delivery_task(5)
    selection = select_capsule(public_task(task), environment_for(task).tools, (capsule,))
    assert selection.memory is not None
    assert selection.considered[0].status == TransferStatus.ACCEPTED
    assert selection.considered[0].source_trajectory_ids == (source.trajectory_id,)
    assert source.trajectory_id not in encode_json(selection.memory)

    agent = DeliveryTargetAgent()
    trajectory = run_task(task, agent, memory=selection.memory)
    assert trajectory.verification.passed
    assert agent.memory_used
    assert trajectory.steps[0].action.arguments["ticket_id"] == task.ticket_id
    assert (
        trajectory.steps[3].action.arguments["parcel_id"]
        != source.steps[3].action.arguments["parcel_id"]
    )


def test_transfer_rejects_wrong_workflow_and_changed_tool_interfaces() -> None:
    capsule = induce(
        run_task(generate_delivery_task(0), DeliveryReferenceAgent()),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    legacy = generate_task(1, Split.TEST)
    result = select_capsule(public_task(legacy), environment_for(legacy).tools, (capsule,))
    assert result.memory is None
    assert result.considered[0].status == TransferStatus.INAPPLICABLE

    locker = generate_delivery_task(200, Split.TEST)
    result = select_capsule(public_task(locker), environment_for(locker).tools, (capsule,))
    assert result.memory is None
    assert result.considered[0].reason == "missing_tool:ship_replacement"

    task = generate_delivery_task(5)
    tools = environment_for(task).tools
    changed = replace(tools[0], parameters=())
    result = select_capsule(public_task(task), (changed, *tools[1:]), (capsule,))
    assert result.memory is None
    assert result.considered[0].status == TransferStatus.INCOMPATIBLE


def test_capsule_guard_yields_to_observed_out_of_stock_and_refunds() -> None:
    capsule = induce(
        run_task(generate_delivery_task(0), DeliveryReferenceAgent()),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    task = generate_delivery_task(201, Split.TEST)
    selection = select_capsule(public_task(task), environment_for(task).tools, (capsule,))
    agent = DeliveryTargetAgent()
    trajectory = run_task(task, agent, memory=selection.memory)
    assert agent.memory_used and trajectory.verification.passed
    assert trajectory.steps[3].observation.code == "out_of_stock"
    assert trajectory.steps[4].action.tool == "issue_refund"
