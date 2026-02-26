#!/bin/sh
set -eu

CONF_DIR="/var/lib/odoo"
CONF_FILE="${ODOO_RC:-${CONF_DIR}/odoo.conf}"

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
  [ -f "${CONF_FILE}" ] || touch "${CONF_FILE}"

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