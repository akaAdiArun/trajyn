from dataclasses import asdict

import pytest

from trajyn.agent import AgentContext
from trajyn.benchmark import DeliveryEnvironment, generate_delivery_task
from trajyn.delivery_agent import DeliveryReferenceAgent
from trajyn.models import AgentDecision, Split, ToolAction
from trajyn.runner import run_task


@pytest.mark.parametrize(
    ("split", "seed", "remedy", "recoveries"),
    [
        (Split.TRAIN, 0, "ship_replacement", []),
        (Split.TRAIN, 1, "issue_refund", []),
        (Split.TRAIN, 2, "acknowledge_delivery", []),
        (Split.TRAIN, 3, "schedule_pickup", []),
        (Split.TRAIN, 4, "ship_replacement", ["warehouse_retry"]),
        (Split.VALIDATION, 100, "acknowledge_delivery", ["carrier_retry"]),
        (Split.VALIDATION, 101, "schedule_pickup", []),
        (Split.VALIDATION, 102, "ship_replacement", ["carrier_retry"]),
        (Split.TEST, 200, "locker_replacement", []),
        (Split.TEST, 201, "issue_refund", ["out_of_stock"]),
        (Split.TEST, 202, "acknowledge_delivery", []),
        (Split.TEST, 203, "schedule_pickup", ["carrier_retry"]),
    ],
)
def test_structural_profiles(split: Split, seed: int, remedy: str, recoveries: list[str]) -> None:
    task = generate_delivery_task(seed, split)
    result = run_task(task, DeliveryReferenceAgent())
    assert result == run_task(task, DeliveryReferenceAgent())
    assert result.verification.passed
    assert result.steps[-2].action.tool == remedy
    assert [step.observation.code for step in result.steps if not step.observation.ok] == recoveries


def test_evaluation_agent_receives_public_task_and_available_tools_only() -> None:
    task = generate_delivery_task(200, Split.TEST)

    class InspectingAgent(DeliveryReferenceAgent):
        def decide(self, context: AgentContext) -> AgentDecision | None:
            assert set(asdict(context.task)) == {"ticket_id", "goal", "workflow"}
            assert "locker_replacement" in {tool.name for tool in context.tools}
            assert "ship_replacement" not in {tool.name for tool in context.tools}
            return super().decide(context)

    assert run_task(task, InspectingAgent()).verification.passed
    assert task.ticket_id != generate_delivery_task(200, Split.TRAIN).ticket_id
    assert task.ticket_id != generate_delivery_task(204, Split.TEST).ticket_id


def test_verifier_can_reject_a_closed_case_with_the_wrong_remedy() -> None:
    task = generate_delivery_task(0)
    env = DeliveryEnvironment(task)
    parcel_id = env.execute(ToolAction("read_case", {"ticket_id": task.ticket_id})).data[
        "parcel_id"
    ]
    refund = env.execute(
        ToolAction("issue_refund", {"ticket_id": task.ticket_id, "parcel_id": parcel_id})
    )
    assert refund.ok
    closed = env.execute(
        ToolAction(
            "close_case", {"ticket_id": task.ticket_id, "receipt_id": refund.data["receipt_id"]}
        )
    )
    assert closed.ok
    assert env.verify().failures == (
        "incorrect_or_missing_remedy",
        "incorrect_inventory",
        "incorrect_refund",
    )


def test_report_and_inventory_listing_can_be_stale() -> None:
    delivery = run_task(generate_delivery_task(202, Split.TEST), DeliveryReferenceAgent())
    assert delivery.steps[0].observation.data["reported_status"] == "lost"
    assert delivery.steps[1].observation.data["status"] == "delivered"

    stock = run_task(generate_delivery_task(201, Split.TEST), DeliveryReferenceAgent())
    assert stock.steps[2].observation.data["available"] is True
    assert stock.steps[3].observation.code == "out_of_stock"
    assert stock.steps[4].action.tool == "issue_refund"


def test_bad_link_and_unavailable_tool_leave_case_open() -> None:
    task = generate_delivery_task(200, Split.TEST)
    env = DeliveryEnvironment(task)
    assert env.execute(ToolAction("ship_replacement")).code == "unknown_tool"
    assert (
        env.execute(ToolAction("inspect_parcel", {"parcel_id": "parcel-other"})).code
        == "parcel_id_mismatch"
    )
    assert "case_not_closed" in env.verify().failures


def test_link_validation_is_order_independent_and_replays_legacy_errors() -> None:
    task = generate_delivery_task(200, Split.TEST)
    env = DeliveryEnvironment(task)
    before = env.verify()
    action = ToolAction("issue_refund", {"ticket_id": "wrong-ticket", "parcel_id": "wrong-parcel"})
    reordered = ToolAction("issue_refund", dict(reversed(tuple(action.arguments.items()))))
    assert env.execute(action) == env.execute(reordered)
    assert env.execute(action).code == "parcel_id_mismatch"
    assert env.replay(reordered, "ticket_id_mismatch").code == "ticket_id_mismatch"
    assert env.replay(reordered, "product_id_mismatch").code == "parcel_id_mismatch"
    assert env.verify() == before
