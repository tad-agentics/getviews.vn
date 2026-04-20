#!/usr/bin/env bash
# Phase C.2.6 — Pattern report: WhatStalled invariant + optional live API check.
#
# **Static (always):** grep pattern UI primitives + design audit artifact; pytest
# `tests/test_report_pattern.py` (WhatStalled schema + C.2.2 acceptance).
#
# **Live (optional):** `POST /answer/sessions` with `intent_type: "trend_spike"` and
# `format: "pattern"`, then `POST .../turns` `kind: "primary"` (SSE), then
# `GET /answer/sessions/:id` — assert §J payload and what_stalled rule:
#   (2 ≤ |what_stalled| ≤ 3) OR (|what_stalled| = 0 and non-empty what_stalled_reason).
#
# Live:
#   export JWT="…"
#   export CLOUD_RUN_URL="https://….run.app"
#   ./artifacts/qa-reports/smoke-answer-pattern.sh
#
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "== pytest: report_pattern (WhatStalled invariant) =="
(cd "$ROOT/cloud-run" && python3 -m pytest tests/test_report_pattern.py -q)

echo "== grep: Pattern body components =="
grep -q 'PatternBody' src/components/v2/answer/ContinuationTurn.tsx
grep -q 'gv-danger' src/components/v2/answer/pattern/WhatStalledCard.tsx
grep -q 'gv-forecast-primary-bg' src/app.css
grep -q 'gv-forecast-primary-bg' src/components/v2/answer/pattern/PatternActionCards.tsx
grep -q 'HookFindingCard' src/components/v2/answer/pattern/PatternBody.tsx

echo "== grep: C.2.5 design audit artifact =="
test -f artifacts/qa-reports/phase-c-design-audit-pattern.md
grep -qi 'PASS' artifacts/qa-reports/phase-c-design-audit-pattern.md

if [[ -z "${CLOUD_RUN_URL:-}" || -z "${JWT:-}" ]]; then
  echo ""
  echo "smoke-answer-pattern: OK (static + pytest; set CLOUD_RUN_URL + JWT for live)"
  exit 0
fi

AUTH=( -H "Authorization: Bearer ${JWT}" )

bad() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

echo ""
echo "== live: POST /answer/sessions (trend_spike + pattern) =="
CREATE_JSON="$(mktemp)"
code_create="$(curl -sS -o "$CREATE_JSON" -w '%{http_code}' -X POST "${AUTH[@]}" \
  -H 'Content-Type: application/json' \
  -d '{"initial_q":"smoke C.2.6 trend","intent_type":"trend_spike","format":"pattern"}' \
  "${CLOUD_RUN_URL%/}/answer/sessions")"
if [[ "$code_create" != "200" ]]; then
  cat "$CREATE_JSON" >&2
  rm -f "$CREATE_JSON"
  bad "create session → HTTP $code_create"
fi
SID="$(jq -r '.id // empty' "$CREATE_JSON")"
rm -f "$CREATE_JSON"
[[ -n "$SID" ]] || bad "create session → missing id"

echo "== live: POST /answer/sessions/$SID/turns (primary, SSE) =="
SSE="$(mktemp)"
code_turns="$(curl -sS -N --max-time 180 -o "$SSE" -w '%{http_code}' -X POST "${AUTH[@]}" \
  -H 'Content-Type: application/json' \
  -d '{"query":"smoke pattern turn","kind":"primary"}' \
  "${CLOUD_RUN_URL%/}/answer/sessions/${SID}/turns")"
if [[ "$code_turns" != "200" ]]; then
  cat "$SSE" >&2
  rm -f "$SSE"
  bad "append turn → HTTP $code_turns"
fi

PAYLOAD_JSON="$(mktemp)"
if ! python3 - "$SSE" <<'PY' >"$PAYLOAD_JSON"
import json, sys
path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line.startswith("data: "):
            continue
        raw = line[6:]
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        err = obj.get("error")
        if err:
            print(err, file=sys.stderr)
            sys.exit(2)
        pl = obj.get("payload")
        if pl is not None:
            json.dump(pl, sys.stdout)
            sys.stdout.write("\n")
            sys.exit(0)
sys.exit(1)
PY
then
  ec=$?
  cat "$SSE" >&2
  rm -f "$SSE" "$PAYLOAD_JSON"
  if [[ "$ec" == 2 ]]; then
    bad "SSE error (credits / backend)"
  fi
  bad "SSE: no payload event"
fi
rm -f "$SSE"

jq -e '.kind == "pattern" and (.report | type == "object")' "$PAYLOAD_JSON" >/dev/null \
  || bad "SSE payload not pattern ReportV1"

REPORT="$(mktemp)"
jq '.report' "$PAYLOAD_JSON" >"$REPORT"
rm -f "$PAYLOAD_JSON"

ws_len="$(jq '.what_stalled | length' "$REPORT")"
reason="$(jq -r '.confidence.what_stalled_reason // ""' "$REPORT")"
ok="$(jq -n \
  --argjson n "$ws_len" \
  --arg r "$reason" \
  '((($n >= 2) and ($n <= 3)) or (($n == 0) and ($r | length > 0)))')"
[[ "$ok" == "true" ]] || bad "what_stalled invariant failed (len=$ws_len reason_len=${#reason})"
rm -f "$REPORT"

echo "== live: GET /answer/sessions/$SID (persisted turn) =="
GET_JSON="$(mktemp)"
code_get="$(curl -sS -o "$GET_JSON" -w '%{http_code}' "${AUTH[@]}" \
  "${CLOUD_RUN_URL%/}/answer/sessions/${SID}")"
if [[ "$code_get" != "200" ]]; then
  cat "$GET_JSON" >&2
  rm -f "$GET_JSON"
  bad "get session → HTTP $code_get"
fi
jq -e '.turns[0].payload.kind == "pattern"' "$GET_JSON" >/dev/null || bad "GET: not pattern"
jq -e '
  .turns[0].payload.report as $rep |
  ($rep.what_stalled | length) as $n |
  ($rep.confidence.what_stalled_reason // "") as $r |
  ((($n >= 2) and ($n <= 3)) or (($n == 0) and ($r | length > 0)))
' "$GET_JSON" >/dev/null || bad "GET: what_stalled invariant"
rm -f "$GET_JSON"

echo ""
echo "smoke-answer-pattern: OK (static + pytest + live)"
