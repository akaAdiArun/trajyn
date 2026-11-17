"""Separate, bounded local-model pilot using the paired evaluation engine."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from trajyn.evaluation import EvaluationPlan, collect_sources, evaluate, validate_seeds
from trajyn.induction import induce
from trajyn.models import Split
from trajyn.ollama import LocalModel, OllamaAgent, OllamaConnection
from trajyn.recording import write_jsonl
from trajyn.report import write_evaluation

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


def _usage(agent: OllamaAgent, seed: int, condition: str | None = None) -> InferenceRecord:
    return InferenceRecord(
        seed,
        condition,
        agent.call_count,
        agent.input_tokens,
        agent.output_tokens,
        agent.termination or "action_limit",
    )


def run_pilot(
    output: Path,
    connection: OllamaConnection,
    source_name: str,
    target_name: str,
    source_seeds: tuple[int, ...] = SOURCE_SEEDS,
    target_seeds: tuple[int, ...] = TARGET_SEEDS,
    max_steps: int = 8,
) -> dict[str, object]:
    validate_seeds(source_seeds)
    plan = EvaluationPlan(target_seeds, Split.TEST, max_steps)
    if set(source_seeds) & set(target_seeds):
        raise ValueError("pilot source and target seeds must be disjoint")
    source_model, target_model = connection.model(source_name), connection.model(target_name)
    if source_model.family == target_model.family or source_model.digest == target_model.digest:
        raise ValueError("pilot requires different model families")

    source_agents: list[OllamaAgent] = []
    target_agents: list[OllamaAgent] = []

    def track(model: LocalModel, agents: list[OllamaAgent]) -> OllamaAgent:
        agent = OllamaAgent(connection, model)
        agents.append(agent)
        return agent

    metadata: dict[str, object] = {
        "schema_version": 1,
        "server_version": connection.api("/api/version").get("version"),
        "source_model": source_model,
        "target_model": target_model,
        "source_seeds": source_seeds,
        "plan": plan,
        "options": connection.options,
        "maximum_model_calls": (len(source_seeds) + 5 * len(target_seeds)) * max_steps,
    }
    sources = collect_sources(
        output / "source",
        source_seeds,
        max_steps=max_steps,
        measure_time=True,
        agent_factory=lambda: track(source_model, source_agents),
    )
    metadata["source_inference"] = [
        _usage(agent, seed) for agent, seed in zip(source_agents, source_seeds, strict=True)
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
        _usage(agent, row.seed, row.condition.value)
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
