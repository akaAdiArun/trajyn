"""Deterministically extract a supported handoff from model-generated training traces."""

from collections.abc import Mapping
from pathlib import Path

from trajyn.lesson import Activation, Exclusion, Lesson, LessonBinding, validate_lesson
from trajyn.lesson_learning import handoff_candidates, tool_contracts
from trajyn.lesson_protocol import read_json, save_json
from trajyn.models import Trajectory, public_task
from trajyn.recording import encode_json

COMPILER_REVISION = 1
ORIGIN = "deterministic_extraction_from_model_generated_traces"


def check_route_codes(routes: Mapping[str, set[str]]) -> tuple[str, ...]:
    """The v1 lesson schema shares one code set across all of its producers."""
    codes = set().union(*routes.values())
    if not routes or not codes:
        raise ValueError("no supported replacement handoff evidence")
    if any(observed != codes for observed in routes.values()):
        raise ValueError("lesson schema would widen unsupported producer/code combinations")
    return tuple(sorted(codes))


def compile_lesson(
    sources: tuple[Trajectory, ...], development: tuple[Trajectory, ...]
) -> tuple[Lesson, dict[str, object]]:
    ordered = tuple(sorted(sources, key=lambda trace: trace.trajectory_id))
    candidates = handoff_candidates(ordered)
    by_id = {trace.trajectory_id: trace for trace in ordered}
    routes: dict[str, set[str]] = {}
    support = []
    evidence = []
    workflows = set()
    for tool, citations in sorted(candidates.items()):
        if not citations:
            continue
        routes[tool] = set()
        for citation in sorted(
            citations, key=lambda c: (c.trajectory_id, c.producer_step, c.consumer_step)
        ):
            trace = by_id[citation.trajectory_id]
            code = trace.steps[citation.producer_step - 1].observation.code
            routes[tool].add(code)
            workflows.add(public_task(trace.task).workflow)
            evidence.append(citation)
            support.append(
                {
                    "producer_tool": tool,
                    "producer_code": code,
                    "consumer_tool": "close_case",
                    "citation": citation,
                }
            )
    codes = check_route_codes(routes)
    if len(workflows) != 1:
        raise ValueError("source handoffs span incompatible workflows")
    lesson = Lesson(
        version=1,
        workflow=next(iter(workflows)),
        producer_tools=tuple(sorted(routes)),
        consumer_tool="close_case",
        output_field="receipt_id",
        success_codes=codes,
        activation=tuple(Activation),
        exclusions=tuple(Exclusion),
        bindings=(
            LessonBinding("ticket_id", "producer.action", "ticket_id"),
            LessonBinding("receipt_id", "producer.observation", "receipt_id"),
        ),
        evidence=tuple(evidence),
        schemas=tool_contracts(ordered),
    )
    validate_lesson(lesson, ordered, development)
    audit: dict[str, object] = {
        "compiler_revision": COMPILER_REVISION,
        "origin": ORIGIN,
        "lesson_id": lesson.lesson_id,
        "predefined_semantics": "typed receipt binding, applicability, and exclusions",
        "observed_routes": {tool: sorted(observed) for tool, observed in routes.items()},
        "support": support,
    }
    return lesson, audit


def verify_compilation(
    root: Path, sources: tuple[Trajectory, ...], development: tuple[Trajectory, ...]
) -> Lesson:
    lesson, audit = compile_lesson(sources, development)
    if encode_json(lesson) != encode_json(read_json(root / "lesson.json")) or (
        encode_json(audit) != encode_json(read_json(root / "compiler-audit.json"))
    ):
        raise ValueError("compiled lesson or source support audit changed")
    return lesson


def write_compilation(
    root: Path, sources: tuple[Trajectory, ...], development: tuple[Trajectory, ...]
) -> Lesson:
    lesson, audit = compile_lesson(sources, development)
    save_json(root / "lesson.json", lesson)
    save_json(root / "compiler-audit.json", audit)
    return verify_compilation(root, sources, development)
