"""
tools.py — Tool definitions (JSON Schema) and dispatch for the Odoo MCP server.

Each definition matches the shape app/mcp/client.py:103-134 (nexia-agent-v2)
parses from a tools/list response: name, description, inputSchema.
"""

from __future__ import annotations

from typing import Any, Callable

from odoo_client import OdooClient

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "search_catalog",
        "description": "Search the live Odoo product catalog by name or SKU. Returns real-time price and stock.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Vehicle, part name, or SKU to search"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_product",
        "description": "Get a single product's price and stock by exact SKU or Odoo product id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sku_or_id": {"type": "string", "description": "Exact SKU (default_code) or numeric product id"},
            },
            "required": ["sku_or_id"],
        },
    },
    {
        "name": "get_stock",
        "description": "Get the on-hand quantity for a product at a stock location.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "Odoo product.product id"},
                "location_id": {"type": "integer", "description": "Stock location id (defaults to the configured warehouse)"},
            },
            "required": ["product_id"],
        },
    },
]


def dispatch(name: str, arguments: dict[str, Any], client: OdooClient) -> Any:
    """Call the tool named `name` with `arguments` against `client`.

    Raises KeyError if `name` is not a known tool — main.py turns that into
    a JSON-RPC error response instead of a 500.

    decrement_stock is intentionally handled here but absent from
    TOOL_DEFINITIONS: it must never appear in a tools/list response, since
    nexia-agent-v2's startup code (app/main.py) auto-registers every tool
    tools/list returns into the registry the LLM can call. It is invoked
    directly by nexia-agent-v2's payment-callback handler via call_tool(),
    bypassing tool discovery entirely.
    """
    handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
        "search_catalog": lambda args: client.search_catalog(args["query"], args.get("limit", 5)),
        "get_product": lambda args: client.get_product(args["sku_or_id"]),
        "get_stock": lambda args: client.get_stock(args["product_id"], args.get("location_id")),
        "decrement_stock": lambda args: client.decrement_stock(
            args["sku"], args["quantity"], args.get("location_id")
        ),
    }
    if name not in handlers:
        raise KeyError(name)
    return handlers[name](arguments)
