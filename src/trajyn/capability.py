"""Portable capability schema for future induction and transfer experiments."""

from dataclasses import dataclass
from datetime import datetime

from trajyn.models import Scalar, ToolSpec


@dataclass(frozen=True, slots=True)
class ApplicabilityCondition:
    """A required value at a named observation or task field."""

    field: str
    equals: Scalar


@dataclass(frozen=True, slots=True)
class CapabilityStep:
    tool: str
    instruction: str


@dataclass(frozen=True, slots=True)
class TrajectoryEvidence:
    trajectory_id: str
    step_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.trajectory_id or not self.step_indices:
            raise ValueError("evidence requires a trajectory ID and at least one step")
        if any(index < 1 for index in self.step_indices):
            raise ValueError("evidence step indices start at 1")


@dataclass(frozen=True, slots=True)
class CapabilityCapsule:
    capability_id: str
    version: int
    goal: str
    conditions: tuple[ApplicabilityCondition, ...]
    required_tools: tuple[ToolSpec, ...]
    steps: tuple[CapabilityStep, ...]
    verifier: str
    evidence: tuple[TrajectoryEvidence, ...]
    limitations: tuple[str, ...]
    created_at: datetime
    confidence: float | None = None

    def __post_init__(self) -> None:
        if not self.capability_id or self.version < 1 or not self.goal or not self.verifier:
            raise ValueError("a capsule requires an ID, positive version, goal, and verifier")
        if not self.steps or not self.evidence:
            raise ValueError("a capsule requires steps and trajectory evidence")
        if self.created_at.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        tool_names = {tool.name for tool in self.required_tools}
        if any(step.tool not in tool_names for step in self.steps):
            raise ValueError("each step must use a declared tool")
