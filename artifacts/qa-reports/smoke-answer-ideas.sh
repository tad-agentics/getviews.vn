#!/usr/bin/env bash
# Phase C.3.5 — Ideas report: schema invariants + optional live API check.
#
# **Static (always):** grep ideas UI primitives + design audit artifact; pytest
# `tests/test_report_ideas.py` (fixture / thin / variant paths + variant enum).
#
# **Live (optional):** `POST /answer/sessions` with `intent_type: "brief_generation"`
# and `format: "ideas"`, then `POST .../turns` `kind: "primary"` (SSE), then
# `GET /answer/sessions/:id` — assert §J payload and §2.2 invariants:
#   - `variant` ∈ {standard, hook_variants}
#   - variant=standard, sample_size ≥ 60 → |ideas| == 5 AND |style_cards| == 5 AND |stop_doing| == 5
#   - variant=standard, sample_size <  60 → |ideas| == 3 AND |stop_doing| == 0
#   - variant=hook_variants              → |stop_doing| == 0
#
# Live:
#   export JWT="…"
#   export CLOUD_RUN_URL="https://….run.app"
#   ./artifacts/qa-reports/smoke-answer-ideas.sh
#
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "== pytest: report_ideas (fixture + thin + variant + compute) =="
(cd "$ROOT/cloud-run" && python3 -m pytest tests/test_report_ideas.py -q)

echo "== grep: Ideas body components wired in ContinuationTurn =="
grep -q 'IdeasBody' src/components/v2/answer/ContinuationTurn.tsx
grep -q 'IdeaBlock' src/components/v2/answer/ideas/IdeasBody.tsx
grep -q 'StopDoingList' src/components/v2/answer/ideas/IdeasBody.tsx
grep -q 'StyleCardGrid' src/components/v2/answer/ideas/IdeasBody.tsx
grep -q 'LeadParagraph' src/components/v2/answer/ideas/IdeasBody.tsx
grep -q 'IdeasActionCards' src/components/v2/answer/ideas/IdeasBody.tsx

echo "== grep: C.3.4 design audit artifact =="
test -f artifacts/qa-reports/phase-c-design-audit-ideas.md
grep -qi 'PASS' artifacts/qa-reports/phase-c-design-audit-ideas.md

echo "== grep: no legacy tokens in src/components/v2/answer/ideas/ =="
# Token gate — zero hex / purple / ink-soft / border-active / gv-purple /
# variant="purple" / rgba / rgb(…).
if grep -rnE 'var\(--purple\)|var\(--ink-soft\)|var\(--border-active\)|--gv-purple|variant="purple"|#[0-9a-fA-F]{3,8}|rgba?\(' \
    src/components/v2/answer/ideas/; then
  echo "FAIL: legacy tokens found in src/components/v2/answer/ideas/" >&2
  exit 1
fi

if [[ -z "${CLOUD_RUN_URL:-}" || -z "${JWT:-}" ]]; then
  echo ""
  echo "smoke-answer-ideas: OK (static + pytest; set CLOUD_RUN_URL + JWT for live)"
  exit 0
fi

AUTH=( -H "Authorization: Bearer ${JWT}" )

bad() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

echo ""
echo "== live: POST /answer/sessions (brief_generation + ideas) =="
CREATE_JSON="$(mktemp)"
code_create="$(curl -sS -o "$CREATE_JSON" -w '%{http_code}' -X POST "${AUTH[@]}" \
  -H 'Content-Type: application/json' \
  -d '{"initial_q":"smoke C.3.5 brief tuần này","intent_type":"brief_generation","format":"ideas"}' \
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
  -d '{"query":"smoke ideas turn","kind":"primary"}' \
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

jq -e '.kind == "ideas" and (.report | type == "object")' "$PAYLOAD_JSON" >/dev/null \
  || bad "SSE payload not ideas ReportV1"

REPORT="$(mktemp)"
jq '.report' "$PAYLOAD_JSON" >"$REPORT"
rm -f "$PAYLOAD_JSON"

variant="$(jq -r '.variant' "$REPORT")"
case "$variant" in
  standard|hook_variants) ;;
  *) bad "variant must be standard|hook_variants (got: $variant)" ;;
esac

n_ideas="$(jq '.ideas | length' "$REPORT")"
n_styles="$(jq '.style_cards | length' "$REPORT")"
n_stop="$(jq '.stop_doing | length' "$REPORT")"
n_sample="$(jq '.confidence.sample_size' "$REPORT")"

if [[ "$variant" == "hook_variants" ]]; then
  [[ "$n_stop" == "0" ]] || bad "hook_variants must suppress stop_doing (got $n_stop)"
fi

if [[ "$variant" == "standard" ]]; then
  if [[ "$n_sample" -lt 60 ]]; then
    [[ "$n_ideas" == "3" ]]  || bad "thin corpus (N=$n_sample) must have 3 ideas (got $n_ideas)"
    [[ "$n_stop"  == "0" ]]  || bad "thin corpus must suppress stop_doing (got $n_stop)"
  else
    [[ "$n_ideas"  == "5" ]] || bad "standard/full must have 5 ideas (got $n_ideas)"
    [[ "$n_styles" == "5" ]] || bad "standard must have 5 style_cards (got $n_styles)"
    [[ "$n_stop"   == "5" ]] || bad "standard/full must have 5 stop_doing (got $n_stop)"
  fi
fi
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
jq -e '.turns[0].payload.kind == "ideas"' "$GET_JSON" >/dev/null || bad "GET: not ideas"
jq -e '
  .turns[0].payload.report as $rep |
  ($rep.variant) as $v |
  ($rep.ideas | length) as $n |
  ($rep.stop_doing | length) as $s |
  ($rep.confidence.sample_size) as $ss |
  (
    ($v == "hook_variants" and $s == 0)
    or ($v == "standard" and $ss >= 60 and $n == 5 and $s == 5)
    or ($v == "standard" and $ss <  60 and $n == 3 and $s == 0)
  )
' "$GET_JSON" >/dev/null || bad "GET: ideas invariants"
rm -f "$GET_JSON"

echo ""
echo "smoke-answer-ideas: OK (static + pytest + live)"
