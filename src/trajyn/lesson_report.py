"""Rebuild lesson audits and paired outcomes from sealed records without a model."""

from collections import Counter
from pathlib import Path
from typing import Any, cast

from trajyn.agent import AgentContext
from trajyn.benchmark import DELIVERY_V3, generate_delivery_task
from trajyn.capability import read_capsules
from trajyn.lesson import EvidenceTransfer, evidence_gate, read_lesson, validate_lesson
from trajyn.lesson_learning import RecordedConnection, tool_contracts, verify_learning
from trajyn.lesson_protocol import (
    ARMS,
    MAX_STEPS,
    OPTIONS,
    artifact_hashes,
    check_hashes,
    digest,
    read_json,
    save_json,
)
from trajyn.lesson_study import (
    AuditedAgent,
    audit_record,
    completed,
    development_pool,
    policy_for,
    read_json_value,
    source_pool,
    verify_frozen,
)
from trajyn.models import DeliveryTask, Split, public_task
from trajyn.ollama import LocalModel, OllamaAgent, OllamaConnection, OllamaError
from trajyn.provenance import read_trajectory
from trajyn.recording import encode_json, write_text
from trajyn.runner import environment_for, run_task
from trajyn.study import _paired_interval, _paired_sign


class ReplayConnection(RecordedConnection):
    def __init__(self, folder: Path) -> None:
        super().__init__(OllamaConnection("http://127.0.0.1:11434", OPTIONS), folder)
        self.archived = [read_json(path) for path in sorted(folder.glob("*.json"))]

    def api(self, path: str, payload: dict[str, object] | None = None) -> dict[str, object]:
        index = len(self.calls)
        if path != "/api/chat" or index >= len(self.archived):
            raise ValueError("recorded API call sequence changed")
        record = self.archived[index]
        if encode_json(payload) != encode_json(record["payload"]):
            raise ValueError("submitted prompt, options, or tool interface changed")
        self.calls.append(record)
        if record["status"] == "responded":
            response: dict[str, object] = record["response"]
            return response
        raise OllamaError(record.get("error", "interrupted_call"))


def replay_attempt(
    folder: Path, task: DeliveryTask, model: LocalModel, policy: Any = None
) -> dict[str, Any]:
    seals = read_json(folder / "seal.json")
    check_hashes(folder, seals)
    if artifact_hashes(folder, exclude=("seal.json",)) != seals:
        raise ValueError("attempt file inventory changed")
    recorded = read_json(folder / "result.json")
    expected = read_trajectory(folder / "trace.jsonl")
    if expected.task != task or read_json_value(model) != recorded["model"]:
        raise ValueError("attempt identity differs from frozen cell")
    connection = ReplayConnection(folder / "calls")
    agent = OllamaAgent(connection, model)
    audited = AuditedAgent(agent, None)
    replayed = run_task(task, audited, max_steps=MAX_STEPS, memory_policy=policy)
    incomplete = any(call["status"] != "responded" for call in connection.calls)
    result = {
        "trajectory_id": replayed.trajectory_id,
        "status": "incomplete" if incomplete else "complete",
        "verified": replayed.verification.passed,
        "termination": agent.termination,
        "model": model,
        "turns": audited.turns,
        "audit": audit_record(policy, audited.turns),
        "calls": agent.call_count,
        "input_tokens": agent.input_tokens,
        "output_tokens": agent.output_tokens,
        "proposals": agent.proposals,
    }
    if (
        replayed != expected
        or read_json_value(result) != recorded
        or (len(connection.calls) != len(connection.archived))
    ):
        raise ValueError("trajectory, prompt delivery, or reported decisions disagree")
    return cast(dict[str, Any], recorded)


def replay_demo(root: Path) -> dict[str, object]:
    check_hashes(root, read_json(root / "demo-seal.json"))
    record = read_json(root / "demo.json")
    sources = tuple(read_trajectory(path) for path in sorted((root / "fixture-sources").glob("*")))
    lesson = read_lesson(root / "lesson.json", tool_contracts(sources))
    validate_lesson(lesson, sources, development_pool(root), require_model=False)
    if record["kind"] != "deterministic_fixture_not_model_learning" or (
        record["lesson_id"] != lesson.lesson_id
    ):
        raise ValueError("fixture provenance changed")
    active = 0
    for row in record["cases"]:
        trace = read_trajectory(root / row["trace"])
        policy = EvidenceTransfer(lesson)
        calls = len(trace.steps) + (len(trace.steps) < trace.max_steps)
        for index in range(calls):
            policy.memory_for(
                AgentContext(
                    public_task(trace.task),
                    environment_for(trace.task).tools,
                    trace.steps[:index],
                    trace.max_steps,
                )
            )
        policy.finish(
            AgentContext(
                public_task(trace.task),
                environment_for(trace.task).tools,
                trace.steps,
                trace.max_steps,
            )
        )
        if (
            read_json_value(policy.decisions) != row["decisions"]
            or policy.offered != row["offered"]
        ):
            raise ValueError("offline gate audit changed")
        active += bool(policy.offered)
    return {
        "kind": record["kind"],
        "replayed_cases": len(record["cases"]),
        "cases_with_offered_hints": active,
        "model_attempts": 0,
        "lesson_id": lesson.lesson_id,
    }


def paired(
    rows: dict[tuple[int, str], dict[str, Any]], seeds: list[int], comparator: str
) -> dict[str, object]:
    values = [
        int(rows[seed, "G"]["verified"]) - int(rows[seed, comparator]["verified"])
        for seed in seeds
        if (seed, "G") in rows and (seed, comparator) in rows
    ]
    gains, losses = values.count(1), values.count(-1)
    return {
        "matched_tasks": len(values),
        "gains": gains,
        "regressions": losses,
        "ties": values.count(0),
        "difference_pp": 100 * sum(values) / len(values) if values else None,
        "descriptive_paired_95_interval_pp": [100 * v for v in _paired_interval(values)]
        if values
        else None,
        "sign_test_p": _paired_sign(gains, losses) if values else None,
    }


def replay_study(root: Path, freeze: Path) -> dict[str, object]:
    if (root / "demo.json").exists():
        return replay_demo(root)
    if not (root / "manifest.json").exists():
        # Missing local inference still has independently replayable reachability work.
        references = list((root / "references").rglob("*.jsonl"))
        for path in references:
            read_trajectory(path)
        for folder in (root / "sources").glob("*/try-*"):
            if (folder / "seal.json").exists():
                recorded = read_json(folder / "result.json")
                trace = read_trajectory(folder / "trace.jsonl")
                assert isinstance(trace.task, DeliveryTask)
                replay_attempt(folder, trace.task, LocalModel(**recorded["model"]))
        verify_learning(root, source_pool(root), development_pool(root))
        return {
            "status": "not_frozen",
            "reference_replays": len(references),
            "live": read_json(root / "status.json") if (root / "status.json").exists() else None,
        }
    manifest = verify_frozen(root, freeze)
    sources = source_pool(root)
    lesson = read_lesson(root / "lesson.json", tool_contracts(sources))
    if lesson.lesson_id != manifest["lesson_id"]:
        raise ValueError("lesson differs from frozen selection")
    validate_lesson(lesson, sources, development_pool(root))
    selected_lesson = verify_learning(root, sources, development_pool(root))
    if selected_lesson != lesson:
        raise ValueError("lesson differs from deterministic proposal selection")
    for name, identity in manifest["references"].items():
        if read_trajectory(root / name).trajectory_id != identity:
            raise ValueError("reference provenance changed")
    for folder in (root / "sources").glob("*/try-*"):
        if (folder / "seal.json").exists():
            trace = read_trajectory(folder / "trace.jsonl")
            assert isinstance(trace.task, DeliveryTask)
            replay_attempt(folder, trace.task, LocalModel(**manifest["models"]["source"]))
    capsules = read_capsules(root / "capsules.jsonl")
    from datetime import datetime

    from trajyn.induction import induce
    from trajyn.lesson_protocol import CREATED_AT

    expected_capsules = []
    for source in sources:
        try:
            expected_capsules.append(induce(source, created_at=datetime.fromisoformat(CREATED_AT)))
        except ValueError:
            continue
    if capsules != tuple(expected_capsules):
        raise ValueError("F capsules differ from deterministic verified training induction")
    rows: dict[tuple[int, str], dict[str, Any]] = {}
    incomplete: list[dict[str, object]] = []
    gate_counts: dict[str, Counter[str]] = {arm: Counter() for arm in ARMS}
    for case in manifest["design"]["cases"]:
        seed = case["seed"]
        task = generate_delivery_task(seed, Split.TEST, workflow=DELIVERY_V3)
        for arm in case["arms"]:
            folder = root / "targets" / f"{seed}-{arm}"
            for prior in sorted(folder.glob("try-*")):
                if not (prior / "seal.json").exists():
                    incomplete.append(
                        {"seed": seed, "arm": arm, "attempt": prior.name, "status": "interrupted"}
                    )
                    continue
                prior_result = replay_attempt(
                    prior,
                    task,
                    LocalModel(**manifest["models"]["target"]),
                    policy_for(arm, lesson, task, capsules),
                )
                if prior_result["status"] != "complete":
                    incomplete.append(
                        {
                            "seed": seed,
                            "arm": arm,
                            "attempt": prior.name,
                            "status": "infrastructure_incomplete",
                            "reason": prior_result["termination"],
                        }
                    )
            chosen = completed(folder)
            if chosen is None:
                incomplete.append(
                    {
                        "seed": seed,
                        "arm": arm,
                        "status": "F_unavailable"
                        if arm == "F" and not manifest["F_available"][str(seed)]
                        else "missing_or_incomplete",
                    }
                )
                continue
            row = read_json(chosen / "result.json")
            rows[seed, arm] = row
            trace = read_trajectory(chosen / "trace.jsonl")
            tools = environment_for(task).tools
            eligible = 0
            for turn in row["turns"]:
                index = turn["after_step"]
                context = AgentContext(public_task(task), tools, trace.steps[:index], MAX_STEPS)
                gate = evidence_gate(lesson, context)
                opportunity = gate.state == "eligible"
                eligible += opportunity
                counts = gate_counts[arm]
                if turn["call"] is not None:
                    counts["eligible_model_calls"] += opportunity
                if turn["responded"] and turn["memory"] is not None:
                    counts["hint_deliveries"] += 1
                    counts[
                        "correct_live_bindings" if opportunity else "symbolic_before_evidence"
                    ] += 1
                    counts["incorrect_deliveries"] += int(case["type"] == "look_alike")
                    followed = (
                        index < len(trace.steps)
                        and opportunity
                        and (
                            trace.steps[index].action.tool == lesson.consumer_tool
                            and trace.steps[index].action.arguments.get("receipt_id")
                            == gate.receipt
                        )
                    )
                    counts["followed_by_intended_action"] += followed
                if opportunity and turn["call"] is not None and turn["memory"] is None:
                    counts["eligible_prompts_without_hint"] += 1
            terminal = evidence_gate(
                lesson, AgentContext(public_task(task), tools, trace.steps, MAX_STEPS)
            )
            gate_counts[arm]["cases_never_obtaining_evidence"] += (
                eligible == 0 and terminal.state != "eligible"
            )
            gate_counts[arm]["terminal_eligible_without_next_call"] += terminal.state == "eligible"
    groups: dict[str, list[int]] = {"overall": [c["seed"] for c in manifest["design"]["cases"]]}
    for case in manifest["design"]["cases"]:
        groups.setdefault(case["type"], []).append(case["seed"])
    results = {}
    for group, seeds in groups.items():
        arm_counts = {}
        for arm in ARMS:
            selected = [
                (seed, row) for (seed, a), row in rows.items() if a == arm and seed in seeds
            ]
            traces = []
            for seed, _ in selected:
                finished = completed(root / "targets" / f"{seed}-{arm}")
                assert finished is not None
                traces.append(read_trajectory(finished / "trace.jsonl"))
            arm_counts[arm] = {
                "verified": sum(row["verified"] for _, row in selected),
                "complete": len(selected),
                "planned": len(seeds),
                "calls": sum(row["calls"] for _, row in selected),
                "input_tokens": sum(row["input_tokens"] for _, row in selected),
                "output_tokens": sum(row["output_tokens"] for _, row in selected),
                "steps": sum(len(trace.steps) for trace in traces),
                "invalid_calls": sum(
                    not s.observation.ok
                    and s.observation.code
                    not in {
                        "carrier_retry",
                        "warehouse_retry",
                        "out_of_stock",
                        "carrier_unavailable",
                    }
                    for t in traces
                    for s in t.steps
                ),
                "model_errors": sum(
                    p["diagnostic"] is not None for _, row in selected for p in row["proposals"]
                ),
            }
        results[group] = {
            "arms": arm_counts,
            "paired": {f"G_vs_{arm}": paired(rows, seeds, arm) for arm in ("A", "G-static", "F")},
        }
    document = {
        "manifest_id": manifest["manifest_id"],
        "evidence_id": digest(artifact_hashes(root / "targets")),
        "results": results,
        "gate_audits": gate_counts,
        "incomplete": incomplete,
        "profile_families": len({c["family"] for c in manifest["design"]["cases"]}),
        "paired_cases": [
            {
                "seed": c["seed"],
                "type": c["type"],
                "family": c["family"],
                "outcomes": {
                    arm: rows[c["seed"], arm]["verified"] if (c["seed"], arm) in rows else None
                    for arm in ARMS
                },
            }
            for c in manifest["design"]["cases"]
        ],
        "caution": "Shared synthetic profile families. Intervals describe fixed tasks. "
        "An action following a hint is observational and does not establish reliance.",
    }
    if (root / "report.json").exists():
        previous = read_json(root / "report.json")
        if previous.get("evidence_id") == document["evidence_id"] and (
            previous != read_json_value(document)
        ):
            raise ValueError("reported results disagree with unchanged recorded evidence")
    save_json(root / "report.json", document)
    lines = [
        "# Experiment 003 recorded results",
        "",
        document["caution"],
        "",
        "| Case type | Arm | Verified / completed | Planned |",
        "| --- | --- | --- | --- |",
    ]
    for group, data in results.items():
        for arm, arm_result in data["arms"].items():
            lines.append(
                f"| {group} | {arm} | {arm_result['verified']}/{arm_result['complete']} "
                f"| {arm_result['planned']} |"
            )
    lines += [
        "",
        "Paired comparisons and public evidence delivery counts are in report.json.",
        "",
        f"Missing or incomplete cells and prior interrupted attempts: {len(incomplete)}.",
    ]
    write_text(root / "report.md", "\n".join(lines) + "\n")
    return {
        "status": "complete" if len(rows) == 96 else "partial",
        "completed_cells": len(rows),
        "results": results,
        "incomplete": incomplete,
    }
