from dataclasses import replace

import pytest

from trajyn.environment import ReplacementEnvironment, _scenario, generate_task
from trajyn.models import Split, ToolAction


@pytest.mark.parametrize(
    ("split", "issue"),
    [
        (Split.TRAIN, "damaged_item"),
        (Split.VALIDATION, "missing_item"),
        (Split.TEST, "wrong_item"),
    ],
)
def test_generation_is_seeded_and_profiles_are_distinct(split: Split, issue: str) -> None:
    task = generate_task(42, split)
    assert task == generate_task(42, split)
    assert task.task_id == f"replacement-{split}-42"
    assert task != generate_task(43, split)
    environment = ReplacementEnvironment(task)
    observation = environment.execute(ToolAction("get_ticket", {"ticket_id": task.ticket_id}))
    assert observation.data["issue"] == issue


def test_environment_rejects_altered_task() -> None:
    task = generate_task(42)
    with pytest.raises(ValueError, match="seed and split"):
        ReplacementEnvironment(replace(task, ticket_id="T-other"))


@pytest.mark.parametrize(
    ("action", "code"),
    [
        (ToolAction("delete_order"), "unknown_tool"),
        (ToolAction("get_ticket"), "invalid_arguments"),
        (ToolAction("get_order", {"order_id": False}), "invalid_arguments"),
        (ToolAction("check_stock", {"sku": "MUG", "extra": "value"}), "invalid_arguments"),
        (ToolAction("check_stock", {"sku": ""}), "invalid_arguments"),
        (ToolAction("get_ticket", {"ticket_id": "unknown"}), "ticket_not_found"),
        (ToolAction("get_order", {"order_id": "unknown"}), "order_not_found"),
        (ToolAction("check_stock", {"sku": "unknown"}), "sku_not_found"),
    ],
)
def test_invalid_actions_return_observations(action: ToolAction, code: str) -> None:
    environment = ReplacementEnvironment(generate_task(42))
    before = environment.verify()
    result = environment.execute(action)
    assert not result.ok
    assert result.code == code
    assert environment.verify() == before


def test_writes_validate_links_and_retries_consume_stock_once() -> None:
    task = generate_task(42)
    environment = ReplacementEnvironment(task)
    ticket = environment.execute(ToolAction("get_ticket", {"ticket_id": task.ticket_id}))
    order_id = ticket.data["order_id"]
    order = environment.execute(ToolAction("get_order", {"order_id": order_id}))
    sku = order.data["sku"]
    reserve = ToolAction(
        "create_replacement", {"ticket_id": task.ticket_id, "order_id": order_id, "sku": sku}
    )
    stock = ToolAction("check_stock", {"sku": sku})
    initial_units = environment.execute(stock).data["available"]
    assert type(initial_units) is int
    resolve_wrong_id = ToolAction(
        "resolve_ticket", {"ticket_id": task.ticket_id, "replacement_id": "unrelated"}
    )
    assert environment.execute(resolve_wrong_id).code == "replacement_mismatch"
    assert (
        environment.execute(
            replace(reserve, arguments={**reserve.arguments, "order_id": "unrelated"})
        ).code
        == "order_mismatch"
    )
    assert (
        environment.execute(
            replace(reserve, arguments={**reserve.arguments, "sku": "unrelated"})
        ).code
        == "sku_mismatch"
    )
    assert environment.execute(stock).data["available"] == initial_units

    created = environment.execute(reserve)
    assert created.code == "replacement_created"
    assert environment.verify().failures == ("ticket_not_resolved_with_replacement",)
    assert environment.execute(resolve_wrong_id).code == "replacement_mismatch"

    resolve = ToolAction(
        "resolve_ticket",
        {"ticket_id": task.ticket_id, "replacement_id": created.data["replacement_id"]},
    )
    assert environment.execute(resolve).ok
    retry = environment.execute(reserve)
    assert retry.code == "replacement_exists"
    assert retry.data == created.data
    assert environment.execute(resolve).ok
    assert environment.execute(stock).data["available"] == initial_units - 1
    assert environment.verify().passed


def test_inventory_and_delivery_preconditions() -> None:
    scenario = _scenario(42, Split.TRAIN)
    environment = ReplacementEnvironment(scenario.task)
    before = environment.verify()
    observed_codes = set()
    for ticket_id, ticket in scenario.tickets.items():
        order = scenario.orders[ticket.order_id]
        if scenario.stock[order.sku] == 0:
            result = environment.execute(
                ToolAction(
                    "create_replacement",
                    {"ticket_id": ticket_id, "order_id": ticket.order_id, "sku": order.sku},
                )
            )
            assert not result.ok
            expected = "out_of_stock" if order.status == "delivered" else "replacement_ineligible"
            assert result.code == expected
            observed_codes.add(result.code)
    assert observed_codes == {"out_of_stock", "replacement_ineligible"}
    assert environment.verify() == before


def test_verifier_rejects_successful_actions_that_modify_an_unrelated_ticket() -> None:
    scenario = _scenario(42, Split.TRAIN)
    environment = ReplacementEnvironment(scenario.task)
    for ticket_id, ticket in scenario.tickets.items():
        order = scenario.orders[ticket.order_id]
        if scenario.stock[order.sku] == 0:
            continue
        reserved = environment.execute(
            ToolAction(
                "create_replacement",
                {"ticket_id": ticket_id, "order_id": ticket.order_id, "sku": order.sku},
            )
        )
        assert reserved.ok
        assert environment.execute(
            ToolAction(
                "resolve_ticket",
                {"ticket_id": ticket_id, "replacement_id": reserved.data["replacement_id"]},
            )
        ).ok
    verification = environment.verify()
    assert not verification.passed
    assert verification.failures == ("stock_incorrect", "unrelated_ticket_modified")
