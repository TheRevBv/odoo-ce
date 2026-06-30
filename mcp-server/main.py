"""
main.py — FastAPI JSON-RPC 2.0 endpoint for the Odoo MCP server.

Speaks the same plain JSON-RPC-over-HTTP contract that nexia-agent-v2's
MCP client (app/mcp/client.py) already implements: a single POST endpoint
dispatching on `method` (tools/list, tools/call), no session handshake.
Deliberately NOT the official `mcp` SDK — that defaults to stdio or
session-based streamable-HTTP, which the existing client does not speak.
"""

from __future__ import annotations

import asyncio
import os

from fastapi import FastAPI, Header, HTTPException, Request

from odoo_client import OdooClient
from tools import TOOL_DEFINITIONS, dispatch

app = FastAPI(title="Odoo MCP Server")

_AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN", "")

_client = OdooClient(
    url=os.environ.get("ODOO_URL", "http://odoo:8069"),
    db=os.environ.get("ODOO_DB_NAME", "odoo"),
    login=os.environ.get("ODOO_ADMIN_LOGIN", "admin"),
    password=os.environ.get("ODOO_ADMIN_PASSWD", "admin"),
    stock_location_id=(
        int(os.environ["ODOO_STOCK_LOCATION_ID"])
        if os.environ.get("ODOO_STOCK_LOCATION_ID")
        else None
    ),
)


def _check_auth(authorization: str | None) -> None:
    if not _AUTH_TOKEN:
        return
    if authorization != f"Bearer {_AUTH_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.post("/")
async def rpc(request: Request, authorization: str | None = Header(default=None)) -> dict:
    _check_auth(authorization)
    body = await request.json()
    request_id = body.get("id")
    method = body.get("method")

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOL_DEFINITIONS}}

    if method == "tools/call":
        params = body.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments", {})
        try:
            result = await asyncio.to_thread(dispatch, name, arguments, _client)
        except KeyError:
            return {
                "jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32601, "message": f"Unknown tool: {name}"},
            }
        except Exception as exc:  # noqa: BLE001 — surfaced as JSON-RPC error, never a 500
            return {
                "jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32000, "message": str(exc)},
            }
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    return {
        "jsonrpc": "2.0", "id": request_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
