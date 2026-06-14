from typing import Any
from google.adk.tools import ToolContext

# Mock DB for Day 2 / M2 (later M5 will use FastMCP)
_ORDERS_DB = {
    "ORD-001": {
        "status": "Shipped",
        "eta": "2026-06-16",
        "items": ["Samsung Galaxy A55"]
    },
    "ORD-002": {
        "status": "Processing",
        "eta": "2026-06-18",
        "items": ["Samsung TV Decoder Pro"]
    }
}


def normalize_order_id(order_id: str) -> str:
    return order_id.strip().upper()


def lookup_order(order_id: str) -> dict[str, Any] | None:
    normalized_order_id = normalize_order_id(order_id)
    order = _ORDERS_DB.get(normalized_order_id)
    if not order:
        return None
    return {
        "order_id": normalized_order_id,
        "status": order["status"],
        "eta": order["eta"],
        "items": list(order["items"]),
    }


def cancel_existing_order(order_id: str) -> dict[str, Any]:
    normalized_order_id = normalize_order_id(order_id)
    if normalized_order_id not in _ORDERS_DB:
        return {"status": "error", "message": "Order not found."}

    _ORDERS_DB[normalized_order_id]["status"] = "Cancelled"
    _ORDERS_DB[normalized_order_id]["eta"] = "N/A"
    return {
        "status": "success",
        "message": f"Order {normalized_order_id} has been cancelled successfully.",
        "data": lookup_order(normalized_order_id),
    }

def get_order_status(order_id: str, tool_context: ToolContext) -> dict[str, Any]:
    """
    Look up the live order status and ETA for a given order ID.
    
    Args:
        order_id: The ID of the order to look up (e.g., ORD-001).
    """
    normalized_order_id = normalize_order_id(order_id)
    tool_context.state["last_order_checked"] = normalized_order_id

    order = lookup_order(normalized_order_id)
    if order:
        return {"status": "success", "data": order}
    return {"status": "error", "message": "Order not found."}

def cancel_order(order_id: str, tool_context: ToolContext) -> dict[str, Any]:
    """
    Cancel an existing order.
    
    Args:
        order_id: The ID of the order to cancel (e.g., ORD-001).
    """
    last_checked = tool_context.state.get("last_order_checked")
    normalized_order_id = normalize_order_id(order_id)

    if last_checked and last_checked != normalized_order_id:
        return {
            "status": "error",
            "message": f"Please confirm the last checked order before cancelling {normalized_order_id}.",
        }

    return cancel_existing_order(normalized_order_id)
