from typing import Any
from google.adk.tools import ToolContext
import json
from pathlib import Path


def load_products() -> list[dict[str, Any]]:
    data_dir = Path(__file__).parent.parent / "rag" / "data"
    with open(data_dir / "products.json", "r") as f:
        return json.load(f)


def search_products(query: str) -> list[dict[str, Any]]:
    lowered_query = query.lower()
    products = load_products()
    return [
        product
        for product in products
        if lowered_query in product["name"].lower()
        or lowered_query in product["category"].lower()
        or lowered_query in product["specs"].lower()
    ]


def list_products_by_category(category: str) -> list[dict[str, Any]]:
    lowered_category = category.lower()
    return [
        product for product in load_products() if product["category"].lower() == lowered_category
    ]

def lookup_product(query: str, tool_context: ToolContext) -> dict[str, Any]:
    """
    Look up product details based on a name or keyword.
    
    Args:
        query: The product name or keyword to search for.
    """
    results = search_products(query)
    
    if results:
        tool_context.state["last_product_checked"] = results[0]["name"]
        return {"status": "success", "data": results}
    return {"status": "error", "message": "Product not found."}
