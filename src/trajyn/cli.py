"""Run seeded tasks and compare experience-transfer conditions."""

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from trajyn.agent import OfflineReferenceAgent
from trajyn.benchmark import generate_delivery_task
from trajyn.capability import read_capsules
from trajyn.delivery_agent import DeliveryReferenceAgent
from trajyn.environment import generate_task
from trajyn.evaluation import (
    MAX_STEPS,
    TEST_SEEDS,
    TRAIN_SEEDS,
    VALIDATION_SEEDS,
    EvaluationPlan,
    collect_sources,
    evaluate,
    induce_sources,
    read_sources,
    validate_seeds,
)
from trajyn.models import Split
from trajyn.recording import encode_json, write_jsonl, write_text, write_trajectory
from trajyn.report import read_evaluation, render_report, write_evaluation
from trajyn.runner import run_task


def _non_negative(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected a non-negative integer") from error
    if number < 0:
        raise argparse.ArgumentTypeError("expected a non-negative integer")
    return number


def _positive(value: str) -> int:
    number = _non_negative(value)
    if number == 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return number


def _seeds(value: str) -> tuple[int, ...]:
    try:
        seeds = tuple(int(item) for item in value.split(","))
        validate_seeds(seeds)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected distinct comma-separated seeds") from error
    return seeds


def _created_at(value: str) -> datetime:
    try:
        timestamp = datetime.fromisoformat(value)
        if timestamp.utcoffset() is None:
            raise ValueError("missing timezone")
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected an ISO timestamp with a timezone") from error
    return timestamp


def _experiment(args: argparse.Namespace) -> dict[str, object]:
    match args.command:
        case "collect":
            sources = collect_sources(args.output, args.seeds, max_steps=args.max_steps)
            return {
                "source_count": len(sources),
                "verified": sum(s.verification.passed for s in sources),
            }
        case "induce":
            sources = read_sources(args.trajectories)
            capsules = induce_sources(sources, created_at=args.created_at or datetime.now(UTC))
            write_jsonl(args.output, capsules)
            return {
                "capsule_count": len(capsules),
                "unverified_sources": len(sources) - len(capsules),
            }
        case "evaluate":
            default_seeds = TEST_SEEDS if args.split == Split.TEST else VALIDATION_SEEDS
            plan = EvaluationPlan(
                args.seeds or default_seeds, args.split, args.max_steps, not args.no_timing
            )
            result = evaluate(
                read_sources(args.trajectories),
                read_capsules(args.capsules),
                args.output,
                plan=plan,
            )
            write_evaluation(args.output, result)
            return {
                "trial_count": len(result.trials),
                "verified": sum(row.passed for row in result.trials),
            }
        case "compare":
            result = read_evaluation(args.results)
            write_text(args.output, render_report(result))
            return {"trial_count": len(result.trials)}
        case _:
            raise ValueError("unknown experiment command")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trajyn", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="write seeded tasks as JSONL")
    demo = commands.add_parser("demo", help="run the rules-based offline reference agent")
    for command in (generate, demo):
        command.add_argument("--seed", type=_non_negative, default=42)
        command.add_argument("--split", type=Split, choices=list(Split), default=Split.TRAIN)
        command.add_argument("--suite", choices=("replacement", "delivery"), default="replacement")
    generate.add_argument("--count", type=_positive, default=1)
    generate.add_argument("--output", type=Path, default=Path("data/generated/tasks.jsonl"))
    demo.add_argument("--output", type=Path, default=Path("runs/demo.jsonl"))
    demo.add_argument("--max-steps", type=_positive, default=8)
    demo.add_argument("--timing", action="store_true", help="record measured elapsed nanoseconds")

    collect = commands.add_parser("collect", help="record delivery training trajectories")
    induction = commands.add_parser("induce", help="derive capsules from verified training data")
    evaluation = commands.add_parser("evaluate", help="run paired held-out memory conditions")
    comparison = commands.add_parser("compare", help="regenerate Markdown from a results document")
    sources_path = Path("runs/source")
    capsules_path = Path("capsules/induced.jsonl")
    evaluation_path = Path("runs/evaluation")
    collect.add_argument("--output", type=Path, default=sources_path)
    collect.add_argument("--seeds", type=_seeds, default=TRAIN_SEEDS)
    for command in (collect, evaluation):
        command.add_argument("--max-steps", type=_positive, default=MAX_STEPS)
    for command in (induction, evaluation):
        command.add_argument("--trajectories", type=Path, default=sources_path)
    induction.add_argument("--output", type=Path, default=capsules_path)
    induction.add_argument("--created-at", type=_created_at)
    evaluation.add_argument("--capsules", type=Path, default=capsules_path)
    evaluation.add_argument("--output", type=Path, default=evaluation_path)
    evaluation.add_argument(
        "--split", type=Split, choices=(Split.VALIDATION, Split.TEST), default=Split.TEST
    )
    evaluation.add_argument("--seeds", type=_seeds)
    evaluation.add_argument("--no-timing", action="store_true")
    comparison.add_argument("--results", type=Path, default=evaluation_path / "results.json")
    comparison.add_argument("--output", type=Path, default=Path("reports/comparison.md"))

    args = parser.parse_args(argv)
    try:
        if args.command in {"collect", "induce", "evaluate", "compare"}:
            print(encode_json({**_experiment(args), "output": str(args.output)}))
            return 0
        task_generator = generate_delivery_task if args.suite == "delivery" else generate_task
        if args.command == "generate":
            tasks = (
                task_generator(seed, args.split)
                for seed in range(args.seed, args.seed + args.count)
            )
            write_jsonl(args.output, tasks)
            print(encode_json({"task_count": args.count, "output": str(args.output)}))
            return 0

        trajectory = run_task(
            task_generator(args.seed, args.split),
            DeliveryReferenceAgent() if args.suite == "delivery" else OfflineReferenceAgent(),
            max_steps=args.max_steps,
            measure_time=args.timing,
        )
        write_trajectory(args.output, trajectory)
    except (OSError, ValueError) as error:
        print(f"trajyn: {error}", file=sys.stderr)
        return 2

    print(
        encode_json(
            {
                "output": str(args.output),
                "trajectory_id": trajectory.trajectory_id,
                "step_count": len(trajectory.steps),
                "verification": trajectory.verification,
            }
        )
    )
    return 0 if trajectory.verification.passed else 1
