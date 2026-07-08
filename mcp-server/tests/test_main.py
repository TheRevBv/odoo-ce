"""tests/test_main.py — tests for main.py (JSON-RPC endpoint, Bearer auth)."""

import importlib
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_module(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_TOKEN", "test-token-123")
    monkeypatch.setenv("ODOO_STOCK_LOCATION_ID", "5")
    import main as main_module
    importlib.reload(main_module)
    return main_module


def test_tools_list_returns_three_tools(app_module):
    client = TestClient(app_module.app)
    response = client.post(
        "/", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        headers={"Authorization": "Bearer test-token-123"},
    )
    assert response.status_code == 200
    names = {t["name"] for t in response.json()["result"]["tools"]}
    assert names == {"search_catalog", "get_product", "get_stock"}


def test_missing_auth_returns_401(app_module):
    client = TestClient(app_module.app)
    response = client.post("/", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    assert response.status_code == 401


def test_wrong_auth_returns_401(app_module):
    client = TestClient(app_module.app)
    response = client.post(
        "/", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


def test_tools_call_dispatches_to_search_catalog(app_module):
    app_module._client.search_catalog = MagicMock(
        return_value=[{"sku": "X", "nombre": "Y", "precio": 1.0, "stock": 2.0}]
    )
    client = TestClient(app_module.app)
    response = client.post(
        "/",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "search_catalog", "arguments": {"query": "balatas"}}},
        headers={"Authorization": "Bearer test-token-123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["result"] == [{"sku": "X", "nombre": "Y", "precio": 1.0, "stock": 2.0}]
    app_module._client.search_catalog.assert_called_once_with("balatas", 5)


def test_tools_call_unknown_tool_returns_jsonrpc_error(app_module):
    client = TestClient(app_module.app)
    response = client.post(
        "/",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "nope", "arguments": {}}},
        headers={"Authorization": "Bearer test-token-123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["error"]["code"] == -32601


def test_tools_call_tool_exception_returns_jsonrpc_error_not_500(app_module):
    app_module._client.get_product = MagicMock(side_effect=RuntimeError("boom"))
    client = TestClient(app_module.app)
    response = client.post(
        "/",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "get_product", "arguments": {"sku_or_id": "X"}}},
        headers={"Authorization": "Bearer test-token-123"},
    )
    assert response.status_code == 200
    assert response.json()["error"]["message"] == "boom"


def test_unknown_method_returns_jsonrpc_error(app_module):
    client = TestClient(app_module.app)
    response = client.post(
        "/", json={"jsonrpc": "2.0", "id": 1, "method": "nope/method", "params": {}},
        headers={"Authorization": "Bearer test-token-123"},
    )
    assert response.status_code == 200
    assert response.json()["error"]["code"] == -32601


def test_health_endpoint_no_auth_required(app_module):
    client = TestClient(app_module.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
