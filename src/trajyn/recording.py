"""Canonical JSON serialization and atomic JSONL trajectory export."""

import json
import os
from collections.abc import Iterable, Mapping
from dataclasses import fields, is_dataclass, replace
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile

from trajyn.models import Trajectory

SCHEMA_VERSION = 1


def _encode_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: getattr(value, field.name) for field in fields(value)}
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def encode_json(value: object) -> str:
    return json.dumps(
        value, default=_encode_value, allow_nan=False, sort_keys=True, separators=(",", ":")
    )


def write_jsonl(path: Path, records: Iterable[object]) -> None:
    """Publish a complete file after all records have been encoded."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
        ) as output:
            temporary = Path(output.name)
            for record in records:
                output.write(encode_json(record) + "\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def trajectory_id(trajectory: Trajectory) -> str:
    content = encode_json(replace(trajectory, trajectory_id=""))
    return f"sha256:{sha256(content.encode('utf-8')).hexdigest()}"


def trajectory_events(trajectory: Trajectory) -> Iterable[dict[str, object]]:
    common = {"schema_version": SCHEMA_VERSION, "trajectory_id": trajectory.trajectory_id}
    yield {
        **common,
        "event": "start",
        "task": trajectory.task,
        "agent": trajectory.agent,
        "max_steps": trajectory.max_steps,
    }
    for step in trajectory.steps:
        yield {**common, "event": "step", "step": step}
    yield {
        **common,
        "event": "finish",
        "stop_reason": trajectory.stop_reason,
        "verification": trajectory.verification,
        "elapsed_ns": trajectory.elapsed_ns,
    }


def write_trajectory(path: Path, trajectory: Trajectory) -> None:
    write_jsonl(path, trajectory_events(trajectory))
