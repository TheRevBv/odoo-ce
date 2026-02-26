FROM odoo:19.0

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential gcc python3-dev \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN if [ -s /tmp/requirements.txt ]; then pip3 install --no-cache-dir -r /tmp/requirements.txt; fi

COPY addons/ /mnt/extra-addons/
COPY docker/odoo-entrypoint-wrapper.sh /usr/local/bin/odoo-entrypoint-wrapper.sh

RUN chown -R odoo:odoo /mnt/extra-addons \
  && chmod 755 /usr/local/bin/odoo-entrypoint-wrapper.sh

USER odoo

ENTRYPOINT ["/usr/local/bin/odoo-entrypoint-wrapper.sh"]
CMD ["odoo"]