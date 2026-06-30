# Odoo MCP Server

Servicio HTTP que expone el catálogo de productos de Odoo (precio, stock) a
`nexia-agent-v2` vía un endpoint JSON-RPC 2.0 hecho a mano — compatible con el
cliente MCP genérico que `nexia-agent-v2` ya tiene (`app/mcp/client.py`), sin
sesión (`Mcp-Session-Id`). Es el único componente del stack que habla con Odoo
directamente; lo hace por XML-RPC oficial (solo lectura), no por SQL crudo —
ver `docs/superpowers/specs/2026-06-30-odoo-mcp-server-design.md` en
`nexia-local-stack` para el diseño completo y las alternativas consideradas.

## Stack técnico

- Python 3.12
- FastAPI + Uvicorn
- `xmlrpc.client` (stdlib) — sin SDK oficial de Odoo ni de MCP
- pytest + `unittest.mock` para tests (sin red real)

## Estructura del proyecto

| Archivo | Responsabilidad |
|---|---|
| `odoo_client.py` | Único módulo que habla con Odoo. Cliente XML-RPC de solo lectura: `search_catalog`, `get_product`, `get_stock`. |
| `tools.py` | Definiciones de las 3 tools en formato JSON Schema (`TOOL_DEFINITIONS`) y el dispatcher que las conecta con `OdooClient`. |
| `main.py` | App FastAPI: un solo endpoint `POST /` que implementa `tools/list`/`tools/call` (JSON-RPC 2.0), autenticación Bearer, y `GET /health`. |
| `Dockerfile` | Imagen `python:3.12-slim`, expone el puerto 8000. |
| `tests/` | Tests unitarios (XML-RPC y HTTP mockeados). |

## Las 3 tools

| Tool | Input | Output |
|---|---|---|
| `search_catalog` | `{query: string, limit?: integer=5}` | `list[{sku, nombre, precio, stock}]` |
| `get_product` | `{sku_or_id: string}` | `{sku, nombre, precio, stock} \| null` |
| `get_stock` | `{product_id: integer, location_id?: integer}` | `{product_id, location_id, quantity}` |

Todas son de solo lectura (`search_read` vía XML-RPC) y asumen productos de
variante única — correcto para el catálogo actual, ver el docstring de
`odoo_client.py` para el detalle de esa simplificación.

## Variables de entorno

| Variable | Default | Para qué sirve |
|---|---|---|
| `ODOO_URL` | `http://odoo:8069` | Base URL del servicio Odoo (XML-RPC) |
| `ODOO_DB_NAME` | `odoo` | Nombre de la base de datos de Odoo |
| `ODOO_ADMIN_LOGIN` | `admin` | Usuario para autenticar en Odoo |
| `ODOO_ADMIN_PASSWD` | `admin` | Password del usuario anterior |
| `ODOO_STOCK_LOCATION_ID` | (ninguno) | ID de `stock.location` usado para calcular existencias; sin esto, `stock` siempre es `None`/`0.0` |
| `MCP_AUTH_TOKEN` | (ninguno) | Bearer token que el endpoint exige en el header `Authorization`. Si está vacío, el endpoint no exige auth — pensado para el stack local, ver nota de seguridad abajo |

No hay archivo `.env` propio de este servicio — todas estas variables las
inyecta `docker-compose.yml` de `nexia-local-stack` al levantar el contenedor
`odoo-mcp`.

## Setup local (fuera de Docker, para desarrollar/testear)

```bash
cd odoo-customized/mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Correr en desarrollo

```bash
source .venv/bin/activate
ODOO_URL=http://localhost:8069 ODOO_STOCK_LOCATION_ID=5 MCP_AUTH_TOKEN=dev-token \
  uvicorn main:app --reload --port 8000
```

Requiere que Odoo esté corriendo y accesible en `ODOO_URL` (en el stack local,
`docker compose up -d odoo` desde `nexia-local-stack`).

## Correr pruebas

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

Todos los tests mockean `xmlrpc.client.ServerProxy` (en `test_odoo_client.py`)
y usan `fastapi.testclient.TestClient` (en `test_main.py`) — no requieren Odoo
ni red real corriendo.

## Despliegue

Se construye y corre como parte de `docker-compose.yml` en `nexia-local-stack`
(servicio `odoo-mcp`, contenedor `nexia_odoo_mcp`). No publica puertos al
host — solo es alcanzable dentro de la red `nexia-net`, por
`nexia-agent-v2` vía `http://odoo-mcp:8000/`.

Para que `nexia-agent-v2` lo descubra, su URL y un token cifrado (Fernet) se
registran en la tabla `mcp_servers` de Postgres con
`nexia-local-stack/scripts/register-odoo-mcp.py` — ver ese script para el
detalle. `nexia-agent-v2` no requiere ningún cambio de código para esto: lee
`mcp_servers` en cada arranque y registra las tools automáticamente.

## Nota de seguridad

Si `MCP_AUTH_TOKEN` no está seteado, el endpoint queda sin autenticación
(fail-open). Es una decisión deliberada para este stack local de un solo
tenant sin datos reales — en la práctica el token siempre se genera y setea
en `nexia-local-stack/.env` antes de levantar el servicio. No usar este
servicio expuesto a una red no confiable sin revisar ese supuesto primero.
