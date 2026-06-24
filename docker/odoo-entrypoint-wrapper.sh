#!/bin/sh
set -eu

# Config escribible. El base image fija ODOO_RC=/etc/odoo/odoo.conf, pero ese directorio es
# de root y el usuario odoo no puede escribir ahí: el sed -i / append de abajo fallan y el
# contenedor entra en bucle de reinicios. Por eso trabajamos SIEMPRE sobre una copia
# escribible en /var/lib/odoo (propiedad de odoo), sembrada desde el conf base.
CONF_DIR="/var/lib/odoo"
CONF_FILE="${CONF_DIR}/odoo.conf"
SRC_CONF="${ODOO_RC:-/etc/odoo/odoo.conf}"

read_master_password() {
  if [ -n "${ODOO_ADMIN_PASSWD_FILE:-}" ] && [ -r "${ODOO_ADMIN_PASSWD_FILE}" ]; then
    cat "${ODOO_ADMIN_PASSWD_FILE}"
    return 0
  fi
  if [ -n "${ODOO_ADMIN_PASSWD:-}" ]; then
    printf '%s' "${ODOO_ADMIN_PASSWD}"
    return 0
  fi
  return 1
}

ensure_conf_file() {
  mkdir -p "${CONF_DIR}"

  # Siembra el conf escribible desde el base si aún no existe (conserva [options],
  # addons_path, data_dir, etc. del conf original).
  if [ ! -f "${CONF_FILE}" ]; then
    if [ -f "${SRC_CONF}" ] && [ "${SRC_CONF}" != "${CONF_FILE}" ]; then
      cp "${SRC_CONF}" "${CONF_FILE}"
    else
      printf '[options]\n' > "${CONF_FILE}"
    fi
  fi

  # Odoo (configparser) exige el header [options]; insértalo si falta (p.ej. si un conf
  # previo quedó sin sección).
  if ! grep -Eq '^[[:space:]]*\[options\]' "${CONF_FILE}" 2>/dev/null; then
    sed -i '1i [options]' "${CONF_FILE}"
  fi

  # Odoo debe leer el mismo conf escribible que estamos editando.
  export ODOO_RC="${CONF_FILE}"

  # agrega/actualiza admin_passwd en este archivo (escribible)
  if master_passwd="$(read_master_password 2>/dev/null)"; then
    escaped="$(printf '%s' "${master_passwd}" | sed 's/[|&\\]/\\&/g')"
    if grep -Eq '^[[:space:]]*admin_passwd[[:space:]]*=' "${CONF_FILE}" 2>/dev/null; then
      sed -i "s|^[[:space:]]*admin_passwd[[:space:]]*=.*|admin_passwd = ${escaped}|" "${CONF_FILE}"
    else
      printf '\nadmin_passwd = %s\n' "${master_passwd}" >> "${CONF_FILE}"
    fi
  fi
}

# Default command
if [ "$#" -eq 0 ]; then
  set -- odoo
fi

# Si vas a ejecutar odoo, asegúrate de usar el config en /var/lib/odoo
if [ "$1" = "odoo" ]; then
  ensure_conf_file
  # Solo añade -c si el usuario no lo pasó ya
  case " $* " in
    *" -c "*|*" --config="*|*" --config "*) : ;;
    *) set -- "$@" "-c" "${CONF_FILE}" ;;
  esac
fi

exec "$@"