"""Public task, action, and trajectory records shared by agents and the runtime."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

type Scalar = str | int | float | bool | None


class Split(StrEnum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    seed: int
    split: Split
    ticket_id: str
    goal: str


@dataclass(frozen=True, slots=True)
class ToolParameter:
    """A required string argument."""

    name: str
    description: str


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: tuple[ToolParameter, ...]


@dataclass(frozen=True, slots=True)
class ToolAction:
    tool: str
    arguments: Mapping[str, Scalar] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "arguments", MappingProxyType(dict(self.arguments)))


@dataclass(frozen=True, slots=True)
class Observation:
    ok: bool
    code: str
    data: Mapping[str, Scalar] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", MappingProxyType(dict(self.data)))


@dataclass(frozen=True, slots=True)
class AgentIdentity:
    provider: str
    model: str
    version: str | None = None


@dataclass(frozen=True, slots=True)
class Usage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None


@dataclass(frozen=True, slots=True)
class AgentDecision:
    action: ToolAction
    usage: Usage | None = None


@dataclass(frozen=True, slots=True)
class Step:
    index: int
    action: ToolAction
    observation: Observation
    usage: Usage | None = None
    elapsed_ns: int | None = None


@dataclass(frozen=True, slots=True)
class Verification:
    verifier: str
    passed: bool
    failures: tuple[str, ...]


class StopReason(StrEnum):
    AGENT_STOPPED = "agent_stopped"
    STEP_LIMIT = "step_limit"


@dataclass(frozen=True, slots=True)
class Trajectory:
    trajectory_id: str
    task: Task
    agent: AgentIdentity
    max_steps: int
    steps: tuple[Step, ...]
    stop_reason: StopReason
    verification: Verification
    elapsed_ns: int | None = None
