"""Read recorded attempts and check their integrity against the seeded simulator."""

import json
from pathlib import Path

from trajyn.benchmark import generate_delivery_task
from trajyn.environment import generate_task
from trajyn.models import (
    AgentIdentity,
    Observation,
    Split,
    Step,
    StopReason,
    ToolAction,
    Trajectory,
    Usage,
    Verification,
)
from trajyn.recording import encode_json, trajectory_events, trajectory_id
from trajyn.runner import environment_for


def replay_trajectory(trajectory: Trajectory) -> None:
    """Reproduce observations and final state from the recorded actions."""
    if type(trajectory.max_steps) is not int or trajectory.max_steps < 1:
        raise ValueError("invalid trajectory budget")
    steps = trajectory.steps
    if len(steps) > trajectory.max_steps or (
        (trajectory.stop_reason == StopReason.STEP_LIMIT) != (len(steps) == trajectory.max_steps)
    ):
        raise ValueError("step count disagrees with budget or stop reason")
    env = environment_for(trajectory.task)
    for index, step in enumerate(steps, 1):
        if step.index != index or encode_json(env.execute(step.action)) != encode_json(
            step.observation
        ):
            raise ValueError(f"recorded observation cannot be reproduced at step {index}")
    if env.verify() != trajectory.verification:
        raise ValueError("recorded verification cannot be reproduced")
    if trajectory_id(trajectory) != trajectory.trajectory_id:
        raise ValueError("trajectory ID does not match recorded content")


def _nonnegative_int(value: object, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _duration(value: object) -> int | None:
    return None if value is None else _nonnegative_int(value, "elapsed_ns")


def read_trajectory(path: Path) -> Trajectory:
    """Load a versioned JSONL attempt and independently replay it."""
    try:
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        start, finish = events[0], events[-1]
        task_record = start["task"]
        seed = _nonnegative_int(task_record["seed"], "seed")
        split = Split(task_record["split"])
        generator = generate_delivery_task if "workflow" in task_record else generate_task
        task = generator(seed, split)
        agent = AgentIdentity(**start["agent"])
        if (
            not isinstance(agent.provider, str)
            or not agent.provider
            or not isinstance(agent.model, str)
            or not agent.model
            or (agent.version is not None and not isinstance(agent.version, str))
        ):
            raise ValueError("invalid agent identity")

        steps = []
        for index, event in enumerate(events[1:-1], 1):
            step = event["step"]
            action = ToolAction(**step["action"])
            if not isinstance(action.tool, str):
                raise ValueError("tool name must be a string")
            if any(
                type(value) not in (str, int, float, bool, type(None))
                for value in action.arguments.values()
            ):
                raise ValueError("tool arguments must be JSON scalars")
            usage = None if step["usage"] is None else Usage(**step["usage"])
            if usage is not None:
                _validate_usage(usage)
            steps.append(
                Step(
                    index,
                    action,
                    Observation(**step["observation"]),
                    usage,
                    _duration(step["elapsed_ns"]),
                )
            )
        verification = finish["verification"]
        trajectory = Trajectory(
            start["trajectory_id"],
            task,
            agent,
            _nonnegative_int(start["max_steps"], "max_steps"),
            tuple(steps),
            StopReason(finish["stop_reason"]),
            Verification(
                verification["verifier"], verification["passed"], tuple(verification["failures"])
            ),
            _duration(finish["elapsed_ns"]),
        )
        if encode_json(list(trajectory_events(trajectory))) != encode_json(events):
            raise ValueError("records do not match the trajectory schema")
        replay_trajectory(trajectory)
    except (TypeError, AttributeError, ValueError, KeyError, IndexError) as error:
        raise ValueError(f"{path}: invalid trajectory ({error})") from error
    return trajectory


def _validate_usage(usage: Usage) -> None:
    for count in (usage.input_tokens, usage.output_tokens):
        if count is not None:
            _nonnegative_int(count, "token count")
    cost = usage.estimated_cost_usd
    if cost is not None and (type(cost) not in (float, int) or cost < 0):
        raise ValueError("invalid estimated inference cost")
