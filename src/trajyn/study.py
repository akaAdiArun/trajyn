"""Summarize paired outcomes and identifier diagnostics from replayed artifacts."""

from collections import Counter
from dataclasses import dataclass
from math import comb, sqrt
from pathlib import Path
from random import Random
from statistics import mean

from trajyn.diagnostics import ToolDiagnostics, diagnose
from trajyn.evaluation import Condition
from trajyn.provenance import read_trajectory
from trajyn.recording import write_jsonl, write_text
from trajyn.report import paired_outcomes, read_evaluation
from trajyn.transfer import TransferStatus


@dataclass(frozen=True, slots=True)
class ConditionSummary:
    condition: Condition
    total: int
    verified: int
    success_interval: tuple[float, float]
    improved: int
    regressed: int
    paired_delta: float
    paired_interval: tuple[float, float]
    paired_sign_p: float
    mean_action_delta: float
    invalid_calls: int
    actions: int
    identifier_arguments: int
    matching_identifiers: int
    missing_identifiers: int
    repeated_actions: int
    recoveries: int
    delivered: int
    accepted: int
    rejected: int
    observation_counts: dict[str, int]
    failures: dict[str, int]


def _wilson(passed: int, total: int) -> tuple[float, float]:
    z = 1.959963984540054
    proportion = passed / total
    scale = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / scale
    radius = z / scale * sqrt((proportion * (1 - proportion) + z * z / (4 * total)) / total)
    return max(0.0, center - radius), min(1.0, center + radius)


def _paired_interval(values: list[int]) -> tuple[float, float]:
    rng = Random(1741)
    count = len(values)
    draws = sorted(mean(rng.choices(values, k=count)) for _ in range(10_000))
    return draws[249], draws[9749]


def _paired_sign(improved: int, regressed: int) -> float:
    discordant = improved + regressed
    numerator = 2 * sum(comb(discordant, i) for i in range(min(improved, regressed) + 1))
    return min(1.0, numerator / (1 << discordant))


def summarize_study(path: Path) -> tuple[ConditionSummary, ...]:
    evaluation = read_evaluation(path)
    pairs = paired_outcomes(evaluation)
    summaries = []
    for condition in evaluation.conditions:
        rows = [row for row in evaluation.trials if row.condition == condition]
        comparison = [pair for pair in pairs if pair.condition == condition]
        scored: list[ToolDiagnostics] = []
        failures: Counter[str] = Counter()
        codes: Counter[str] = Counter()
        for row in rows:
            if row.trajectory_file != f"trajectories/{row.seed}-{condition.value}.jsonl":
                raise ValueError("unexpected trajectory path")
            trajectory = read_trajectory(path.parent / row.trajectory_file)
            if (
                trajectory.trajectory_id != row.trajectory_id
                or trajectory.verification.passed != row.passed
            ):
                raise ValueError("recorded trial disagrees with replay")
            diagnostics = diagnose(trajectory)
            scored.append(diagnostics)
            codes.update(diagnostics.observations)
            failures.update(trajectory.verification.failures)
        outcomes = Counter(pair.outcome_vs_a for pair in comparison)
        improved, regressed = outcomes["improved"], outcomes["regressed"]
        differences = [
            int(pair.outcome_vs_a == "improved") - int(pair.outcome_vs_a == "regressed")
            for pair in comparison
        ]
        accepted = sum(
            row.transfer is not None and row.transfer.status == TransferStatus.ACCEPTED
            for row in rows
        )
        passed = sum(row.passed for row in rows)
        summaries.append(
            ConditionSummary(
                condition,
                len(rows),
                passed,
                _wilson(passed, len(rows)),
                improved,
                regressed,
                mean(differences),
                _paired_interval(differences),
                _paired_sign(improved, regressed),
                mean(pair.action_delta for pair in comparison),
                sum(row.invalid_calls for row in rows),
                sum(row.action_count for row in rows),
                sum(row.identifier_arguments for row in scored),
                sum(row.matching_identifiers for row in scored),
                sum(row.missing_identifiers for row in scored),
                sum(row.repeated_actions for row in scored),
                sum(row.recovery_episodes for row in scored),
                sum(row.memory_delivered for row in rows),
                accepted,
                sum(row.transfer is not None for row in rows) - accepted,
                dict(sorted(codes.items())),
                dict(sorted(failures.items())),
            )
        )
    return tuple(summaries)


def write_study_analysis(results: Path, output: Path) -> tuple[ConditionSummary, ...]:
    summaries = summarize_study(results)
    write_jsonl(output / "analysis.json", [{"version": 1, "conditions": summaries}])
    lines = [
        "# Paired analysis",
        "",
        "| Arm | Verified (Wilson 95%) | Improved / regressed vs A | Paired delta (95%) | "
        "Paired sign p | Mean action delta | Invalid calls | Matching identifiers | Delivered | "
        "Accepted / rejected |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for metric in summaries:
        low, high = metric.success_interval
        left, right = metric.paired_interval
        lines.append(
            f"| {metric.condition.value} | {metric.verified}/{metric.total} "
            f"({low:.0%} to {high:.0%}) | "
            f"{metric.improved}/{metric.regressed} | {metric.paired_delta:+.0%} "
            f"({left:+.0%} to {right:+.0%}) | {metric.paired_sign_p:.3f} | "
            f"{metric.mean_action_delta:+.2f} | {metric.invalid_calls}/{metric.actions} | "
            f"{metric.matching_identifiers}/{metric.identifier_arguments} | {metric.delivered} | "
            f"{metric.accepted}/{metric.rejected} |"
        )
    lines += [
        "",
        "Intervals for paired deltas resample whole held-out tasks. Estimates are descriptive "
        "for the fixed, small task set. The sign tests are unadjusted. Matching identifiers "
        "means the executed value matched a public value available before the call. In a "
        "public-grounded configuration it measures executed bindings, not the model's "
        "ability to reproduce identifiers. Model inference usage is in the comparison "
        "and complete call totals in the pilot metadata.",
        "",
        "## Verification failures",
        "",
    ]
    lines.extend(
        f"- {item.condition.value} · "
        + (", ".join(f"`{name}` ({count})" for name, count in item.failures.items()) or "none")
        for item in summaries
    )
    write_text(output / "analysis.md", "\n".join(lines) + "\n")
    return summaries
