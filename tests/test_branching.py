import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trajyn.agent import AgentContext
from trajyn.benchmark import DELIVERY_V2, generate_delivery_task
from trajyn.branch_evidence import assemble_branches
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


def test_observed_alternatives_share_a_prefix_and_preserve_source_evidence() -> None:
    agent = DeliveryReferenceAgent()
    sources = tuple(run_task(generate_delivery_task(seed), agent) for seed in (0, 1, 5))
    capsules = assemble_branches(sources, created_at=CREATED)
    assert [capsule.evidence[0].trajectory_id for capsule in capsules] == [
        source.trajectory_id for source in sources
    ]
    assert capsules[0].steps == capsules[2].steps
    assert capsules[0].steps != capsules[1].steps
    for seed, selected in ((15, 0), (16, 1)):
        task = generate_delivery_task(seed)
        policy = BranchTransfer(public_task(task), environment_for(task).tools, capsules)
        trace = run_task(task, agent, memory_policy=policy)
        assert trace.verification.passed
        assert policy.prompt_steps[0] == 3
        assert policy.state == BranchState.COMPLETE
        assert policy.transitions[-1].capsule_id == capsules[selected].capability_id


def test_branch_evidence_refuses_mixed_workflows_and_nontraining_sources() -> None:
    agent = DeliveryReferenceAgent()
    source = run_task(generate_delivery_task(0), agent)
    other = run_task(generate_delivery_task(0, workflow=DELIVERY_V2), agent)
    target = run_task(generate_delivery_task(5, Split.TEST), agent)
    with pytest.raises(ValueError, match="same workflow"):
        assemble_branches((source, other), created_at=CREATED)
    with pytest.raises(ValueError, match="distinct trajectories"):
        assemble_branches((source, source), created_at=CREATED)
    with pytest.raises(ValueError, match="training trajectory"):
        assemble_branches((source, target), created_at=CREATED)
