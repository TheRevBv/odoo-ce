# Dockerfile
FROM odoo:19.0

USER root

# (Opcional) Dependencias del sistema para addons con libs nativas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc python3-dev \
  && rm -rf /var/lib/apt/lists/*

# (Opcional) deps pip para tus addons
COPY requirements.txt /tmp/requirements.txt
RUN if [ -s /tmp/requirements.txt ]; then pip3 install --no-cache-dir -r /tmp/requirements.txt; fi

# Addons custom dentro de /mnt/extra-addons (ruta típica del contenedor)
COPY addons/ /mnt/extra-addons/

RUN chown -R odoo:odoo /mnt/extra-addons

USER odoo
