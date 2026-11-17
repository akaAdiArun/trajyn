import json
from pathlib import Path

import pytest

from trajyn.agent import AgentContext
from trajyn.benchmark import DELIVERY_V2, generate_delivery_task
from trajyn.models import Observation, Step, ToolAction, Usage, public_task
from trajyn.ollama import InferenceOptions, LocalModel, OllamaAgent, OllamaConnection
from trajyn.pilot import run_pilot
from trajyn.provenance import read_trajectory
from trajyn.recording import encode_json
from trajyn.runner import environment_for


class FixtureConnection(OllamaConnection):
    def __init__(self, options: InferenceOptions | None = None) -> None:
        super().__init__("http://127.0.0.1:11537", options or InferenceOptions())
        self.requests: list[dict[str, object]] = []
        self.tool_ticket: str | None = None

    def model(self, name: str) -> LocalModel:
        return LocalModel(name, name.ljust(64, "0"), name, name == "first")

    def api(self, path: str, payload: dict[str, object] | None = None) -> dict[str, object]:
        if path == "/api/version":
            return {"version": "fixture"}
        assert path == "/api/chat"
        assert payload is not None
        self.requests.append(payload)
        calls = []
        if self.tool_ticket is not None:
            calls.append(
                {
                    "function": {
                        "name": "read_case",
                        "arguments": {"ticket_id": self.tool_ticket},
                    }
                }
            )
        content = (
            encode_json({"action": "read_case", "arguments": {"ticket_id": self.tool_ticket}})
            if "format" in payload and self.tool_ticket
            else "excluded"
        )
        return {
            "message": {"tool_calls": calls, "thinking": "excluded", "content": content},
            "prompt_eval_count": 32,
            "eval_count": 7,
        }


def test_local_agent_exposes_public_tools_and_records_only_public_decision() -> None:
    connection = FixtureConnection()
    task = generate_delivery_task(200)
    connection.tool_ticket = task.ticket_id
    agent = OllamaAgent(connection, connection.model("first"))
    live_task = public_task(task)
    decision = agent.decide(AgentContext(live_task, environment_for(task).tools, (), 8))
    assert decision is not None
    assert decision.action == ToolAction("read_case", {"ticket_id": task.ticket_id})
    assert decision.usage == Usage(32, 7)
    assert agent.call_count == 1
    assert "excluded" not in encode_json(decision)
    request = connection.requests[0]
    assert request["think"] is False
    assert task.task_id not in encode_json(request)
    assert "inspect_parcel" in encode_json(request["tools"])


def test_schema_mode_executes_a_model_selected_action() -> None:
    connection = FixtureConnection(InferenceOptions(tool_mode="json"))
    task = generate_delivery_task(202)
    connection.tool_ticket = task.ticket_id
    agent = OllamaAgent(connection, connection.model("second"))
    decision = agent.decide(AgentContext(public_task(task), environment_for(task).tools, (), 8))
    assert decision is not None
    assert decision.action == ToolAction("read_case", {"ticket_id": task.ticket_id})
    request = connection.requests[0]
    assert "tools" not in request
    assert '"enum":["read_case","inspect_parcel"' in encode_json(request["format"])
    assert "Public tool history" in encode_json(request["messages"])


def test_public_grounding_keeps_original_proposal_and_ignores_failed_observations() -> None:
    connection = FixtureConnection(InferenceOptions(tool_mode="json", grounding="public"))
    connection.tool_ticket = "model-proposed-id"
    task = generate_delivery_task(202)
    agent = OllamaAgent(connection, connection.model("second"))
    failed = Step(1, ToolAction("read_case"), Observation(False, "failed", {"ticket_id": "fake"}))
    context = AgentContext(public_task(task), environment_for(task).tools, (failed,), 8)
    decision = agent.decide(context)
    assert decision is not None
    assert decision.action == ToolAction("read_case", {"ticket_id": task.ticket_id})
    (proposal,) = agent.proposals
    assert proposal.original == ToolAction("read_case", {"ticket_id": "model-proposed-id"})
    assert proposal.bindings[0].source_step == 0
    assert '"required":["action"]' in encode_json(connection.requests[0]["format"])


def test_native_mode_rejects_deterministic_assistance() -> None:
    with pytest.raises(ValueError, match="JSON action mode"):
        InferenceOptions(grounding="public")


def test_local_pilot_preserves_source_failure_and_prevents_unfounded_transfer(
    tmp_path: Path,
) -> None:
    connection = FixtureConnection()
    outcome = run_pilot(tmp_path, connection, "first", "second", (0,), (200,))
    assert outcome["status"] == "no_inducible_sources"
    assert outcome["target_trials"] == 0
    assert len(connection.requests) == 1
    trajectory = read_trajectory(tmp_path / "source" / "source-0.jsonl")
    assert not trajectory.verification.passed
    assert trajectory.agent.provider == "ollama"
    assert "model_returned_no_tool" in (tmp_path / "pilot.json").read_text(encoding="utf-8")


def test_local_adapter_requires_a_loopback_endpoint_and_distinct_families(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="loopback"):
        OllamaConnection("https://example.com")
    with pytest.raises(ValueError, match="different model families"):
        run_pilot(tmp_path, FixtureConnection(), "first", "first", (0,), (200,))


def test_pilot_reuses_verified_sources_without_new_source_calls(tmp_path: Path) -> None:
    archive = Path(__file__).resolve().parents[1] / "examples/experiment-001/run"
    original = json.loads((archive / "pilot.json").read_text(encoding="utf-8"))
    source = LocalModel(**original["source_model"])

    class ArchivedSourceConnection(FixtureConnection):
        def model(self, name: str) -> LocalModel:
            return source if name == source.name else super().model(name)

    connection = ArchivedSourceConnection()
    outcome = run_pilot(
        tmp_path,
        connection,
        source.name,
        "second",
        tuple(original["source_seeds"]),
        (530,),
        12,
        workflow=DELIVERY_V2,
        branch_aware=True,
        source_archive=archive,
    )
    assert outcome["status"] == "completed"
    assert len(connection.requests) == outcome["target_trials"] == 6
    assert all(request["model"] == "second" for request in connection.requests)
    assert (tmp_path / "capsules.jsonl").read_text(encoding="utf-8") == (
        archive / "capsules.jsonl"
    ).read_text(encoding="utf-8")
    metadata = json.loads((tmp_path / "pilot.json").read_text(encoding="utf-8"))
    assert metadata["source_options"] == original["options"]
    assert metadata["source_inference"] == original["source_inference"]
    assert metadata["maximum_model_calls"] == 72
