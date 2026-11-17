import csv
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trajyn.benchmark import generate_delivery_task
from trajyn.capability import read_capsules
from trajyn.cli import main
from trajyn.evaluation import (
    Condition,
    EvaluationPlan,
    collect_sources,
    evaluate,
    induce_sources,
    read_sources,
)
from trajyn.models import Split, public_task
from trajyn.provenance import read_trajectory
from trajyn.report import paired_outcomes, read_evaluation
from trajyn.retrieval import rank_experience
from trajyn.runner import environment_for
from trajyn.transfer import TransferStatus

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def test_paired_cli_pipeline_exports_replayable_data_and_comparison(tmp_path: Path) -> None:
    source_dir, capsules = tmp_path / "source", tmp_path / "capsules.jsonl"
    output, compare = tmp_path / "out", tmp_path / "comparison.md"
    assert main(["collect", "--seeds", "0,1,2,3,4", "--output", str(source_dir)]) == 0
    assert (
        main(
            [
                "induce",
                "--trajectories",
                str(source_dir),
                "--created-at",
                CREATED.isoformat(),
                "--output",
                str(capsules),
            ]
        )
        == 0
    )
    args = [
        "evaluate",
        "--trajectories",
        str(source_dir),
        "--capsules",
        str(capsules),
        "--seeds",
        "200,201,202,203",
        "--no-timing",
        "--output",
        str(output),
    ]
    assert main(args) == 0
    result_file = output / "results.json"
    untimed = result_file.read_bytes()
    assert main(args) == 0
    assert result_file.read_bytes() == untimed
    result = read_evaluation(result_file)
    assert len(result.trials) == 20
    assert {row.condition for row in result.trials} == set(Condition)
    assert [(row.seed, row.condition) for row in result.trials if not row.passed] == [
        (200, Condition.SUMMARY)
    ]
    assert {row.agent.model for row in result.trials} == {"delivery-target"}
    assert all(source.agent.model == "delivery-reference" for source in result.sources)
    for trial in result.trials:
        trajectory = read_trajectory(output / trial.trajectory_file)
        assert trajectory.trajectory_id == trial.trajectory_id
        assert trajectory.verification.passed == trial.passed

    by_trial = {(row.seed, row.condition): row for row in result.trials}
    locker = by_trial[(200, Condition.CAPSULE)]
    assert locker.transfer is not None and locker.transfer.status == TransferStatus.ACCEPTED
    assert locker.memory_delivered and locker.memory_used
    shelf = json.loads((output / "retrieval.json").read_text(encoding="utf-8"))
    ranked = shelf["targets"][0]["candidates"]
    assert ranked[0]["source_seed"] == 1
    assert ranked[-1]["compatibility"] == TransferStatus.INCOMPATIBLE
    assert shelf["targets"][1]["order"] == ["B", "C", "D", "E", "A"]
    for seed in (200, 201, 202, 203):
        assert (
            len(
                {
                    by_trial[(seed, arm)].source_trajectory_id
                    for arm in (
                        Condition.RAW,
                        Condition.SUMMARY,
                        Condition.CAPSULE,
                    )
                }
            )
            == 1
        )
    stale = by_trial[(201, Condition.CAPSULE)]
    assert stale.transfer is not None and stale.transfer.status == TransferStatus.ACCEPTED
    assert stale.memory_used and stale.recovery_episodes == 1
    control = by_trial[(203, Condition.CONTROL)]
    assert control.memory_delivered and control.memory_used is False
    assert control.source_trajectory_id == result.control_source.trajectory_id

    with (output / "results.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 20
    assert rows[0]["outcome_vs_a"] == "same_success"
    table = [
        line
        for line in (output / "comparison.md").read_text(encoding="utf-8").splitlines()
        if line.startswith("|")
    ][:7]
    assert len(table) == 7 and {line.count("|") for line in table} == {12}
    assert main(["compare", "--results", str(result_file), "--output", str(compare)]) == 0
    assert compare.read_bytes() == (output / "comparison.md").read_bytes()
    assert len(read_capsules(capsules)) == 5


def test_paired_outcomes_measure_an_observed_regression_at_tighter_budget(tmp_path: Path) -> None:
    source = collect_sources(tmp_path / "source", (0,))
    capsule = induce_sources(source, created_at=CREATED)
    result = evaluate(
        source,
        capsule,
        tmp_path / "out",
        plan=EvaluationPlan((202,), max_steps=5, measure_time=False),
    )
    outcomes = {row.condition: row for row in paired_outcomes(result)}
    assert outcomes[Condition.SUMMARY].outcome_vs_a == "regressed"
    assert outcomes[Condition.SUMMARY].invalid_call_delta == 1
    assert outcomes[Condition.CAPSULE].outcome_vs_a == "same_success"


def test_evaluation_rejects_leakage_and_tampered_provenance(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    sources = collect_sources(source_dir, (0,))
    assert read_sources(source_dir) == sources
    (capsule,) = induce_sources(sources, created_at=CREATED)
    output = tmp_path / "out"
    with pytest.raises(ValueError, match="disjoint"):
        evaluate(sources, (capsule,), output, plan=EvaluationPlan((0,)))
    with pytest.raises(ValueError, match="cannot be reproduced"):
        evaluate(sources, (replace(capsule, subtask="changed"),), output)
    with pytest.raises(ValueError, match="exactly the verified"):
        evaluate(sources, (), output)
    with pytest.raises(ValueError, match="held-out"):
        EvaluationPlan((200,), split=Split.TRAIN)


def test_rankings_depend_on_public_context_and_can_reject_every_candidate(tmp_path: Path) -> None:
    sources = collect_sources(tmp_path / "source", (0,))
    capsules = induce_sources(sources, created_at=CREATED)
    mapping = {
        source.trajectory_id: capsule for source, capsule in zip(sources, capsules, strict=True)
    }
    delivered = generate_delivery_task(202, Split.TEST)
    stale = generate_delivery_task(201, Split.TEST)
    first = rank_experience(
        public_task(delivered), environment_for(delivered).tools, sources, mapping
    )
    second = rank_experience(public_task(stale), environment_for(stale).tools, sources, mapping)
    assert first == second
    locker = generate_delivery_task(200, Split.TEST)
    (incompatible,) = rank_experience(
        public_task(locker),
        environment_for(locker).tools,
        sources,
        mapping,
    )
    assert incompatible.compatibility == TransferStatus.INCOMPATIBLE
    assert incompatible.tool_coverage_bp < 10_000
