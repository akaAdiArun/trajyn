"""Match capsule applicability and tool interfaces against a public task."""

from dataclasses import dataclass
from enum import StrEnum

from trajyn.agent import AgentContext
from trajyn.capability import CapabilityCapsule
from trajyn.induction import observation_guard
from trajyn.memory import CapsuleMemory
from trajyn.models import PublicTask, Scalar, ToolAction, ToolSpec


class TransferStatus(StrEnum):
    ACCEPTED = "accepted"
    INAPPLICABLE = "rejected_inapplicable"
    INCOMPATIBLE = "rejected_incompatible"


@dataclass(frozen=True, slots=True)
class TransferConsideration:
    capsule_id: str
    source_trajectory_ids: tuple[str, ...]
    status: TransferStatus
    reason: str


@dataclass(frozen=True, slots=True)
class TransferSelection:
    memory: CapsuleMemory | None
    considered: tuple[TransferConsideration, ...]


def _check(
    task: PublicTask, tools: dict[str, ToolSpec], capsule: CapabilityCapsule
) -> tuple[TransferStatus, str]:
    if any(
        condition.field != "task.workflow" or task.workflow != condition.equals
        for condition in capsule.conditions
    ):
        return TransferStatus.INAPPLICABLE, "public_condition_mismatch"
    if any(step.expect is None for step in capsule.steps):
        return TransferStatus.INCOMPATIBLE, "executable_steps_required"
    for required in capsule.required_tools:
        if required.name not in tools:
            return TransferStatus.INCOMPATIBLE, f"missing_tool:{required.name}"
        if required != tools[required.name]:
            return TransferStatus.INCOMPATIBLE, f"changed_interface:{required.name}"
    return TransferStatus.ACCEPTED, "public_conditions_and_interfaces_match"


def select_capsule(
    task: PublicTask, tools: tuple[ToolSpec, ...], candidates: tuple[CapabilityCapsule, ...]
) -> TransferSelection:
    """Consider candidates in retrieval order and accept the first compatible capsule."""
    tool_index = {tool.name: tool for tool in tools}
    considered = []
    for capsule in candidates:
        status, reason = _check(task, tool_index, capsule)
        considered.append(
            TransferConsideration(
                capsule.capability_id,
                tuple(evidence.trajectory_id for evidence in capsule.evidence),
                status,
                reason,
            )
        )
        if status == TransferStatus.ACCEPTED:
            return TransferSelection(CapsuleMemory(capsule.goal, capsule.steps), tuple(considered))
    return TransferSelection(None, tuple(considered))


def capsule_action(context: AgentContext, memory: CapsuleMemory) -> ToolAction | None:
    index = len(context.steps)
    if index >= len(memory.steps):
        return None
    for previous, expected in zip(context.steps, memory.steps[:index], strict=True):
        if previous.action.tool != expected.tool or (
            observation_guard(previous.observation) != expected.expect
        ):
            return None

    proposed = memory.steps[index]
    arguments: dict[str, Scalar] = {}
    for binding in proposed.bindings:
        if binding.source_step == 0:
            value: Scalar = context.task.ticket_id
        else:
            observation = context.steps[binding.source_step - 1].observation
            value = observation.data.get(binding.field) if observation.ok else None
        if not isinstance(value, str) or not value:
            return None
        arguments[binding.parameter] = value
    return ToolAction(proposed.tool, arguments)
