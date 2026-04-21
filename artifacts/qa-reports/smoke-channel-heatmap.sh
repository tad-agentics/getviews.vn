#!/usr/bin/env bash
# Phase D.1.4 — smoke GET /channel/analyze posting_heatmap shape.
#
# Pass criteria (per phase-d-plan.md D.1.4):
#   - posting_heatmap is present in the response
#   - it is a JSON array of 7 rows × 8 number cells (when non-empty)
#   - OR it is an empty array when the corpus is temporally sparse
#
# Usage:
#   export JWT="eyJhbGci..."
#   export CLOUD_RUN_URL="https://getviews-api-xxxxx.run.app"
#   export HANDLE="@someone"          # required — handle to analyze
#   ./artifacts/qa-reports/smoke-channel-heatmap.sh

set -euo pipefail

: "${CLOUD_RUN_URL:?Set CLOUD_RUN_URL to the deployed Cloud Run service URL.}"
: "${JWT:?Set JWT to a real user access_token (Supabase session).}"
: "${HANDLE:?Set HANDLE to the TikTok handle to analyze.}"

AUTH=(-H "Authorization: Bearer $JWT")
handle_q=$(printf '%s' "$HANDLE" | sed 's/^@//')

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

code=$(curl -sS -o "$tmp" -w '%{http_code}' "${AUTH[@]}" \
  "$CLOUD_RUN_URL/channel/analyze?handle=$handle_q")
if [[ "$code" != "200" ]]; then
  echo "FAIL /channel/analyze → HTTP $code" >&2
  cat "$tmp" >&2
  exit 1
fi

if ! jq -e '.posting_heatmap != null' < "$tmp" >/dev/null; then
  echo "FAIL posting_heatmap missing from response" >&2
  cat "$tmp" >&2
  exit 1
fi

len=$(jq '.posting_heatmap | length' < "$tmp")
if [[ "$len" == "0" ]]; then
  echo "OK posting_heatmap is empty — sparse corpus, frontend hides panel"
  exit 0
fi

if [[ "$len" != "7" ]]; then
  echo "FAIL posting_heatmap outer length = $len (expected 7 or 0)" >&2
  exit 1
fi

# Each row should have 8 numeric cells.
row_shape_ok=$(jq '[.posting_heatmap[] | length == 8 and (all(. | type == "number"))] | all' < "$tmp")
if [[ "$row_shape_ok" != "true" ]]; then
  echo "FAIL posting_heatmap rows are not 7×8 number[][]" >&2
  jq '.posting_heatmap' < "$tmp" >&2
  exit 1
fi

total=$(jq '[.posting_heatmap[][]] | add' < "$tmp")
jq --argjson total "$total" '{handle, total_posts_in_heatmap: $total, heatmap_shape: "7x8"}' < "$tmp"
echo "OK /channel/analyze posting_heatmap is 7×8 number[][] (total posts = $total)"
