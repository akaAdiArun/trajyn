"""Separate, bounded local-model pilot using the paired evaluation engine."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from trajyn.benchmark import DELIVERY_V1, generate_delivery_task
from trajyn.diagnostics import ToolDiagnostics, diagnose
from trajyn.evaluation import EvaluationPlan, collect_sources, evaluate, validate_seeds
from trajyn.induction import induce
from trajyn.models import Split, Trajectory
from trajyn.ollama import PROMPT_REVISION, LocalModel, ModelProposal, OllamaAgent, OllamaConnection
from trajyn.provenance import read_trajectory
from trajyn.recording import write_jsonl, write_trajectory
from trajyn.report import write_evaluation
from trajyn.runner import run_task

SOURCE_SEEDS = (0, 1, 2, 3)
TARGET_SEEDS = (200, 202)


@dataclass(frozen=True, slots=True)
class InferenceRecord:
    seed: int
    condition: str | None
    calls: int
    input_tokens: int
    output_tokens: int
    termination: str
    proposals: tuple[ModelProposal, ...]
    diagnostics: ToolDiagnostics


def _usage(
    agent: OllamaAgent, trajectory: Trajectory, condition: str | None = None
) -> InferenceRecord:
    return InferenceRecord(
        trajectory.task.seed,
        condition,
        agent.call_count,
        agent.input_tokens,
        agent.output_tokens,
        agent.termination or "action_limit",
        tuple(agent.proposals),
        diagnose(trajectory),
    )


def calibrate_models(
    output: Path,
    connection: OllamaConnection,
    names: tuple[str, ...],
    seeds: tuple[int, ...],
    max_steps: int,
    *,
    workflow: str = DELIVERY_V1,
) -> dict[str, object]:
    """Run no-memory validation attempts for each supplied model."""
    validate_seeds(seeds)
    if not names or len(set(names)) != len(names):
        raise ValueError("pass distinct model names")
    configurations = tuple(connection.model(name) for name in names)
    records = []
    server = connection.api("/api/version").get("version")
    for index, model in enumerate(configurations):
        for seed in seeds:
            agent = OllamaAgent(connection, model)
            attempt = run_task(
                generate_delivery_task(seed, Split.VALIDATION, workflow=workflow),
                agent,
                max_steps=max_steps,
                measure_time=True,
            )
            path = f"model-{index}/{seed}.jsonl"
            write_trajectory(output / path, attempt)
            records.append(
                {
                    "model": model,
                    "seed": seed,
                    "trajectory": path,
                    "trajectory_id": attempt.trajectory_id,
                    "verified": attempt.verification.passed,
                    "inference": _usage(agent, attempt),
                }
            )
            write_jsonl(
                output / "calibration.json",
                [
                    {
                        "prompt_revision": PROMPT_REVISION,
                        "server_version": server,
                        "options": connection.options,
                        "split": Split.VALIDATION,
                        "workflow": workflow,
                        "seeds": seeds,
                        "max_steps": max_steps,
                        "attempts": records,
                    }
                ],
            )
    return {"attempts": len(records), "verified": sum(row["verified"] is True for row in records)}


def run_pilot(
    output: Path,
    connection: OllamaConnection,
    source_name: str,
    target_name: str,
    source_seeds: tuple[int, ...] = SOURCE_SEEDS,
    target_seeds: tuple[int, ...] = TARGET_SEEDS,
    max_steps: int = 8,
    *,
    workflow: str = DELIVERY_V1,
    expected_source_digest: str | None = None,
    expected_target_digest: str | None = None,
) -> dict[str, object]:
    validate_seeds(source_seeds)
    plan = EvaluationPlan(target_seeds, Split.TEST, max_steps)
    if set(source_seeds) & set(target_seeds):
        raise ValueError("pilot source and target seeds must be disjoint")
    source_model, target_model = connection.model(source_name), connection.model(target_name)
    if source_model.family == target_model.family or source_model.digest == target_model.digest:
        raise ValueError("pilot requires different model families")
    if expected_source_digest is not None and source_model.digest != expected_source_digest:
        raise ValueError("installed source digest differs from the frozen protocol")
    if expected_target_digest is not None and target_model.digest != expected_target_digest:
        raise ValueError("installed target digest differs from the frozen protocol")

    source_agents: list[OllamaAgent] = []
    target_agents: list[OllamaAgent] = []

    def track(model: LocalModel, agents: list[OllamaAgent]) -> OllamaAgent:
        agent = OllamaAgent(connection, model)
        agents.append(agent)
        return agent

    metadata: dict[str, object] = {
        "schema_version": 1,
        "prompt_revision": PROMPT_REVISION,
        "server_version": connection.api("/api/version").get("version"),
        "source_model": source_model,
        "target_model": target_model,
        "source_seeds": source_seeds,
        "plan": plan,
        "options": connection.options,
        "workflow": workflow,
        "maximum_model_calls": (len(source_seeds) + 5 * len(target_seeds)) * max_steps,
    }
    sources = collect_sources(
        output / "source",
        source_seeds,
        max_steps=max_steps,
        measure_time=True,
        workflow=workflow,
        agent_factory=lambda: track(source_model, source_agents),
    )
    metadata["source_inference"] = [
        _usage(agent, attempt) for agent, attempt in zip(source_agents, sources, strict=True)
    ]
    created_at = datetime.now(UTC)
    capsules = []
    accepted_sources = []
    exclusions = {}
    for source in sources:
        if not source.verification.passed:
            accepted_sources.append(source)  # Failed attempts remain in the source metadata.
            continue
        try:
            capsules.append(induce(source, created_at=created_at))
        except ValueError as error:
            exclusions[source.trajectory_id] = str(error)
        else:
            accepted_sources.append(source)

    metadata["induction_exclusions"] = exclusions
    counts: dict[str, object] = {
        "source_count": len(sources),
        "verified_sources": sum(source.verification.passed for source in sources),
        "capsule_count": len(capsules),
        "target_trials": 0,
        "status": "no_inducible_sources" if not capsules else "collected",
    }
    write_jsonl(output / "pilot.json", [{**metadata, **counts}])
    if not capsules:
        return counts

    write_jsonl(output / "capsules.jsonl", capsules)
    result = evaluate(
        tuple(accepted_sources),
        tuple(capsules),
        output / "evaluation",
        plan=plan,
        target_factory=lambda: track(target_model, target_agents),
    )
    write_evaluation(output / "evaluation", result)
    metadata["target_inference"] = [
        _usage(
            agent, read_trajectory(output / "evaluation" / row.trajectory_file), row.condition.value
        )
        for agent, row in zip(target_agents, result.trials, strict=True)
    ]
    counts.update(
        {
            "target_trials": len(result.trials),
            "verified_targets": sum(row.passed for row in result.trials),
            "status": "completed",
        }
    )
    write_jsonl(output / "pilot.json", [{**metadata, **counts}])
    return counts
