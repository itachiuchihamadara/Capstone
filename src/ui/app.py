import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from dotenv import load_dotenv

from src.agents.contracts import AgentResponse, UiComponent
from src.agents.orchestrator import process_user_message
from src.config.settings import FAST_MODEL
from src.tools.order_tools import cancel_existing_order

load_dotenv()

st.set_page_config(page_title="eComBot v7", layout="wide")

APP_CSS = """
.shell {
  max-width: 1200px;
  margin: 0 auto;
}
.panel {
  border: 1px solid #d8d1c6;
  border-radius: 18px;
  padding: 16px;
  background: linear-gradient(180deg, #fffdf8 0%, #f6efe4 100%);
  box-shadow: 0 10px 30px rgba(94, 66, 33, 0.08);
}
.badge {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 999px;
  background: #1f4f46;
  color: #f8f3e8;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.trace-pill {
  display: inline-block;
  margin: 4px 6px 0 0;
  padding: 6px 10px;
  border-radius: 999px;
  background: #efe3cf;
  color: #674522;
  font-size: 12px;
}
.order-card, .product-card, .faq-card, .fallback-card {
  border: 1px solid #e3d7c7;
  border-radius: 16px;
  padding: 16px;
  background: #fffaf2;
  margin-bottom: 12px;
}
.status-pill {
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}
.status-pill.shipped { background: #dff7e7; color: #0b6b35; }
.status-pill.processing { background: #fff1cf; color: #8f5e00; }
.status-pill.cancelled { background: #f8d8d8; color: #8d1f1f; }
.price { font-size: 20px; font-weight: 700; color: #1f4f46; }
.source-tag {
  display: inline-block;
  margin: 4px 6px 0 0;
  padding: 4px 10px;
  border-radius: 999px;
  background: #243746;
  color: #f7f9fb;
  font-size: 12px;
}
"""
st.markdown(f"<style>{APP_CSS}</style>", unsafe_allow_html=True)


def _status_class(status: str) -> str:
    return status.strip().lower().replace(" ", "-")


def _render_model_badge(model_name: str) -> str:
    return (
        "<div class='panel'><div class='badge'>LiteLLM Model</div>"
        f"<p style='margin:12px 0 0 0; font-size:16px;'>{model_name}</p></div>"
    )


def _render_sources(sources: list[str]) -> str:
    if not sources:
        return "<div class='panel'><strong>RAG Sources</strong><p>No source tags for this reply.</p></div>"
    tags = "".join(f"<span class='source-tag'>{source}</span>" for source in sources)
    return f"<div class='panel'><strong>RAG Sources</strong><div style='margin-top:8px'>{tags}</div></div>"


def _render_trace(response: AgentResponse) -> str:
    steps = "".join(
        f"<li><strong>{step.title}:</strong> {step.detail}</li>" for step in response.planner_steps
    )
    pills = "".join(
        [
            "<span class='trace-pill'>Orchestrator</span>",
            f"<span class='trace-pill'>{response.agent_name}</span>",
            f"<span class='trace-pill'>{response.intent}</span>",
        ]
    )
    return (
        "<div class='panel'><strong>Routing Trace</strong>"
        f"<div style='margin-top:8px'>{pills}</div>"
        f"<p style='margin-top:12px'>{response.planner_reason}</p>"
        f"<ol style='padding-left:18px'>{steps}</ol></div>"
    )


def _render_cards(response: AgentResponse) -> str:
    rendered = []
    for component in response.components:
        if component.kind == "order_card":
            order = component.payload
            items = "".join(f"<li>{item}</li>" for item in order["items"])
            rendered.append(
                "<div class='order-card'>"
                f"<div style='display:flex; justify-content:space-between; gap:12px; align-items:center'><h3 style='margin:0'>{order['order_id']}</h3>"
                f"<span class='status-pill {_status_class(order['status'])}'>{order['status']}</span></div>"
                f"<p><strong>ETA:</strong> {order['eta']}</p>"
                f"<p><strong>Items:</strong></p><ul>{items}</ul>"
                "</div>"
            )
        elif component.kind == "product_cards":
            recommended_id = component.payload.get("recommended_id")
            for product in component.payload["products"]:
                accent = " style='border:2px solid #1f4f46;'" if product["id"] == recommended_id else ""
                badge = "<div class='badge' style='background:#9c4f19'>Recommended</div>" if product["id"] == recommended_id else ""
                rendered.append(
                    f"<div class='product-card'{accent}>"
                    f"{badge}<h3 style='margin:12px 0 6px 0'>{product['name']}</h3>"
                    f"<p class='price'>₹{product['price']}</p>"
                    f"<p><strong>Category:</strong> {product['category']}</p>"
                    f"<p>{product['specs']}</p>"
                    f"<p><strong>Warranty:</strong> {product['warranty']}</p>"
                    "</div>"
                )
        elif component.kind == "faq_card":
            rendered.append(
                "<div class='faq-card'>"
                f"<h3 style='margin-top:0'>{component.payload['question']}</h3>"
                f"<p>{component.payload['answer']}</p>"
                "</div>"
            )
        elif component.kind == "fallback":
            rendered.append(
                "<div class='fallback-card'>"
                f"<p style='margin:0'>{component.payload['message']}</p>"
                "</div>"
            )

    if not rendered:
        rendered.append(
            "<div class='fallback-card'><p style='margin:0'>No structured component was generated, so the raw answer is shown in chat.</p></div>"
        )
    return "<div class='panel'><strong>Structured Output</strong><div style='margin-top:12px'>" + "".join(rendered) + "</div></div>"


def _empty_state() -> tuple[str, str, str, str, dict]:
    return (
        "<div class='panel'><strong>Structured Output</strong><p>Ask about an order or product to render cards here.</p></div>",
        "<div class='panel'><strong>Routing Trace</strong><p>The orchestrator trace will appear after the first message.</p></div>",
        "<div class='panel'><strong>RAG Sources</strong><p>Sources will appear here when used.</p></div>",
        _render_model_badge(FAST_MODEL),
    )


# --- Streamlit UI Setup ---

st.markdown(
    """
    <div class='shell'>
      <h1 style='margin-bottom:8px'>eComBot v7</h1>
      <p style='margin-top:0'>Planner-executor orchestration with Support and Sales agents, plus structured UI cards and streaming responses.</p>
    </div>
    """,
    unsafe_allow_html=True
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_response" not in st.session_state:
    st.session_state.last_response = None

col_chat, col_panels = st.columns([3, 2])

with col_chat:
    chat_container = st.container(height=520)
    
    col_btns = st.columns([1, 1, 4])
    with col_btns[0]:
        if st.button("Cancel last order"):
            order_id = st.session_state.last_response.metadata.get("order_id") if st.session_state.last_response else None
            if not order_id:
                st.session_state.messages.append({"role": "user", "content": "Cancel last order"})
                st.session_state.messages.append({"role": "assistant", "content": "There is no active order card to cancel yet."})
                st.session_state.last_response = None
            else:
                cancellation = cancel_existing_order(order_id)
                updated_order = cancellation.get("data") or {"order_id": order_id, "status": "Unknown", "eta": "N/A", "items": []}
                response = AgentResponse(
                    agent_name="Support Agent",
                    intent="order_cancellation",
                    answer=cancellation["message"],
                    model=FAST_MODEL,
                    planner_reason="The UI cancel action executes a direct Support workflow on the currently displayed order.",
                    planner_steps=[],
                    components=[UiComponent("order_card", updated_order)],
                    sources=["Orders DB"],
                    metadata={"order_id": order_id},
                )
                st.session_state.last_response = response
                st.session_state.messages.append({"role": "user", "content": "Cancel last order"})
                st.session_state.messages.append({"role": "assistant", "content": response.answer})
            st.rerun()
                
    with col_btns[1]:
        if st.button("Clear"):
            st.session_state.messages = []
            st.session_state.last_response = None
            st.rerun()

    prompt = st.chat_input("Try: Where is my order ORD-001? or What phone should I buy under 18000?")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                response = process_user_message(prompt)
                
                full_response = ""
                chunk_size = 18
                for stop in range(chunk_size, len(response.answer) + chunk_size, chunk_size):
                    full_response = response.answer[:stop]
                    message_placeholder.markdown(full_response + "▌")
                    time.sleep(0.02)
                
                full_response = response.answer
                message_placeholder.markdown(full_response)
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.session_state.last_response = response
            st.rerun()

with col_panels:
    if st.session_state.last_response:
        response = st.session_state.last_response
        st.markdown(_render_cards(response), unsafe_allow_html=True)
        st.markdown(_render_trace(response), unsafe_allow_html=True)
        st.markdown(_render_sources(response.sources), unsafe_allow_html=True)
        st.markdown(_render_model_badge(response.model), unsafe_allow_html=True)
    else:
        cards_html, trace_html, sources_html, badge_html = _empty_state()
        st.markdown(cards_html, unsafe_allow_html=True)
        st.markdown(trace_html, unsafe_allow_html=True)
        st.markdown(sources_html, unsafe_allow_html=True)
        st.markdown(badge_html, unsafe_allow_html=True)
