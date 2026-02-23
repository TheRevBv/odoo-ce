#!/bin/sh
set -eu

CONF_FILE="${ODOO_RC:-/etc/odoo/odoo.conf}"

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

set_admin_password() {
  master_passwd="$1"
  escaped_master_passwd="$(printf '%s' "${master_passwd}" | sed 's/[|&\\]/\\&/g')"

  [ -n "${master_passwd}" ] || return 0

  if [ ! -e "${CONF_FILE}" ]; then
    touch "${CONF_FILE}"
  fi

  if grep -Eq '^[[:space:]]*admin_passwd[[:space:]]*=' "${CONF_FILE}" 2>/dev/null; then
    sed -i "s|^[[:space:]]*admin_passwd[[:space:]]*=.*|admin_passwd = ${escaped_master_passwd}|" "${CONF_FILE}"
  else
    printf '\nadmin_passwd = %s\n' "${master_passwd}" >> "${CONF_FILE}"
  fi
}

if master_passwd="$(read_master_password 2>/dev/null)"; then
  set_admin_password "${master_passwd}"
fi

exec /entrypoint.sh "$@"
