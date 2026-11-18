"""Fixed Experiment 003 design, independent references, and artifact integrity."""

import json
import subprocess
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any

from trajyn.benchmark import DELIVERY_V3, delivery_profiles, generate_delivery_task
from trajyn.delivery_agent import DeliveryReferenceAgent
from trajyn.models import Split
from trajyn.ollama import PROMPT_REVISION, InferenceOptions
from trajyn.recording import encode_json, write_text, write_trajectory
from trajyn.runner import run_task

TRAIN_SEEDS = tuple(range(600, 612))
DEV_SEEDS = tuple(range(804, 816))
TEST_SEEDS = tuple(range(1008, 1032))
ARMS = ("A", "F", "G", "G-static")
OPTIONS = InferenceOptions(timeout_seconds=75, tool_mode="json", grounding="public")
MAX_STEPS = 10
INDUCTION_REVISION = 3
RENDERER_REVISION = 1
CREATED_AT = "2026-11-18T00:00:00+00:00"


def digest(value: object) -> str:
    return sha256(encode_json(value).encode()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: object) -> None:
    write_text(path, encode_json(value) + "\n")


def design() -> dict[str, object]:
    profiles = delivery_profiles(DELIVERY_V3)
    cases = []
    for index, seed in enumerate(TEST_SEEDS):
        profile = profiles["test"][seed % len(profiles["test"])]
        cases.append(
            {
                "seed": seed,
                "split": "test",
                "type": (
                    "familiar" if index < 8 else "different_route" if index < 16 else "look_alike"
                ),
                "family": digest(profile)[:12],
                "profile": profile,
                "arms": ARMS[index % 4 :] + ARMS[: index % 4],
            }
        )
    return {
        "version": 1,
        "dated": CREATED_AT,
        "workflow": DELIVERY_V3,
        "train_seeds": TRAIN_SEEDS,
        "dev_seeds": DEV_SEEDS,
        "cases": cases,
        "profiles": profiles,
        "source_limit": 12,
        "source_attempt_cap_including_scripted": 16,
        "model_source_attempt_cap_including_retries": 14,
        "scripted_counterexamples": 2,
        "induction_calls": 4,
        "induction_output_tokens": 1100,
        "induction_context_tokens": 8192,
        "induction_seeds": [17, 18, 19, 20],
        "induction_temperature": 0,
        "induction_timeout_seconds": 75,
        "max_steps": MAX_STEPS,
        "options": asdict(OPTIONS),
        "prompt_revision": PROMPT_REVISION,
        "induction_revision": INDUCTION_REVISION,
        "renderer_revision": RENDERER_REVISION,
        "source_model": "qwen3:8b",
        "target_model": "granite4:3b",
        "selection": "first valid proposal in call order with all positive producers cited",
        "acceptance": "verified Qwen training flow plus all separate development prefixes",
        "analysis": "matched complete pairs; gains/losses/ties; exact sign test; descriptive "
        "paired bootstrap with seed 1741; report shared profile families",
        "stop": "four hours per invocation; no changed models; no learned lesson means no targets",
    }


def reference_replays(root: Path) -> dict[str, str]:
    """Operator-only reachability evidence, never exposed to induction or target calls."""
    references = {}
    for split, seeds in ((Split.VALIDATION, DEV_SEEDS), (Split.TEST, TEST_SEEDS)):
        for seed in seeds:
            trace = run_task(
                generate_delivery_task(seed, split, workflow=DELIVERY_V3),
                DeliveryReferenceAgent(),
                max_steps=MAX_STEPS,
            )
            if not trace.verification.passed:
                raise ValueError(f"reference cannot reach completion: {split}/{seed}")
            name = f"references/{split}/{seed}.jsonl"
            write_trajectory(root / name, trace)
            references[name] = trace.trajectory_id
    return references


def artifact_hashes(root: Path, *, exclude: tuple[str, ...] = ()) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
        and not any(p.relative_to(root).as_posix().startswith(part) for part in exclude)
    }


def check_hashes(root: Path, expected: dict[str, str]) -> None:
    for name, checksum in expected.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError(f"missing or unsafe artifact: {name}")
        if sha256(path.read_bytes()).hexdigest() != checksum:
            raise ValueError(f"changed artifact: {name}")


def committed_freeze(path: Path) -> str:
    """Require the exact frozen manifest to have a published-history Git object."""
    repository = Path(
        subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
    )
    relative = path.resolve().relative_to(repository.resolve()).as_posix()
    revision = subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", relative], cwd=repository, text=True
    ).strip()
    if not revision:
        raise ValueError("commit the frozen manifest before held-out inference")
    content = subprocess.check_output(["git", "show", f"{revision}:{relative}"], cwd=repository)
    if content.replace(b"\r\n", b"\n") != path.read_bytes().replace(b"\r\n", b"\n"):
        raise ValueError("frozen manifest differs from its committed version")
    return revision
