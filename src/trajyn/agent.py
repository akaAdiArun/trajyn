"""Provider-independent agent contract and deterministic offline reference agent."""

from dataclasses import dataclass
from typing import Protocol

from trajyn.memory import Memory
from trajyn.models import AgentDecision, AgentIdentity, PublicTask, Step, ToolAction, ToolSpec


@dataclass(frozen=True, slots=True)
class AgentContext:
    task: PublicTask
    tools: tuple[ToolSpec, ...]
    steps: tuple[Step, ...]
    max_steps: int
    memory: Memory | None = None


class Agent(Protocol):
    @property
    def identity(self) -> AgentIdentity: ...

    def decide(self, context: AgentContext) -> AgentDecision | None:
        """Return one public tool decision or stop the attempt."""


class MemoryPolicy(Protocol):
    def memory_for(self, context: AgentContext) -> Memory | None: ...

    def finish(self, context: AgentContext) -> None: ...


class OfflineReferenceAgent:
    """Rules-based baseline for the replacement workflow."""

    identity = AgentIdentity("offline", "replacement-reference", "1")

    def decide(self, context: AgentContext) -> AgentDecision | None:
        ticket_id = context.task.ticket_id
        if not context.steps:
            return AgentDecision(ToolAction("get_ticket", {"ticket_id": ticket_id}))

        latest = context.steps[-1].observation
        if not latest.ok:
            return None

        match len(context.steps):
            case 1:
                order_id = latest.data.get("order_id")
                if latest.data.get("status") == "open" and isinstance(order_id, str):
                    return AgentDecision(ToolAction("get_order", {"order_id": order_id}))
            case 2:
                sku = latest.data.get("sku")
                if latest.data.get("status") == "delivered" and isinstance(sku, str):
                    return AgentDecision(ToolAction("check_stock", {"sku": sku}))
            case 3:
                available = latest.data.get("available")
                if type(available) is int and available > 0:
                    return AgentDecision(
                        ToolAction(
                            "create_replacement",
                            {
                                "ticket_id": ticket_id,
                                "order_id": context.steps[1].action.arguments["order_id"],
                                "sku": context.steps[2].action.arguments["sku"],
                            },
                        )
                    )
            case 4:
                replacement_id = latest.data.get("replacement_id")
                if isinstance(replacement_id, str):
                    return AgentDecision(
                        ToolAction(
                            "resolve_ticket",
                            {"ticket_id": ticket_id, "replacement_id": replacement_id},
                        )
                    )
        return None
