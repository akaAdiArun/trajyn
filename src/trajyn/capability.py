"""Versioned, portable capability schemas."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from trajyn.models import Scalar, ToolParameter, ToolSpec
from trajyn.recording import encode_json


@dataclass(frozen=True, slots=True)
class ApplicabilityCondition:
    """A required value at a named observation or task field."""

    field: str
    equals: Scalar

    def __post_init__(self) -> None:
        if not isinstance(self.field, str) or not self.field:
            raise ValueError("condition field must be a non-empty string")
        if type(self.equals) not in (str, bool, int, float, type(None)):
            raise ValueError("conditions compare against JSON scalars")


@dataclass(frozen=True, slots=True)
class ArgumentBinding:
    parameter: str
    source_step: int
    field: str


@dataclass(frozen=True, slots=True)
class ObservationGuard:
    code: str
    facts: tuple[ApplicabilityCondition, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code:
            raise ValueError("observation guard requires a result code")


@dataclass(frozen=True, slots=True)
class CapabilityStep:
    tool: str
    instruction: str
    bindings: tuple[ArgumentBinding, ...] = ()
    expect: ObservationGuard | None = None


@dataclass(frozen=True, slots=True)
class TrajectoryEvidence:
    trajectory_id: str
    step_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.trajectory_id, str)
            or not self.trajectory_id
            or not self.step_indices
        ):
            raise ValueError("evidence requires a trajectory ID and at least one step")
        if any(type(index) is not int or index < 1 for index in self.step_indices):
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
    schema_version: int = 1
    subtask: str = ""
    failure_conditions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            not self.capability_id
            or type(self.version) is not int
            or self.version < 1
            or not self.goal
            or not self.verifier
        ):
            raise ValueError("a capsule requires an ID, positive version, goal, and verifier")
        if not self.steps or not self.evidence:
            raise ValueError("a capsule requires steps and trajectory evidence")
        if self.created_at.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        if self.confidence is not None and (
            type(self.confidence) not in (float, int) or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("unsupported capability schema version")
        tools = {tool.name: tool for tool in self.required_tools}
        if len(tools) != len(self.required_tools):
            raise ValueError("each tool must be declared once")
        for index, step in enumerate(self.steps, 1):
            if step.tool not in tools:
                raise ValueError("each step must use a declared tool")
            if step.expect is None:
                if step.bindings:
                    raise ValueError("each executable step needs an observation guard")
                continue
            expected = {parameter.name for parameter in tools[step.tool].parameters}
            actual = {binding.parameter for binding in step.bindings}
            if actual != expected or len(actual) != len(step.bindings):
                raise ValueError("each tool parameter must have exactly one binding")
            for binding in step.bindings:
                if type(binding.source_step) is not int or not 0 <= binding.source_step < index:
                    raise ValueError("bindings may refer only to the task or earlier steps")
                if binding.source_step == 0 and binding.field != "ticket_id":
                    raise ValueError("the only supported task binding is ticket_id")
                if binding.field != binding.parameter:
                    raise ValueError("bindings require a like-named observation field")


def _decode_capsule(record: object) -> CapabilityCapsule:
    if not isinstance(record, dict):
        raise ValueError("capsule must be a JSON object")
    try:
        steps = []
        for step in record["steps"]:
            guard = step["expect"]
            expectation = (
                None
                if guard is None
                else ObservationGuard(
                    guard["code"], tuple(ApplicabilityCondition(**fact) for fact in guard["facts"])
                )
            )
            steps.append(
                CapabilityStep(
                    step["tool"],
                    step["instruction"],
                    tuple(ArgumentBinding(**binding) for binding in step["bindings"]),
                    expectation,
                )
            )
        tools = tuple(
            ToolSpec(
                tool["name"],
                tool["description"],
                tuple(ToolParameter(**parameter) for parameter in tool["parameters"]),
            )
            for tool in record["required_tools"]
        )
        evidence = tuple(
            TrajectoryEvidence(item["trajectory_id"], tuple(item["step_indices"]))
            for item in record["evidence"]
        )
        capsule = CapabilityCapsule(
            **{
                **record,
                "steps": tuple(steps),
                "required_tools": tools,
                "evidence": evidence,
                "conditions": tuple(
                    ApplicabilityCondition(**item) for item in record["conditions"]
                ),
                "limitations": tuple(record["limitations"]),
                "failure_conditions": tuple(record["failure_conditions"]),
                "created_at": datetime.fromisoformat(record["created_at"]),
            }
        )
        if encode_json(capsule) != encode_json(record):
            raise ValueError("record does not match the capsule schema")
    except (TypeError, ValueError, KeyError, AttributeError) as error:
        raise ValueError(f"invalid capsule ({error})") from error
    return capsule


def read_capsule(path: Path) -> CapabilityCapsule:
    return _decode_capsule(json.loads(path.read_text(encoding="utf-8")))


def read_capsules(path: Path) -> tuple[CapabilityCapsule, ...]:
    return tuple(
        _decode_capsule(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines()
    )
