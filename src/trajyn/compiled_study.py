"""Experiment 003B preparation, execution, and offline replay without Qwen induction."""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from trajyn.benchmark import DELIVERY_V3, generate_delivery_task
from trajyn.induction import induce
from trajyn.lesson_compiler import COMPILER_REVISION, ORIGIN, write_compilation
from trajyn.lesson_protocol import (
    CREATED_AT,
    OPTIONS,
    artifact_hashes,
    design,
    digest,
    read_json,
    reference_replays,
    save_json,
)
from trajyn.lesson_study import (
    development_pool,
    models,
    read_json_value,
    reuse_sources,
    run,
    runtime_hashes,
    source_pool,
    study_lock,
    verify_frozen,
)
from trajyn.models import Split, public_task
from trajyn.ollama import OllamaConnection
from trajyn.recording import write_jsonl
from trajyn.runner import environment_for
from trajyn.transfer import select_capsule

DEFAULT_OUTPUT = Path("runs/experiment-003b")
DEFAULT_FREEZE = Path("docs/EXPERIMENT_003B_FROZEN.json")


def compiled_design() -> dict[str, object]:
    source_collection_fields = {
        "scripted_counterexamples",
        "source_attempt_cap_including_scripted",
        "model_source_attempt_cap_including_retries",
    }
    planned = {
        key: value
        for key, value in design().items()
        if not key.startswith("induction_") and key not in source_collection_fields
    }
    planned.update(
        experiment="003B",
        lesson_origin=ORIGIN,
        compiler_revision=COMPILER_REVISION,
        source_inference_calls=0,
        induction_calls=0,
        selection="all verified handoff evidence; reject unsupported producer/code cross-products",
        stop="four hours per invocation; fixed models; compilation must validate before targets",
        diagnostics="first action and confirmed hint delivery after qualifying receipt; "
        "calls before closure; never reached evidence versus missed and incorrect delivery; "
        "paired call efficiency reported separately from verified completion",
    )
    return planned


def reject_existing_targets(root: Path, *, allow_own: bool = False) -> None:
    """Refuse another live run of these exact held-out task instances."""
    cases = read_json_value(compiled_design())["cases"]
    expected = {
        generate_delivery_task(case["seed"], Split.TEST, workflow=DELIVERY_V3).task_id
        for case in cases
    }
    for start in root.parent.glob("*/targets/*/try-*/started.json"):
        if allow_own and start.is_relative_to(root):
            continue
        record = read_json(start)
        if record["task"]["task_id"] in expected and record["model"]["name"] == "granite4:3b":
            raise ValueError(f"existing target inference for this dataset: {start}")


def prepare_compiled(
    root: Path, connection: OllamaConnection, freeze: Path, source_archive: Path
) -> dict[str, object]:
    reject_existing_targets(root)
    if freeze.exists() or root.exists() and any(root.iterdir()):
        raise ValueError("compiled preparation requires a new output directory and freeze file")
    source, target = models(connection)
    root.mkdir(parents=True, exist_ok=True)
    save_json(root / "design.json", compiled_design())
    save_json(
        root / "models.json",
        {"source": source, "target": target, "server": connection.api("/api/version")},
    )
    reuse_sources(root, source_archive, source, target)
    references = reference_replays(root)
    sources = source_pool(root)
    lesson = write_compilation(root, sources, development_pool(root))
    capsules = []
    exclusions = []
    for trace in sources:
        try:
            capsules.append(induce(trace, created_at=datetime.fromisoformat(CREATED_AT)))
        except ValueError as error:
            exclusions.append({"trajectory_id": trace.trajectory_id, "reason": str(error)})
    write_jsonl(root / "capsules.jsonl", capsules)
    save_json(root / "capsule-exclusions.json", exclusions)
    availability = {}
    for case in read_json_value(compiled_design())["cases"]:
        task = generate_delivery_task(case["seed"], Split.TEST, workflow=DELIVERY_V3)
        availability[str(task.seed)] = (
            select_capsule(public_task(task), environment_for(task).tools, tuple(capsules)).memory
            is not None
        )
    payload = {
        "experiment": "003B",
        "compiler_revision": COMPILER_REVISION,
        "lesson_origin": ORIGIN,
        "design": compiled_design(),
        "models": read_json(root / "models.json"),
        "lesson_id": lesson.lesson_id,
        "observed_routes": read_json(root / "compiler-audit.json")["observed_routes"],
        "source_archive": read_json(root / "source-import.json"),
        "prior_induction_result": "three revisions, no accepted lesson, zero target attempts",
        "references": references,
        "F_available": availability,
        "runtime": runtime_hashes(),
        "files": artifact_hashes(root),
    }
    manifest = {**payload, "manifest_id": digest(payload)}
    save_json(root / "manifest.json", manifest)
    save_json(freeze, manifest)
    verify_frozen(root, freeze, require_commit=False)
    from trajyn.lesson_report import replay_study

    replay_study(root, freeze, require_commit=False)
    return {
        "status": "ready_to_freeze",
        "experiment": "003B",
        "lesson_id": lesson.lesson_id,
        "routes": payload["observed_routes"],
        "manifest_id": manifest["manifest_id"],
        "source_attempts_reused": len(sources),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "replay"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--source-archive", type=Path, default=Path("runs/experiment-003"))
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    args = parser.parse_args(argv)
    try:
        with study_lock(args.output.parent / "experiment-003b-live"), study_lock(args.output):
            if args.command == "prepare":
                result = prepare_compiled(
                    args.output,
                    OllamaConnection(args.ollama_url, OPTIONS),
                    args.freeze,
                    args.source_archive,
                )
            elif args.command == "run":
                reject_existing_targets(args.output, allow_own=True)
                result = run(args.output, OllamaConnection(args.ollama_url, OPTIONS), args.freeze)
            else:
                from trajyn.lesson_report import replay_study

                result = replay_study(args.output, args.freeze)
        from trajyn.recording import encode_json

        print(encode_json(result))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"compiled-study: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
