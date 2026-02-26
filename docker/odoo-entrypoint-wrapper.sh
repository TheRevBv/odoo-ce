#!/bin/sh
set -eu

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

# Default command
if [ "$#" -eq 0 ]; then
  set -- odoo
fi

# If running odoo, inject admin password as a flag (no touching /etc/odoo)
if [ "$1" = "odoo" ]; then
  if master_passwd="$(read_master_password 2>/dev/null)"; then
    case " $* " in
      *" --admin-passwd "*|*" --admin-passwd="*) : ;;
      *) set -- "$@" "--admin-passwd=${master_passwd}" ;;
    esac
  fi
fi

exec "$@"