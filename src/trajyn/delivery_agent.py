"""Deterministic delivery fixture policy built from public observations."""

from trajyn.agent import AgentContext
from trajyn.benchmark import RECOVERY_CODES
from trajyn.models import AgentDecision, AgentIdentity, Scalar, ToolAction


def observed(context: AgentContext, field: str) -> Scalar:
    if field == "ticket_id":
        return context.task.ticket_id
    for step in reversed(context.steps):
        if step.observation.ok and field in step.observation.data:
            return step.observation.data[field]
    return None


def action_from_observations(context: AgentContext, tool_name: str) -> ToolAction | None:
    for tool in context.tools:
        if tool.name != tool_name:
            continue
        arguments: dict[str, Scalar] = {}
        for parameter in tool.parameters:
            value = observed(context, parameter.name)
            if not isinstance(value, str) or not value:
                return None
            arguments[parameter.name] = value
        return ToolAction(tool_name, arguments)
    return None


class DeliveryReferenceAgent:
    """Rules-based source fixture for the delivery benchmark."""

    identity = AgentIdentity("offline", "delivery-reference", "1")

    def decide(self, context: AgentContext) -> AgentDecision | None:
        if context.steps:
            latest = context.steps[-1].observation
            if latest.code == "case_closed" or (
                not latest.ok and latest.code not in RECOVERY_CODES
            ):
                return None

        if observed(context, "receipt_id"):
            tool = "close_case"
        elif not observed(context, "parcel_id"):
            tool = "read_case"
        else:
            match observed(context, "status"):
                case None:
                    tool = "inspect_parcel"
                case "delivered":
                    tool = "acknowledge_delivery"
                case "held":
                    tool = "schedule_pickup"
                case "lost":
                    tool = self._lost_tool(context)
                case _:
                    return None

        action = action_from_observations(context, tool)
        return AgentDecision(action) if action is not None else None

    def _lost_tool(self, context: AgentContext) -> str:
        available = observed(context, "available")
        if available is None:
            return "get_stock"
        if available is False or context.steps[-1].observation.code == "out_of_stock":
            return "issue_refund"
        if any(tool.name == "locker_replacement" for tool in context.tools):
            return "locker_replacement"
        return "ship_replacement"
