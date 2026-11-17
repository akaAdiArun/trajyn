"""Measure tool-use errors and public identifier accuracy from recorded steps."""

from collections import Counter
from dataclasses import dataclass

from trajyn.grounding import public_identifiers
from trajyn.models import Trajectory
from trajyn.recording import encode_json
from trajyn.runner import environment_for


@dataclass(frozen=True, slots=True)
class ToolDiagnostics:
    identifier_arguments: int
    matching_identifiers: int
    missing_identifiers: int
    identifier_mismatches: int
    invalid_arguments: int
    wrong_tool: int
    repeated_actions: int
    successful_calls: int
    recovery_episodes: int
    verified: bool
    observations: dict[str, int]


def diagnose(trajectory: Trajectory) -> ToolDiagnostics:
    requested = matching = missing = repeated = 0
    seen: set[str] = set()
    counts: Counter[str] = Counter()
    tools = {tool.name: tool for tool in environment_for(trajectory.task).tools}
    for index, step in enumerate(trajectory.steps):
        counts[step.observation.code] += 1
        signature = encode_json(step.action)
        repeated += signature in seen
        seen.add(signature)
        tool = tools.get(step.action.tool)
        if tool is None:
            continue
        available = public_identifiers(trajectory.task.ticket_id, trajectory.steps[:index])
        for parameter in tool.parameters:
            field = parameter.name
            if not (field.endswith("_id") or field == "sku"):
                continue
            requested += 1
            value = step.action.arguments.get(field)
            if value is None:
                missing += 1
            elif field in available and value == available[field][0]:
                matching += 1
    return ToolDiagnostics(
        requested,
        matching,
        missing,
        requested - matching - missing,
        counts["invalid_arguments"],
        counts["unknown_tool"] + counts["remedy_ineligible"],
        repeated,
        sum(step.observation.ok for step in trajectory.steps),
        sum(
            not before.observation.ok and after.observation.ok
            for before, after in zip(trajectory.steps, trajectory.steps[1:], strict=False)
        ),
        trajectory.verification.passed,
        dict(sorted(counts.items())),
    )
