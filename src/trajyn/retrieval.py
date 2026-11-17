"""Rank archived experiences using only public target metadata."""

import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass

from trajyn.capability import CapabilityCapsule
from trajyn.models import PublicTask, Split, ToolSpec, Trajectory, public_task
from trajyn.transfer import TransferStatus, select_capsule


@dataclass(frozen=True, slots=True)
class RankedExperience:
    source_id: str
    source_seed: int
    compatibility: TransferStatus
    reason: str
    tool_coverage_bp: int
    goal_similarity_bp: int


def _tokens(task: PublicTask) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", task.goal.replace(task.ticket_id, "").lower()))


def _coverage(matches: Collection[object], required: Collection[object]) -> int:
    return len(matches) * 10_000 // max(len(required), 1)


def rank_experience(
    task: PublicTask,
    tools: tuple[ToolSpec, ...],
    sources: tuple[Trajectory, ...],
    capsules: Mapping[str, CapabilityCapsule],
) -> tuple[RankedExperience, ...]:
    public_tokens = _tokens(task)
    interfaces = set(tools)
    ranks = []
    for source in sources:
        original = public_task(source.task)
        capsule = capsules.get(source.trajectory_id)
        if not source.verification.passed or source.task.split != Split.TRAIN or capsule is None:
            continue
        if original.workflow != task.workflow:
            continue
        required = set(capsule.required_tools)
        previous_tokens = _tokens(original)
        (check,) = select_capsule(task, tools, (capsule,)).considered
        ranks.append(
            RankedExperience(
                source.trajectory_id,
                source.task.seed,
                check.status,
                check.reason,
                _coverage(required & interfaces, required),
                _coverage(public_tokens & previous_tokens, public_tokens | previous_tokens),
            )
        )
    return tuple(
        sorted(
            ranks,
            key=lambda candidate: (
                candidate.compatibility != TransferStatus.ACCEPTED,
                -candidate.tool_coverage_bp,
                -candidate.goal_similarity_bp,
                candidate.source_seed,
                candidate.source_id,
            ),
        )
    )
