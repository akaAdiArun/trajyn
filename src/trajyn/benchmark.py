"""Delivery-exception benchmark with split-specific scenarios and a state verifier."""

from dataclasses import dataclass
from hashlib import sha256

from trajyn.models import (
    DeliveryTask,
    Observation,
    Split,
    ToolAction,
    ToolParameter,
    ToolSpec,
    Verification,
)

_TICKET = ToolParameter("ticket_id", "Current support ticket identifier.")
_PARCEL = ToolParameter("parcel_id", "Linked parcel identifier from read_case.")
_PRODUCT = ToolParameter("product_id", "Product identifier from inspect_parcel.")
_RECEIPT = ToolParameter("receipt_id", "Receipt identifier from a posted remedy.")
_APPROVAL = ToolParameter("approval_id", "Authorization returned by approve_refund.")
_LOOKUP = ToolSpec("find_parcel", "Find the linked parcel when the case lacks its ID.", (_TICKET,))
_BACKUP = ToolSpec(
    "query_carrier_backup",
    "Read carrier facts when the primary carrier lookup is unavailable.",
    (_PARCEL,),
)
_APPROVE = ToolSpec(
    "approve_refund",
    "Request an approval ID for a lost parcel without replacement stock.",
    (_TICKET, _PARCEL),
)
_REFUND_WITH_APPROVAL = ToolSpec(
    "issue_refund",
    "Refund a lost parcel using a refund authorization.",
    (_TICKET, _PARCEL, _APPROVAL),
)
_READ_TOOLS = (
    ToolSpec("read_case", "Read the customer report and linked parcel.", (_TICKET,)),
    ToolSpec("inspect_parcel", "Read authoritative carrier and product data.", (_PARCEL,)),
    ToolSpec("get_stock", "Read the stock listing for a product.", (_PRODUCT,)),
)
_REMEDIES = (
    ToolSpec("issue_refund", "Refund a lost parcel.", (_TICKET, _PARCEL)),
    ToolSpec(
        "acknowledge_delivery",
        "Confirm a parcel marked delivered by the carrier.",
        (_TICKET, _PARCEL),
    ),
    ToolSpec(
        "schedule_pickup", "Arrange collection of a parcel held by the carrier.", (_TICKET, _PARCEL)
    ),
)
_SHIP = ToolSpec(
    "ship_replacement", "Dispatch a replacement from the warehouse.", (_TICKET, _PARCEL, _PRODUCT)
)
_LOCKER = ToolSpec(
    "locker_replacement", "Reserve a replacement in a local locker.", (_TICKET, _PARCEL, _PRODUCT)
)
_CLOSE = ToolSpec("close_case", "Close the case with a posted remedy receipt.", (_TICKET, _RECEIPT))
RECOVERY_CODES = frozenset(
    {
        "carrier_retry",
        "warehouse_retry",
        "out_of_stock",
        "carrier_unavailable",
    }
)
_REQUIRED_STATUS = {
    "ship_replacement": "lost",
    "locker_replacement": "lost",
    "issue_refund": "lost",
    "acknowledge_delivery": "delivered",
    "schedule_pickup": "held",
}
_GOAL = (
    "Resolve the delivery exception for ticket {ticket_id}. Check the carrier. For a lost "
    "parcel, prefer a replacement when available and refund otherwise. Confirm a delivered "
    "parcel or arrange pickup of a held parcel. Close the case using the remedy receipt."
)
DELIVERY_V1 = "delivery-exception-v1"
DELIVERY_V2 = "delivery-exception-v2"


@dataclass(frozen=True, slots=True)
class _Profile:
    status: str
    stock: int = 0
    locker: bool = False
    carrier_retry: bool = False
    warehouse_retry: bool = False
    stale_listing: bool = False
    stale_report: bool = False
    missing_parcel: bool = False
    backup_carrier: bool = False
    refund_approval: bool = False


# Seed modulo table length selects a profile. Each row defines its own structural support.
_PROFILES = {
    Split.TRAIN: (
        _Profile("lost", stock=3),
        _Profile("lost"),
        _Profile("delivered"),
        _Profile("held"),
        _Profile("lost", stock=2, warehouse_retry=True),
    ),
    Split.VALIDATION: (
        _Profile("lost", stock=1, carrier_retry=True),
        _Profile("delivered", carrier_retry=True),
        _Profile("held"),
    ),
    Split.TEST: (
        _Profile("lost", stock=2, locker=True),
        _Profile("lost", stale_listing=True),
        _Profile("delivered", stale_report=True),
        _Profile("held", carrier_retry=True),
    ),
}

_EXPANDED = {
    Split.TRAIN: (
        _Profile("lost", stock=3),
        _Profile("lost", refund_approval=True),
        _Profile("delivered", stale_report=True),
        _Profile("held", backup_carrier=True),
        _Profile("lost", stock=2, missing_parcel=True),
        _Profile("lost", stock=2, locker=True),
        _Profile("lost", stale_listing=True),
        _Profile("held", carrier_retry=True),
    ),
    Split.VALIDATION: (
        _Profile("lost", stock=2, carrier_retry=True, missing_parcel=True),
        _Profile("delivered", missing_parcel=True),
        _Profile("lost", stock=2, locker=True, backup_carrier=True),
        _Profile("held", stale_report=True),
        _Profile("lost", backup_carrier=True, refund_approval=True),
        _Profile("lost", stock=3, warehouse_retry=True),
    ),
    Split.TEST: (
        _Profile("lost", stock=2, locker=True, missing_parcel=True, warehouse_retry=True),
        _Profile("lost", stale_listing=True, missing_parcel=True, refund_approval=True),
        _Profile("delivered", backup_carrier=True, stale_report=True),
        _Profile("held", missing_parcel=True, backup_carrier=True),
        _Profile("lost", stale_listing=True, backup_carrier=True, refund_approval=True),
        _Profile("lost", stock=1, locker=True, carrier_retry=True),
        _Profile("held", carrier_retry=True, stale_report=True, missing_parcel=True),
        _Profile("delivered", carrier_retry=True, missing_parcel=True, stale_report=True),
    ),
}


def generate_delivery_task(
    seed: int, split: Split = Split.TRAIN, *, workflow: str = DELIVERY_V1
) -> DeliveryTask:
    if seed < 0:
        raise ValueError("seed must be non-negative")
    if workflow not in (DELIVERY_V1, DELIVERY_V2):
        raise ValueError("unsupported delivery workflow")
    ref = _instance_ref(seed, split, workflow)
    ticket_id = f"case-{ref[:20]}"
    return DeliveryTask(
        f"delivery-{ref}", seed, split, ticket_id, _GOAL.format(ticket_id=ticket_id), workflow
    )


def _instance_ref(seed: int, split: Split, workflow: str) -> str:
    return sha256(f"{workflow}/{split}/{seed}".encode()).hexdigest()


class DeliveryEnvironment:
    def __init__(self, task: DeliveryTask) -> None:
        if task != generate_delivery_task(task.seed, task.split, workflow=task.workflow):
            raise ValueError("task does not match its seed and split")
        profiles = (_EXPANDED if task.workflow == DELIVERY_V2 else _PROFILES)[task.split]
        self._profile = profiles[task.seed % len(profiles)]
        ref = _instance_ref(task.seed, task.split, task.workflow)
        self._workflow = task.workflow
        self._ticket = task.ticket_id
        self._parcel = f"parcel-{ref[20:36]}"
        self._product = f"product-{ref[36:52]}"
        self._receipt = f"receipt-{ref[52:]}"
        self._approval = f"approval-{sha256(ref.encode()).hexdigest()[:12]}"
        self._approved = False
        self._parcel_value = 500 + (task.seed % 37) * 113
        self._initial_stock = self._profile.stock
        if task.workflow == DELIVERY_V2 and self._initial_stock:
            self._initial_stock += int(ref[-2:], 16) % 3
        self._stock = self._initial_stock
        self._refund = 0
        self._carrier_retry = self._profile.carrier_retry
        self._warehouse_retry = self._profile.warehouse_retry
        self._closed_with: str | None = None
        self._remedy: str | None = None
        refunds = (_REFUND_WITH_APPROVAL if self._profile.refund_approval else _REMEDIES[0],)
        self.tools = (
            *_READ_TOOLS,
            *((_LOOKUP,) if self._profile.missing_parcel else ()),
            *((_BACKUP,) if self._profile.backup_carrier else ()),
            *((_APPROVE,) if self._profile.refund_approval else ()),
            *refunds,
            *_REMEDIES[1:],
            _LOCKER if self._profile.locker else _SHIP,
            _CLOSE,
        )
        self._parameters = {
            tool.name: {parameter.name for parameter in tool.parameters} for tool in self.tools
        }

    def execute(self, action: ToolAction) -> Observation:
        return self._execute(action)

    def replay(self, action: ToolAction, recorded_code: str) -> Observation:
        # Earlier traces could report any mismatched field before JSON sorted the keys.
        return self._execute(action, preferred_mismatch=recorded_code.removesuffix("_mismatch"))

    def _execute(self, action: ToolAction, *, preferred_mismatch: str | None = None) -> Observation:
        if action.tool not in self._parameters:
            return Observation(False, "unknown_tool")
        if action.arguments.keys() != self._parameters[action.tool] or any(
            not isinstance(value, str) or not value for value in action.arguments.values()
        ):
            return Observation(False, "invalid_arguments")

        expected = {
            "ticket_id": self._ticket,
            "parcel_id": self._parcel,
            "product_id": self._product,
            "receipt_id": self._receipt,
            "approval_id": self._approval,
        }
        mismatches = sorted(
            name for name, value in action.arguments.items() if value != expected[name]
        )
        if mismatches:
            name = preferred_mismatch if preferred_mismatch in mismatches else mismatches[0]
            return Observation(False, f"{name}_mismatch")

        match action.tool:
            case "read_case":
                reported_status = "lost" if self._profile.stale_report else self._profile.status
                if self._profile.missing_parcel:
                    return Observation(
                        True, "case_needs_lookup", {"reported_status": reported_status}
                    )
                return Observation(
                    True,
                    "case_read",
                    {"parcel_id": self._parcel, "reported_status": reported_status},
                )
            case "find_parcel":
                return Observation(True, "parcel_found", {"parcel_id": self._parcel})
            case "inspect_parcel" | "query_carrier_backup":
                if action.tool == "inspect_parcel" and self._profile.backup_carrier:
                    return Observation(False, "carrier_unavailable")
                if self._carrier_retry:
                    self._carrier_retry = False
                    return Observation(False, "carrier_retry")
                return Observation(
                    True,
                    "parcel_inspected",
                    {"status": self._profile.status, "product_id": self._product},
                )
            case "approve_refund":
                if self._profile.status != "lost" or self._stock != 0 or self._remedy is not None:
                    return Observation(False, "remedy_ineligible")
                self._approved = True
                return Observation(True, "refund_approved", {"approval_id": self._approval})
            case "get_stock":
                return Observation(
                    True,
                    "stock_read",
                    {"available": self._stock > 0 or self._profile.stale_listing},
                )
            case "close_case":
                if self._remedy is None:
                    return Observation(False, "remedy_required")
                self._closed_with = self._receipt
                return Observation(True, "case_closed")
            case _:
                return self._post_remedy(action.tool)

    def _post_remedy(self, tool: str) -> Observation:
        if self._remedy is not None:
            if self._remedy != tool:
                return Observation(False, "remedy_already_posted")
            return Observation(True, "remedy_exists", {"receipt_id": self._receipt})
        if self._profile.status != _REQUIRED_STATUS[tool]:
            return Observation(False, "remedy_ineligible")
        if tool in {_SHIP.name, _LOCKER.name}:
            if self._warehouse_retry:
                self._warehouse_retry = False
                return Observation(False, "warehouse_retry")
            if self._stock == 0:
                return Observation(False, "out_of_stock")
            self._stock -= 1
        if tool == "issue_refund":
            if self._profile.refund_approval and not self._approved:
                return Observation(False, "approval_required")
            self._refund = self._parcel_value
        self._remedy = tool
        return Observation(True, "remedy_posted", {"receipt_id": self._receipt})

    def verify(self) -> Verification:
        """Check the intended business outcome even if a different remedy was posted."""
        match self._profile.status:
            case "delivered":
                expected = "acknowledge_delivery"
            case "held":
                expected = "schedule_pickup"
            case _:
                if self._initial_stock:
                    expected = "locker_replacement" if self._profile.locker else "ship_replacement"
                else:
                    expected = "issue_refund"
        expected_stock = self._initial_stock - int(
            expected in {"ship_replacement", "locker_replacement"}
        )
        expected_refund = self._parcel_value if expected == "issue_refund" else 0

        failures = []
        if self._closed_with != self._receipt:
            failures.append("case_not_closed")
        if self._remedy != expected:
            failures.append("incorrect_or_missing_remedy")
        if self._stock != expected_stock:
            failures.append("incorrect_inventory")
        if self._refund != expected_refund:
            failures.append("incorrect_refund")
        if self._approved != (expected == "issue_refund" and self._profile.refund_approval):
            failures.append("incorrect_approval")
        version = "v2" if self._workflow == DELIVERY_V2 else "v1"
        return Verification(f"delivery_exception_state_{version}", not failures, tuple(failures))
