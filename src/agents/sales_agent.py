import re
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from src.agents.contracts import AgentResponse, PlannerStep, UiComponent
from src.config.settings import FAST_MODEL
from src.tools.product_tools import list_products_by_category, search_products

load_dotenv()

if TYPE_CHECKING:
    from google.adk.agents import LlmAgent

SALES_INSTRUCTION = """
You are the eComBot Sales Agent.
Your job is to help customers discover products, compare options,
recommend the best fit, and suggest useful upsells.

Guidelines:
- Focus on product discovery, recommendations, comparisons, and budgets.
- Use catalog-backed tools instead of inventing product data.
- Explain recommendations with concise reasoning.
- Offer a practical alternative when there are multiple viable options.
""".strip()

_BUDGET_PATTERN = re.compile(r"(?:under|below|budget|around)?\s*₹?\$?\s*(\d[\d,]*)", re.IGNORECASE)


def get_sales_agent() -> "LlmAgent":
    from google.adk.agents import LlmAgent
    from google.adk.models.lite_llm import LiteLlm

    return LlmAgent(
        name="SalesAgent",
        model=LiteLlm(model=FAST_MODEL),
        instruction=SALES_INSTRUCTION,
        tools=[],
        description="Handles product discovery, recommendations, comparisons, and upsells.",
    )


def _extract_budget(query: str) -> int | None:
    match = _BUDGET_PATTERN.search(query)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def _normalize_query(query: str) -> str:
    return query.strip().lower()


def _shortlist_products(query: str) -> list[dict]:
    lowered = _normalize_query(query)
    matches = search_products(query)
    if matches:
        return matches
    if "phone" in lowered or "smartphone" in lowered or "mobile" in lowered:
        return list_products_by_category("Smartphone")
    return list_products_by_category("Smartphone")


def handle_sales_request(query: str) -> AgentResponse:
    budget = _extract_budget(query)
    planner_steps = [
        PlannerStep("Identify shopping goal", "Parsed the request for product intent, comparison needs, and budget."),
    ]

    shortlist = _shortlist_products(query)
    if budget is not None:
        planner_steps.append(PlannerStep("Apply budget filter", f"Kept products priced at or below {budget}."))
        budget_filtered = [product for product in shortlist if product["price"] <= budget]
        if budget_filtered:
            shortlist = budget_filtered

    if not shortlist:
        return AgentResponse(
            agent_name="Sales Agent",
            intent="product_discovery",
            answer="I could not find a good catalog match for that request. Try a product name, category, or budget so I can narrow it down.",
            model=FAST_MODEL,
            planner_reason="No catalog match was found for the shopping request.",
            planner_steps=planner_steps,
            components=[UiComponent("fallback", {"message": "No structured product card available for this request."})],
            sources=["Product Catalog"],
        )

    shortlist = sorted(shortlist, key=lambda product: product["price"])
    planner_steps.append(PlannerStep("Compare shortlisted products", f"Prepared {len(shortlist)} catalog option(s) for recommendation."))
    recommended = shortlist[-1]
    alternative = shortlist[0] if shortlist[0]["id"] != recommended["id"] else None

    answer_lines = [
        f"I would recommend the {recommended['name']}.",
        f"It is priced at {recommended['price']} and offers {recommended['specs']}.",
    ]
    if budget is not None:
        answer_lines.append(f"This recommendation stays within your stated budget of {budget}.")
    if alternative:
        answer_lines.append(
            f"If you want a lower-cost option, consider the {alternative['name']} at {alternative['price']}."
        )

    return AgentResponse(
        agent_name="Sales Agent",
        intent="product_recommendation",
        answer=" ".join(answer_lines),
        model=FAST_MODEL,
        planner_reason="The request is product-led and requires discovery or recommendation, so it was delegated to Sales.",
        planner_steps=planner_steps,
        components=[
            UiComponent(
                "product_cards",
                {
                    "products": shortlist[:3],
                    "recommended_id": recommended["id"],
                },
            )
        ],
        sources=["Product Catalog"],
        metadata={"budget": budget, "recommended_product": recommended["name"]},
    )


sales_agent = None