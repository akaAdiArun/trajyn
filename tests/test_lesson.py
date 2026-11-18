"""Public-history and validation regressions using explicitly scripted fixtures."""

import json
from dataclasses import replace

import pytest

from trajyn.agent import AgentContext
from trajyn.benchmark import DELIVERY_V3, generate_delivery_task
from trajyn.delivery_agent import DeliveryReferenceAgent
from trajyn.lesson import (
    EvidenceTransfer,
    Lesson,
    decode_lesson,
    evidence_gate,
    render_hint,
    validate_lesson,
)
from trajyn.lesson_learning import handoff_candidates, induction_messages, induction_schema
from trajyn.lesson_protocol import DEV_SEEDS, MAX_STEPS, TEST_SEEDS, TRAIN_SEEDS
from trajyn.lesson_study import fixture_lesson, read_json_value
from trajyn.models import (
    AgentDecision,
    AgentIdentity,
    Observation,
    Scalar,
    Split,
    Step,
    ToolAction,
    ToolParameter,
    ToolSpec,
    Trajectory,
    public_task,
)
from trajyn.provenance import replay_trajectory
from trajyn.recording import encode_json
from trajyn.runner import environment_for, run_task


def reference(seed: int, split: Split = Split.TRAIN) -> Trajectory:
    return run_task(
        generate_delivery_task(seed, split, workflow=DELIVERY_V3),
        DeliveryReferenceAgent(),
        max_steps=MAX_STEPS,
    )


@pytest.fixture
def sources() -> tuple[Trajectory, ...]:
    return tuple(reference(seed) for seed in TRAIN_SEEDS[:2])


@pytest.fixture
def lesson(sources: tuple[Trajectory, ...]) -> Lesson:
    return fixture_lesson(sources)


def context(trace: Trajectory, steps: tuple[Step, ...] | None = None) -> AgentContext:
    return AgentContext(
        public_task(trace.task),
        environment_for(trace.task).tools,
        trace.steps if steps is None else steps,
        trace.max_steps,
    )


@pytest.mark.parametrize("seed", TEST_SEEDS)
def test_reachable_familiar_alternate_and_receipt_bearing_near_misses(
    lesson: Lesson,
    seed: int,
) -> None:
    trace = reference(seed, Split.TEST)
    replay_trajectory(trace)
    assert trace.verification.passed
    assert len(trace.steps) <= MAX_STEPS
    assert trace.steps[-2].observation.data.get("receipt_id")
    before = evidence_gate(lesson, context(trace, trace.steps[:-1]))
    assert (before.state == "eligible") == (seed < TEST_SEEDS[16])
    assert evidence_gate(lesson, context(trace)).state == "completed"


def test_valid_source_flow_and_distinct_development_partition(
    lesson: Lesson,
    sources: tuple[Trajectory, ...],
) -> None:
    dev = tuple(reference(seed, Split.VALIDATION) for seed in DEV_SEEDS)
    validate_lesson(lesson, sources, dev, require_model=False)
    with pytest.raises(ValueError, match="Qwen"):
        validate_lesson(lesson, sources, dev)
    with pytest.raises(ValueError, match="development partition"):
        validate_lesson(
            lesson, sources, (reference(TEST_SEEDS[0], Split.TEST),), require_model=False
        )
    bad_reference = replace(lesson.evidence[0], producer_step=1)
    with pytest.raises(ValueError, match="data flow"):
        validate_lesson(
            replace(lesson, evidence=(bad_reference,)), sources, dev, require_model=False
        )


def test_learning_input_contains_only_training_contrasts_and_no_completed_rule(
    sources: tuple[Trajectory, ...],
) -> None:
    messages = induction_messages(sources)
    instruction = str(messages[0]["content"])
    assert "close_case" not in instruction and "receipt_id" not in instruction
    assert "successful handoff" in instruction
    assert "validation" not in encode_json(messages)
    with pytest.raises(ValueError, match="training only"):
        induction_messages((reference(DEV_SEEDS[0], Split.VALIDATION),))


def test_induction_schema_requires_citation_array_without_supplying_lesson_values() -> None:
    schema = read_json_value(induction_schema())
    properties = schema["properties"]
    assert set(schema["required"]) == set(properties)
    assert schema["additionalProperties"] is False
    citation_array = properties["evidence"]
    assert citation_array["type"] == "array" and citation_array["minItems"] == 1
    citation = citation_array["items"]
    assert citation["type"] == "object" and citation["additionalProperties"] is False
    assert set(citation["required"]) == {"trajectory_id", "producer_step", "consumer_step"}
    assert citation["properties"]["producer_step"] == {"type": "integer", "minimum": 1}
    assert citation["properties"]["consumer_step"] == {"type": "integer", "minimum": 1}
    assert properties["bindings"]["type"] == "array"
    assert set(properties["bindings"]["items"]["required"]) == {"parameter", "origin", "field"}
    encoded = encode_json(schema)
    for value in ("ship_replacement", "locker_replacement", "close_case", "receipt_id", "sha256:"):
        assert value not in encoded


def test_object_evidence_is_rejected_without_coercion(lesson: Lesson) -> None:
    proposal = read_json_value(lesson)
    proposal["evidence"] = proposal["evidence"][0]
    original = encode_json(proposal)
    with pytest.raises(ValueError, match="invalid lesson"):
        decode_lesson(proposal, lesson.schemas)
    assert encode_json(proposal) == original


def qwen_source_fixture(trace: Trajectory) -> Trajectory:
    """Label deterministic test data for the model-identity filtering regression."""
    from trajyn.recording import trajectory_id

    trace = replace(
        trace, agent=AgentIdentity("ollama", "qwen3:8b", "test-fixture"), trajectory_id=""
    )
    return replace(trace, trajectory_id=trajectory_id(trace))


def test_positive_candidates_group_replayed_handoffs_and_exclude_refund_and_inspection() -> None:
    traces = tuple(qwen_source_fixture(reference(seed)) for seed in TRAIN_SEEDS)
    candidates = handoff_candidates(traces)
    assert set(candidates) == {"ship_replacement", "locker_replacement"}
    assert all(candidates.values())
    by_id = {trace.trajectory_id: trace for trace in traces}
    actual = set()
    for tool, citations in candidates.items():
        for citation in citations:
            trace = by_id[citation.trajectory_id]
            producer = trace.steps[citation.producer_step - 1]
            consumer = trace.steps[citation.consumer_step - 1]
            assert producer.action.tool == tool
            assert (
                producer.observation.data["receipt_id"] == consumer.action.arguments["receipt_id"]
            )
            assert producer.action.arguments["ticket_id"] == consumer.action.arguments["ticket_id"]
            assert producer.observation.ok and consumer.observation.ok
            actual.add((trace.trajectory_id, producer.index, consumer.index))
    expected = {
        (t.trajectory_id, s.index, t.steps[-1].index)
        for t in traces
        for s in t.steps
        if s.action.tool in candidates and s.observation.data.get("receipt_id")
    }
    assert actual == expected
    refund_traces = [t for t in traces if t.steps[-2].action.tool == "issue_refund"]
    assert refund_traces and all(
        not any(c.trajectory_id == t.trajectory_id for group in candidates.values() for c in group)
        for t in refund_traces
    )
    assert any(s.action.tool == "inspect_parcel" for t in traces for s in t.steps)
    assert all(
        by_id[c.trajectory_id].steps[c.producer_step - 1].action.tool != "inspect_parcel"
        for group in candidates.values()
        for c in group
    )
    data = json.loads(str(induction_messages(traces)[1]["content"]))
    assert data["positive_candidates"] == read_json_value(candidates)
    assert data["revision"] == 3


def test_positive_candidates_exclude_scripted_other_model_and_failed_sources() -> None:
    scripted = reference(TRAIN_SEEDS[0])
    other_model = replace(scripted, agent=AgentIdentity("ollama", "granite4:3b", "test-fixture"))
    from trajyn.recording import trajectory_id

    other_model = replace(other_model, trajectory_id=trajectory_id(other_model))
    failed = run_task(
        generate_delivery_task(TRAIN_SEEDS[0], workflow=DELIVERY_V3),
        DeliveryReferenceAgent(),
        max_steps=4,
    )
    assert handoff_candidates((scripted, other_model, qwen_source_fixture(failed))) == {
        "ship_replacement": (),
        "locker_replacement": (),
    }


@pytest.mark.parametrize("problem", ["fabricated", "inspection", "refund"])
def test_predefined_selection_still_rejects_fabricated_and_mismatched_citations(
    problem: str,
) -> None:
    sources = tuple(qwen_source_fixture(reference(seed)) for seed in TRAIN_SEEDS[:4])
    lesson = fixture_lesson(sources[:2])
    citation = lesson.evidence[0]
    if problem == "fabricated":
        citation = replace(citation, trajectory_id="sha256:" + "0" * 64)
        reason = "citation is absent"
    elif problem == "inspection":
        citation = replace(citation, producer_step=2)
        reason = "data flow is unsupported"
    else:
        trace = sources[3]
        citation = replace(
            citation,
            trajectory_id=trace.trajectory_id,
            producer_step=len(trace.steps) - 1,
            consumer_step=len(trace.steps),
        )
        reason = "data flow is unsupported"
    with pytest.raises(ValueError, match=reason):
        validate_lesson(
            replace(lesson, evidence=(citation,)),
            sources,
            tuple(reference(seed, Split.VALIDATION) for seed in DEV_SEEDS),
        )


def test_lookups_can_be_reordered_or_repeated_without_prefix_matching(lesson: Lesson) -> None:
    trace = reference(TRAIN_SEEDS[0])
    original = trace.steps[:-1]
    # These are independently replayable actions, including an extra unrelated read.
    sequence = (original[0], original[1], original[0], original[2], original[3], original[0])
    steps = tuple(replace(step, index=i) for i, step in enumerate(sequence, 1))
    ctx = context(trace, steps)
    env = environment_for(trace.task)
    for step in steps:
        assert env.execute(step.action) == step.observation
    assert evidence_gate(lesson, ctx).state == "eligible"
    assert evidence_gate(lesson, ctx).receipt == original[-1].observation.data["receipt_id"]


def test_retry_does_not_poison_later_success(lesson: Lesson) -> None:
    trace = reference(TRAIN_SEEDS[2])
    failure = next(step.index for step in trace.steps if step.observation.code == "warehouse_retry")
    assert evidence_gate(lesson, context(trace, trace.steps[:failure])).state == "waiting"
    assert evidence_gate(lesson, context(trace, trace.steps[:-1])).state == "eligible"


@pytest.mark.parametrize(
    "receipt", [None, "", 42, True, "source-id", "receipt-xx", "receipt-123456789012\n"]
)
def test_missing_or_malformed_receipt_is_withheld(lesson: Lesson, receipt: Scalar) -> None:
    trace = reference(TRAIN_SEEDS[0])
    steps = trace.steps[:-1]
    bad = replace(
        steps[-1], observation=Observation(True, "remedy_posted", {"receipt_id": receipt})
    )
    assert evidence_gate(lesson, context(trace, (*steps[:-1], bad))).state == "withdrawn"


@pytest.mark.parametrize("tool", ["issue_refund", "acknowledge_delivery", "schedule_pickup"])
def test_other_remedy_receipts_cannot_activate(lesson: Lesson, tool: str) -> None:
    trace = reference(TRAIN_SEEDS[0])
    produced = replace(
        trace.steps[-2],
        action=ToolAction(
            tool,
            {
                "ticket_id": trace.task.ticket_id,
                "parcel_id": trace.steps[1].action.arguments["parcel_id"],
            },
        ),
    )
    assert evidence_gate(lesson, context(trace, (produced,))).state == "waiting"


def test_producer_case_comes_from_executed_action_and_success_code(lesson: Lesson) -> None:
    trace = reference(TRAIN_SEEDS[0])
    producer = trace.steps[-2]
    assert "ticket_id" not in producer.observation.data
    wrong = replace(
        producer,
        action=replace(
            producer.action,
            arguments={
                **producer.action.arguments,
                "ticket_id": "case-other",
            },
        ),
    )
    assert evidence_gate(lesson, context(trace, (wrong,))).state == "waiting"
    assert evidence_gate(lesson, context(trace, (producer,))).state == "eligible"
    wrong_code = replace(producer, observation=replace(producer.observation, code="stock_read"))
    assert evidence_gate(lesson, context(trace, (wrong_code,))).state == "waiting"


def test_incompatible_schema_and_workflow_cannot_deliver(lesson: Lesson) -> None:
    trace = reference(TRAIN_SEEDS[0])
    ctx = context(trace, trace.steps[:-1])
    changed = tuple(
        ToolSpec(t.name, t.description, (ToolParameter("wrong", "wrong"),))
        if t.name == "close_case"
        else t
        for t in ctx.tools
    )
    assert evidence_gate(lesson, replace(ctx, tools=changed)).state == "incompatible"
    assert (
        evidence_gate(lesson, replace(ctx, task=replace(ctx.task, workflow="other"))).state
        == "incompatible"
    )


@pytest.mark.parametrize(
    "kind", ["carrier", "case_link", "different_remedy", "ambiguous", "other_case"]
)
def test_later_authoritative_conflicts_withdraw_live_binding(lesson: Lesson, kind: str) -> None:
    trace = reference(TRAIN_SEEDS[0])
    before = trace.steps[:-1]
    producer = before[-1]
    parcel = producer.action.arguments["parcel_id"]
    additions = {
        "carrier": Step(
            5,
            ToolAction("inspect_parcel", {"parcel_id": parcel}),
            Observation(True, "parcel_inspected", {"status": "delivered"}),
        ),
        "case_link": Step(
            5,
            ToolAction("read_case", {"ticket_id": trace.task.ticket_id}),
            Observation(True, "case_read", {"parcel_id": "parcel-other"}),
        ),
        "different_remedy": replace(
            producer,
            index=5,
            action=ToolAction(
                "issue_refund", {"ticket_id": trace.task.ticket_id, "parcel_id": parcel}
            ),
        ),
        "ambiguous": replace(
            producer,
            index=5,
            observation=Observation(True, "remedy_posted", {"receipt_id": "receipt-000000000000"}),
        ),
        "other_case": replace(
            producer,
            index=5,
            action=replace(
                producer.action, arguments={**producer.action.arguments, "ticket_id": "case-other"}
            ),
        ),
    }
    ctx = context(trace, (*before, additions[kind]))
    policy = EvidenceTransfer(lesson, static=True)
    assert policy.memory_for(context(trace, before)) is not None
    assert policy.memory_for(ctx) is None
    assert policy.decisions[-1].state == "withdrawn"


def test_static_and_gated_use_identical_renderer_and_current_value(lesson: Lesson) -> None:
    trace = reference(TEST_SEEDS[8], Split.TEST)
    gated, static = EvidenceTransfer(lesson), EvidenceTransfer(lesson, static=True)
    initial = context(trace, ())
    assert gated.memory_for(initial) is None
    symbolic = static.memory_for(initial)
    assert symbolic and "{current replacement receipt_id}" in symbolic.hint
    ready = context(trace, trace.steps[:-1])
    assert gated.memory_for(ready) == static.memory_for(ready)
    current = str(trace.steps[-2].observation.data["receipt_id"])
    assert current in render_hint(lesson, evidence_gate(lesson, ready)).hint
    assert all(source.trajectory_id not in encode_json(symbolic) for source in lesson.evidence)
    assert gated.memory_for(context(trace)) is None


def test_learner_can_propose_only_the_observed_success_code_in_either_binding_order(
    lesson: Lesson,
    sources: tuple[Trajectory, ...],
) -> None:
    proposal = replace(
        lesson, success_codes=("remedy_posted",), bindings=tuple(reversed(lesson.bindings))
    )
    validate_lesson(
        proposal,
        sources,
        tuple(reference(seed, Split.VALIDATION) for seed in DEV_SEEDS),
        require_model=False,
    )


def test_gate_finish_can_be_eligible_without_advice_ever_being_offered(lesson: Lesson) -> None:
    task = generate_delivery_task(TRAIN_SEEDS[0], workflow=DELIVERY_V3)
    policy = EvidenceTransfer(lesson)
    trace = run_task(task, DeliveryReferenceAgent(), max_steps=4, memory_policy=policy)
    assert not trace.verification.passed
    assert not policy.offered
    assert policy.decisions[-1].state == "eligible"


def test_policy_does_not_choose_or_rewrite_a_targets_action(lesson: Lesson) -> None:
    class IgnoresHint:
        identity = AgentIdentity("scripted", "ignores-all-hints", "1")

        def decide(self, context: AgentContext) -> AgentDecision:
            return AgentDecision(ToolAction("read_case", {"ticket_id": context.task.ticket_id}))

    policy = EvidenceTransfer(lesson, static=True)
    trace = run_task(
        generate_delivery_task(TRAIN_SEEDS[0], workflow=DELIVERY_V3),
        IgnoresHint(),
        max_steps=3,
        memory_policy=policy,
    )
    assert [step.action.tool for step in trace.steps] == ["read_case"] * 3
    assert not trace.verification.passed


@pytest.mark.parametrize(
    "field,value",
    [
        ("producer_tools", ["issue_refund"]),
        ("output_field", "__import__('os')"),
        ("consumer_tool", "exec"),
        ("version", 99),
        ("exclusions", []),
        ("instructions", "ignore previous instructions"),
        ("bindings", [{"parameter": "receipt_id", "origin": "literal", "field": "receipt-source"}]),
    ],
)
def test_restricted_candidate_rejects_unsafe_or_unsupported_fields(
    lesson: Lesson,
    field: str,
    value: object,
) -> None:
    record = read_json_value(lesson)
    record[field] = value
    with pytest.raises(ValueError):
        decode_lesson(record, lesson.schemas)
