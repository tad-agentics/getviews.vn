#!/usr/bin/env bash
# Phase B · B.2.5 — smoke `GET /kol/browse` (+ optional toggle-pin dry read).
#
# Usage:
#   export JWT="eyJhbGci..."
#   export CLOUD_RUN_URL="https://getviews-api-xxxxx.run.app"
#   ./artifacts/qa-reports/smoke-kol.sh
#
# Exit 0 when browse returns 200 + JSON with rows/total/reference_handles.

set -euo pipefail

: "${CLOUD_RUN_URL:?Set CLOUD_RUN_URL to the deployed Cloud Run service URL.}"
: "${JWT:?Set JWT to a real user access_token (Supabase session).}"

AUTH=(-H "Authorization: Bearer $JWT")

tmp=$(mktemp)
code=$(curl -sS -o "$tmp" -w '%{http_code}' "${AUTH[@]}" \
  "$CLOUD_RUN_URL/kol/browse?tab=discover&page=1&page_size=5&sort=match&order_dir=desc")
if [[ "$code" != "200" ]]; then
  echo "FAIL /kol/browse → HTTP $code" >&2
  cat "$tmp" >&2
  rm -f "$tmp"
  exit 1
fi
if ! jq -e '.rows != null and .total != null and .reference_handles != null' < "$tmp" >/dev/null; then
  echo "FAIL /kol/browse → missing expected keys" >&2
  cat "$tmp" >&2
  rm -f "$tmp"
  exit 1
fi
jq '{tab, niche_id, page, page_size, total, n_rows: (.rows | length), first_handle: .rows[0].handle}' < "$tmp"
rm -f "$tmp"
echo "OK /kol/browse (discover)"
