#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# zerto_insert-checkpoint.sh — Insert a checkpoint into a Zerto VPG
#
# Usage:
#   ./zerto_insert-checkpoint.sh "<VPG_NAME>" "<CHECKPOINT_TEXT>"
#
# Examples:
#   ./zerto_insert-checkpoint.sh "ResilienceApp Remote" "Pre-deploy v2.3.1"
#   ./zerto_insert-checkpoint.sh "ResilienceApp Local"  "Manual backup 08/04/2026"
#
# The script automatically detects which ZVMA hosts the VPG and authenticates
# to it (tries client_credentials, then password grant, then legacy session
# auth for Zerto < 9 — same three-tier fallback as the original script).
#
# REQUIRED environment variables (no hardcoded defaults — set these before
# running, e.g. in a .env you source, or export them in your shell):
#   ORIGIN_ZVMA_HOST, ORIGIN_ZVMA_USERNAME, ORIGIN_ZVMA_PASSWORD
#   DESTINATION_ZVMA_HOST, DESTINATION_ZVMA_USERNAME, DESTINATION_ZVMA_PASSWORD
#
# OPTIONAL (blank is fine if your ZVMA doesn't use client_credentials):
#   ORIGIN_ZVMA_PORT (default 443), ORIGIN_ZVMA_CLIENT_ID, ORIGIN_ZVMA_CLIENT_SECRET
#   DESTINATION_ZVMA_PORT (default 443), DESTINATION_ZVMA_CLIENT_ID, DESTINATION_ZVMA_CLIENT_SECRET
#
# Adapted from the Order Simulator reference script:
#   - Renamed ZVM1_*/ZVM2_* → ORIGIN_ZVMA_*/DESTINATION_ZVMA_* to match the
#     naming already used by observability-console/zerto-probe.
#   - Removed ALL hardcoded hosts/passwords/client secrets that were present
#     as defaults in the original file — those were real credentials and
#     must never live in a script. Every credential is now a required
#     environment variable; the script refuses to run if any are missing.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Parameters ────────────────────────────────────────────────────────────────
VPG_NAME="${1:-}"
CHECKPOINT_TEXT="${2:-}"

if [ -z "$VPG_NAME" ] || [ -z "$CHECKPOINT_TEXT" ]; then
  echo "Usage: $0 \"<VPG_NAME>\" \"<CHECKPOINT_TEXT>\""
  echo ""
  echo "Examples:"
  echo "  $0 \"ResilienceApp Remote\" \"Pre-deploy v2.3.1\""
  echo "  $0 \"ResilienceApp Local\"  \"Manual backup\""
  exit 1
fi

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}ℹ${NC}  $*"; }
success() { echo -e "${GREEN}✓${NC}  $*"; }
error()   { echo -e "${RED}✗${NC}  $*" >&2; }

# ── ZVMA configuration — REQUIRED env vars, no hardcoded credentials ─────────
ORIGIN_ZVMA_PORT="${ORIGIN_ZVMA_PORT:-443}"
DESTINATION_ZVMA_PORT="${DESTINATION_ZVMA_PORT:-443}"

required_vars=(ORIGIN_ZVMA_HOST ORIGIN_ZVMA_USERNAME ORIGIN_ZVMA_PASSWORD \
                DESTINATION_ZVMA_HOST DESTINATION_ZVMA_USERNAME DESTINATION_ZVMA_PASSWORD)
missing=()
for var in "${required_vars[@]}"; do
  [ -z "${!var:-}" ] && missing+=("$var")
done
if [ ${#missing[@]} -gt 0 ]; then
  error "Missing required environment variables: ${missing[*]}"
  echo ""
  echo "Set them before running this script, e.g.:"
  echo "  export ORIGIN_ZVMA_HOST=zvma-origin.your-domain.local"
  echo "  export ORIGIN_ZVMA_USERNAME=admin@local"
  echo "  export ORIGIN_ZVMA_PASSWORD='...'"
  echo "  export DESTINATION_ZVMA_HOST=zvma-destination.your-domain.local"
  echo "  export DESTINATION_ZVMA_USERNAME=admin@local"
  echo "  export DESTINATION_ZVMA_PASSWORD='...'"
  echo "(ORIGIN_ZVMA_CLIENT_ID/SECRET and DESTINATION_ZVMA_CLIENT_ID/SECRET are optional.)"
  exit 1
fi

# ── Helper: curl without TLS verification ─────────────────────────────────────
_curl() { curl -sk --max-time 15 "$@"; }

# ── Auth: OAuth2 client_credentials → password grant → session fallback ───────
get_token() {
  local host="$1" port="$2" client_id="$3" client_secret="$4"
  local username="$5" password="$6"
  local token_url="https://${host}:${port}/auth/realms/zerto/protocol/openid-connect/token"
  local token=""

  # Attempt 1: client_credentials (only if a client_id/secret was configured)
  if [ -n "$client_id" ] && [ -n "$client_secret" ]; then
    token=$(_curl -X POST "$token_url" \
      -d "grant_type=client_credentials&client_id=${client_id}&client_secret=${client_secret}" \
      | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
  fi

  # Attempt 2: password grant
  if [ -z "$token" ]; then
    token=$(_curl -X POST "$token_url" \
      -d "grant_type=password&client_id=${client_id:-zerto-client}&client_secret=${client_secret}&username=${username}&password=${password}&scope=openid" \
      | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
  fi

  # Attempt 3: session auth (Zerto < 9)
  if [ -z "$token" ]; then
    local creds
    creds=$(printf '%s:%s' "$username" "$password" | base64 | tr -d '\n')
    token=$(_curl -X POST "https://${host}:${port}/v1/session/add" \
      -H "Authorization: Basic ${creds}" \
      -H "Content-Type: application/json" \
      -D - -o /dev/null | grep -i 'x-zerto-session:' | awk '{print $2}' | tr -d '\r')
  fi

  echo "$token"
}

# ── Helper: authenticated GET JSON endpoint ───────────────────────────────────
api_get() {
  local host="$1" port="$2" token="$3" path="$4"
  _curl -H "Authorization: Bearer ${token}" \
        -H "Accept: application/json" \
        "https://${host}:${port}${path}"
}

# ── Helper: authenticated POST JSON endpoint ──────────────────────────────────
api_post() {
  local host="$1" port="$2" token="$3" path="$4" body="$5"
  _curl -X POST \
        -H "Authorization: Bearer ${token}" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d "$body" \
        "https://${host}:${port}${path}"
}

# ── Detect which ZVMA hosts the VPG and retrieve its identifier ──────────────
find_vpg() {
  local target_vpg="$1"
  local hosts=("$ORIGIN_ZVMA_HOST" "$DESTINATION_ZVMA_HOST")
  local ports=("$ORIGIN_ZVMA_PORT" "$DESTINATION_ZVMA_PORT")
  local client_ids=("${ORIGIN_ZVMA_CLIENT_ID:-}" "${DESTINATION_ZVMA_CLIENT_ID:-}")
  local client_secrets=("${ORIGIN_ZVMA_CLIENT_SECRET:-}" "${DESTINATION_ZVMA_CLIENT_SECRET:-}")
  local usernames=("$ORIGIN_ZVMA_USERNAME" "$DESTINATION_ZVMA_USERNAME")
  local passwords=("$ORIGIN_ZVMA_PASSWORD" "$DESTINATION_ZVMA_PASSWORD")
  local zvm_labels=("Origin ZVMA" "Destination ZVMA")

  for i in 0 1; do
    local host="${hosts[$i]}" port="${ports[$i]}"
    local cid="${client_ids[$i]}" csecret="${client_secrets[$i]}"
    local user="${usernames[$i]}" pass="${passwords[$i]}"
    local label="${zvm_labels[$i]}"

    info "Trying ${label} (${host}:${port})..." >&2

    local token
    token=$(get_token "$host" "$port" "$cid" "$csecret" "$user" "$pass")
    if [ -z "$token" ]; then
      error "Could not authenticate to ${label}" >&2
      continue
    fi

    local vpgs_json
    vpgs_json=$(api_get "$host" "$port" "$token" "/v1/vpgs")

    local vpg_id
    vpg_id=$(echo "$vpgs_json" \
      | sed 's/},{/}\n{/g' \
      | grep "\"VpgName\":\"${target_vpg}\"" \
      | grep -o '"VpgIdentifier":"[^"]*"' | cut -d'"' -f4 | head -1)

    if [ -n "$vpg_id" ]; then
      echo "${host}|${port}|${token}|${vpg_id}|${label}"
      return 0
    fi
  done

  return 1
}

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}Zerto — Insert checkpoint${NC}"
echo -e "  VPG:        ${CYAN}${VPG_NAME}${NC}"
echo -e "  Checkpoint: ${CYAN}${CHECKPOINT_TEXT}${NC}"
echo ""

info "Searching for VPG across configured ZVMAs..."
result=$(find_vpg "$VPG_NAME") || {
  error "VPG \"${VPG_NAME}\" not found on any ZVMA."
  exit 1
}

IFS='|' read -r ZVM_HOST ZVM_PORT TOKEN VPG_ID ZVM_LABEL <<< "$result"
success "VPG found on ${ZVM_LABEL} — ID: ${VPG_ID}"

info "Inserting checkpoint..."
CP_BODY="{\"CheckpointName\":\"${CHECKPOINT_TEXT}\"}"
response=$(api_post "$ZVM_HOST" "$ZVM_PORT" "$TOKEN" \
  "/v1/vpgs/${VPG_ID}/checkpoints" "$CP_BODY")

if echo "$response" | grep -qi '"error\|"message\|"detail'; then
  error "API error: ${response}"
  exit 1
fi

echo ""
success "Checkpoint inserted successfully!"
echo -e "  ZVMA:       ${ZVM_LABEL} (${ZVM_HOST})"
echo -e "  VPG:        ${VPG_NAME}"
echo -e "  VPG ID:     ${VPG_ID}"
echo -e "  Checkpoint: ${CHECKPOINT_TEXT}"
[ -n "$response" ] && echo -e "  Response:   ${response}"
echo ""
