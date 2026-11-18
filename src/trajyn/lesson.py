"""An auditable, restricted language for one learned action-to-action handoff."""

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

from trajyn.agent import AgentContext
from trajyn.benchmark import DELIVERY_V3
from trajyn.memory import LessonMemory
from trajyn.models import Scalar, Split, ToolSpec, Trajectory, public_task
from trajyn.provenance import replay_trajectory
from trajyn.recording import encode_json
from trajyn.runner import environment_for


class Activation(StrEnum):
    SUCCESS = "successful_observation"
    CODE = "supported_success_code"
    CASE = "executed_action_matches_current_case"
    VALUE = "well_formed_observed_value"


class Exclusion(StrEnum):
    CLOSED = "successful_consumer_already_observed"
    AMBIGUOUS = "conflicting_binding"
    CONTRADICTION = "later_authoritative_contradiction"
    WRONG_TOOL = "different_producing_operation"


@dataclass(frozen=True, slots=True)
class LessonBinding:
    parameter: str
    origin: str
    field: str


@dataclass(frozen=True, slots=True)
class LessonEvidence:
    trajectory_id: str
    producer_step: int
    consumer_step: int


@dataclass(frozen=True, slots=True)
class Lesson:
    version: int
    workflow: str
    producer_tools: tuple[str, ...]
    consumer_tool: str
    output_field: str
    success_codes: tuple[str, ...]
    activation: tuple[Activation, ...]
    exclusions: tuple[Exclusion, ...]
    bindings: tuple[LessonBinding, ...]
    evidence: tuple[LessonEvidence, ...]
    schemas: tuple[ToolSpec, ...]

    def __post_init__(self) -> None:
        if type(self.version) is not int or self.version != 1 or self.workflow != DELIVERY_V3:
            raise ValueError("unsupported lesson version or workflow")
        if (
            not self.producer_tools
            or not set(self.producer_tools) <= {"ship_replacement", "locker_replacement"}
            or tuple(sorted(set(self.producer_tools))) != self.producer_tools
        ):
            raise ValueError("unsupported or duplicated producer")
        if self.consumer_tool != "close_case" or self.output_field != "receipt_id":
            raise ValueError("unsupported consumer or field")
        if (
            not self.success_codes
            or not set(self.success_codes) <= {"remedy_exists", "remedy_posted"}
            or tuple(sorted(set(self.success_codes))) != self.success_codes
        ):
            raise ValueError("unsupported observation codes")
        if self.activation != tuple(Activation) or self.exclusions != tuple(Exclusion):
            raise ValueError("all applicability and exclusion predicates are required in order")
        if len(self.bindings) != 2 or set(self.bindings) != {
            LessonBinding("ticket_id", "producer.action", "ticket_id"),
            LessonBinding("receipt_id", "producer.observation", "receipt_id"),
        }:
            raise ValueError("unsupported symbolic argument bindings")
        if not self.evidence or any(
            type(e.producer_step) is not int
            or type(e.consumer_step) is not int
            or not 0 < e.producer_step < e.consumer_step
            for e in self.evidence
        ):
            raise ValueError("invalid source step references")

    @property
    def lesson_id(self) -> str:
        return "lesson:" + sha256(encode_json(self).encode()).hexdigest()


def decode_lesson(record: object, schemas: tuple[ToolSpec, ...]) -> Lesson:
    """Reject extra keys, prose, expressions, arbitrary fields, and literal bindings."""
    if not isinstance(record, dict):
        raise ValueError("proposal must be an object")
    if "schemas" in record and encode_json(record["schemas"]) != encode_json(schemas):
        raise ValueError("lesson tool contracts differ from replayed training interfaces")
    try:
        candidate = {**record, "schemas": schemas}
        lesson = Lesson(
            **{
                **candidate,
                "producer_tools": tuple(candidate["producer_tools"]),
                "success_codes": tuple(candidate["success_codes"]),
                "activation": tuple(Activation(v) for v in candidate["activation"]),
                "exclusions": tuple(Exclusion(v) for v in candidate["exclusions"]),
                "bindings": tuple(LessonBinding(**v) for v in candidate["bindings"]),
                "evidence": tuple(LessonEvidence(**v) for v in candidate["evidence"]),
            }
        )
        if encode_json(lesson) != encode_json(candidate):
            raise ValueError("noncanonical lesson schema")
        return lesson
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise ValueError(f"invalid lesson ({error})") from error


def read_lesson(path: Path, schemas: tuple[ToolSpec, ...]) -> Lesson:
    return decode_lesson(json.loads(path.read_text(encoding="utf-8")), schemas)


def valid_receipt(value: Scalar) -> bool:
    return isinstance(value, str) and re.fullmatch(r"receipt-[a-f0-9]{12}", value) is not None


@dataclass(frozen=True, slots=True)
class GateDecision:
    after_step: int
    state: str
    reason: str
    references: tuple[int, ...] = ()
    receipt: str | None = None


def evidence_gate(lesson: Lesson, context: AgentContext) -> GateDecision:
    """Use public executed evidence alone. No simulator, verifier, or task labels."""
    count = len(context.steps)

    def decision(
        state: str, reason: str, refs: tuple[int, ...] = (), receipt: str | None = None
    ) -> GateDecision:
        return GateDecision(count, state, reason, refs, receipt)

    tools = {tool.name: tool for tool in context.tools}
    expected = {tool.name: tool for tool in lesson.schemas}
    producers = set(lesson.producer_tools) & tools.keys()
    if (
        context.task.workflow != lesson.workflow
        or not producers
        or any(tools.get(name) != expected.get(name) for name in {*producers, lesson.consumer_tool})
    ):
        return decision("incompatible", "workflow_or_tool_schema_changed")
    binding: str | None = None
    references: list[int] = []
    parcel: Scalar = None
    invalid: str | None = None
    for step in context.steps:
        action, observation = step.action, step.observation
        current = action.arguments.get("ticket_id") == context.task.ticket_id
        if not observation.ok:
            continue
        if action.tool == lesson.consumer_tool and current and observation.code == "case_closed":
            return decision("completed", "current_case_closed", (step.index,))
        if action.tool in producers and current and observation.code in lesson.success_codes:
            specification = tools[action.tool]
            if set(action.arguments) != {p.name for p in specification.parameters}:
                invalid = "producer_arguments_do_not_match_contract"
                references.append(step.index)
                continue
            value = observation.data.get(lesson.output_field)
            if not valid_receipt(value):
                invalid = "missing_or_malformed_receipt"
                references.append(step.index)
                continue
            assert isinstance(value, str)
            if binding is not None and value != binding:
                invalid = "ambiguous_receipts"
            binding = value
            parcel = action.arguments.get("parcel_id")
            references.append(step.index)
        elif (
            binding is not None
            and action.tool in producers
            and not current
            and observation.code in lesson.success_codes
            and "receipt_id" in observation.data
        ):
            invalid = "another_case_receipt_overrides_public_binding"
            references.append(step.index)
        elif (
            binding is not None
            and action.tool in {"issue_refund", "schedule_pickup", "acknowledge_delivery"}
            and current
            and observation.code in lesson.success_codes
        ):
            invalid = "different_remedy_posted"
            references.append(step.index)
        elif binding is not None and action.tool in {"inspect_parcel", "query_carrier_backup"}:
            if action.arguments.get("parcel_id") == parcel and (
                observation.code == "parcel_inspected" and observation.data.get("status") != "lost"
            ):
                invalid = "later_carrier_contradicts_replacement"
                references.append(step.index)
        elif (
            binding is not None
            and action.tool in {"read_case", "find_parcel"}
            and current
            and "parcel_id" in observation.data
            and observation.data["parcel_id"] != parcel
        ):
            invalid = "case_parcel_binding_changed"
            references.append(step.index)
    if invalid is not None:
        return decision("withdrawn", invalid, tuple(references))
    if binding is None:
        return decision("waiting", "no_current_successful_supported_producer")
    return decision("eligible", "successful_public_handoff", tuple(references), binding)


def render_hint(lesson: Lesson, decision: GateDecision) -> LessonMemory:
    source = "/".join(lesson.producer_tools)
    value = decision.receipt if decision.state == "eligible" else "{current replacement receipt_id}"
    return LessonMemory(
        lesson.lesson_id,
        f"After a successful {source} for the current ticket, use its receipt_id in close_case. "
        f"Bind ticket_id from that executed action. receipt_id = {value}. "
        "Skip this advice for another remedy, conflicting evidence, or an already closed case.",
    )


class EvidenceTransfer:
    """Offer a fixed hint. The target retains every action decision."""

    def __init__(self, lesson: Lesson, *, static: bool = False) -> None:
        self.lesson = lesson
        self.static = static
        self.decisions: list[GateDecision] = []
        self.offered: list[int] = []

    def memory_for(self, context: AgentContext) -> LessonMemory | None:
        decision = evidence_gate(self.lesson, context)
        self.decisions.append(decision)
        if decision.state == "eligible" or self.static and decision.state == "waiting":
            self.offered.append(len(context.steps))
            return render_hint(self.lesson, decision)
        return None

    def finish(self, context: AgentContext) -> None:
        # Eligibility here is an opportunity only, never prompt delivery.
        self.decisions.append(evidence_gate(self.lesson, context))


def validate_lesson(
    lesson: Lesson,
    sources: tuple[Trajectory, ...],
    development: tuple[Trajectory, ...],
    *,
    require_model: bool = True,
) -> None:
    by_id = {source.trajectory_id: source for source in sources}
    covered = set()
    for reference in lesson.evidence:
        source = by_id.get(reference.trajectory_id)
        if source is None or source.task.split != Split.TRAIN:
            raise ValueError("citation is absent or outside training")
        replay_trajectory(source)
        if (
            not source.verification.passed
            or require_model
            and (source.agent.provider != "ollama" or source.agent.model != "qwen3:8b")
        ):
            raise ValueError("handoff requires a verified Qwen source success")
        if reference.consumer_step > len(source.steps):
            raise ValueError("citation step is out of range")
        producer = source.steps[reference.producer_step - 1]
        consumer = source.steps[reference.consumer_step - 1]
        context = AgentContext(
            public_task(source.task),
            environment_for(source.task).tools,
            source.steps[: reference.consumer_step - 1],
            source.max_steps,
        )
        match = evidence_gate(lesson, context)
        if not (
            producer.action.tool in lesson.producer_tools
            and producer.observation.ok
            and producer.observation.code in lesson.success_codes
            and producer.action.arguments.get("ticket_id") == source.task.ticket_id
            and match.state == "eligible"
            and producer.index in match.references
            and producer.observation.data.get(lesson.output_field) == match.receipt
            and consumer.action.tool == lesson.consumer_tool
            and consumer.observation.ok
            and consumer.observation.code == "case_closed"
            and consumer.action.arguments.get("ticket_id") == source.task.ticket_id
            and consumer.action.arguments.get("receipt_id") == match.receipt
        ):
            raise ValueError("cited source-to-consumer data flow is unsupported")
        covered.add(producer.action.tool)
    if covered != set(lesson.producer_tools):
        raise ValueError("each producing operation needs verified cited support")
    if not development:
        raise ValueError("separate development examples required")
    positives = negatives = 0
    for trace in development:
        if trace.task.split != Split.VALIDATION:
            raise ValueError("development partition required")
        replay_trajectory(trace)
        for index in range(len(trace.steps) + 1):
            steps = trace.steps[:index]
            context = AgentContext(
                public_task(trace.task), environment_for(trace.task).tools, steps, trace.max_steps
            )
            actual = evidence_gate(lesson, context).state == "eligible"
            closed = any(s.action.tool == "close_case" and s.observation.ok for s in steps)
            expected = any(
                s.action.tool in lesson.producer_tools
                and s.observation.ok
                and valid_receipt(s.observation.data.get("receipt_id"))
                for s in steps
            )
            if actual != (expected and not closed):
                raise ValueError("development applicability mismatch")
            positives += actual
            negatives += not actual and any(s.observation.data.get("receipt_id") for s in steps)
    if not positives or not negatives:
        raise ValueError("development needs positive handoffs and receipt-bearing exclusions")
