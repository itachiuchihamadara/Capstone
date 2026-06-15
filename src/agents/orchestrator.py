from dotenv import load_dotenv
from typing import TYPE_CHECKING

from src.agents.contracts import AgentPlan, AgentResponse, PlannerStep, UiComponent
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

CAPABILITIES_ANSWER = (
    "I can help with order support such as tracking, cancellations, returns, and warranty questions, "
    "and I can also help with product discovery such as recommendations, comparisons, and budget-based shopping advice."
)

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

META_KEYWORDS = {
    "what can you help",
    "what do you do",
    "help me with",
    "capabilities",
    "who are you",
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


def _has_support_signal(lowered_query: str) -> bool:
    return "ord-" in lowered_query or any(keyword in lowered_query for keyword in SUPPORT_KEYWORDS)


def _has_sales_signal(lowered_query: str) -> bool:
    return any(keyword in lowered_query for keyword in SALES_KEYWORDS)


def _has_meta_signal(lowered_query: str) -> bool:
    return any(keyword in lowered_query for keyword in META_KEYWORDS)


def plan_route(query: str) -> AgentPlan:
    lowered_query = query.lower()
    steps = [PlannerStep("Classify request", "Checked whether the user intent is support-led or sales-led.")]
    support_signal = _has_support_signal(lowered_query)
    sales_signal = _has_sales_signal(lowered_query)
    meta_signal = _has_meta_signal(lowered_query)

    if meta_signal and not support_signal and not sales_signal:
        return AgentPlan(
            intent="self",
            delegated_agent="Orchestrator",
            reason="The request is a capability or meta question that the Orchestrator can answer directly.",
            planner_steps=steps + [PlannerStep("Answer directly", "Handled the request without delegation because it is a meta question.")],
        )

    if support_signal and sales_signal:
        return AgentPlan(
            intent="mixed",
            delegated_agent="Support Agent + Sales Agent",
            reason="The request includes both post-purchase support work and product discovery work, so it needs a planner-executor handoff.",
            planner_steps=steps + [PlannerStep("Create mixed plan", "Planned a two-step flow: Support first, then Sales with support context.")],
        )

    if support_signal:
        return AgentPlan(
            intent="support",
            delegated_agent="Support Agent",
            reason="The request references an order or post-purchase support workflow.",
            planner_steps=steps + [PlannerStep("Delegate to specialist", "Selected Support Agent for order and support operations.")],
        )

    if sales_signal:
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
    trace = [
        f"User message: {query}",
        f"Routing decision: {plan.intent}",
        f"Delegated agent: {plan.delegated_agent}",
    ]

    if plan.intent == "self":
        response = AgentResponse(
            agent_name="Orchestrator",
            intent="self",
            answer=CAPABILITIES_ANSWER,
            model=FAST_MODEL,
            planner_reason=plan.reason,
            planner_steps=plan.planner_steps,
            components=[UiComponent("faq_card", {"question": query, "answer": CAPABILITIES_ANSWER})],
            sources=["Orchestrator"],
        )
    elif plan.intent == "mixed":
        support_response = handle_support_request(query)
        support_response.planner_steps.insert(
            0,
            PlannerStep("Run support task", "Executed the support portion first to gather order context."),
        )
        sales_response = handle_sales_request(query, context=support_response.answer)
        sales_response.planner_steps.insert(
            0,
            PlannerStep("Run sales task", "Executed the sales portion after the support result was available."),
        )

        combined_components = support_response.components + sales_response.components
        combined_sources = support_response.sources + [source for source in sales_response.sources if source not in support_response.sources]
        combined_metadata = dict(support_response.metadata)
        combined_metadata.update(sales_response.metadata)
        combined_metadata["mixed_response"] = {
            "support_agent": support_response.answer,
            "sales_agent": sales_response.answer,
        }
        response = AgentResponse(
            agent_name="Orchestrator",
            intent="mixed",
            answer=f"Support update: {support_response.answer} Sales recommendation: {sales_response.answer}",
            model=FAST_MODEL,
            planner_reason=plan.reason,
            planner_steps=plan.planner_steps + support_response.planner_steps + sales_response.planner_steps,
            components=combined_components,
            sources=combined_sources,
            metadata=combined_metadata,
        )
        trace.append("Agent call: Support Agent for order investigation")
        trace.append("Agent call: Sales Agent for follow-up recommendation")
    elif plan.delegated_agent == "Support Agent":
        response = handle_support_request(query)
        trace.append("Agent call: Support Agent")
    else:
        response = handle_sales_request(query)
        trace.append("Agent call: Sales Agent")

    response.planner_reason = plan.reason
    if plan.intent not in {"self", "mixed"}:
        response.planner_steps = plan.planner_steps + response.planner_steps
    response.metadata["delegated_agent"] = plan.delegated_agent
    response.metadata["intent"] = plan.intent
    response.metadata["trace"] = trace
    return response


def process_user_message(query: str) -> AgentResponse:
    plan = plan_route(query)
    return execute_plan(plan, query)

orchestrator_agent = None
