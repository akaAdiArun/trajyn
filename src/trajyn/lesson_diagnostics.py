"""Public post-receipt behavior, distinct from the independently verified outcome."""

from collections import Counter
from typing import Any

from trajyn.agent import AgentContext
from trajyn.lesson import Lesson, evidence_gate
from trajyn.models import Trajectory, public_task
from trajyn.recording import encode_json
from trajyn.runner import environment_for


def post_receipt(lesson: Lesson, trace: Trajectory, row: dict[str, Any]) -> dict[str, Any]:
    tools = environment_for(trace.task).tools
    first = next(
        (
            index
            for index in range(len(trace.steps) + 1)
            if evidence_gate(
                lesson,
                AgentContext(public_task(trace.task), tools, trace.steps[:index], trace.max_steps),
            ).state
            == "eligible"
        ),
        None,
    )
    closed = next(
        (
            s.index
            for s in trace.steps
            if s.action.tool == "close_case"
            and s.observation.ok
            and s.observation.code == "case_closed"
            and s.action.arguments.get("ticket_id") == trace.task.ticket_id
        ),
        None,
    )
    if first is None:
        return {"reached_qualifying_receipt": False, "case_closed": closed is not None}
    turn = next((t for t in row["turns"] if t["after_step"] == first), None)
    calls_before_close = sum(
        t["call"] is not None
        and first <= t["after_step"]
        and (closed is None or t["after_step"] < closed)
        for t in row["turns"]
    )
    next_action = trace.steps[first].action if first < len(trace.steps) else None
    next_observation = trace.steps[first].observation if first < len(trace.steps) else None
    return {
        "reached_qualifying_receipt": True,
        "receipt_after_step": first,
        "next_model_call": turn["call"] if turn is not None else None,
        "next_call_responded": bool(turn is not None and turn["responded"]),
        "next_decision_hint_offered": bool(turn is not None and turn["memory"] is not None),
        "next_decision_hint_delivered": bool(
            turn is not None and turn["memory"] is not None and turn["responded"]
        ),
        "first_action_after_receipt": next_action,
        "first_observation_after_receipt": next_observation,
        "closure_step": closed,
        "case_closed": closed is not None,
        "model_calls_until_closure_or_end": calls_before_close,
        "extra_calls_before_closure": max(0, calls_before_close - 1)
        if closed is not None
        else None,
        "terminal_opportunity_without_next_call": turn is None or turn["call"] is None,
    }


def summarize_post_receipt(rows: list[dict[str, Any]]) -> dict[str, object]:
    reached = [row for row in rows if row["reached_qualifying_receipt"]]
    first_actions = Counter(
        row["first_action_after_receipt"].tool
        if row["first_action_after_receipt"] is not None
        else "no_action"
        for row in reached
    )
    return {
        "attempts": len(rows),
        "reached_evidence": len(reached),
        "never_reached_evidence": len(rows) - len(reached),
        "next_decision_hint_delivered": sum(row["next_decision_hint_delivered"] for row in reached),
        "next_call_without_hint": sum(
            row["next_model_call"] is not None and not row["next_decision_hint_delivered"]
            for row in reached
        ),
        "terminal_opportunity_without_next_call": sum(
            row["terminal_opportunity_without_next_call"] for row in reached
        ),
        "first_actions": dict(first_actions),
        "closed_after_receipt": sum(row["case_closed"] for row in reached),
        "never_closed_after_receipt": sum(not row["case_closed"] for row in reached),
        "extra_calls_before_closure": sum(
            row["extra_calls_before_closure"] or 0 for row in reached
        ),
    }


def paired_efficiency(
    rows: dict[tuple[int, str], dict[str, Any]], seeds: list[int], comparator: str
) -> dict[str, object]:
    pairs = [
        (rows[seed, "G"], rows[seed, comparator])
        for seed in seeds
        if (seed, "G") in rows and (seed, comparator) in rows
    ]
    deltas = [left["calls"] - right["calls"] for left, right in pairs]
    successful = [
        left["calls"] - right["calls"]
        for left, right in pairs
        if left["verified"] and right["verified"]
    ]
    return {
        "matched_tasks": len(pairs),
        "G_fewer_calls": sum(value < 0 for value in deltas),
        "G_more_calls": sum(value > 0 for value in deltas),
        "equal_calls": deltas.count(0),
        "mean_call_difference_G_minus_comparator": sum(deltas) / len(deltas) if deltas else None,
        "both_verified_tasks": len(successful),
        "both_verified_mean_call_difference": sum(successful) / len(successful)
        if successful
        else None,
        "interpretation": "Efficiency is separate from independently verified completion.",
    }


def diagnostic_text(document: dict[str, Any]) -> str:
    lines = [
        "",
        "## Paired verified completion",
        "",
        "| Case type | Comparison | Matched | Gains | Losses | Ties | Difference, pp |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for group, result in document["results"].items():
        for comparison, pair in result["paired"].items():
            delta = pair["difference_pp"]
            shown = f"{delta:+.2f}" if delta is not None else "unavailable"
            lines.append(
                f"| {group} | {comparison} | {pair['matched_tasks']} | {pair['gains']} "
                f"| {pair['regressions']} | {pair['ties']} | {shown} |"
            )
    lines += [
        "",
        "## Post-receipt diagnostics",
        "",
        "Grounding supplies the receipt argument after the model selects close_case. "
        "The following measures describe tool selection and extra calls, "
        "and remain separate from the completion comparisons.",
        "",
    ]
    lines.extend(
        f"- {arm} {encode_json(values)}" for arm, values in document["post_receipt_summary"].items()
    )
    lines += ["", "## Paired efficiency", "", encode_json(document["paired_efficiency"]), ""]
    return "\n".join(lines)
