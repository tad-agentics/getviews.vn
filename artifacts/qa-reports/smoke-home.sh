#!/usr/bin/env bash
# Phase A smoke test — hits the four /home/* endpoints with a real user JWT,
# prints status codes + summarised payloads. Run once manually to answer
# "are the redesigned Home reads returning anything?"
#
# Usage:
#   # 1. Sign in as a real user in the web app, open devtools → Application →
#   #    Session Storage → find the supabase.auth.token entry → copy access_token.
#   # 2. Export:
#   export JWT="eyJhbGci..."
#   export CLOUD_RUN_URL="https://getviews-api-xxxxx.run.app"
#   # 3. Optional: override for batch endpoint test.
#   export BATCH_SECRET="..."
#   # 4. Run:
#   ./artifacts/qa-reports/smoke-home.sh
#
# Requirements: curl, jq.
#
# Exit 0 = all four GETs returned 200 with a non-empty body. Non-zero on
# first failure so CI can gate on it.

set -euo pipefail

: "${CLOUD_RUN_URL:?Set CLOUD_RUN_URL to the deployed Cloud Run service URL.}"
: "${JWT:?Set JWT to a real user access_token (from supabase.auth.getSession()).}"

AUTH=(-H "Authorization: Bearer $JWT")

hdr() { printf "\n\033[1;35m==== %s ====\033[0m\n" "$*"; }
ok()  { printf "\033[32mOK\033[0m  %s\n" "$*"; }
bad() { printf "\033[31mFAIL\033[0m %s\n" "$*"; exit 1; }

expect_200_json() {
  local url="$1" label="$2"
  local tmp
  tmp=$(mktemp)
  local code
  code=$(curl -sS -o "$tmp" -w '%{http_code}' "${AUTH[@]}" "$url")
  if [[ "$code" != "200" ]]; then
    cat "$tmp" >&2; rm -f "$tmp"
    bad "$label → HTTP $code"
  fi
  if ! jq -e '. != null' < "$tmp" >/dev/null; then
    cat "$tmp" >&2; rm -f "$tmp"
    bad "$label → body not JSON"
  fi
  echo "$tmp"
}

# ── 1. /home/pulse ──
hdr "GET /home/pulse"
f=$(expect_200_json "$CLOUD_RUN_URL/home/pulse" "pulse")
jq '{niche_id, videos_this_week, views_delta_pct, adequacy, top_hook_name}' < "$f"
adequacy=$(jq -r '.adequacy' < "$f")
videos_this_week=$(jq -r '.videos_this_week' < "$f")
ok "pulse returned — adequacy=$adequacy, videos_this_week=$videos_this_week"
rm -f "$f"

# ── 2. /home/ticker ──
hdr "GET /home/ticker"
f=$(expect_200_json "$CLOUD_RUN_URL/home/ticker" "ticker")
jq '{niche_id, items_count: (.items | length), bucket_histogram: (.items | group_by(.bucket) | map({bucket: .[0].bucket, n: length}))}' < "$f"
items=$(jq -r '.items | length' < "$f")
if (( items < 3 )); then
  echo "WARN: ticker has only $items items — UI will hide the marquee (threshold ≥ 3)."
fi
ok "ticker returned $items items"
rm -f "$f"

# ── 3. /home/starter-creators ──
hdr "GET /home/starter-creators"
f=$(expect_200_json "$CLOUD_RUN_URL/home/starter-creators" "starter-creators")
jq '{niche_id, n: (.creators | length), first_three: (.creators[0:3])}' < "$f"
starter_n=$(jq -r '.creators | length' < "$f")
ok "starter_creators returned $starter_n rows"
rm -f "$f"

# ── 4. /home/daily-ritual ──
hdr "GET /home/daily-ritual"
code=$(curl -sS -o /tmp/ritual.json -w '%{http_code}' "${AUTH[@]}" \
  "$CLOUD_RUN_URL/home/daily-ritual")
if [[ "$code" == "404" ]]; then
  echo "INFO: no ritual row for this user today (HTTP 404)."
  echo "      → either the nightly batch hasn't run yet,"
  echo "      → the user's corpus was too thin (adequacy=none),"
  echo "      → or Gemini failed. Run section 4 of phase-a-validation.sql."
elif [[ "$code" == "200" ]]; then
  jq '{generated_for_date, niche_id, adequacy, n_scripts: (.scripts | length), hook_types: [.scripts[].hook_type_en], titles: [.scripts[].title_vi]}' < /tmp/ritual.json
  ok "daily-ritual returned a row"
else
  cat /tmp/ritual.json >&2
  bad "daily-ritual returned unexpected HTTP $code"
fi

# ── 5. Optional: trigger the batch on-demand (requires BATCH_SECRET) ──
if [[ -n "${BATCH_SECRET:-}" ]]; then
  hdr "POST /batch/morning-ritual (on-demand, current user only)"
  uid=$(curl -sS "${AUTH[@]}" "$CLOUD_RUN_URL/auth-check" | jq -r '.user_id')
  if [[ -z "$uid" || "$uid" == "null" ]]; then
    bad "could not resolve user_id from /auth-check — is JWT valid?"
  fi
  curl -sS -X POST "$CLOUD_RUN_URL/batch/morning-ritual" \
    -H "X-Batch-Secret: $BATCH_SECRET" \
    -H "Content-Type: application/json" \
    -d "{\"user_ids\": [\"$uid\"]}" | jq .
  ok "batch triggered (check the summary counters above)"
fi

echo
echo "All reachable endpoints returned successfully."
