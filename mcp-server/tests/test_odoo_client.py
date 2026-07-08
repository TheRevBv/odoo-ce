"""tests/test_odoo_client.py — tests for odoo_client.py (XML-RPC wrapper)."""

from unittest.mock import MagicMock, patch

from odoo_client import OdooClient


def _client(**overrides):
    defaults = dict(
        url="http://odoo:8069", db="odoo", login="admin", password="admin",
        stock_location_id=5,
    )
    defaults.update(overrides)
    return OdooClient(**defaults)


def _fake_proxy_factory(common_proxy, models_proxy):
    def fake_proxy(url):
        return common_proxy if url.endswith("/xmlrpc/2/common") else models_proxy
    return fake_proxy


def test_search_catalog_empty_query_returns_empty_list():
    client = _client()
    assert client.search_catalog("   ") == []


def test_search_catalog_returns_products_with_stock():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.side_effect = [
        [{"id": 42, "default_code": "GDB-1420", "name": "Balata delantera TRW GDB-1420", "lst_price": 520.0}],
        [{"product_id": [42, "Balata delantera TRW GDB-1420"], "quantity": 4.0}],
    ]

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        result = _client().search_catalog("jetta", limit=5)

    assert result == [
        {"sku": "GDB-1420", "nombre": "Balata delantera TRW GDB-1420", "precio": 520.0, "stock": 4.0}
    ]


def test_search_catalog_no_results_returns_empty_list():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.return_value = []

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        result = _client().search_catalog("xyz-no-match")

    assert result == []


def test_search_catalog_auth_failure_returns_empty_list():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 0  # Odoo devuelve 0/False si falla auth

    with patch("odoo_client.xmlrpc.client.ServerProxy", return_value=common_proxy):
        result = _client().search_catalog("balatas")

    assert result == []


def test_search_catalog_xmlrpc_fault_returns_empty_list():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.side_effect = ConnectionError("odoo down")

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        result = _client().search_catalog("balatas")

    assert result == []


def test_search_catalog_single_word_domain_unchanged():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.return_value = []

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        _client().search_catalog("Tsuru")

    call_args = models_proxy.execute_kw.call_args_list[0].args
    domain = call_args[5][0]
    assert domain == ["|", ["default_code", "ilike", "Tsuru"], ["name", "ilike", "Tsuru"]]


def test_search_catalog_multi_word_domain_ands_each_word():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.return_value = []

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        _client().search_catalog("Bendix Tsuru")

    call_args = models_proxy.execute_kw.call_args_list[0].args
    domain = call_args[5][0]
    assert domain == [
        "|", ["default_code", "ilike", "Bendix"], ["name", "ilike", "Bendix"],
        "|", ["default_code", "ilike", "Tsuru"], ["name", "ilike", "Tsuru"],
    ]


def test_search_catalog_sku_with_hyphen_stays_single_token():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.return_value = []

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        _client().search_catalog("RD-105")

    call_args = models_proxy.execute_kw.call_args_list[0].args
    domain = call_args[5][0]
    assert domain == ["|", ["default_code", "ilike", "RD-105"], ["name", "ilike", "RD-105"]]


def test_search_catalog_filters_short_connector_words():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.return_value = []

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        _client().search_catalog("balatas de Tsuru")

    call_args = models_proxy.execute_kw.call_args_list[0].args
    domain = call_args[5][0]
    assert domain == [
        "|", ["default_code", "ilike", "balata"], ["name", "ilike", "balata"],
        "|", ["default_code", "ilike", "Tsuru"], ["name", "ilike", "Tsuru"],
    ]


def test_search_catalog_empty_after_filtering_short_words_returns_empty_list():
    with patch("odoo_client.xmlrpc.client.ServerProxy") as mock_proxy:
        result = _client().search_catalog("de la")

    assert result == []
    mock_proxy.assert_not_called()


def test_search_catalog_strips_trailing_s_from_plural_word():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.return_value = []

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        _client().search_catalog("balatas")

    call_args = models_proxy.execute_kw.call_args_list[0].args
    domain = call_args[5][0]
    assert domain == ["|", ["default_code", "ilike", "balata"], ["name", "ilike", "balata"]]


def test_search_catalog_plural_multi_word_matches_singular_catalog():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.return_value = []

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        _client().search_catalog("Bendix balatas Tsuru")

    call_args = models_proxy.execute_kw.call_args_list[0].args
    domain = call_args[5][0]
    assert domain == [
        "|", ["default_code", "ilike", "Bendix"], ["name", "ilike", "Bendix"],
        "|", ["default_code", "ilike", "balata"], ["name", "ilike", "balata"],
        "|", ["default_code", "ilike", "Tsuru"], ["name", "ilike", "Tsuru"],
    ]


def test_search_catalog_does_not_strip_short_plural_looking_word():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.return_value = []

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        _client().search_catalog("gas")

    call_args = models_proxy.execute_kw.call_args_list[0].args
    domain = call_args[5][0]
    assert domain == ["|", ["default_code", "ilike", "gas"], ["name", "ilike", "gas"]]


def test_search_catalog_word_not_ending_in_s_unaffected():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.return_value = []

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        _client().search_catalog("Tsuru")

    call_args = models_proxy.execute_kw.call_args_list[0].args
    domain = call_args[5][0]
    assert domain == ["|", ["default_code", "ilike", "Tsuru"], ["name", "ilike", "Tsuru"]]


def test_get_product_by_sku():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.side_effect = [
        [{"id": 42, "default_code": "GDB-1420", "name": "Balata TRW GDB-1420", "lst_price": 520.0}],
        [{"product_id": [42, "x"], "quantity": 4.0}],
    ]

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        result = _client().get_product("GDB-1420")

    assert result == {"sku": "GDB-1420", "nombre": "Balata TRW GDB-1420", "precio": 520.0, "stock": 4.0}


def test_get_product_by_numeric_id():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.side_effect = [
        [{"id": 42, "default_code": "GDB-1420", "name": "Balata TRW GDB-1420", "lst_price": 520.0}],
        [{"product_id": [42, "x"], "quantity": 4.0}],
    ]

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        result = _client().get_product("42")

    assert result["sku"] == "GDB-1420"
    search_call_args = models_proxy.execute_kw.call_args_list[0].args
    domain = search_call_args[5][0]
    assert domain == [["id", "=", 42]]


def test_get_product_not_found_returns_none():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.return_value = []

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        result = _client().get_product("NO-SUCH-SKU")

    assert result is None


def test_get_stock_uses_default_location_when_not_specified():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.return_value = [{"product_id": [42, "x"], "quantity": 4.0}]

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        result = _client(stock_location_id=5).get_stock(42)

    assert result == {"product_id": 42, "location_id": 5, "quantity": 4.0}
    args = models_proxy.execute_kw.call_args.args
    domain = args[5][0]
    assert ["location_id", "=", 5] in domain


def test_get_stock_overrides_location_when_specified():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.return_value = []

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        result = _client(stock_location_id=5).get_stock(42, location_id=9)

    assert result["location_id"] == 9
    args = models_proxy.execute_kw.call_args.args
    domain = args[5][0]
    assert ["location_id", "=", 9] in domain


def test_get_stock_zero_when_no_quants():
    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 2
    models_proxy = MagicMock()
    models_proxy.execute_kw.return_value = []

    with patch("odoo_client.xmlrpc.client.ServerProxy", side_effect=_fake_proxy_factory(common_proxy, models_proxy)):
        result = _client().get_stock(999)

    assert result == {"product_id": 999, "location_id": 5, "quantity": 0.0}
