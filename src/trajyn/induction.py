"""Induce a guarded procedure from a verified training execution."""

from datetime import datetime
from hashlib import sha256

from trajyn.benchmark import RECOVERY_CODES
from trajyn.capability import (
    ApplicabilityCondition,
    ArgumentBinding,
    CapabilityCapsule,
    CapabilityStep,
    ObservationGuard,
    TrajectoryEvidence,
)
from trajyn.models import Observation, PublicTask, Split, Step, Trajectory, public_task
from trajyn.provenance import replay_trajectory
from trajyn.runner import environment_for


def observation_guard(observation: Observation) -> ObservationGuard:
    """Retain branch-relevant facts without retaining opaque instance identifiers."""
    facts = []
    if (status := observation.data.get("status")) is not None:
        facts.append(ApplicabilityCondition("status", status))
    stock = observation.data.get("available")
    if isinstance(stock, int):
        facts.append(ApplicabilityCondition("stock_positive", stock > 0))
    return ObservationGuard(observation.code, tuple(facts))


def _bindings(
    step: Step, earlier: tuple[Step, ...], task: PublicTask
) -> tuple[ArgumentBinding, ...]:
    bindings = []
    for parameter, value in sorted(step.action.arguments.items()):
        if parameter == "ticket_id" and value == task.ticket_id:
            bindings.append(ArgumentBinding(parameter, 0, "ticket_id"))
            continue
        for source in reversed(earlier):
            if source.observation.ok and source.observation.data.get(parameter) == value:
                bindings.append(ArgumentBinding(parameter, source.index, parameter))
                break
        else:
            raise ValueError(f"no observed source for {parameter} at step {step.index}")
    return tuple(bindings)


def induce(trajectory: Trajectory, *, created_at: datetime) -> CapabilityCapsule:
    if trajectory.task.split != Split.TRAIN:
        raise ValueError("induction requires a training trajectory")
    replay_trajectory(trajectory)
    if not trajectory.verification.passed:
        raise ValueError("induction requires a verified successful trajectory")

    task = public_task(trajectory.task)
    tools = {tool.name: tool for tool in environment_for(trajectory.task).tools}
    procedure = []
    for step in trajectory.steps:
        tool = tools.get(step.action.tool)
        if tool is None or (
            not step.observation.ok and step.observation.code not in RECOVERY_CODES
        ):
            raise ValueError(f"unsupported outcome at step {step.index}")
        bindings = _bindings(step, trajectory.steps[: step.index - 1], task)
        procedure.append(
            CapabilityStep(
                tool.name, tool.description, bindings, observation_guard(step.observation)
            )
        )

    digest = sha256(f"trajyn/capsule/1/{trajectory.trajectory_id}".encode()).hexdigest()
    return CapabilityCapsule(
        capability_id=f"capsule:{digest}",
        version=1,
        goal=task.goal.replace(task.ticket_id, "{ticket_id}"),
        conditions=(ApplicabilityCondition("task.workflow", task.workflow),),
        required_tools=tuple(
            tools[name] for name in dict.fromkeys(step.tool for step in procedure)
        ),
        steps=tuple(procedure),
        verifier=trajectory.verification.verifier,
        evidence=(
            TrajectoryEvidence(
                trajectory.trajectory_id, tuple(step.index for step in trajectory.steps)
            ),
        ),
        limitations=("One observed branch. Alternative routes require independent task handling.",),
        created_at=created_at,
        subtask="Use observed identifiers to execute and close a support workflow.",
        failure_conditions=(
            "A required tool or parameter differs from the source interface.",
            "A public observation diverges from the observed branch.",
            "A required identifier is absent from its bound observation.",
        ),
    )
