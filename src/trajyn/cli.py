"""Generate seeded tasks and run the offline reference agent."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from trajyn.agent import OfflineReferenceAgent
from trajyn.environment import generate_task
from trajyn.models import Split
from trajyn.recording import encode_json, write_jsonl, write_trajectory
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trajyn", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="write seeded tasks as JSONL")
    demo = commands.add_parser("demo", help="run the rules-based offline reference agent")
    for command in (generate, demo):
        command.add_argument("--seed", type=_non_negative, default=42)
        command.add_argument("--split", type=Split, choices=list(Split), default=Split.TRAIN)
    generate.add_argument("--count", type=_positive, default=1)
    generate.add_argument("--output", type=Path, default=Path("data/generated/tasks.jsonl"))
    demo.add_argument("--output", type=Path, default=Path("runs/demo.jsonl"))
    demo.add_argument("--max-steps", type=_positive, default=8)
    demo.add_argument("--timing", action="store_true", help="record measured elapsed nanoseconds")

    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            tasks = (
                generate_task(seed, args.split) for seed in range(args.seed, args.seed + args.count)
            )
            write_jsonl(args.output, tasks)
            print(encode_json({"task_count": args.count, "output": str(args.output)}))
            return 0

        trajectory = run_task(
            generate_task(args.seed, args.split),
            OfflineReferenceAgent(),
            max_steps=args.max_steps,
            measure_time=args.timing,
        )
        write_trajectory(args.output, trajectory)
    except OSError as error:
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
