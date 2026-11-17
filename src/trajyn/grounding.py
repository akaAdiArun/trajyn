"""Resolve tool arguments from the current task and successful public observations."""

from dataclasses import dataclass

from trajyn.agent import AgentContext
from trajyn.models import Scalar, Step, ToolAction


@dataclass(frozen=True, slots=True)
class PublicBinding:
    parameter: str
    source_step: int


def public_identifiers(ticket_id: str, steps: tuple[Step, ...]) -> dict[str, tuple[str, int]]:
    values = {"ticket_id": (ticket_id, 0)}
    for step in steps:
        if step.observation.ok:
            values.update(
                (key, (value, step.index))
                for key, value in step.observation.data.items()
                if (key.endswith("_id") or key == "sku") and isinstance(value, str) and value
            )
    return values


def bind_public_action(
    context: AgentContext, tool_name: str
) -> tuple[ToolAction, tuple[PublicBinding, ...]]:
    available = public_identifiers(context.task.ticket_id, context.steps)
    values: dict[str, Scalar] = {}
    bindings = []
    tool = next((item for item in context.tools if item.name == tool_name), None)
    if tool is not None:
        for parameter in tool.parameters:
            if parameter.name in available:
                value, index = available[parameter.name]
                values[parameter.name] = value
                bindings.append(PublicBinding(parameter.name, index))
    return ToolAction(tool_name, values), tuple(bindings)
