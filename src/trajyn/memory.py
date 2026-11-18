"""Only condition-specific public memory crosses the agent boundary."""

from dataclasses import dataclass

from trajyn.capability import CapabilityStep
from trajyn.models import PublicTask, Step


@dataclass(frozen=True, slots=True)
class RawMemory:
    task: PublicTask
    steps: tuple[Step, ...]


@dataclass(frozen=True, slots=True)
class SummaryStep:
    tool: str
    instruction: str


@dataclass(frozen=True, slots=True)
class SummaryMemory:
    steps: tuple[SummaryStep, ...]


@dataclass(frozen=True, slots=True)
class CapsuleMemory:
    goal: str
    steps: tuple[CapabilityStep, ...]


@dataclass(frozen=True, slots=True)
class LessonMemory:
    """Only a fixed renderer can produce this short, symbolic or live hint."""

    lesson_id: str
    hint: str


type Memory = RawMemory | SummaryMemory | CapsuleMemory | LessonMemory
