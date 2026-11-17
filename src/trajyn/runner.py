"""Execute one bounded agent attempt against a fresh seeded environment."""

from dataclasses import replace
from time import perf_counter_ns

from trajyn.agent import Agent, AgentContext
from trajyn.benchmark import DeliveryEnvironment
from trajyn.environment import ReplacementEnvironment
from trajyn.memory import Memory
from trajyn.models import DeliveryTask, Step, StopReason, Task, Trajectory, public_task
from trajyn.recording import trajectory_id


def environment_for(task: Task) -> DeliveryEnvironment | ReplacementEnvironment:
    if isinstance(task, DeliveryTask):
        return DeliveryEnvironment(task)
    return ReplacementEnvironment(task)


def run_task(
    task: Task,
    agent: Agent,
    *,
    max_steps: int = 8,
    measure_time: bool = False,
    memory: Memory | None = None,
) -> Trajectory:
    if max_steps < 1:
        raise ValueError("max_steps must be positive")

    environment = environment_for(task)
    public = public_task(task)
    identity = agent.identity
    steps: list[Step] = []
    stop_reason = StopReason.STEP_LIMIT
    started_ns = perf_counter_ns() if measure_time else None
    for index in range(1, max_steps + 1):
        step_started_ns = perf_counter_ns() if measure_time else None
        decision = agent.decide(
            AgentContext(public, environment.tools, tuple(steps), max_steps, memory)
        )
        if decision is None:
            stop_reason = StopReason.AGENT_STOPPED
            break
        observation = environment.execute(decision.action)
        steps.append(
            Step(
                index,
                decision.action,
                observation,
                decision.usage,
                perf_counter_ns() - step_started_ns if step_started_ns is not None else None,
            )
        )

    verification = environment.verify()
    trajectory = Trajectory(
        trajectory_id="",
        task=task,
        agent=identity,
        max_steps=max_steps,
        steps=tuple(steps),
        stop_reason=stop_reason,
        verification=verification,
        elapsed_ns=perf_counter_ns() - started_ns if started_ns is not None else None,
    )
    return replace(trajectory, trajectory_id=trajectory_id(trajectory))
