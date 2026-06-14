import asyncio
import re
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from src.agents.contracts import AgentResponse, PlannerStep, UiComponent
from src.config.settings import FAST_MODEL
from src.tools.order_tools import get_order_status, cancel_order
from src.tools.order_tools import cancel_existing_order, lookup_order, normalize_order_id
from src.tools.product_tools import lookup_product
from src.rag.retriever import retrieve_knowledge

load_dotenv()

if TYPE_CHECKING:
    from google.adk.agents import LlmAgent

APP_NAME = "ecombot"
USER_ID = "user-1"
SESSION_ID = "session-1"
ORDER_ID_PATTERN = re.compile(r"\bORD-\d{3}\b", re.IGNORECASE)

SUPPORT_INSTRUCTION = """
You are the eComBot Support Agent.
Your capabilities:
- Check order status using get_order_status.
- Cancel an order using cancel_order.
- Look up products using lookup_product.
- Answer FAQs and product specs using retrieve_knowledge.

Guidelines:
- Ground your answers in the retrieve_knowledge tool output. If the tool says "No relevant information found", gracefully say you don't know and offer to connect to a human agent. Do not hallucinate product specs.
- Always use the tools to look up real data.
- Maintain context across the conversation.
- Keep responses professional and concise.
"""


def retrieve_support_knowledge(query: str) -> str:
    """Search the support knowledge base for FAQs and product information."""
    return retrieve_knowledge(query, top_k=3)


def get_support_agent() -> "LlmAgent":
    from google.adk.agents import LlmAgent
    from google.adk.models.lite_llm import LiteLlm

    return LlmAgent(
        name="SupportAgent",
        model=LiteLlm(model=FAST_MODEL),
        instruction=SUPPORT_INSTRUCTION,
        tools=[get_order_status, cancel_order, lookup_product, retrieve_support_knowledge],
        description="Handles e-commerce support queries: orders, complaints, returns, and FAQs.",
    )


def _extract_order_id(query: str) -> str | None:
    match = ORDER_ID_PATTERN.search(query)
    if not match:
        return None
    return normalize_order_id(match.group(0))


def _build_order_card(order: dict[str, object]) -> UiComponent:
    return UiComponent("order_card", order)


def handle_support_request(query: str) -> AgentResponse:
    lowered_query = query.lower()
    planner_steps = [
        PlannerStep("Determine support workflow", "Checked whether the request is about order status, cancellation, or support knowledge."),
    ]
    order_id = _extract_order_id(query)

    if "cancel" in lowered_query:
        if not order_id:
            return AgentResponse(
                agent_name="Support Agent",
                intent="order_cancellation",
                answer="I can cancel the order once you share the order ID, for example ORD-001.",
                model=FAST_MODEL,
                planner_reason="Cancellation was requested, but no order ID was provided.",
                planner_steps=planner_steps,
                components=[UiComponent("fallback", {"message": "No order card is available until an order ID is provided."})],
                sources=["Orders DB"],
            )

        cancellation = cancel_existing_order(order_id)
        if cancellation["status"] == "success":
            order = cancellation["data"]
            return AgentResponse(
                agent_name="Support Agent",
                intent="order_cancellation",
                answer=cancellation["message"],
                model=FAST_MODEL,
                planner_reason="The request is a post-purchase order action, so it belongs to Support.",
                planner_steps=planner_steps + [PlannerStep("Execute cancellation", f"Cancelled order {order_id} in the orders store.")],
                components=[_build_order_card(order)],
                sources=["Orders DB"],
                metadata={"order_id": order_id},
            )

    if order_id or "order" in lowered_query or "shipping" in lowered_query or "return" in lowered_query:
        if not order_id:
            return AgentResponse(
                agent_name="Support Agent",
                intent="order_support",
                answer="Please share your order ID so I can check the latest order status for you.",
                model=FAST_MODEL,
                planner_reason="The request is support-related, but the order lookup needs an order ID.",
                planner_steps=planner_steps,
                components=[UiComponent("fallback", {"message": "Awaiting an order ID to render an order status card."})],
                sources=["Orders DB"],
            )

        order = lookup_order(order_id)
        if not order:
            return AgentResponse(
                agent_name="Support Agent",
                intent="order_status",
                answer=f"I could not find order {order_id}. Please verify the order ID and try again.",
                model=FAST_MODEL,
                planner_reason="The request is for order support, but the order ID was not found.",
                planner_steps=planner_steps + [PlannerStep("Check order store", f"No record matched {order_id}.")],
                components=[UiComponent("fallback", {"message": "No structured order card is available because the order was not found."})],
                sources=["Orders DB"],
                metadata={"order_id": order_id},
            )

        answer = (
            f"Your order {order_id} is currently {order['status']}. "
            f"The estimated delivery date is {order['eta']}."
        )
        return AgentResponse(
            agent_name="Support Agent",
            intent="order_status",
            answer=answer,
            model=FAST_MODEL,
            planner_reason="The request is about an existing order, so it was delegated to Support.",
            planner_steps=planner_steps + [PlannerStep("Lookup order", f"Fetched live status for {order_id} from the orders store.")],
            components=[_build_order_card(order)],
            sources=["Orders DB"],
            metadata={"order_id": order_id},
        )

    knowledge = retrieve_support_knowledge(query)
    if knowledge.startswith("No relevant information found"):
        answer = "I do not have a reliable support article for that yet. I can connect you to a human support agent if needed."
        components = [UiComponent("fallback", {"message": "No knowledge-base answer was available for this support request."})]
    else:
        answer = knowledge.split("\n\n")[0]
        components = [UiComponent("faq_card", {"question": query, "answer": knowledge})]

    return AgentResponse(
        agent_name="Support Agent",
        intent="support_knowledge",
        answer=answer,
        model=FAST_MODEL,
        planner_reason="The request is informational post-purchase support, so it belongs to Support.",
        planner_steps=planner_steps + [PlannerStep("Query knowledge base", "Retrieved the closest FAQ or support article match.")],
        components=components,
        sources=["Knowledge Base"],
    )


root_agent = None

async def main():
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )

    runner = Runner(
        agent=get_support_agent(),
        app_name=APP_NAME,
        session_service=session_service,
    )

    user_prompt = "Hi, can you tell me the status of my order ORD-001?"
    print(f"User: {user_prompt}\n")

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=user_prompt)],
    )

    response_text = ""
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=user_message,
    ):
        if event.is_final_response():
            response_text = event.content.parts[0].text or ""

    print(f"\nAgent Response: {response_text}")

if __name__ == "__main__":
    asyncio.run(main())