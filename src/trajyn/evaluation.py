"""Paired, held-out evaluation using independently fresh environment state."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from trajyn.agent import Agent, AgentContext, OfflineReferenceAgent
from trajyn.benchmark import DELIVERY_V1, DELIVERY_V2, RECOVERY_CODES, generate_delivery_task
from trajyn.branching import BranchState, BranchTransfer, Transition
from trajyn.capability import CapabilityCapsule
from trajyn.delivery_agent import DeliveryReferenceAgent
from trajyn.environment import generate_task
from trajyn.induction import induce
from trajyn.memory import Memory
from trajyn.models import AgentIdentity, Split, Task, Trajectory, Usage, public_task
from trajyn.provenance import read_trajectory, replay_trajectory
from trajyn.recording import encode_json, write_jsonl, write_trajectory
from trajyn.retrieval import rank_experience
from trajyn.runner import environment_for, run_task
from trajyn.target import DeliveryTargetAgent, as_raw_memory, summarize
from trajyn.transfer import TransferConsideration, select_capsule

TRAIN_SEEDS = tuple(range(8))
VALIDATION_SEEDS = tuple(range(100, 106))
TEST_SEEDS = tuple(range(200, 208))
MAX_STEPS = 8


class Condition(StrEnum):
    NO_MEMORY = "A"
    RAW = "B"
    SUMMARY = "C"
    CAPSULE = "D"
    CONTROL = "E"
    DYNAMIC = "F"


BASE_CONDITIONS = tuple(condition for condition in Condition if condition != Condition.DYNAMIC)


@dataclass(frozen=True, slots=True)
class EvaluationPlan:
    seeds: tuple[int, ...] = TEST_SEEDS
    split: Split = Split.TEST
    max_steps: int = MAX_STEPS
    measure_time: bool = True

    def __post_init__(self) -> None:
        validate_seeds(self.seeds)
        if self.split not in (Split.VALIDATION, Split.TEST):
            raise ValueError("evaluation requires a held-out validation or test split")
        if type(self.max_steps) is not int or self.max_steps < 1:
            raise ValueError("max_steps must be positive")
        if type(self.measure_time) is not bool:
            raise ValueError("measure_time must be Boolean")


@dataclass(frozen=True, slots=True)
class SourceRecord:
    task_id: str
    seed: int
    split: Split
    agent: AgentIdentity
    max_steps: int
    trajectory_id: str
    passed: bool


@dataclass(frozen=True, slots=True)
class Trial:
    task_id: str
    seed: int
    split: Split
    condition: Condition
    agent: AgentIdentity
    max_steps: int
    trajectory_id: str
    trajectory_file: str
    stop_reason: str
    passed: bool
    completed: bool
    action_count: int
    invalid_calls: int
    tool_failures: int
    recovery_episodes: int
    failures: tuple[str, ...]
    elapsed_ns: int | None
    usage: Usage
    source_trajectory_id: str | None
    memory_delivered: bool
    memory_used: bool | None
    transfer: TransferConsideration | None


@dataclass(frozen=True, slots=True)
class Evaluation:
    plan: EvaluationPlan
    sources: tuple[SourceRecord, ...]
    control_source: SourceRecord
    trials: tuple[Trial, ...]
    schema_version: int = 1

    @property
    def conditions(self) -> tuple[Condition, ...]:
        return (
            tuple(Condition)
            if any(row.condition == Condition.DYNAMIC for row in self.trials)
            else BASE_CONDITIONS
        )


@dataclass(frozen=True, slots=True)
class TransferAudit:
    seed: int
    condition: Condition
    capsule_id: str
    transitions: tuple[Transition, ...]
    delivered_after_steps: tuple[int, ...]
    continued_after_divergence: int


def validate_seeds(seeds: tuple[int, ...]) -> None:
    if not seeds or any(type(seed) is not int or seed < 0 for seed in seeds):
        raise ValueError("seeds must be non-negative integers")
    if len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be distinct")


def _source_record(source: Trajectory) -> SourceRecord:
    return SourceRecord(
        source.task.task_id,
        source.task.seed,
        source.task.split,
        source.agent,
        source.max_steps,
        source.trajectory_id,
        source.verification.passed,
    )


def collect_sources(
    output: Path,
    seeds: tuple[int, ...] = TRAIN_SEEDS,
    *,
    agent_factory: Callable[[], Agent] = DeliveryReferenceAgent,
    max_steps: int = MAX_STEPS,
    measure_time: bool = False,
    workflow: str = DELIVERY_V1,
) -> tuple[Trajectory, ...]:
    validate_seeds(seeds)
    sources = tuple(
        run_task(
            generate_delivery_task(seed, workflow=workflow),
            agent_factory(),
            max_steps=max_steps,
            measure_time=measure_time,
        )
        for seed in seeds
    )
    for source in sources:
        write_trajectory(output / f"source-{source.task.seed}.jsonl", source)
    write_jsonl(
        output / "manifest.json",
        [{"schema_version": 1, "sources": [_source_record(source) for source in sources]}],
    )
    return sources


def read_sources(directory: Path) -> tuple[Trajectory, ...]:
    if directory.is_file():
        return (read_trajectory(directory),)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    try:
        if manifest["schema_version"] != 1:
            raise ValueError("unsupported source manifest schema")
        entries = manifest["sources"]
        seeds = tuple(record["seed"] for record in entries)
        validate_seeds(seeds)
        sources = tuple(read_trajectory(directory / f"source-{seed}.jsonl") for seed in seeds)
        if encode_json([_source_record(source) for source in sources]) != encode_json(entries):
            raise ValueError("trajectories disagree with source manifest")
        return sources
    except (TypeError, KeyError) as error:
        raise ValueError(f"{directory}: invalid source manifest ({error})") from error


def induce_sources(
    sources: tuple[Trajectory, ...], *, created_at: datetime
) -> tuple[CapabilityCapsule, ...]:
    capsules = tuple(
        induce(source, created_at=created_at) for source in sources if source.verification.passed
    )
    if not capsules:
        raise ValueError("no verified successful source trajectories")
    return capsules


def _validate_sources(
    sources: tuple[Trajectory, ...],
    capsules: tuple[CapabilityCapsule, ...],
) -> dict[str, CapabilityCapsule]:
    validate_seeds(tuple(source.task.seed for source in sources))
    workflow = public_task(sources[0].task).workflow
    for source in sources:
        replay_trajectory(source)
        if (
            source.task.split != Split.TRAIN
            or workflow not in (DELIVERY_V1, DELIVERY_V2)
            or public_task(source.task).workflow != workflow
        ):
            raise ValueError("evaluation retrieval requires delivery training trajectories")
    capsule_by_source = {}
    for capsule in capsules:
        if len(capsule.evidence) != 1:
            raise ValueError("evaluation requires single-trajectory evidence per capsule")
        source_id = capsule.evidence[0].trajectory_id
        if source_id in capsule_by_source:
            raise ValueError("duplicate capsule for source trajectory")
        capsule_by_source[source_id] = capsule
    passed_ids = {source.trajectory_id for source in sources if source.verification.passed}
    if not passed_ids or capsule_by_source.keys() != passed_ids:
        raise ValueError("capsules must cover exactly the verified successful source trajectories")
    for source in sources:
        if source.verification.passed:
            capsule = capsule_by_source[source.trajectory_id]
            if capsule != induce(source, created_at=capsule.created_at):
                raise ValueError("capsule cannot be reproduced from source evidence")
    return capsule_by_source


def _memory(
    condition: Condition,
    task: Task,
    source: Trajectory,
    capsule: CapabilityCapsule,
    control: Trajectory,
) -> tuple[Memory | None, str | None, TransferConsideration | None]:
    match condition:
        case Condition.RAW:
            return as_raw_memory(source), source.trajectory_id, None
        case Condition.SUMMARY:
            return summarize(source), source.trajectory_id, None
        case Condition.CAPSULE | Condition.DYNAMIC:
            selection = select_capsule(public_task(task), environment_for(task).tools, (capsule,))
            memory = selection.memory if condition == Condition.CAPSULE else None
            return memory, source.trajectory_id, selection.considered[0]
        case Condition.CONTROL:
            return as_raw_memory(control), control.trajectory_id, None
        case Condition.NO_MEMORY:
            return None, None, None


def _usage(trajectory: Trajectory) -> Usage:
    readings = [step.usage for step in trajectory.steps if step.usage is not None]
    inputs = [usage.input_tokens for usage in readings if usage.input_tokens is not None]
    outputs = [usage.output_tokens for usage in readings if usage.output_tokens is not None]
    costs = [usage.estimated_cost_usd for usage in readings if usage.estimated_cost_usd is not None]
    return Usage(
        sum(inputs) if inputs else None,
        sum(outputs) if outputs else None,
        sum(costs) if costs else None,
    )


def _trial(
    trajectory: Trajectory,
    *,
    condition: Condition,
    relative_path: str,
    source_id: str | None,
    memory_delivered: bool,
    memory_used: bool | None,
    transfer: TransferConsideration | None,
) -> Trial:
    observations = [step.observation for step in trajectory.steps]
    failures = [obs for obs in observations if not obs.ok]
    recovered = sum(
        not previous.ok and following.ok
        for previous, following in zip(observations, observations[1:], strict=False)
    )
    task = trajectory.task
    return Trial(
        task.task_id,
        task.seed,
        task.split,
        condition,
        trajectory.agent,
        trajectory.max_steps,
        trajectory.trajectory_id,
        relative_path,
        trajectory.stop_reason,
        trajectory.verification.passed,
        "case_not_closed" not in trajectory.verification.failures,
        len(trajectory.steps),
        sum(obs.code not in RECOVERY_CODES for obs in failures),
        len(failures),
        recovered,
        trajectory.verification.failures,
        trajectory.elapsed_ns,
        _usage(trajectory),
        source_id,
        memory_delivered,
        memory_used,
        transfer,
    )


def evaluate(
    sources: tuple[Trajectory, ...],
    capsules: tuple[CapabilityCapsule, ...],
    output: Path,
    *,
    plan: EvaluationPlan = EvaluationPlan(),
    target_factory: Callable[[], Agent] = DeliveryTargetAgent,
    branch_aware: bool = False,
) -> Evaluation:
    capsule_by_source = _validate_sources(sources, capsules)
    if set(plan.seeds) & {source.task.seed for source in sources}:
        raise ValueError("target seeds must be disjoint from training seeds")

    by_id = {source.trajectory_id: source for source in sources}
    control = run_task(generate_task(42), OfflineReferenceAgent())
    write_trajectory(output / "negative-control.jsonl", control)

    trials: list[Trial] = []
    retrieval = []
    conditions = tuple(Condition) if branch_aware else BASE_CONDITIONS
    audits: list[TransferAudit] = []
    for index, seed in enumerate(plan.seeds):
        task = generate_delivery_task(
            seed, plan.split, workflow=public_task(sources[0].task).workflow
        )
        ranking = rank_experience(
            public_task(task), environment_for(task).tools, sources, capsule_by_source
        )
        if not ranking:
            raise ValueError("no verified source matches the public target workflow")
        source = by_id[ranking[0].source_id]
        capsule = capsule_by_source[source.trajectory_id]
        offset = index % len(conditions)
        order = conditions[offset:] + conditions[:offset]
        retrieval.append(
            {
                "task_id": task.task_id,
                "seed": seed,
                "selected_source_id": source.trajectory_id,
                "order": order,
                "candidates": ranking,
            }
        )
        for condition in order:
            memory, source_id, transfer = _memory(condition, task, source, capsule, control)
            agent = target_factory()
            policy = (
                BranchTransfer(public_task(task), environment_for(task).tools, (capsule,))
                if branch_aware and condition in (Condition.CAPSULE, Condition.DYNAMIC)
                else None
            )
            trajectory = run_task(
                task,
                agent,
                max_steps=plan.max_steps,
                measure_time=plan.measure_time,
                memory=memory,
                memory_policy=policy if condition == Condition.DYNAMIC else None,
            )
            delivered = memory is not None
            if policy is not None:
                audits.append(_transfer_audit(condition, capsule, trajectory, policy, delivered))
                if condition == Condition.DYNAMIC:
                    delivered = bool(policy.prompt_steps)
            if trials and trajectory.agent != trials[0].agent:
                raise ValueError("all conditions must use the same target agent identity")
            relative_path = f"trajectories/{seed}-{condition.value}.jsonl"
            write_trajectory(output / relative_path, trajectory)
            used = agent.memory_used if isinstance(agent, DeliveryTargetAgent) else None
            trials.append(
                _trial(
                    trajectory,
                    condition=condition,
                    relative_path=relative_path,
                    source_id=source_id,
                    memory_delivered=delivered,
                    memory_used=used,
                    transfer=transfer,
                )
            )
    write_jsonl(output / "retrieval.json", [{"policy_version": 1, "targets": retrieval}])
    if branch_aware:
        write_jsonl(output / "transfer.json", [{"schema_version": 1, "trials": audits}])
    return Evaluation(
        plan, tuple(map(_source_record, sources)), _source_record(control), tuple(trials)
    )


def _transfer_audit(
    condition: Condition,
    capsule: CapabilityCapsule,
    trajectory: Trajectory,
    policy: BranchTransfer,
    static_delivered: bool,
) -> TransferAudit:
    steps = trajectory.steps
    if condition == Condition.CAPSULE:
        task = public_task(trajectory.task)
        tools = environment_for(trajectory.task).tools
        for count in range(len(steps)):
            policy.memory_for(AgentContext(task, tools, steps[:count], trajectory.max_steps))
        policy.finish(AgentContext(task, tools, steps, trajectory.max_steps))
        prompts = tuple(range(len(steps))) if static_delivered else ()
    else:
        prompts = tuple(step for step in policy.prompt_steps if step < len(steps))
    divergence = next(
        (
            item.after_step
            for item in policy.transitions
            if item.state == BranchState.DIVERGED
            or (
                item.state == BranchState.ABSTAINED
                and item.reason
                in (
                    "public_operation_diverged",
                    "public_observation_diverged",
                    "missing_public_prerequisite",
                )
            )
        ),
        len(steps),
    )
    return TransferAudit(
        trajectory.task.seed,
        condition,
        capsule.capability_id,
        tuple(policy.transitions),
        prompts,
        sum(step >= divergence for step in prompts),
    )
