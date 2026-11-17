import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from trajyn.agent import AgentContext
from trajyn.benchmark import generate_delivery_task
from trajyn.branching import BranchState, BranchTransfer
from trajyn.delivery_agent import DeliveryReferenceAgent
from trajyn.evaluation import Condition, EvaluationPlan, collect_sources, evaluate, induce_sources
from trajyn.induction import induce
from trajyn.models import AgentDecision, PublicTask, Split, public_task
from trajyn.report import paired_outcomes
from trajyn.runner import environment_for, run_task

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


class ObservingAgent(DeliveryReferenceAgent):
    def __init__(self) -> None:
        self.contexts: list[AgentContext] = []

    def decide(self, context: AgentContext) -> AgentDecision | None:
        self.contexts.append(context)
        return super().decide(context)


def test_compatible_guard_abstains_before_a_different_remedy() -> None:
    source = run_task(generate_delivery_task(0), DeliveryReferenceAgent())
    capsule = induce(source, created_at=CREATED)
    task = generate_delivery_task(202, Split.TEST)
    policy = BranchTransfer(public_task(task), environment_for(task).tools, (capsule,))
    agent = ObservingAgent()
    trace = run_task(task, agent, memory_policy=policy)
    assert trace.verification.passed
    assert [step.state for step in policy.transitions] == [
        BranchState.CANDIDATE,
        BranchState.COMPATIBLE,
        BranchState.CONDITIONAL,
        BranchState.ABSTAINED,
    ]
    assert policy.transitions[-1].reason == "public_observation_diverged"
    assert policy.transitions[-1].after_step == 2
    assert all(context.memory is None for context in agent.contexts)
    assert trace.steps[2].action.tool == "acknowledge_delivery"


def test_stale_listing_withdraws_and_preserves_public_history() -> None:
    capsule = induce(
        run_task(generate_delivery_task(0), DeliveryReferenceAgent()), created_at=CREATED
    )
    task = generate_delivery_task(201, Split.TEST)
    policy = BranchTransfer(public_task(task), environment_for(task).tools, (capsule,))
    agent = ObservingAgent()
    trace = run_task(task, agent, memory_policy=policy)
    assert trace.verification.passed
    assert [step.state for step in policy.transitions[-3:]] == [
        BranchState.ACTIVE,
        BranchState.DIVERGED,
        BranchState.WITHDRAWN,
    ]
    assert policy.prompt_steps == [2, 3]
    assert policy.transitions[-1].after_step == 4
    assert agent.contexts[4].steps[-1].observation.code == "out_of_stock"
    assert agent.contexts[4].memory is None
    assert trace.steps[4].action.tool == "issue_refund"


def test_completed_and_initial_rejections() -> None:
    capsule = induce(
        run_task(generate_delivery_task(0), DeliveryReferenceAgent()), created_at=CREATED
    )
    task = generate_delivery_task(5)
    tools = environment_for(task).tools
    policy = BranchTransfer(public_task(task), tools, (capsule,))
    trace = run_task(task, DeliveryReferenceAgent(), memory_policy=policy)
    assert trace.verification.passed
    assert policy.state == BranchState.COMPLETE
    wrong_task = PublicTask(task.ticket_id, task.goal, "unrelated")
    assert BranchTransfer(wrong_task, tools, (capsule,)).state == BranchState.INAPPLICABLE
    assert BranchTransfer(public_task(task), (), (capsule,)).state == BranchState.INCOMPATIBLE


def test_missing_public_prerequisite_blocks_activation() -> None:
    task = generate_delivery_task(5)
    source = run_task(generate_delivery_task(0), DeliveryReferenceAgent())
    capsule = induce(source, created_at=CREATED)
    tools = environment_for(task).tools
    policy = BranchTransfer(public_task(task), tools, (capsule,))
    trace = run_task(task, DeliveryReferenceAgent())
    first, carrier = trace.steps[:2]
    observation = replace(carrier.observation, data={"status": "lost"})
    context = AgentContext(
        public_task(task), tools, (first, replace(carrier, observation=observation)), 8
    )
    assert policy.memory_for(context) is None
    assert policy.transitions[-1].reason == "missing_public_prerequisite"


def test_six_arm_offline_counterfactual_records_continued_static_delivery(tmp_path: Path) -> None:
    sources = collect_sources(tmp_path / "source", (0,))
    capsules = induce_sources(sources, created_at=CREATED)
    plan = EvaluationPlan((200, 201, 202, 203), measure_time=False)
    result = evaluate(sources, capsules, tmp_path / "evaluation", plan=plan, branch_aware=True)
    assert len(paired_outcomes(result)) == 24
    assert result.conditions == tuple(Condition)
    artifact = json.loads((tmp_path / "evaluation/transfer.json").read_text())
    audits = {(item["seed"], item["condition"]): item for item in artifact["trials"]}
    assert audits[202, "D"]["continued_after_divergence"] > 0
    assert audits[202, "F"]["delivered_after_steps"] == []
    assert audits[201, "F"]["transitions"][-1]["state"] == BranchState.WITHDRAWN
    assert all(
        item["continued_after_divergence"] == 0
        for item in artifact["trials"]
        if item["condition"] == "F"
    )
    assert audits[200, "F"]["transitions"][-1]["state"] == BranchState.INCOMPATIBLE
