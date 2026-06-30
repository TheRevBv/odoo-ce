"""
odoo_client.py — Read-only XML-RPC wrapper for Odoo product/stock queries.

This is the only module in this service that talks to Odoo. It uses Odoo's
official XML-RPC API (xmlrpc.client, stdlib) — no direct database access,
so it respects Odoo's ACLs and business logic instead of bypassing them
the way sales-core's SQL-direct client does (documented technical debt,
see nexia-local-stack CLAUDE.md "Deuda técnica #1").

Assumes single-variant products (no product.attribute combinations): reads
default_code/lst_price directly from product.product, which is correct as
long as each product.template has exactly one auto-created variant — true
for the catalog seeded by nexia-local-stack/scripts/seed-odoo-catalog.py.
"""

from __future__ import annotations

import xmlrpc.client
from typing import Any


class OdooClient:
    """Lazy-authenticating XML-RPC client for read-only product/stock queries."""

    def __init__(
        self,
        url: str,
        db: str,
        login: str,
        password: str,
        stock_location_id: int | None = None,
    ) -> None:
        self._url = url
        self._db = db
        self._login = login
        self._password = password
        self._stock_location_id = stock_location_id
        self._uid: int | None = None

    def _authenticate(self) -> int | None:
        if self._uid is not None:
            return self._uid
        common = xmlrpc.client.ServerProxy(f"{self._url}/xmlrpc/2/common")
        uid = common.authenticate(self._db, self._login, self._password, {})
        if not uid:
            return None
        self._uid = uid
        return uid

    def _execute_kw(self, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        uid = self._authenticate()
        if uid is None:
            raise RuntimeError(f"Odoo authentication failed for login '{self._login}'")
        models = xmlrpc.client.ServerProxy(f"{self._url}/xmlrpc/2/object")
        return models.execute_kw(self._db, uid, self._password, model, method, args, kwargs or {})

    def _stock_for_products(self, product_ids: list[int], location_id: int | None) -> dict[int, float]:
        loc = location_id if location_id is not None else self._stock_location_id
        if not product_ids or loc is None:
            return {}
        quants = self._execute_kw(
            "stock.quant", "search_read",
            [[["product_id", "in", product_ids], ["location_id", "=", loc]]],
            {"fields": ["product_id", "quantity"]},
        )
        totals: dict[int, float] = {}
        for q in quants:
            pid = q["product_id"][0]
            totals[pid] = totals.get(pid, 0.0) + q["quantity"]
        return totals

    def search_catalog(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return []
        try:
            products = self._execute_kw(
                "product.product", "search_read",
                [["|", ["default_code", "ilike", query], ["name", "ilike", query]]],
                {"fields": ["id", "default_code", "name", "lst_price"], "limit": max(1, min(limit, 20))},
            )
            if not products:
                return []
            stock = self._stock_for_products([p["id"] for p in products], None)
        except Exception:
            return []

        return [
            {
                "sku": p["default_code"] or None,
                "nombre": p["name"],
                "precio": float(p["lst_price"]),
                "stock": stock.get(p["id"]),
            }
            for p in products
        ]

    def get_product(self, sku_or_id: str) -> dict[str, Any] | None:
        sku_or_id = (sku_or_id or "").strip()
        if not sku_or_id:
            return None
        domain = [["id", "=", int(sku_or_id)]] if sku_or_id.isdigit() else [["default_code", "=", sku_or_id]]

        try:
            products = self._execute_kw(
                "product.product", "search_read", [domain],
                {"fields": ["id", "default_code", "name", "lst_price"], "limit": 1},
            )
            if not products:
                return None
            stock = self._stock_for_products([products[0]["id"]], None)
        except Exception:
            return None

        p = products[0]
        return {
            "sku": p["default_code"] or None,
            "nombre": p["name"],
            "precio": float(p["lst_price"]),
            "stock": stock.get(p["id"]),
        }

    def get_stock(self, product_id: int, location_id: int | None = None) -> dict[str, Any]:
        loc = location_id if location_id is not None else self._stock_location_id
        try:
            stock = self._stock_for_products([product_id], loc)
        except Exception:
            stock = {}
        return {
            "product_id": product_id,
            "location_id": loc,
            "quantity": stock.get(product_id, 0.0),
        }
