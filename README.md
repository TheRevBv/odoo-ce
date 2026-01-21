# Odoo Customized (Docker Compose)

Este proyecto proporciona un entorno reproducible de Odoo CE con Postgres usando Docker y Docker Compose. Los addons personalizados se empaquetan en la imagen desde la carpeta [addons/](addons/), y las dependencias Python opcionales se gestionan vía [requirements.txt](requirements.txt).

## Requisitos
- Docker 24+ y Docker Compose v2
- Puertos libres (por defecto `8069` para HTTP y `8072` para longpoll)

## Estructura
- [Dockerfile](Dockerfile): Construye la imagen basada en `odoo:19.0`, instala `requirements` y copia `addons` a `/mnt/extra-addons`.
- [addons/](addons/): Addons personalizados que se incluirán en la imagen.
- [requirements.txt](requirements.txt): Paquetes Python adicionales para tus addons (opcional).
- [deploy/docker-compose.yml](deploy/docker-compose.yml): Orquestación de servicios `odoo` y `db`.
- [deploy/.env.template](deploy/.env.template): Variables de entorno ejemplo para el Compose.

## Configuración rápida
1. Copia el template de entorno y ajusta valores:
   ```bash
   cd deploy
   cp .env.template .env
   # Edita .env si necesitas cambiar imagen, puertos, credenciales, etc.
   ```
2. Construye la imagen de Odoo personalizada (usa los valores por defecto del template):
   ```bash
   cd ..
   docker build -t odoo/customized:develop .
   ```
3. Levanta los servicios con Compose:
   ```bash
   cd deploy
   docker compose up -d
   ```
4. Accede a Odoo en http://localhost:8069 y crea tu base de datos inicial.

## Flujo de desarrollo (bind-mount)
Para evitar reconstruir la imagen cuando editas `addons/`, usa el override de desarrollo que ya está incluido en [deploy/docker-compose.override.yml](deploy/docker-compose.override.yml):

```bash
cd deploy
# Si no lo levantaste todavía, construye una sola vez la imagen base
docker build -t odoo/customized:develop ..

# Compose detecta automáticamente docker-compose.override.yml en el mismo directorio
docker compose up -d
```

Qué hace el override:
- Monta `../addons` dentro del contenedor en `/mnt/extra-addons`.
- Fuerza `--addons-path` para incluir los addons montados.
- Activa `--dev=reload` para recargar automáticamente el servidor ante cambios en código Python.

Notas para desarrollo:
- Cambios en XML/QWeb o assets pueden requerir reiniciar el servicio: `docker compose restart odoo`.
- Tras modificar un módulo, actualízalo desde Apps (Actualizar/Upgrade) o vía línea de comandos si tienes scripts.
- Revisa logs en tiempo real: `docker compose logs -f odoo`.

## Variables de entorno principales
Se definen en [deploy/.env.template](deploy/.env.template) y son consumidas por el Compose:
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: Configuración de la base de datos.
- `ODOO_IMAGE`, `ODOO_TAG`: Nombre y tag de la imagen de Odoo a usar.
- `ODOO_PORT`, `ODOO_LONGPOLL_PORT`: Puertos expuestos del servicio Odoo.
- `HOST`, `PORT`, `USER`, `PASSWORD`: Parámetros de conexión desde Odoo hacia Postgres (el `PASSWORD` referenciado usa `POSTGRES_PASSWORD`).

## Addons y dependencias
- Los addons en [addons/](addons/) se copian a `/mnt/extra-addons` dentro de la imagen.
- Si tus addons requieren dependencias Python, añádelas a [requirements.txt](requirements.txt) (una por línea) y reconstruye la imagen:
  ```bash
  docker build -t odoo/customized:develop .
  ```
- Nota: En esta configuración los addons se empaquetan en la imagen. Si cambias código en `addons/`, vuelve a construir la imagen y recrea el contenedor:
  ```bash
  docker compose down
  docker build -t odoo/customized:develop ..
  docker compose up -d --force-recreate
  ```
 - Alternativa en desarrollo: usa el bind-mount con el override para evitar reconstrucciones (ver sección anterior).

## Persistencia de datos
- Volumen `pg_data`: datos de Postgres.
- Volumen `odoo_data`: filestore y datos del servicio Odoo.

## Comandos útiles
```bash
# Ver logs de Odoo y Postgres
cd deploy
docker compose logs -f

# Reiniciar servicios
docker compose restart

# Apagar y limpiar (sin borrar volúmenes)
docker compose down

# Apagar y borrar volúmenes (CUIDADO: elimina datos)
docker compose down -v
```

## Personalización
- Cambia `ODOO_IMAGE` y `ODOO_TAG` en `.env` si quieres usar otro nombre/tag.
- Modifica [Dockerfile](Dockerfile) para añadir dependencias del sistema que necesiten tus addons.
- Ajusta puertos en `.env` si los predeterminados están ocupados.

## Notas
- La imagen base es `odoo:19.0`. Revisa compatibilidad de tus addons con esta versión.
- El healthcheck espera que Postgres esté listo antes de iniciar Odoo.
- Primera ejecución: Odoo pedirá crear una base de datos; usa el host `db`, usuario `odoo` y la contraseña definida en `.env`.

## Licencia
Este repositorio no especifica una licencia. Si necesitas una, añade una sección de licencia o un archivo `LICENSE` acorde a tu proyecto.
