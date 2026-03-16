#!/bin/bash
# Verification script for the prototype environment
# Checks: containers running, n8n accessible, Odoo accessible, Odoo JSON-RPC responds

set -euo pipefail

# Load .env if available
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a
  . "$SCRIPT_DIR/.env"
  set +a
fi

ODOO_URL="http://localhost:${ODOO_PORT:-8069}"
N8N_URL="http://localhost:${N8N_PORT:-5678}"
ODOO_DB="${ODOO_DB:-odoo_db}"
ODOO_PASSWORD="${ODOO_PASSWORD:-admin}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
  local description="$1"
  shift
  if "$@" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} $description"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}✗${NC} $description"
    FAIL=$((FAIL + 1))
  fi
}

echo "========================================="
echo "  Prototype Environment Verification"
echo "========================================="
echo ""

# 1. Check containers are running
echo "1. Docker Containers"
check "proto-postgres-odoo is running" docker inspect -f '{{.State.Running}}' proto-postgres-odoo
check "proto-odoo is running" docker inspect -f '{{.State.Running}}' proto-odoo
check "proto-n8n is running" docker inspect -f '{{.State.Running}}' proto-n8n
echo ""

# 2. Check n8n health
echo "2. n8n Health"
check "n8n is accessible at ${N8N_URL}" curl -fsSL --max-time 10 "${N8N_URL}/healthz"
echo ""

# 3. Check Odoo health
echo "3. Odoo Health"
check "Odoo login page loads at ${ODOO_URL}" curl -fsSL --max-time 10 "${ODOO_URL}/web/login"
echo ""

# 4. Check Odoo JSON-RPC
echo "4. Odoo JSON-RPC API"
AUTH_RESPONSE=$(curl -s --max-time 15 -X POST "${ODOO_URL}/web/session/authenticate" \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"params\":{\"db\":\"${ODOO_DB}\",\"login\":\"admin\",\"password\":\"${ODOO_PASSWORD}\"}}" 2>/dev/null || echo '{}')

ODOO_UID=$(echo "$AUTH_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('result',{}).get('uid',''))" 2>/dev/null || echo "")

if [ -n "$ODOO_UID" ] && [ "$ODOO_UID" != "" ] && [ "$ODOO_UID" != "None" ] && [ "$ODOO_UID" != "False" ]; then
  echo -e "  ${GREEN}✓${NC} Odoo authentication successful (uid=$ODOO_UID)"
  PASS=$((PASS + 1))

  # Extract session cookie
  SESSION_COOKIE=$(curl -sI --max-time 15 -X POST "${ODOO_URL}/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"params\":{\"db\":\"${ODOO_DB}\",\"login\":\"admin\",\"password\":\"${ODOO_PASSWORD}\"}}" 2>/dev/null \
    | grep -i 'set-cookie' | head -1 | sed 's/.*: //' | cut -d';' -f1 || echo "")

  PRODUCT_RESPONSE=$(curl -s --max-time 15 -X POST "${ODOO_URL}/jsonrpc" \
    -H "Content-Type: application/json" \
    -H "Cookie: ${SESSION_COOKIE}" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"service\":\"object\",\"method\":\"execute_kw\",\"args\":[\"${ODOO_DB}\",${ODOO_UID},\"${ODOO_PASSWORD}\",\"product.product\",\"search_read\",[[]],{\"fields\":[\"name\",\"list_price\"],\"limit\":3}]}}" 2>/dev/null || echo '{}')

  PRODUCT_COUNT=$(echo "$PRODUCT_RESPONSE" | python3 -c "import sys,json; r=json.load(sys.stdin).get('result',[]); print(len(r))" 2>/dev/null || echo "0")

  if [ "$PRODUCT_COUNT" -gt 0 ] 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} JSON-RPC product query returned ${PRODUCT_COUNT} products"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}✗${NC} JSON-RPC product query returned no products"
    FAIL=$((FAIL + 1))
  fi
else
  echo -e "  ${RED}✗${NC} Odoo authentication failed"
  FAIL=$((FAIL + 1))
  echo -e "  ${YELLOW}⚠${NC} Skipping product query (authentication required)"
  FAIL=$((FAIL + 1))
fi

echo ""
echo "========================================="
echo -e "  Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
echo "========================================="

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
