"""Summarize paired outcomes and identifier diagnostics from replayed artifacts."""

import json
from collections import Counter
from dataclasses import dataclass
from math import comb, sqrt
from pathlib import Path
from random import Random
from statistics import mean

from trajyn.branching import BranchState
from trajyn.diagnostics import ToolDiagnostics, diagnose
from trajyn.evaluation import Condition, Evaluation
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


@dataclass(frozen=True, slots=True)
class BranchSummary:
    paired_success: dict[int, int]
    improved: int
    regressed: int
    paired_delta: float
    paired_interval: tuple[float, float]
    paired_sign_p: float
    active: int
    abstained: int
    withdrawn: int
    terminal_states: dict[str, int]
    continued_after_divergence: dict[str, int]


def _branch_summary(results: Path, evaluation: Evaluation) -> BranchSummary:
    artifact = json.loads((results.parent / "transfer.json").read_text(encoding="utf-8"))
    if artifact["schema_version"] != 1:
        raise ValueError("unsupported transfer audit schema")
    audits = {(row["seed"], row["condition"]): row for row in artifact["trials"]}
    arms = (Condition.CAPSULE, Condition.DYNAMIC)
    rows = {(row.seed, row.condition): row for row in evaluation.trials if row.condition in arms}
    if len(audits) != len(artifact["trials"]) or audits.keys() != rows.keys():
        raise ValueError("transfer audit does not match the D/F trial matrix")
    for key, audit in audits.items():
        trial = rows[key]
        prompts = audit["delivered_after_steps"]
        if (
            trial.transfer is None
            or audit["capsule_id"] != trial.transfer.capsule_id
            or prompts != sorted(set(prompts))
            or any(not 0 <= step < trial.action_count for step in prompts)
            or not 0 <= audit["continued_after_divergence"] <= len(prompts)
        ):
            raise ValueError("transfer audit disagrees with trial")

    paired = {
        seed: int(rows[seed, Condition.DYNAMIC].passed) - int(rows[seed, Condition.CAPSULE].passed)
        for seed in evaluation.plan.seeds
    }
    values = list(paired.values())
    improved, regressed = values.count(1), values.count(-1)
    lifecycle = [
        [BranchState(item["state"]) for item in audit["transitions"]]
        for (_, condition), audit in audits.items()
        if condition == Condition.DYNAMIC
    ]
    if any(not states for states in lifecycle):
        raise ValueError("missing branch lifecycle")
    return BranchSummary(
        paired,
        improved,
        regressed,
        mean(values),
        _paired_interval(values),
        _paired_sign(improved, regressed),
        sum(BranchState.ACTIVE in states for states in lifecycle),
        sum(BranchState.ABSTAINED in states for states in lifecycle),
        sum(BranchState.WITHDRAWN in states for states in lifecycle),
        dict(Counter(states[-1].value for states in lifecycle)),
        {
            arm.value: sum(
                audit["continued_after_divergence"]
                for (_, condition), audit in audits.items()
                if condition == arm
            )
            for arm in arms
        },
    )


def write_study_analysis(results: Path, output: Path) -> tuple[ConditionSummary, ...]:
    summaries = summarize_study(results)
    document: dict[str, object] = {"version": 1, "conditions": summaries}
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
    if any(summary.condition == Condition.DYNAMIC for summary in summaries):
        branch = _branch_summary(results, read_evaluation(results))
        document["branch_transfer"] = branch
        low, high = branch.paired_interval
        continued = branch.continued_after_divergence
        lines += [
            "",
            "## Branch-aware vs static capsule",
            "",
            f"F vs D yielded {branch.improved} gains and {branch.regressed} regressions "
            f"({branch.paired_delta:+.0%}, 95% interval {low:+.0%} to {high:+.0%}, "
            f"paired sign p = {branch.paired_sign_p:.3f}).",
            f"Across {len(branch.paired_success)} F attempts, {branch.active} activated, "
            f"{branch.abstained} abstained, and {branch.withdrawn} withdrew.",
            f"Capsules remained in {continued['D']} D tool-producing prompts after the "
            f"shadow gate flagged divergence and {continued['F']} F prompts after divergence.",
            "",
            "| Seed | Verified outcome F minus D |",
            "| ---: | ---: |",
        ]
        lines.extend(f"| {seed} | {delta:+d} |" for seed, delta in branch.paired_success.items())
    write_jsonl(output / "analysis.json", [document])
    write_text(output / "analysis.md", "\n".join(lines) + "\n")
    return summaries
