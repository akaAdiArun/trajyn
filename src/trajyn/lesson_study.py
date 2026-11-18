"""Experiment 003 operator entry point. Run with python -m trajyn.lesson_study."""

import argparse
import importlib
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Any, cast

from trajyn.agent import AgentContext, MemoryPolicy
from trajyn.benchmark import DELIVERY_V3, generate_delivery_task
from trajyn.branching import BranchTransfer
from trajyn.capability import CapabilityCapsule, read_capsules
from trajyn.delivery_agent import DeliveryReferenceAgent
from trajyn.induction import induce
from trajyn.lesson import (
    Activation,
    EvidenceTransfer,
    Exclusion,
    Lesson,
    LessonBinding,
    LessonEvidence,
    read_lesson,
    validate_lesson,
)
from trajyn.lesson_learning import RecordedConnection, learn, prompt_for, tool_contracts
from trajyn.lesson_protocol import (
    CREATED_AT,
    DEV_SEEDS,
    MAX_STEPS,
    OPTIONS,
    TRAIN_SEEDS,
    artifact_hashes,
    check_hashes,
    committed_freeze,
    design,
    digest,
    read_json,
    reference_replays,
    save_json,
)
from trajyn.models import (
    AgentDecision,
    AgentIdentity,
    DeliveryTask,
    Split,
    Trajectory,
    public_task,
)
from trajyn.ollama import LocalModel, OllamaAgent, OllamaConnection, OllamaError
from trajyn.provenance import read_trajectory, replay_trajectory
from trajyn.recording import encode_json, write_jsonl, write_trajectory
from trajyn.runner import environment_for, run_task

DEFAULT_FREEZE = Path("docs/EXPERIMENT_003_FROZEN.json")


@contextmanager
def study_lock(root: Path) -> Iterator[None]:
    """OS advisory lock is automatically released on exit, including process failure."""
    root.parent.mkdir(parents=True, exist_ok=True)
    with root.with_suffix(".lock").open("a+b") as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        if os.name == "nt":
            msvcrt = importlib.import_module("msvcrt")

            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl = importlib.import_module("fcntl")

            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def runtime_hashes() -> dict[str, str]:
    return artifact_hashes(Path(__file__).parent, exclude=("__pycache__",))


def models(connection: OllamaConnection) -> tuple[LocalModel, LocalModel]:
    return connection.model("qwen3:8b"), connection.model("granite4:3b")


def policy_for(
    arm: str, lesson: Lesson, task: DeliveryTask, capsules: tuple[CapabilityCapsule, ...]
) -> MemoryPolicy | None:
    if arm == "A":
        return None
    if arm == "F":
        return BranchTransfer(public_task(task), environment_for(task).tools, capsules)
    if arm in {"G", "G-static"}:
        return EvidenceTransfer(lesson, static=arm == "G-static")
    raise ValueError("unknown study arm")


def audit_record(policy: MemoryPolicy | None, turns: list[dict[str, Any]]) -> dict[str, object]:
    delivered = tuple(t["after_step"] for t in turns if t["memory"] is not None and t["responded"])
    if isinstance(policy, EvidenceTransfer):
        return {"decisions": policy.decisions, "offered": policy.offered, "delivered": delivered}
    if isinstance(policy, BranchTransfer):
        return {
            "transitions": policy.transitions,
            "considerations": policy.considerations,
            "offered": policy.prompt_steps,
            "delivered": delivered,
        }
    return {"delivered": delivered}


class AuditedAgent:
    def __init__(self, agent: OllamaAgent, output: Path | None) -> None:
        self.agent = agent
        self.identity = agent.identity
        self.output = output
        self.turns: list[dict[str, Any]] = []

    def decide(self, context: AgentContext) -> AgentDecision | None:
        before = self.agent.call_count
        record: dict[str, Any] = {
            "after_step": len(context.steps),
            "memory": context.memory,
            "prompt_hash": digest(prompt_for(context)),
            "responded": False,
            "call": None,
        }
        self.turns.append(record)
        if self.output is not None:
            save_json(self.output / "progress.json", self.turns)
        decision = self.agent.decide(context)
        if self.agent.call_count > before:
            record["call"] = self.agent.call_count
            connection = self.agent.connection
            assert isinstance(connection, RecordedConnection)
            record["responded"] = connection.calls[-1]["status"] == "responded"
        if self.output is not None:
            save_json(self.output / "progress.json", self.turns)
        return decision


def attempt(
    root: Path,
    task: DeliveryTask,
    connection: OllamaConnection,
    model: LocalModel,
    policy: MemoryPolicy | None = None,
    deadline: float | None = None,
) -> dict[str, Any]:
    if root.exists():
        raise ValueError("attempt directory already exists")
    root.mkdir(parents=True)
    save_json(root / "started.json", {"task": task, "model": model})
    recorded = RecordedConnection(connection, root / "calls", deadline)
    agent = OllamaAgent(recorded, model)
    audited = AuditedAgent(agent, root)
    trace = run_task(task, audited, max_steps=MAX_STEPS, memory_policy=policy)
    write_trajectory(root / "trace.jsonl", trace)
    incomplete = any(call["status"] != "responded" for call in recorded.calls)
    result = {
        "trajectory_id": trace.trajectory_id,
        "status": "incomplete" if incomplete else "complete",
        "verified": trace.verification.passed,
        "termination": agent.termination,
        "model": model,
        "turns": audited.turns,
        "audit": audit_record(policy, audited.turns),
        "calls": agent.call_count,
        "input_tokens": agent.input_tokens,
        "output_tokens": agent.output_tokens,
        "proposals": agent.proposals,
    }
    save_json(root / "result.json", result)
    save_json(root / "seal.json", artifact_hashes(root))
    return result


def completed(folder: Path) -> Path | None:
    for path in sorted(folder.glob("try-*"), reverse=True):
        if (path / "seal.json").exists():
            check_hashes(path, read_json(path / "seal.json"))
            if read_json(path / "result.json")["status"] == "complete":
                return path
    return None


def next_attempt(folder: Path) -> Path:
    number = max((int(p.name.removeprefix("try-")) for p in folder.glob("try-*")), default=0) + 1
    return folder / f"try-{number:04}"


def source_pool(root: Path) -> tuple[Trajectory, ...]:
    traces = []
    for seed in TRAIN_SEEDS:
        path = completed(root / "sources" / str(seed))
        if path is not None:
            traces.append(read_trajectory(path / "trace.jsonl"))
    return tuple(traces)


def development_pool(root: Path) -> tuple[Trajectory, ...]:
    return tuple(
        read_trajectory(root / f"references/validation/{seed}.jsonl") for seed in DEV_SEEDS
    )


def scripted_contrasts(root: Path) -> tuple[Trajectory, ...]:
    """Explicitly labeled training counterexamples, never a model attempt."""
    result = []
    for seed in TRAIN_SEEDS[:2]:

        class StopBeforeConsumer(DeliveryReferenceAgent):
            identity = AgentIdentity("scripted", "stop-before-handoff-counterexample", "1")

            def decide(self, context: AgentContext) -> AgentDecision | None:
                if any(s.observation.data.get("receipt_id") for s in context.steps):
                    return None
                return super().decide(context)

        trace = run_task(
            generate_delivery_task(seed, Split.TRAIN, workflow=DELIVERY_V3),
            StopBeforeConsumer(),
            max_steps=MAX_STEPS,
        )
        write_trajectory(root / "scripted-counterexamples" / f"{seed}.jsonl", trace)
        result.append(trace)
    return tuple(result)


def reuse_sources(root: Path, archive: Path, source: LocalModel, target: LocalModel) -> None:
    """Replay and identity-check a complete source corpus before copying its records."""
    from trajyn.lesson_report import replay_attempt

    if root.resolve().is_relative_to(archive.resolve()):
        raise ValueError("retry output must be outside the original archive")
    metadata = read_json(archive / "models.json")
    if metadata["source"] != read_json_value(source) or metadata["target"] != read_json_value(
        target
    ):
        raise ValueError("source archive model identities differ from installed models")
    old_design = read_json(archive / "design.json")
    new_design = read_json_value(design())
    if {k: v for k, v in old_design.items() if k != "induction_revision"} != {
        k: v for k, v in new_design.items() if k != "induction_revision"
    }:
        raise ValueError("source archive uses a different study design")
    checked = []
    for seed in TRAIN_SEEDS:
        folder = completed(archive / "sources" / str(seed))
        if folder is None:
            raise ValueError(f"source archive lacks a complete attempt for training seed {seed}")
        task = generate_delivery_task(seed, Split.TRAIN, workflow=DELIVERY_V3)
        replay_attempt(folder, task, source)
        trace = read_trajectory(folder / "trace.jsonl")
        if trace.agent != AgentIdentity("ollama", source.name, source.digest):
            raise ValueError(f"source trajectory model identity changed for seed {seed}")
        checked.append((folder, folder.relative_to(archive), trace.trajectory_id))
    for folder, relative, _ in checked:
        destination = root / relative
        if destination.exists():
            if artifact_hashes(destination) != artifact_hashes(folder):
                raise ValueError("retry source records differ from their original archive")
        else:
            shutil.copytree(folder, destination)
    save_json(
        root / "source-import.json",
        {
            "source_archive": archive.as_posix(),
            "source_model": source,
            "target_model": target,
            "attempts": {relative.as_posix(): identity for _, relative, identity in checked},
            "files": artifact_hashes(archive / "sources"),
        },
    )


def prepare(
    root: Path, connection: OllamaConnection, freeze: Path, source_archive: Path | None = None
) -> dict[str, object]:
    deadline = monotonic() + 4 * 60 * 60
    if (root / "manifest.json").exists():
        return {
            "status": "already_frozen",
            "resume": f"python -m trajyn.lesson_study run --output {root}",
        }
    root.mkdir(parents=True, exist_ok=True)
    save_json(root / "design.json", design())
    references = reference_replays(root)
    try:
        source, target = models(connection)
        catalog = {"source": source, "target": target, "server": connection.api("/api/version")}
        if (root / "models.json").exists() and read_json(root / "models.json") != read_json_value(
            catalog
        ):
            raise ValueError("installed models or server changed during source collection")
        save_json(root / "models.json", catalog)
    except OllamaError as error:
        save_json(
            root / "status.json",
            {
                "status": "blocked",
                "reason": str(error),
                "target_attempts": 0,
                "learned_lesson": None,
            },
        )
        return cast(dict[str, object], read_json(root / "status.json"))
    if source_archive is not None:
        reuse_sources(root, source_archive, source, target)
    for seed in TRAIN_SEEDS:
        if monotonic() >= deadline or len(list((root / "sources").glob("*/try-*"))) >= 14:
            break
        folder = root / "sources" / str(seed)
        if completed(folder) is not None:
            continue
        attempt(
            next_attempt(folder),
            generate_delivery_task(seed, Split.TRAIN, workflow=DELIVERY_V3),
            connection,
            source,
            deadline=deadline,
        )
        save_json(
            root / "source-progress.json", {"finished_training_cases": len(source_pool(root))}
        )
    sources = source_pool(root)
    if len(sources) != len(TRAIN_SEEDS):
        return {"status": "incomplete_sources", "completed": len(sources), "model_attempt_cap": 14}
    contrasts = scripted_contrasts(root)
    lesson = learn(root, connection, source, sources + contrasts, development_pool(root), deadline)
    if lesson is None:
        if monotonic() >= deadline - 1:
            return {"status": "invocation_cap_reached", "resume": "repeat prepare"}
        save_json(root / "status.json", {"status": "no_valid_learned_lesson", "target_attempts": 0})
        return cast(dict[str, object], read_json(root / "status.json"))
    capsules = []
    for trace in sources:
        try:
            capsules.append(induce(trace, created_at=datetime.fromisoformat(CREATED_AT)))
        except ValueError:
            continue
    write_jsonl(root / "capsules.jsonl", capsules)
    # All held-out interfaces must retrieve a compatible candidate before any targets run.
    from trajyn.transfer import select_capsule

    availability = {}
    for case in read_json_value(design())["cases"]:
        task = generate_delivery_task(case["seed"], Split.TEST, workflow=DELIVERY_V3)
        availability[str(task.seed)] = (
            select_capsule(public_task(task), environment_for(task).tools, tuple(capsules)).memory
            is not None
        )
    payload = {
        "design": design(),
        "models": catalog,
        "lesson_id": lesson.lesson_id,
        "references": references,
        "runtime": runtime_hashes(),
        "F_available": availability,
        "files": artifact_hashes(root, exclude=("status.json",)),
    }
    manifest = {**payload, "manifest_id": digest(payload)}
    if freeze.exists():
        raise ValueError("choose a new freeze path instead of overwriting a frozen protocol")
    save_json(root / "manifest.json", manifest)
    save_json(freeze, manifest)
    return {
        "status": "ready_to_freeze",
        "lesson_id": lesson.lesson_id,
        "next": f"git add {freeze.as_posix()} && git commit -m 'Freeze Experiment 003 protocol'",
    }


def read_json_value(value: object) -> Any:
    import json

    return json.loads(encode_json(value))


def verify_frozen(root: Path, freeze: Path, *, require_commit: bool = True) -> dict[str, Any]:
    manifest = read_json(root / "manifest.json")
    if read_json(freeze) != manifest:
        raise ValueError("archive and committed protocol disagree")
    payload = {k: v for k, v in manifest.items() if k != "manifest_id"}
    if digest(payload) != manifest["manifest_id"] or manifest["design"] != read_json_value(
        design()
    ):
        raise ValueError("frozen protocol differs from the fixed design")
    if manifest["runtime"] != runtime_hashes():
        raise ValueError("runtime changed since protocol freeze")
    check_hashes(root, manifest["files"])
    inputs = artifact_hashes(
        root,
        exclude=(
            "manifest.json",
            "status.json",
            "targets/",
            "target-progress.json",
            "report.json",
            "report.md",
        ),
    )
    if inputs != manifest["files"]:
        raise ValueError("frozen input file inventory changed")
    if require_commit:
        committed_freeze(freeze)
    return cast(dict[str, Any], manifest)


def run(root: Path, connection: OllamaConnection, freeze: Path) -> dict[str, object]:
    deadline = monotonic() + 4 * 60 * 60
    manifest = verify_frozen(root, freeze)
    source, target = models(connection)
    if read_json_value(source) != manifest["models"]["source"] or (
        read_json_value(target) != manifest["models"]["target"]
    ):
        raise ValueError("installed model identities differ from the frozen models")
    lesson = read_lesson(root / "lesson.json", tool_contracts(source_pool(root)))
    capsules = read_capsules(root / "capsules.jsonl")
    validate_lesson(lesson, source_pool(root), development_pool(root))
    for case in manifest["design"]["cases"]:
        for arm in case["arms"]:
            if arm == "F" and not manifest["F_available"][str(case["seed"])]:
                continue
            folder = root / "targets" / f"{case['seed']}-{arm}"
            if completed(folder) is not None:
                continue
            if monotonic() >= deadline:
                return {"status": "invocation_cap_reached", "resume": "run the same command"}
            task = generate_delivery_task(case["seed"], Split.TEST, workflow=DELIVERY_V3)
            result = attempt(
                next_attempt(folder),
                task,
                connection,
                target,
                policy_for(arm, lesson, task, capsules),
                deadline,
            )
            save_json(
                root / "target-progress.json",
                {
                    "seed": case["seed"],
                    "arm": arm,
                    "status": result["status"],
                    "manifest_id": manifest["manifest_id"],
                },
            )
    from trajyn.lesson_report import replay_study

    return replay_study(root, freeze)


def fixture_lesson(sources: tuple[Trajectory, ...]) -> Lesson:
    """Hand-authored deterministic test learner. Never invoked by live prepare/run."""
    evidence = []
    producers = set()
    for trace in sources:
        for step in trace.steps:
            if (
                step.action.tool in {"ship_replacement", "locker_replacement"}
                and step.observation.ok
            ):
                consumer = next(s for s in trace.steps if s.action.tool == "close_case")
                evidence.append(LessonEvidence(trace.trajectory_id, step.index, consumer.index))
                producers.add(step.action.tool)
                break
    return Lesson(
        1,
        DELIVERY_V3,
        tuple(sorted(producers)),
        "close_case",
        "receipt_id",
        ("remedy_exists", "remedy_posted"),
        tuple(Activation),
        tuple(Exclusion),
        (
            LessonBinding("ticket_id", "producer.action", "ticket_id"),
            LessonBinding("receipt_id", "producer.observation", "receipt_id"),
        ),
        tuple(evidence),
        tool_contracts(sources),
    )


def demo(root: Path) -> dict[str, object]:
    from trajyn.lesson_report import replay_demo

    if (root / "demo.json").exists():
        return replay_demo(root)
    root.mkdir(parents=True, exist_ok=True)
    sources = tuple(
        run_task(
            generate_delivery_task(s, workflow=DELIVERY_V3),
            DeliveryReferenceAgent(),
            max_steps=MAX_STEPS,
        )
        for s in TRAIN_SEEDS[:2]
    )
    for index, trace in enumerate(sources):
        write_trajectory(root / f"fixture-sources/{index}.jsonl", trace)
    reference_replays(root)
    lesson = fixture_lesson(sources)
    validate_lesson(lesson, sources, development_pool(root), require_model=False)
    save_json(root / "lesson.json", lesson)
    records = []
    for case in read_json_value(design())["cases"]:
        task = generate_delivery_task(case["seed"], Split.TEST, workflow=DELIVERY_V3)
        # A target that ignores every hint demonstrates that policy does not select actions.
        policy = EvidenceTransfer(lesson)
        trace = run_task(task, DeliveryReferenceAgent(), max_steps=MAX_STEPS, memory_policy=policy)
        replay_trajectory(trace)
        name = f"targets/{task.seed}.jsonl"
        write_trajectory(root / name, trace)
        records.append({"trace": name, "decisions": policy.decisions, "offered": policy.offered})
    save_json(
        root / "demo.json",
        {
            "kind": "deterministic_fixture_not_model_learning",
            "cases": records,
            "lesson_id": lesson.lesson_id,
        },
    )
    save_json(root / "demo-seal.json", artifact_hashes(root))
    return replay_demo(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("demo", "prepare", "run", "replay"))
    parser.add_argument("--output", type=Path, default=Path("runs/experiment-003"))
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument(
        "--source-archive",
        type=Path,
        help="reuse a complete, independently replayed training source archive",
    )
    args = parser.parse_args(argv)
    if args.source_archive is not None and args.command != "prepare":
        parser.error("--source-archive is supported by prepare")
    try:
        with study_lock(args.output):
            if args.command == "demo":
                result = demo(args.output)
            elif args.command == "replay":
                from trajyn.lesson_report import replay_study

                result = replay_study(args.output, args.freeze)
            elif args.command == "prepare":
                result = prepare(
                    args.output,
                    OllamaConnection(args.ollama_url, OPTIONS),
                    args.freeze,
                    args.source_archive,
                )
            else:
                result = run(args.output, OllamaConnection(args.ollama_url, OPTIONS), args.freeze)
        print(encode_json(result))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"lesson-study: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
