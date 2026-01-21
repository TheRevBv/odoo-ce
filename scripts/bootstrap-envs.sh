#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/bootstrap-envs.sh -r OWNER/REPO
#   ./scripts/bootstrap-envs.sh -r OWNER/REPO --preprod-key ~/.ssh/id_ed25519 --prod-key ~/.ssh/id_ed25519
#
# Files expected:
#   env/preprod.secrets   (dotenv format)
#   env/prod.secrets
#   env/preprod.vars
#   env/prod.vars
#
# Notes:
# - NEVER commit env/*.secrets
# - For SSH keys, store as base64 in VPS_SSH_KEY_B64 to avoid newline/format issues.

REPO=""
PREPROD_KEY_FILE=""
PROD_KEY_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -r|--repo) REPO="${2:-}"; shift 2 ;;
    --preprod-key) PREPROD_KEY_FILE="${2:-}"; shift 2 ;;
    --prod-key) PROD_KEY_FILE="${2:-}"; shift 2 ;;
    -h|--help)
      sed -n '1,120p' "$0"
      exit 0
      ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [[ -z "$REPO" ]]; then
  echo "ERROR: missing --repo OWNER/REPO"
  exit 1
fi

need() { command -v "$1" >/dev/null 2>&1 || { echo "ERROR: '$1' not found"; exit 1; }; }
need gh
need base64
need tr

# Ensure logged in
if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh not authenticated. Run: gh auth login"
  exit 1
fi

ensure_env() {
  local env_name="$1"
  echo "==> Ensuring environment: $env_name"
  gh api -X PUT "repos/${REPO}/environments/${env_name}" --silent >/dev/null
}

b64_of_key() {
  local key_path="$1"
  if [[ ! -f "$key_path" ]]; then
    echo "ERROR: key file not found: $key_path"
    exit 1
  fi
  # Remove CR just in case the key file has Windows line endings.
  tr -d '\r' < "$key_path" | base64 -w0
}

upsert_secret_kv() {
  local env_name="$1"
  local key="$2"
  local value="$3"
  echo "  - secret: $key"
  gh secret set "$key" -R "$REPO" -e "$env_name" -b "$value" >/dev/null
}

apply_key_file_as_secret() {
  local env_name="$1"
  local key_file="$2"
  if [[ -z "$key_file" ]]; then return 0; fi
  echo "==> Encoding SSH key for $env_name from: $key_file"
  local b64
  b64="$(b64_of_key "$key_file")"
  upsert_secret_kv "$env_name" "VPS_SSH_KEY_B64" "$b64"
}

apply_secrets_file() {
  local env_name="$1"
  local file_path="$2"

  if [[ ! -f "$file_path" ]]; then
    echo "==> (skip) Secrets file not found: $file_path"
    return 0
  fi

  echo "==> Applying secrets from: $file_path (env=$env_name)"
  # gh secret set supports dotenv file directly:
  gh secret set -R "$REPO" -e "$env_name" -f "$file_path" >/dev/null
}

apply_vars_file() {
  local env_name="$1"
  local file_path="$2"

  if [[ ! -f "$file_path" ]]; then
    echo "==> (skip) Vars file not found: $file_path"
    return 0
  fi

  echo "==> Applying vars from: $file_path (env=$env_name)"
  gh variable set -R "$REPO" -e "$env_name" -f "$file_path" >/dev/null
}

# Main
echo "Repo: $REPO"
echo

ensure_env "preprod"
ensure_env "prod"

# Optional: push SSH key as base64 secret
apply_key_file_as_secret "preprod" "$PREPROD_KEY_FILE"
apply_key_file_as_secret "prod" "$PROD_KEY_FILE"

# Apply files
apply_secrets_file "preprod" "env/preprod.secrets"
apply_secrets_file "prod"    "env/prod.secrets"

apply_vars_file "preprod" "env/preprod.vars"
apply_vars_file "prod"    "env/prod.vars"

echo
echo "✅ Done. Environments bootstrapped and values uploaded."
echo "Tip: make sure your workflow job uses 'environment: preprod' or 'environment: prod' to access env secrets."
