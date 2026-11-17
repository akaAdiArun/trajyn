import pytest

from trajyn.agent import AgentContext, OfflineReferenceAgent
from trajyn.environment import generate_task
from trajyn.models import AgentDecision, AgentIdentity, Split, StopReason, ToolAction, Usage
from trajyn.runner import run_task


@pytest.mark.parametrize("split", list(Split))
@pytest.mark.parametrize("seed", [0, 42, 99])
def test_reference_agent_verifies_in_five_steps(seed: int, split: Split) -> None:
    task = generate_task(seed, split)
    trajectory = run_task(task, OfflineReferenceAgent())
    assert trajectory == run_task(task, OfflineReferenceAgent())
    assert trajectory.agent.provider == "offline"
    assert trajectory.stop_reason is StopReason.AGENT_STOPPED
    assert trajectory.verification.passed
    assert [step.action.tool for step in trajectory.steps] == [
        "get_ticket",
        "get_order",
        "check_stock",
        "create_replacement",
        "resolve_ticket",
    ]


def test_step_budget_records_partial_progress() -> None:
    task = generate_task(42)
    trajectory = run_task(task, OfflineReferenceAgent(), max_steps=4)
    assert trajectory.stop_reason is StopReason.STEP_LIMIT
    assert len(trajectory.steps) == 4
    assert not trajectory.verification.passed
    assert trajectory.verification.failures == ("ticket_not_resolved_with_replacement",)
    assert run_task(task, OfflineReferenceAgent(), max_steps=5).verification.passed

    with pytest.raises(ValueError, match="positive"):
        run_task(task, OfflineReferenceAgent(), max_steps=0)


def test_agent_protocol_records_failed_steps_and_optional_measurements() -> None:
    class InvalidActionAgent:
        identity = AgentIdentity("fixture", "invalid-action", "1")

        def decide(self, context: AgentContext) -> AgentDecision:
            assert context.task == task
            assert len(context.tools) == 5
            assert len(context.steps) < context.max_steps == 2
            return AgentDecision(ToolAction("unsupported"), Usage(input_tokens=12))

    task = generate_task(42)
    trajectory = run_task(task, InvalidActionAgent(), max_steps=2, measure_time=True)
    assert trajectory.stop_reason is StopReason.STEP_LIMIT
    assert [step.index for step in trajectory.steps] == [1, 2]
    for step in trajectory.steps:
        assert not step.observation.ok
        assert step.observation.code == "unknown_tool"
        assert step.usage == Usage(input_tokens=12)
        assert step.elapsed_ns is not None and step.elapsed_ns >= 0
    assert trajectory.elapsed_ns is not None and trajectory.elapsed_ns >= 0
    assert not trajectory.verification.passed
