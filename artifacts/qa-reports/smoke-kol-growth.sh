#!/usr/bin/env bash
# Phase D.1.5 — smoke /kol/browse TĂNG 30D shape + batch_analytics Pass 3.
#
# Pass criteria (per phase-d-plan.md D.1.5):
#   1. /kol/browse returns 200 with rows each carrying a numeric
#      growth_30d_pct (either real view-velocity or proxy fallback).
#   2. The values sit within the union of real (clipped [-0.99, 2.0])
#      and proxy (±0.22) bands.
#   3. Cloud Run logs include at least one `[kol-growth]` entry per
#      request so the mix of real vs proxy reads is observable.
#      (Log inspection is a manual step — command printed for copy.)
#
# Usage:
#   export JWT="eyJhbGci..."
#   export CLOUD_RUN_URL="https://getviews-api-xxxxx.run.app"
#   ./artifacts/qa-reports/smoke-kol-growth.sh

set -euo pipefail

: "${CLOUD_RUN_URL:?Set CLOUD_RUN_URL to the deployed Cloud Run service URL.}"
: "${JWT:?Set JWT to a real user access_token (Supabase session).}"

AUTH=(-H "Authorization: Bearer $JWT")

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

code=$(curl -sS -o "$tmp" -w '%{http_code}' "${AUTH[@]}" \
  "$CLOUD_RUN_URL/kol/browse?tab=discover&page=1&page_size=10&sort=growth&order_dir=desc")
if [[ "$code" != "200" ]]; then
  echo "FAIL /kol/browse → HTTP $code" >&2
  cat "$tmp" >&2
  exit 1
fi

n=$(jq '.rows | length' < "$tmp")
if [[ "$n" == "0" ]]; then
  echo "FAIL /kol/browse returned no rows — cannot assert growth_30d_pct shape" >&2
  cat "$tmp" >&2
  exit 1
fi

# Every row must carry a numeric growth_30d_pct in the real ∪ proxy union.
shape_ok=$(jq '[.rows[] | (.growth_30d_pct | type == "number")
                 and (.growth_30d_pct >= -0.99 and .growth_30d_pct <= 2.0)] | all' < "$tmp")
if [[ "$shape_ok" != "true" ]]; then
  echo "FAIL one or more rows lack a numeric growth_30d_pct in [-0.99, 2.0]" >&2
  jq '.rows[] | {handle, growth_30d_pct}' < "$tmp" >&2
  exit 1
fi

echo "OK /kol/browse returns $n rows with growth_30d_pct in expected range"
jq '{n_rows: (.rows | length),
     sample: [.rows[0:3] | .[] | {handle, growth_30d_pct, match_score}]}' < "$tmp"

cat <<INFO

Manual log check (Cloud Run):
  gcloud logging read '
    resource.type="cloud_run_revision"
    textPayload:"[kol-growth]"
  ' --limit=20 --freshness=10m --format='value(textPayload)'

Expect a mix of "source=real" and "source=proxy reason=…" lines so the
D.5.1 cost dashboard can attribute which % of TĂNG 30D reads came from
the column vs the fallback.
INFO
