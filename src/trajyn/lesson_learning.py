"""Bounded local induction from replayed training contrasts, with every proposal saved."""

import json
from dataclasses import replace
from pathlib import Path
from time import monotonic

from trajyn.agent import AgentContext
from trajyn.lesson import (
    Activation,
    Exclusion,
    Lesson,
    LessonEvidence,
    decode_lesson,
    valid_receipt,
    validate_lesson,
)
from trajyn.lesson_protocol import (
    INDUCTION_REVISION,
    OPTIONS,
    digest,
    read_json,
    save_json,
)
from trajyn.models import Split, ToolSpec, Trajectory, public_task
from trajyn.ollama import LocalModel, OllamaConnection, OllamaError, _messages
from trajyn.provenance import replay_trajectory
from trajyn.recording import encode_json
from trajyn.runner import environment_for


def tool_contracts(sources: tuple[Trajectory, ...]) -> tuple[ToolSpec, ...]:
    tools: dict[str, ToolSpec] = {}
    for source in sources:
        for tool in environment_for(source.task).tools:
            # Refund approval schemas can differ. Only schemas used by the lesson
            # are selected after decoding, and each replacement/close schema is fixed.
            if tool.name in tools and tools[tool.name] != tool:
                continue
            tools[tool.name] = tool
    return tuple(tools[name] for name in sorted(tools))


def induction_schema() -> dict[str, object]:
    """Constrain record shapes without supplying a lesson or citation values."""
    text = {"type": "string", "minLength": 1}
    names = {"type": "array", "minItems": 1, "items": text}
    binding = {
        "type": "object",
        "additionalProperties": False,
        "properties": {field: text for field in ("parameter", "origin", "field")},
        "required": ["parameter", "origin", "field"],
    }
    citation = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "trajectory_id": text,
            "producer_step": {"type": "integer", "minimum": 1},
            "consumer_step": {"type": "integer", "minimum": 1},
        },
        "required": ["trajectory_id", "producer_step", "consumer_step"],
    }
    properties = {
        "version": {"type": "integer", "minimum": 1},
        "workflow": text,
        "producer_tools": names,
        "consumer_tool": text,
        "output_field": text,
        "success_codes": names,
        "activation": names,
        "exclusions": names,
        "bindings": {"type": "array", "minItems": 1, "items": binding},
        "evidence": {"type": "array", "minItems": 1, "items": citation},
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties),
    }


def handoff_candidates(sources: tuple[Trajectory, ...]) -> dict[str, tuple[LessonEvidence, ...]]:
    """Enumerate witnessed replacement handoffs, separately for each producing tool."""
    candidates: dict[str, list[LessonEvidence]] = {
        "ship_replacement": [],
        "locker_replacement": [],
    }
    for source in sources:
        replay_trajectory(source)
        if source.task.split != Split.TRAIN:
            raise ValueError("handoff candidates require training records")
        if not (
            source.verification.passed
            and source.agent.provider == "ollama"
            and source.agent.model == "qwen3:8b"
        ):
            continue
        for producer in source.steps:
            receipt = producer.observation.data.get("receipt_id")
            if not (
                producer.action.tool in candidates
                and producer.observation.ok
                and producer.observation.code in {"remedy_posted", "remedy_exists"}
                and producer.action.arguments.get("ticket_id") == source.task.ticket_id
                and valid_receipt(receipt)
            ):
                continue
            for consumer in source.steps[producer.index :]:
                if (
                    consumer.action.tool == "close_case"
                    and consumer.observation.ok
                    and consumer.observation.code == "case_closed"
                    and consumer.action.arguments.get("ticket_id") == source.task.ticket_id
                    and consumer.action.arguments.get("receipt_id") == receipt
                ):
                    citation = LessonEvidence(source.trajectory_id, producer.index, consumer.index)
                    if citation not in candidates[producer.action.tool]:
                        candidates[producer.action.tool].append(citation)
    return {tool: tuple(references) for tool, references in candidates.items()}


def induction_messages(
    sources: tuple[Trajectory, ...], *, revision: int = INDUCTION_REVISION
) -> list[dict[str, object]]:
    if revision not in (1, 2, 3):
        raise ValueError("unsupported induction revision")
    for source in sources:
        replay_trajectory(source)
        if source.task.split != Split.TRAIN:
            raise ValueError("learner may see training only")
    # Only training records enter induction. Revision 3 adds enumerated evidence
    # references for the predefined handoff, preserving the earlier prompt revisions.
    selected: list[Trajectory] = []
    for passed in (True, False):
        routes: set[tuple[str, ...]] = set()
        for source in sources:
            route = tuple(s.action.tool for s in source.steps)
            if source.verification.passed == passed and route not in routes:
                selected.append(source)
                routes.add(route)
            if len(routes) == 2:
                break
    contrasts = [
        {
            "trajectory_id": t.trajectory_id,
            "origin": t.agent,
            "verified": t.verification.passed,
            "steps": [
                {"index": s.index, "action": s.action, "observation": s.observation}
                for s in t.steps
            ],
        }
        for t in selected
    ]
    vocabulary = {
        "version": 1,
        "workflow": public_task(sources[0].task).workflow,
        "fields": [
            "ticket_id",
            "parcel_id",
            "product_id",
            "receipt_id",
            "approval_id",
            "status",
            "available",
        ],
        "activation": list(Activation),
        "exclusions": list(Exclusion),
        "origins": ["producer.action", "producer.observation"],
    }
    return [
        {
            "role": "system",
            "content": (
                "Compare replay-checked attempts. Propose ONE narrow successful handoff between "
                "actions with applicability boundaries. Derive operations, value flow, and "
                "symbolic bindings from the records. Cite producer and later consumer steps. "
                "Include all safety predicates in order. Use only the restricted vocabulary "
                "and public tools. Exclude instance IDs from reusable fields. Return a JSON object "
                "with version, workflow, producer_tools (sorted), consumer_tool, output_field, "
                "success_codes (sorted), activation, exclusions, "
                + (
                    "bindings (parameter, origin, field), "
                    "and evidence (trajectory_id, producer_step, consumer_step). "
                    "No free prose or code."
                    if revision == 1
                    else "bindings as an array of objects with parameter, origin, and field. "
                    "evidence must be a nonempty array of citation objects with trajectory_id, "
                    "producer_step, and consumer_step. Cite the action producing the value and "
                    "a strictly later action consuming it. No free prose or code."
                )
                + (
                    " This revision tests evidence-grounded selection within a predefined handoff. "
                    "Select one or both supported replacement routes in positive_candidates "
                    "and cite their evidence. Each entry references a replay-verified successful "
                    "producer and later consumer. Use only the selected route names as "
                    "producer_tools. Derive bindings and success codes from those producing and "
                    "consuming steps, using only arguments required by the consumer. "
                    "Contrasts are not positive candidates."
                    if revision == 3
                    else ""
                )
            ),
        },
        {
            "role": "user",
            "content": encode_json(
                {
                    "revision": revision,
                    "vocabulary": vocabulary,
                    "public_tool_contracts": tool_contracts(sources),
                    "contrasts": contrasts,
                    **(
                        {"positive_candidates": handoff_candidates(sources)}
                        if revision == 3
                        else {}
                    ),
                }
            ),
        },
    ]


class RecordedConnection(OllamaConnection):
    """Save the exact submitted prompt and raw local reply, including failed calls."""

    def __init__(
        self, connection: OllamaConnection, folder: Path, deadline: float | None = None
    ) -> None:
        super().__init__(
            f"http://[{connection.host}]:{connection.port}"
            if ":" in connection.host
            else f"http://{connection.host}:{connection.port}",
            connection.options,
        )
        self.folder = folder
        self.calls: list[dict[str, object]] = []
        self.deadline = deadline

    def api(self, path: str, payload: dict[str, object] | None = None) -> dict[str, object]:
        if path != "/api/chat":
            return super().api(path, payload)
        record: dict[str, object] = {"payload": payload, "status": "started"}
        self.calls.append(record)
        target = self.folder / f"{len(self.calls):03}.json"
        save_json(target, record)
        try:
            if self.deadline is not None:
                remaining = self.deadline - monotonic()
                if remaining < 1:
                    raise OllamaError("invocation_cap_reached")
                self.options = replace(
                    self.options,
                    timeout_seconds=max(1, min(self.options.timeout_seconds, int(remaining))),
                )
            response = super().api(path, payload)
        except OllamaError as error:
            record.update(status="infrastructure_error", error=str(error))
            save_json(target, record)
            raise
        record.update(status="responded", response=response)
        save_json(target, record)
        return response


def learn(
    root: Path,
    connection: OllamaConnection,
    model: LocalModel,
    sources: tuple[Trajectory, ...],
    dev: tuple[Trajectory, ...],
    deadline: float | None = None,
) -> Lesson | None:
    messages = induction_messages(sources)
    save_json(root / "induction-input.json", messages)
    save_json(root / "induction-candidates.json", handoff_candidates(sources))
    schemas = tool_contracts(sources)
    for call in range(1, 5):
        target = root / "proposals" / f"{call}.json"
        if target.exists():
            record = read_json(target)
        else:
            if deadline is not None and monotonic() >= deadline - 1:
                return None
            learner = RecordedConnection(
                OllamaConnection(
                    f"http://[{connection.host}]:{connection.port}"
                    if ":" in connection.host
                    else f"http://{connection.host}:{connection.port}",
                    replace(OPTIONS, output_tokens=1100),
                ),
                root / "induction-calls" / str(call),
                deadline,
            )
            payload: dict[str, object] = {
                "model": model.name,
                "messages": messages,
                "format": induction_schema(),
                "stream": False,
                "keep_alive": "3m",
                "options": {
                    "seed": 17 + call - 1,
                    "temperature": 0,
                    "num_ctx": 8192,
                    "num_predict": 1100,
                },
            }
            if model.supports_thinking:
                payload["think"] = False
            try:
                response = learner.api("/api/chat", payload)
                content = response.get("message", {})
                proposal = json.loads(content["content"]) if isinstance(content, dict) else None
                record = {"call": call, "proposal": proposal}
            except (OllamaError, ValueError, KeyError, TypeError) as error:
                record = {"call": call, "proposal": None, "error": str(error)}
            save_json(target, record)
        try:
            lesson = decode_lesson(record["proposal"], schemas)
            validate_lesson(lesson, sources, dev)
        except ValueError as error:
            save_json(
                root / "validations" / f"{call}.json",
                {"accepted": False, "reason": str(error), "proposal_hash": digest(record)},
            )
            continue
        save_json(
            root / "validations" / f"{call}.json",
            {"accepted": True, "lesson_id": lesson.lesson_id, "proposal_hash": digest(record)},
        )
        save_json(root / "lesson.json", lesson)
        return lesson
    return None


def prompt_for(context: AgentContext) -> list[dict[str, object]]:
    return _messages(context, structured=True, grounded=True)


def verify_learning(
    root: Path, sources: tuple[Trajectory, ...], dev: tuple[Trajectory, ...]
) -> Lesson | None:
    """Re-evaluate archived proposals and rejection reasons without inference."""
    if not (root / "induction-input.json").exists():
        return None
    from trajyn.provenance import read_trajectory

    counterexamples = tuple(
        read_trajectory(p) for p in sorted((root / "scripted-counterexamples").glob("*.jsonl"))
    )
    contrasts = sources + counterexamples
    archived_messages = read_json(root / "induction-input.json")
    revision = json.loads(archived_messages[1]["content"])["revision"]
    if revision == 3 and encode_json(read_json(root / "induction-candidates.json")) != (
        encode_json(handoff_candidates(contrasts))
    ):
        raise ValueError("positive candidate references differ from replayed training handoffs")
    if encode_json(archived_messages) != encode_json(
        induction_messages(contrasts, revision=revision)
    ):
        raise ValueError("learner input changed or contains non-training records")
    selected = None
    for call in range(1, 5):
        path = root / "proposals" / f"{call}.json"
        if not path.exists():
            continue
        if selected is not None:
            raise ValueError("proposals continued after deterministic selection")
        record = read_json(path)
        raw = read_json(root / "induction-calls" / str(call) / "001.json")
        if raw["payload"]["format"] != ("json" if revision == 1 else induction_schema()):
            raise ValueError("induction response format differs from its revision")
        if raw["payload"]["messages"] != read_json(root / "induction-input.json"):
            raise ValueError("submitted induction prompt differs from archived input")
        if raw["status"] == "responded":
            try:
                proposal = json.loads(raw["response"]["message"]["content"])
            except (KeyError, TypeError, ValueError):
                proposal = None
            if proposal != record["proposal"]:
                raise ValueError("candidate differs from raw learner response")
        elif record["proposal"] is not None:
            raise ValueError("failed learner call has a fabricated proposal")
        try:
            lesson = decode_lesson(record["proposal"], tool_contracts(contrasts))
            validate_lesson(lesson, contrasts, dev)
        except ValueError as error:
            validation = {"accepted": False, "reason": str(error), "proposal_hash": digest(record)}
        else:
            selected = lesson
            validation = {
                "accepted": True,
                "lesson_id": lesson.lesson_id,
                "proposal_hash": digest(record),
            }
        if validation != read_json(root / "validations" / f"{call}.json"):
            raise ValueError("lesson validation or rejection reason changed")
    return selected
