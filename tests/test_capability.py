import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from trajyn.capability import (
    ApplicabilityCondition,
    CapabilityCapsule,
    CapabilityStep,
    TrajectoryEvidence,
)
from trajyn.models import ToolParameter, ToolSpec
from trajyn.recording import encode_json


def test_capsule_validates_shape_and_serializes_provenance() -> None:
    capsule = CapabilityCapsule(
        capability_id="read-open-ticket",
        version=1,
        goal="Read a ticket before attempting a replacement.",
        conditions=(ApplicabilityCondition("task.ticket_id", "T-42"),),
        required_tools=(
            ToolSpec("get_ticket", "Read a ticket.", (ToolParameter("ticket_id", "Ticket ID"),)),
        ),
        steps=(CapabilityStep("get_ticket", "Read the ticket referenced by the task."),),
        verifier="replacement_state_v1",
        evidence=(TrajectoryEvidence("fixture-trajectory", (1,)),),
        limitations=("Fixture-only example",),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    record = json.loads(encode_json(capsule))
    assert record["evidence"] == [{"trajectory_id": "fixture-trajectory", "step_indices": [1]}]
    assert record["created_at"] == "2026-01-01T00:00:00+00:00"

    with pytest.raises(ValueError, match="declared tool"):
        replace(capsule, required_tools=())
    with pytest.raises(ValueError, match="confidence"):
        replace(capsule, confidence=1.2)
    with pytest.raises(ValueError, match="timezone"):
        replace(capsule, created_at=datetime(2026, 1, 1))
    with pytest.raises(ValueError, match="indices"):
        TrajectoryEvidence("fixture-trajectory", (0,))
