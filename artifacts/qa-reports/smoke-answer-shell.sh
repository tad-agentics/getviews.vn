#!/usr/bin/env bash
# Phase C.1.6 — smoke checks for /app/answer shell + answer session API.
#
# **Static (always):** grep wiring + C.1.5 token regression (`--gv-scrim`). No secrets.
#
# **Live (optional):** matches phase-c-plan §C.1.6 — `POST /answer/sessions`,
# `POST /answer/sessions/:id/turns` with `kind: "primary"` (SSE), then
# `GET /answer/sessions/:id`; assert HTTP 200 and pattern envelope.
#
# Live usage (same pattern as smoke-home.sh / smoke-kol.sh):
#   export JWT="eyJhbGci..."   # supabase session access_token
#   export CLOUD_RUN_URL="https://....run.app"
#   ./artifacts/qa-reports/smoke-answer-shell.sh
#
# Requirements: curl, jq; live mode also needs python3 (stdlib only).
#
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "== grep: answer route registered =="
grep -q 'app/answer' src/routes.ts
grep -q 'AnswerScreen' src/routes/_app/answer/route.tsx

echo "== grep: ChatScreen removed =="
! test -f src/routes/_app/ChatScreen.tsx

echo "== grep: ReportV1 in api-types =="
grep -q 'export type ReportV1' src/lib/api-types.ts

echo "== grep: C.1 shell primitives =="
grep -q 'ResearchStepStrip' src/components/v2/answer/ResearchStrip.tsx
grep -q 'RelatedQs' src/components/v2/answer/RelatedQs.tsx
grep -q 'gv-route-main--answer' src/app.css
grep -q 'listsForUser' src/hooks/useAnswerSessionQueries.ts
grep -q 'next_cursor' src/lib/answerApi.ts

echo "== grep: C.1.5 scrim token (SessionDrawer) =="
grep -q '\-\-gv-scrim' src/app.css
grep -q 'var(--gv-scrim)' src/components/v2/answer/SessionDrawer.tsx

echo "== grep: backend list_sessions scope =="
grep -q 'scope: str' cloud-run/getviews_pipeline/answer_session.py
grep -q 'next_cursor' cloud-run/main.py

echo "== grep: design audit artifact (C.1.5) =="
test -f artifacts/qa-reports/phase-c-design-audit-answer-shell.md
grep -qi 'PASS' artifacts/qa-reports/phase-c-design-audit-answer-shell.md

if [[ -z "${CLOUD_RUN_URL:-}" || -z "${JWT:-}" ]]; then
  echo ""
  echo "smoke-answer-shell: OK (static only; set CLOUD_RUN_URL + JWT for live API checks)"
  exit 0
fi

AUTH=( -H "Authorization: Bearer ${JWT}" )

bad() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

echo ""
echo "== live: POST /answer/sessions =="
CREATE_JSON="$(mktemp)"
code_create="$(curl -sS -o "$CREATE_JSON" -w '%{http_code}' -X POST "${AUTH[@]}" \
  -H 'Content-Type: application/json' \
  -d '{"initial_q":"smoke C.1.6","intent_type":"pattern_audit","format":"pattern"}' \
  "${CLOUD_RUN_URL%/}/answer/sessions")"
if [[ "$code_create" != "200" ]]; then
  cat "$CREATE_JSON" >&2
  rm -f "$CREATE_JSON"
  bad "create session → HTTP $code_create"
fi
SID="$(jq -r '.id // empty' "$CREATE_JSON")"
rm -f "$CREATE_JSON"
[[ -n "$SID" ]] || bad "create session → missing id"

echo "== live: POST /answer/sessions/$SID/turns (SSE) =="
SSE="$(mktemp)"
code_turns="$(curl -sS -N --max-time 180 -o "$SSE" -w '%{http_code}' -X POST "${AUTH[@]}" \
  -H 'Content-Type: application/json' \
  -d '{"query":"smoke primary turn","kind":"primary"}' \
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
    bad "SSE stream returned error (need credits or backend?)"
  fi
  bad "SSE stream: no payload event found"
fi
rm -f "$SSE"

jq -e '.kind == "pattern" and (.report | type == "object")' "$PAYLOAD_JSON" >/dev/null \
  || bad "SSE payload is not a pattern §J envelope"
rm -f "$PAYLOAD_JSON"

echo "== live: GET /answer/sessions/$SID =="
GET_JSON="$(mktemp)"
code_get="$(curl -sS -o "$GET_JSON" -w '%{http_code}' "${AUTH[@]}" \
  "${CLOUD_RUN_URL%/}/answer/sessions/${SID}")"
if [[ "$code_get" != "200" ]]; then
  cat "$GET_JSON" >&2
  rm -f "$GET_JSON"
  bad "get session → HTTP $code_get"
fi
jq -e '.turns | length >= 1' "$GET_JSON" >/dev/null || bad "GET: expected at least one turn"
jq -e '.turns[0].payload.kind == "pattern" and (.turns[0].payload.report | type == "object")' "$GET_JSON" >/dev/null \
  || bad "GET: first turn payload is not pattern ReportV1"
rm -f "$GET_JSON"

echo ""
echo "smoke-answer-shell: OK (static + live)"
