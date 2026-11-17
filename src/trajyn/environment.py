"""Synthetic support API for replacing one item from a delivered order."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from random import Random

from trajyn.models import (
    Observation,
    Split,
    Task,
    ToolAction,
    ToolParameter,
    ToolSpec,
    Verification,
)

_TICKET = ToolParameter("ticket_id", "Support ticket identifier.")
_ORDER = ToolParameter("order_id", "Order identifier returned by get_ticket.")
_SKU = ToolParameter("sku", "Catalog SKU for the original item.")
_REPLACEMENT = ToolParameter("replacement_id", "Identifier returned by create_replacement.")

TOOLS = (
    ToolSpec("get_ticket", "Read a support ticket.", (_TICKET,)),
    ToolSpec("get_order", "Read an order and its delivery status.", (_ORDER,)),
    ToolSpec("check_stock", "Look up available units by SKU.", (_SKU,)),
    ToolSpec(
        "create_replacement",
        "Reserve one unit for a ticket's delivered order.",
        (_TICKET, _ORDER, _SKU),
    ),
    ToolSpec("resolve_ticket", "Close a ticket using its replacement.", (_TICKET, _REPLACEMENT)),
)
_PARAMETERS = {tool.name: {parameter.name for parameter in tool.parameters} for tool in TOOLS}
_PROFILES = {
    Split.TRAIN: ("damaged_item", ("MUG", "TRAY", "LAMP")),
    Split.VALIDATION: ("missing_item", ("MAT", "BIN", "RACK")),
    Split.TEST: ("wrong_item", ("CUP", "JAR", "BOWL")),
}


@dataclass(frozen=True, slots=True)
class _Ticket:
    order_id: str
    issue: str
    status: str = "open"
    replacement_id: str | None = None


@dataclass(frozen=True, slots=True)
class _Order:
    sku: str
    status: str


@dataclass(frozen=True, slots=True)
class _Replacement:
    replacement_id: str
    order_id: str
    sku: str


@dataclass(frozen=True, slots=True)
class _Scenario:
    task: Task
    tickets: dict[str, _Ticket]
    orders: dict[str, _Order]
    stock: dict[str, int]


def _scenario(seed: int, split: Split) -> _Scenario:
    if seed < 0:
        raise ValueError("seed must be non-negative")
    rng = Random(f"{split}:{seed}")
    issue, skus = _PROFILES[split]
    sku, decoy_sku, pending_sku = rng.sample(skus, 3)
    ticket_id, decoy_ticket, pending_ticket, empty_ticket = rng.sample(range(1000, 9999), 4)
    order_id, decoy_order, pending_order, empty_order = rng.sample(range(1000, 9999), 4)

    target = f"T-{ticket_id}"
    order = f"O-{order_id}"
    other_order = f"O-{decoy_order}"
    undelivered_order = f"O-{pending_order}"
    unavailable_order = f"O-{empty_order}"
    task = Task(
        task_id=f"replacement-{split}-{seed}",
        seed=seed,
        split=split,
        ticket_id=target,
        goal=(
            f"Reserve one replacement for the original item reported as {issue.replace('_', ' ')} "
            f"in ticket {target}, then resolve that ticket with the replacement."
        ),
    )
    return _Scenario(
        task=task,
        tickets={
            target: _Ticket(order, issue),
            f"T-{decoy_ticket}": _Ticket(other_order, "damaged_item"),
            f"T-{pending_ticket}": _Ticket(undelivered_order, "missing_item"),
            f"T-{empty_ticket}": _Ticket(unavailable_order, "wrong_item"),
        },
        orders={
            order: _Order(sku, "delivered"),
            other_order: _Order(decoy_sku, "delivered"),
            undelivered_order: _Order(pending_sku, "in_transit"),
            unavailable_order: _Order(pending_sku, "delivered"),
        },
        stock={sku: rng.randint(1, 6), decoy_sku: rng.randint(1, 6), pending_sku: 0},
    )


def generate_task(seed: int, split: Split = Split.TRAIN) -> Task:
    return _scenario(seed, split).task


class ReplacementEnvironment:
    tools = TOOLS

    def __init__(self, task: Task) -> None:
        self._initial = _scenario(task.seed, task.split)
        if task != self._initial.task:
            raise ValueError("task does not match its seed and split")
        self._tickets = self._initial.tickets.copy()
        self._orders = self._initial.orders.copy()
        self._stock = self._initial.stock.copy()
        self._replacements: dict[str, _Replacement] = {}
        self._handlers: dict[str, Callable[..., Observation]] = {
            "get_ticket": self._get_ticket,
            "get_order": self._get_order,
            "check_stock": self._check_stock,
            "create_replacement": self._create_replacement,
            "resolve_ticket": self._resolve_ticket,
        }

    def execute(self, action: ToolAction) -> Observation:
        if action.tool not in self._handlers:
            return Observation(False, "unknown_tool")
        if action.arguments.keys() != _PARAMETERS[action.tool]:
            return Observation(False, "invalid_arguments")
        arguments: dict[str, str] = {}
        for name, value in action.arguments.items():
            if not isinstance(value, str) or not value:
                return Observation(False, "invalid_arguments")
            arguments[name] = value
        return self._handlers[action.tool](**arguments)

    def _get_ticket(self, ticket_id: str) -> Observation:
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return Observation(False, "ticket_not_found")
        return Observation(
            True,
            "ticket_found",
            {
                "order_id": ticket.order_id,
                "issue": ticket.issue,
                "status": ticket.status,
                "replacement_id": ticket.replacement_id,
            },
        )

    def _get_order(self, order_id: str) -> Observation:
        order = self._orders.get(order_id)
        if order is None:
            return Observation(False, "order_not_found")
        return Observation(True, "order_found", {"sku": order.sku, "status": order.status})

    def _check_stock(self, sku: str) -> Observation:
        if sku not in self._stock:
            return Observation(False, "sku_not_found")
        return Observation(True, "stock_found", {"available": self._stock[sku]})

    def _create_replacement(self, ticket_id: str, order_id: str, sku: str) -> Observation:
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return Observation(False, "ticket_not_found")
        if ticket.order_id != order_id:
            return Observation(False, "order_mismatch")
        order = self._orders[order_id]
        if order.sku != sku:
            return Observation(False, "sku_mismatch")
        existing = self._replacements.get(ticket_id)
        if existing is not None:
            return Observation(
                True, "replacement_exists", {"replacement_id": existing.replacement_id}
            )
        if ticket.status != "open" or order.status != "delivered":
            return Observation(False, "replacement_ineligible")
        if self._stock[sku] < 1:
            return Observation(False, "out_of_stock")

        replacement_id = f"R-{ticket_id}"
        self._replacements[ticket_id] = _Replacement(replacement_id, order_id, sku)
        self._stock[sku] -= 1
        return Observation(True, "replacement_created", {"replacement_id": replacement_id})

    def _resolve_ticket(self, ticket_id: str, replacement_id: str) -> Observation:
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return Observation(False, "ticket_not_found")
        replacement = self._replacements.get(ticket_id)
        if replacement is None or replacement.replacement_id != replacement_id:
            return Observation(False, "replacement_mismatch")
        self._tickets[ticket_id] = replace(ticket, status="resolved", replacement_id=replacement_id)
        return Observation(True, "ticket_resolved")

    def verify(self) -> Verification:
        """Check persisted state and reject side effects on unrelated records."""
        ticket_id = self._initial.task.ticket_id
        initial_ticket = self._initial.tickets[ticket_id]
        original_sku = self._initial.orders[initial_ticket.order_id].sku
        replacement = self._replacements.get(ticket_id)
        ticket = self._tickets[ticket_id]
        failures = []
        if replacement is None:
            failures.append("replacement_missing")
        elif replacement.order_id != initial_ticket.order_id or replacement.sku != original_sku:
            failures.append("replacement_incorrect")
        if replacement is None or ticket != replace(
            initial_ticket, status="resolved", replacement_id=replacement.replacement_id
        ):
            failures.append("ticket_not_resolved_with_replacement")

        expected_stock = self._initial.stock.copy()
        expected_stock[original_sku] -= 1
        if self._stock != expected_stock:
            failures.append("stock_incorrect")
        if self._replacements.keys() - {ticket_id} or any(
            self._tickets[key] != initial
            for key, initial in self._initial.tickets.items()
            if key != ticket_id
        ):
            failures.append("unrelated_ticket_modified")
        return Verification("replacement_state_v1", not failures, tuple(failures))
