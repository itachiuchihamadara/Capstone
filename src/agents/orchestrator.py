from dotenv import load_dotenv
from typing import TYPE_CHECKING

from src.agents.contracts import AgentPlan, AgentResponse, PlannerStep
from src.agents.sales_agent import handle_sales_request
from src.agents.support_agent import handle_support_request
from src.config.settings import FAST_MODEL

load_dotenv()

if TYPE_CHECKING:
    from google.adk.agents import LlmAgent

ORCHESTRATOR_INSTRUCTION = """
You are the eComBot Orchestrator.
Your job is to classify the user's intent, create a plan, and delegate the task
to the most appropriate specialist agent.

Support Agent handles orders, complaints, returns, and post-purchase help.
Sales Agent handles product discovery, comparisons, recommendations, and upsells.

Always think planner first, executor second.
""".strip()

SUPPORT_KEYWORDS = {
    "order",
    "where is my order",
    "track",
    "shipping",
    "shipment",
    "refund",
    "return",
    "cancel",
    "complaint",
    "warranty",
}

SALES_KEYWORDS = {
    "buy",
    "recommend",
    "comparison",
    "compare",
    "price",
    "phone",
    "smartphone",
    "product",
    "specs",
    "upsell",
}

def get_orchestrator() -> "LlmAgent":
    from google.adk.agents import LlmAgent
    from google.adk.models.lite_llm import LiteLlm

    return LlmAgent(
        name="Orchestrator",
        model=LiteLlm(model=FAST_MODEL),
        instruction=ORCHESTRATOR_INSTRUCTION,
        description="Main entry point for eComBot with planner-executor routing."
    )


def plan_route(query: str) -> AgentPlan:
    lowered_query = query.lower()
    steps = [PlannerStep("Classify request", "Checked whether the user intent is support-led or sales-led.")]

    if "ord-" in lowered_query or any(keyword in lowered_query for keyword in SUPPORT_KEYWORDS):
        return AgentPlan(
            intent="support",
            delegated_agent="Support Agent",
            reason="The request references an order or post-purchase support workflow.",
            planner_steps=steps + [PlannerStep("Delegate to specialist", "Selected Support Agent for order and support operations.")],
        )

    if any(keyword in lowered_query for keyword in SALES_KEYWORDS):
        return AgentPlan(
            intent="sales",
            delegated_agent="Sales Agent",
            reason="The request is about product discovery, comparison, recommendation, or price.",
            planner_steps=steps + [PlannerStep("Delegate to specialist", "Selected Sales Agent for product discovery and recommendation.")],
        )

    return AgentPlan(
        intent="sales",
        delegated_agent="Sales Agent",
        reason="The request is ambiguous but product-led guidance is the safest default for general shopping queries.",
        planner_steps=steps + [PlannerStep("Fallback route", "Defaulted to Sales Agent because no support signal was detected.")],
    )


def execute_plan(plan: AgentPlan, query: str) -> AgentResponse:
    if plan.delegated_agent == "Support Agent":
        response = handle_support_request(query)
    else:
        response = handle_sales_request(query)

    response.planner_reason = plan.reason
    response.planner_steps = plan.planner_steps + response.planner_steps
    response.metadata["delegated_agent"] = plan.delegated_agent
    response.metadata["intent"] = plan.intent
    return response


def process_user_message(query: str) -> AgentResponse:
    plan = plan_route(query)
    return execute_plan(plan, query)

orchestrator_agent = None
