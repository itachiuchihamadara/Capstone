from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlannerStep:
    title: str
    detail: str


@dataclass
class UiComponent:
    kind: str
    payload: dict[str, Any]


@dataclass
class AgentPlan:
    intent: str
    delegated_agent: str
    reason: str
    planner_steps: list[PlannerStep] = field(default_factory=list)


@dataclass
class AgentResponse:
    agent_name: str
    intent: str
    answer: str
    model: str
    planner_reason: str
    planner_steps: list[PlannerStep] = field(default_factory=list)
    components: list[UiComponent] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)