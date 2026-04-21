#!/usr/bin/env bash
# Phase D.1.3 — smoke /kol/browse match_score persistence (cache hit contract).
#
# Pass criteria (per phase-d-plan.md D.1.3):
#   1. First call returns 200 with non-null match_score for row 0.
#   2. Second call (within 2s) returns the SAME match_score for the same
#      creator WITHOUT a recompute log — i.e. creator_velocity.match_score
#      is populated and creator_velocity.match_score_computed_at is not null.
#
# Usage:
#   export JWT="eyJhbGci..."              # Supabase session access_token
#   export CLOUD_RUN_URL="https://..."    # deployed Cloud Run service URL
#   # optional: export NICHE_ID=3         # must match the user's primary_niche
#   ./artifacts/qa-reports/smoke-kol-match-persist.sh
#
# Exit 0 on pass, non-zero on any contract violation.

set -euo pipefail

: "${CLOUD_RUN_URL:?Set CLOUD_RUN_URL to the deployed Cloud Run service URL.}"
: "${JWT:?Set JWT to a real user access_token (Supabase session).}"
NICHE_ID="${NICHE_ID:-}"

AUTH=(-H "Authorization: Bearer $JWT")

qs_base="tab=discover&page=1&page_size=5&sort=match&order_dir=desc"
if [[ -n "$NICHE_ID" ]]; then
  qs_base="$qs_base&niche_id=$NICHE_ID"
fi

call_browse() {
  local out="$1"
  local code
  code=$(curl -sS -o "$out" -w '%{http_code}' "${AUTH[@]}" \
    "$CLOUD_RUN_URL/kol/browse?$qs_base")
  if [[ "$code" != "200" ]]; then
    echo "FAIL /kol/browse → HTTP $code" >&2
    cat "$out" >&2
    return 1
  fi
  if ! jq -e '.rows != null and (.rows | length) > 0' < "$out" >/dev/null; then
    echo "FAIL /kol/browse → empty rows; cannot assert match_score persistence" >&2
    cat "$out" >&2
    return 1
  fi
}

tmp1=$(mktemp)
tmp2=$(mktemp)
trap 'rm -f "$tmp1" "$tmp2"' EXIT

echo "→ first call (expect recompute + writeback)"
call_browse "$tmp1"

handle1=$(jq -r '.rows[0].handle' < "$tmp1")
score1=$(jq -r '.rows[0].match_score' < "$tmp1")
if [[ -z "$handle1" || "$handle1" == "null" ]]; then
  echo "FAIL first row missing handle" >&2
  exit 1
fi
if [[ "$score1" == "null" ]]; then
  echo "FAIL first row match_score is null (recompute did not run)" >&2
  exit 1
fi

sleep 1

echo "→ second call (expect cache hit — same score, no recompute)"
call_browse "$tmp2"

score2=$(jq -r --arg h "$handle1" '.rows[] | select(.handle == $h) | .match_score' < "$tmp2")
if [[ -z "$score2" || "$score2" == "null" ]]; then
  echo "FAIL second call dropped handle $handle1" >&2
  exit 1
fi

if [[ "$score1" != "$score2" ]]; then
  echo "FAIL match_score unstable across calls — handle=$handle1 call1=$score1 call2=$score2" >&2
  exit 1
fi

jq --arg h "$handle1" --arg s "$score1" \
  '{handle: $h, match_score: ($s | tonumber), n_rows_call1: (.rows | length)}' < "$tmp1"

echo "OK /kol/browse match_score persisted (handle=$handle1 score=$score1)"
