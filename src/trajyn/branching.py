"""Observation-gated capsule delivery with an auditable per-attempt lifecycle."""

from dataclasses import dataclass
from enum import StrEnum

from trajyn.agent import AgentContext
from trajyn.capability import CapabilityCapsule
from trajyn.induction import observation_guard
from trajyn.memory import CapsuleMemory
from trajyn.models import PublicTask, Step, ToolSpec
from trajyn.transfer import TransferConsideration, TransferStatus, capsule_action, select_capsule


class BranchState(StrEnum):
    CANDIDATE = "candidate"
    COMPATIBLE = "compatible"
    CONDITIONAL = "conditionally_applicable"
    ACTIVE = "active"
    DIVERGED = "diverged"
    WITHDRAWN = "withdrawn"
    ABSTAINED = "abstained"
    INCOMPATIBLE = "rejected_incompatible"
    INAPPLICABLE = "rejected_inapplicable"
    COMPLETE = "completed"
    ENDED = "attempt_ended"


@dataclass(frozen=True, slots=True)
class Transition:
    state: BranchState
    after_step: int
    reason: str
    capsule_id: str | None = None


@dataclass(frozen=True, slots=True)
class BranchCandidate:
    capsule_id: str
    memory: CapsuleMemory
    anchor: int


def _mismatch(candidate: BranchCandidate, steps: tuple[Step, ...]) -> str | None:
    for observed, expected in zip(steps, candidate.memory.steps, strict=False):
        if observed.action.tool != expected.tool:
            return "public_operation_diverged"
        if observation_guard(observed.observation) != expected.expect:
            return "public_observation_diverged"
    return None


class BranchTransfer:
    """Wait for recorded branch evidence, then withdraw on any public divergence."""

    def __init__(
        self,
        task: PublicTask,
        tools: tuple[ToolSpec, ...],
        capsules: tuple[CapabilityCapsule, ...],
    ) -> None:
        self.considerations: list[TransferConsideration] = []
        self.transitions: list[Transition] = []
        self.prompt_steps: list[int] = []
        self._candidates: list[BranchCandidate] = []
        self._active: BranchCandidate | None = None
        self._transition(BranchState.CANDIDATE, 0, "retrieved_public_candidates")
        compatible = False
        for capsule in capsules:
            selection = select_capsule(task, tools, (capsule,))
            self.considerations.extend(selection.considered)
            if selection.memory is None:
                continue
            compatible = True
            anchor = next(
                (
                    index
                    for index, step in enumerate(capsule.steps, 1)
                    if step.expect is not None and step.expect.facts
                ),
                None,
            )
            if anchor is not None:
                self._candidates.append(
                    BranchCandidate(capsule.capability_id, selection.memory, anchor)
                )
        if compatible:
            self._transition(BranchState.COMPATIBLE, 0, "public_conditions_and_interfaces_match")
            if self._candidates:
                self._transition(BranchState.CONDITIONAL, 0, "awaiting_observed_branch_facts")
            else:
                self._transition(BranchState.ABSTAINED, 0, "no_branch_facts_in_source")
        elif not self.considerations:
            self._transition(BranchState.ABSTAINED, 0, "no_candidates")
        else:
            check = next(
                (
                    item
                    for item in self.considerations
                    if item.status == TransferStatus.INCOMPATIBLE
                ),
                self.considerations[0],
            )
            self._transition(BranchState(check.status.value), 0, check.reason, check.capsule_id)

    @property
    def state(self) -> BranchState:
        return self.transitions[-1].state

    def _transition(
        self, state: BranchState, after: int, reason: str, capsule_id: str | None = None
    ) -> None:
        self.transitions.append(Transition(state, after, reason, capsule_id))

    def _advance(self, context: AgentContext) -> None:
        count = len(context.steps)
        if self.state == BranchState.ACTIVE:
            assert self._active is not None
            active = self._active
            reason = _mismatch(active, context.steps)
            if reason is None and count >= len(active.memory.steps):
                self._transition(
                    BranchState.COMPLETE, count, "matched_recorded_procedure", active.capsule_id
                )
                return
            if reason is None and capsule_action(context, active.memory) is None:
                reason = "missing_public_prerequisite"
            if reason:
                self._transition(BranchState.DIVERGED, count, reason, active.capsule_id)
                self._transition(BranchState.WITHDRAWN, count, "remove_guidance", active.capsule_id)
            return

        if self.state != BranchState.CONDITIONAL:
            return
        matches = [
            candidate
            for candidate in self._candidates
            if _mismatch(candidate, context.steps) is None
        ]
        if not matches:
            reason = _mismatch(self._candidates[0], context.steps)
            assert reason is not None
            self._transition(BranchState.ABSTAINED, count, reason)
            return
        if any(count < candidate.anchor for candidate in matches):
            return
        # Distinct compatible branches may share the observed prefix. Wait for
        # evidence to distinguish them instead of guessing which history applies.
        selected = matches[0]
        if any(candidate.memory != selected.memory for candidate in matches[1:]):
            return
        if count >= len(selected.memory.steps):
            self._transition(BranchState.ABSTAINED, count, "procedure_already_observed")
        elif capsule_action(context, selected.memory) is None:
            self._transition(BranchState.ABSTAINED, count, "missing_public_prerequisite")
        else:
            self._active = selected
            self._transition(
                BranchState.ACTIVE, count, "matched_observed_branch_facts", selected.capsule_id
            )

    def memory_for(self, context: AgentContext) -> CapsuleMemory | None:
        self._advance(context)
        if self.state == BranchState.ACTIVE:
            assert self._active is not None
            self.prompt_steps.append(len(context.steps))
            return self._active.memory
        return None

    def finish(self, context: AgentContext) -> None:
        if self.state == BranchState.CONDITIONAL:
            if all(_mismatch(candidate, context.steps) for candidate in self._candidates):
                self._advance(context)
            else:
                self._transition(
                    BranchState.ABSTAINED,
                    len(context.steps),
                    "run_ended_without_applicable_guidance",
                )
        elif self.state == BranchState.ACTIVE:
            self._advance(context)
        if self.state == BranchState.ACTIVE:
            self._transition(
                BranchState.ENDED, len(context.steps), "attempt_ended_before_procedure"
            )
