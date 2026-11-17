"""Fixture target and baselines for testing condition delivery and fallback."""

from trajyn.agent import AgentContext
from trajyn.delivery_agent import DeliveryReferenceAgent, action_from_observations
from trajyn.induction import observation_guard
from trajyn.memory import CapsuleMemory, RawMemory, SummaryMemory, SummaryStep
from trajyn.models import AgentDecision, AgentIdentity, ToolAction, Trajectory, public_task
from trajyn.transfer import capsule_action


def as_raw_memory(source: Trajectory) -> RawMemory:
    return RawMemory(public_task(source.task), source.steps)


def summarize(source: Trajectory) -> SummaryMemory:
    """Summarize the sequence with argument roles only."""
    return SummaryMemory(
        tuple(
            SummaryStep(
                step.action.tool,
                "Use the current task or earlier observations for "
                + ", ".join(sorted(step.action.arguments))
                + ".",
            )
            for step in source.steps
        )
    )


class DeliveryTargetAgent(DeliveryReferenceAgent):
    """Adopt suggestions while the visible history supports them; fall back on divergence."""

    identity = AgentIdentity("offline", "delivery-target", "1")

    def __init__(self) -> None:
        self.memory_used = False
        self._abandoned = False

    def decide(self, context: AgentContext) -> AgentDecision | None:
        if context.memory is not None and not self._abandoned:
            suggestion = self._suggest(context)
            if suggestion is not None:
                self.memory_used = True
                return AgentDecision(suggestion)
            self._abandoned = True
        return super().decide(context)

    def _suggest(self, context: AgentContext) -> ToolAction | None:
        memory = context.memory
        index = len(context.steps)
        if isinstance(memory, CapsuleMemory):
            return capsule_action(context, memory)
        if memory is None or index >= len(memory.steps):
            return None

        if isinstance(memory, RawMemory):
            for live, observed in zip(context.steps, memory.steps[:index], strict=True):
                if live.action.tool != observed.action.tool or (
                    observation_guard(live.observation) != observation_guard(observed.observation)
                ):
                    return None
            name = memory.steps[index].action.tool
        else:
            if any(not step.observation.ok for step in context.steps):
                return None
            name = memory.steps[index].tool
        return action_from_observations(context, name)
