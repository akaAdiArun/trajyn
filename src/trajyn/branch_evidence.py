"""Assemble observed alternatives while retaining independently replayable evidence."""

from datetime import datetime

from trajyn.capability import CapabilityCapsule
from trajyn.induction import induce
from trajyn.models import Trajectory


def assemble_branches(
    sources: tuple[Trajectory, ...], *, created_at: datetime
) -> tuple[CapabilityCapsule, ...]:
    """Return independently induced candidates for one workflow, goal and verifier."""
    if not sources:
        raise ValueError("branch evidence requires at least one source")
    if len({source.trajectory_id for source in sources}) != len(sources):
        raise ValueError("branch evidence requires distinct trajectories")
    capsules = tuple(induce(source, created_at=created_at) for source in sources)
    reference = capsules[0]
    if any(
        (capsule.conditions, capsule.goal, capsule.verifier)
        != (reference.conditions, reference.goal, reference.verifier)
        for capsule in capsules[1:]
    ):
        raise ValueError("branch evidence requires the same workflow, goal and verifier")
    return capsules
