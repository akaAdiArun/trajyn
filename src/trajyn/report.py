"""Machine-readable paired outcomes and standalone Markdown comparisons."""

import csv
import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from statistics import mean

from trajyn.evaluation import Condition, Evaluation, EvaluationPlan, SourceRecord, Trial
from trajyn.models import AgentIdentity, Split, Usage
from trajyn.recording import encode_json, write_jsonl, write_text
from trajyn.transfer import TransferConsideration, TransferStatus


@dataclass(frozen=True, slots=True)
class PairedOutcome:
    task_id: str
    condition: Condition
    outcome_vs_a: str
    action_delta: int
    invalid_call_delta: int


def paired_outcomes(evaluation: Evaluation) -> tuple[PairedOutcome, ...]:
    samples = {(row.seed, row.condition): row for row in evaluation.trials}
    expected = {(seed, condition) for seed in evaluation.plan.seeds for condition in Condition}
    if samples.keys() != expected or len(samples) != len(evaluation.trials):
        raise ValueError("evaluation must contain one trial per seed and condition")
    agent = evaluation.trials[0].agent
    outcomes = []
    for row in evaluation.trials:
        baseline = samples[(row.seed, Condition.NO_MEMORY)]
        if (
            row.task_id != baseline.task_id
            or row.agent != agent
            or row.split != evaluation.plan.split
            or row.max_steps != evaluation.plan.max_steps
        ):
            raise ValueError("paired trials must share task, agent, split, and action budget")
        if row.passed == baseline.passed:
            outcome = "same_success" if row.passed else "same_failure"
        else:
            outcome = "improved" if row.passed else "regressed"
        outcomes.append(
            PairedOutcome(
                row.task_id,
                row.condition,
                outcome,
                row.action_count - baseline.action_count,
                row.invalid_calls - baseline.invalid_calls,
            )
        )
    return tuple(outcomes)


def _optional_total(values: Iterable[int | float | None]) -> str:
    available = [value for value in values if value is not None]
    return f"{sum(available):g}" if available else "—"


def render_report(result: Evaluation) -> str:
    paired = paired_outcomes(result)
    source = ", ".join(
        sorted({f"{row.agent.provider}/{row.agent.model}" for row in result.sources})
    )
    agent = result.trials[0].agent
    lines = [
        "# Paired delivery-exception comparison",
        "",
        f"Target `{agent.provider}/{agent.model}` ({agent.version or 'version unavailable'}). "
        f"Source {source}.",
        f"Partition `{result.plan.split}`. Seeds {', '.join(map(str, result.plan.seeds))}. "
        f"Budget {result.plan.max_steps} actions per attempt.",
        "",
        "| Condition | Verified | Closed | Mean actions | Invalid calls | Tool failures | "
        "Recoveries | Mean ms | Delivered / Used | Accepted / Rejected | "
        "Improved / Regressed vs A |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    names = {
        Condition.NO_MEMORY: "A · No memory",
        Condition.RAW: "B · Raw trajectory",
        Condition.SUMMARY: "C · Procedural summary",
        Condition.CAPSULE: "D · Capsule",
        Condition.CONTROL: "E · Irrelevant trajectory",
    }
    per_condition = {
        condition: tuple(row for row in result.trials if row.condition == condition)
        for condition in Condition
    }
    for condition, rows in per_condition.items():
        durations = [row.elapsed_ns / 1_000_000 for row in rows if row.elapsed_ns is not None]
        timing = f"{mean(durations):.3f}" if durations else "—"
        used = sum(row.memory_used is True for row in rows)
        use_label = str(used) if all(row.memory_used is not None for row in rows) else "unknown"
        decisions = [row.transfer.status for row in rows if row.transfer is not None]
        accepted = decisions.count(TransferStatus.ACCEPTED)
        decision_label = f"{accepted} / {len(decisions) - accepted}" if decisions else "—"
        outcomes = Counter(row.outcome_vs_a for row in paired if row.condition == condition)
        lines.append(
            f"| {names[condition]} | {sum(row.passed for row in rows)}/{len(rows)} | "
            f"{sum(row.completed for row in rows)}/{len(rows)} | "
            f"{mean(row.action_count for row in rows):.2f} | "
            f"{sum(row.invalid_calls for row in rows)} | "
            f"{sum(row.tool_failures for row in rows)} | "
            f"{sum(row.recovery_episodes for row in rows)} | {timing} | "
            f"{sum(row.memory_delivered for row in rows)} / {use_label} | {decision_label} | "
            f"{outcomes['improved']} / {outcomes['regressed']} |"
        )

    lines += [
        "",
        "## Recorded usage",
        "",
        "| Condition | Input tokens | Output tokens | Estimated cost (USD) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for condition, rows in per_condition.items():
        inputs = _optional_total(row.usage.input_tokens for row in rows)
        outputs = _optional_total(row.usage.output_tokens for row in rows)
        costs = _optional_total(row.usage.estimated_cost_usd for row in rows)
        lines.append(f"| {condition.value} | {inputs} | {outputs} | {costs} |")

    lines += [
        "",
        "## Per-task outcomes",
        "",
        "| Seed | Condition | Verified | Actions | Failure codes | Capsule check |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for row in result.trials:
        failures = ", ".join(row.failures) or "—"
        transfer = row.transfer.reason if row.transfer else "—"
        lines.append(
            f"| {row.seed} | {row.condition.value} | {'yes' if row.passed else 'no'} | "
            f"{row.action_count} | {failures} | {transfer} |"
        )

    lines.extend(
        [
            "",
            "## Limits",
            "",
            "The suite is synthetic and small. Pairs quantify observed differences on these "
            "instances. Recovery counts a failed-call episode followed by a successful call. "
            "Invalid calls exclude explicitly modeled service and stock failures. "
            "Token and cost totals cover recorded usage only. Runtime depends on the machine.",
            "",
        ]
    )
    if agent.provider == "offline":
        lines.extend(
            [
                "The source and target are fixed fixture policies. Their outcomes test the "
                "evaluation plumbing and provide no evidence of cross-model improvement.",
                "",
            ]
        )
    return "\n".join(lines)


def write_evaluation(output: Path, result: Evaluation) -> None:
    pairs = paired_outcomes(result)
    rows = []
    for trial, pair in zip(result.trials, pairs, strict=True):
        row = json.loads(encode_json(trial))
        row.update(
            {
                "outcome_vs_a": pair.outcome_vs_a,
                "action_delta_vs_a": pair.action_delta,
                "invalid_call_delta_vs_a": pair.invalid_call_delta,
            }
        )
        rows.append(
            {
                key: encode_json(value) if isinstance(value, (dict, list)) else value
                for key, value in row.items()
            }
        )
    text = StringIO()
    writer = csv.DictWriter(text, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    write_text(output / "results.csv", text.getvalue())
    write_text(output / "comparison.md", render_report(result))
    write_jsonl(output / "results.json", [{"evaluation": result, "paired": pairs}])


def _read_source(data: object) -> SourceRecord:
    if not isinstance(data, dict):
        raise ValueError("source must be an object")
    return SourceRecord(
        **{
            **data,
            "agent": AgentIdentity(**data["agent"]),
            "split": Split(data["split"]),
        }
    )


def read_evaluation(path: Path) -> Evaluation:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        record = document["evaluation"]
        if type(record["schema_version"]) is not int or record["schema_version"] != 1:
            raise ValueError("unsupported evaluation schema version")
        plan = EvaluationPlan(
            **{
                **record["plan"],
                "seeds": tuple(record["plan"]["seeds"]),
                "split": Split(record["plan"]["split"]),
            }
        )
        trials = []
        for trial in record["trials"]:
            transfer = trial["transfer"]
            consideration = (
                None
                if transfer is None
                else TransferConsideration(
                    transfer["capsule_id"],
                    tuple(transfer["source_trajectory_ids"]),
                    TransferStatus(transfer["status"]),
                    transfer["reason"],
                )
            )
            trials.append(
                Trial(
                    **{
                        **trial,
                        "agent": AgentIdentity(**trial["agent"]),
                        "usage": Usage(**trial["usage"]),
                        "split": Split(trial["split"]),
                        "condition": Condition(trial["condition"]),
                        "failures": tuple(trial["failures"]),
                        "transfer": consideration,
                    }
                )
            )
        evaluation = Evaluation(
            plan,
            tuple(_read_source(source) for source in record["sources"]),
            _read_source(record["control_source"]),
            tuple(trials),
        )
        if encode_json(
            {"evaluation": evaluation, "paired": paired_outcomes(evaluation)}
        ) != encode_json(document):
            raise ValueError("evaluation records do not match the declared pairs")
    except (KeyError, ValueError, TypeError, AttributeError) as error:
        raise ValueError(f"{path}: invalid evaluation ({error})") from error
    return evaluation
