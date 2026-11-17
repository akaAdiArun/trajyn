import json
from pathlib import Path

import pytest

from trajyn.cli import main
from trajyn.recording import write_jsonl


def test_generate_writes_consecutive_seeds(tmp_path: Path) -> None:
    output = tmp_path / "data" / "tasks.jsonl"
    args = ["generate", "--seed", "42", "--count", "3", "--split", "validation"]
    assert main([*args, "--output", str(output)]) == 0
    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert [record["seed"] for record in records] == [42, 43, 44]
    assert all(record["split"] == "validation" for record in records)
    assert len({record["task_id"] for record in records}) == 3


def test_demo_writes_deterministic_versioned_events(tmp_path: Path) -> None:
    first, second = tmp_path / "first.jsonl", tmp_path / "second.jsonl"
    for output in (first, second):
        assert main(["demo", "--split", "test", "--seed", "42", "--output", str(output)]) == 0
    assert first.read_bytes() == second.read_bytes()
    events = [json.loads(line) for line in first.read_text(encoding="utf-8").splitlines()]
    assert [event["event"] for event in events] == ["start", *(["step"] * 5), "finish"]
    assert {event["schema_version"] for event in events} == {1}
    assert {event["trajectory_id"] for event in events} == {events[0]["trajectory_id"]}
    assert events[0]["task"]["task_id"] == "replacement-test-42"
    assert events[0]["agent"]["provider"] == "offline"
    for index, event in enumerate(events[1:-1], start=1):
        step = event["step"]
        assert step["index"] == index
        assert isinstance(step["action"]["arguments"], dict)
        assert step["observation"]["ok"]
        assert step["elapsed_ns"] is None
    assert events[-1]["verification"] == {
        "verifier": "replacement_state_v1",
        "passed": True,
        "failures": [],
    }


def test_demo_saves_failed_attempt_with_nonzero_exit_code(tmp_path: Path) -> None:
    output = tmp_path / "failed.jsonl"
    assert main(["demo", "--max-steps", "4", "--output", str(output)]) == 1
    finish = json.loads(output.read_text(encoding="utf-8").splitlines()[-1])
    assert finish["stop_reason"] == "step_limit"
    assert finish["verification"]["failures"] == ["ticket_not_resolved_with_replacement"]


@pytest.mark.parametrize(
    "args",
    [["generate", "--seed", "-1"], ["generate", "--count", "0"], ["demo", "--split", "prod"]],
)
def test_cli_rejects_invalid_options(args: list[str]) -> None:
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2


def test_jsonl_write_failure_preserves_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "run.jsonl"
    write_jsonl(output, [{"prior": "result"}])
    original = output.read_bytes()

    with pytest.raises(TypeError, match="not JSON serializable"):
        write_jsonl(output, [{"would": "partially write"}, object()])

    assert output.read_bytes() == original
    assert list(tmp_path.iterdir()) == [output]
