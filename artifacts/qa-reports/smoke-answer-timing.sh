#!/usr/bin/env bash
# Phase C.4.6 — Timing report: variance + fatigue invariants + optional live API.
#
# **Static (always):** grep Timing UI primitives + design audit artifact; pytest
# `tests/test_report_timing.py` (fixture / thin / fatigued / compute helpers).
#
# **Live (optional):** `POST /answer/sessions` with `intent_type: "timing"` and
# `format: "timing"`, then `POST .../turns` `kind: "primary"` (SSE), then
# `GET /answer/sessions/:id` — assert §J payload and §2.3 invariants:
#   - `grid` is 7×8 matrix of numeric cells.
#   - `variance_note.kind` ∈ {strong, weak, sparse}.
#   - `top_3_windows` has exactly 3 entries (or 0 on empty state).
#   - `fatigue_band` is either null or `{weeks_at_top ≥ 4, copy}`.
#   - `top_window.lift_multiplier` matches `variance_note.kind` thresholds
#     (strong ≥ 2.0, weak 1.3–2.0, sparse < 1.3).
#
# Live:
#   export JWT="…"
#   export CLOUD_RUN_URL="https://….run.app"
#   ./artifacts/qa-reports/smoke-answer-timing.sh
#
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "== pytest: report_timing (fixture + thin + fatigued + compute) =="
(cd "$ROOT/cloud-run" && python3 -m pytest tests/test_report_timing.py -q)

echo "== grep: Timing body components wired in ContinuationTurn =="
grep -q 'TimingBody' src/components/v2/answer/ContinuationTurn.tsx
grep -q 'TimingHeadline' src/components/v2/answer/timing/TimingBody.tsx
grep -q 'TimingHeatmap' src/components/v2/answer/timing/TimingBody.tsx
grep -q 'VarianceNote' src/components/v2/answer/timing/TimingBody.tsx
grep -q 'FatigueBand' src/components/v2/answer/timing/TimingBody.tsx
grep -q 'TimingActionCards' src/components/v2/answer/timing/TimingBody.tsx

echo "== grep: C.4.5 design audit artifact =="
test -f artifacts/qa-reports/phase-c-design-audit-timing.md
grep -qi 'PASS' artifacts/qa-reports/phase-c-design-audit-timing.md

echo "== grep: no legacy tokens in src/components/v2/answer/timing/ =="
if grep -rnE 'var\(--purple\)|var\(--ink-soft\)|var\(--border-active\)|--gv-purple|variant="purple"|#[0-9a-fA-F]{3,8}|rgba?\(' \
    src/components/v2/answer/timing/; then
  echo "FAIL: legacy tokens found in src/components/v2/answer/timing/" >&2
  exit 1
fi

if [[ -z "${CLOUD_RUN_URL:-}" || -z "${JWT:-}" ]]; then
  echo ""
  echo "smoke-answer-timing: OK (static + pytest; set CLOUD_RUN_URL + JWT for live)"
  exit 0
fi

AUTH=( -H "Authorization: Bearer ${JWT}" )

bad() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

echo ""
echo "== live: POST /answer/sessions (timing + timing) =="
CREATE_JSON="$(mktemp)"
code_create="$(curl -sS -o "$CREATE_JSON" -w '%{http_code}' -X POST "${AUTH[@]}" \
  -H 'Content-Type: application/json' \
  -d '{"initial_q":"smoke C.4.6 giờ nào post tốt?","intent_type":"timing","format":"timing"}' \
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
  -d '{"query":"smoke timing turn","kind":"primary"}' \
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

jq -e '.kind == "timing" and (.report | type == "object")' "$PAYLOAD_JSON" >/dev/null \
  || bad "SSE payload not timing ReportV1"

REPORT="$(mktemp)"
jq '.report' "$PAYLOAD_JSON" >"$REPORT"
rm -f "$PAYLOAD_JSON"

# Grid is 7x8.
rows="$(jq '.grid | length' "$REPORT")"
cols="$(jq '.grid[0] | length' "$REPORT")"
[[ "$rows" == "7" ]] || bad "grid must have 7 rows (got $rows)"
[[ "$cols" == "8" ]] || bad "grid[0] must have 8 cols (got $cols)"

# variance_note.kind ∈ {strong, weak, sparse}
vkind="$(jq -r '.variance_note.kind' "$REPORT")"
case "$vkind" in
  strong|weak|sparse) ;;
  *) bad "variance_note.kind must be strong|weak|sparse (got: $vkind)" ;;
esac

# top_3_windows — exactly 3 when variance is strong/weak; may be fewer on sparse.
n_top="$(jq '.top_3_windows | length' "$REPORT")"
if [[ "$vkind" != "sparse" ]]; then
  [[ "$n_top" == "3" ]] || bad "non-sparse variance must have 3 top windows (got $n_top)"
fi

# Lift thresholds must match variance kind.
lift="$(jq '.top_window.lift_multiplier' "$REPORT")"
ok_lift="$(jq -n \
  --argjson lift "$lift" \
  --arg kind "$vkind" \
  '
    ($kind == "strong"  and $lift >= 2.0) or
    ($kind == "weak"    and $lift >= 1.3 and $lift < 2.0) or
    ($kind == "sparse"  and $lift < 1.3)
  ')"
[[ "$ok_lift" == "true" ]] || bad "variance_note.kind=$vkind inconsistent with lift=$lift"

# fatigue_band is either null or has weeks_at_top >= 4.
ok_fatigue="$(jq '
  (.fatigue_band == null) or
  ((.fatigue_band.weeks_at_top | type == "number") and (.fatigue_band.weeks_at_top >= 4))
' "$REPORT")"
[[ "$ok_fatigue" == "true" ]] || bad "fatigue_band invariant violated"

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
jq -e '.turns[0].payload.kind == "timing"' "$GET_JSON" >/dev/null || bad "GET: not timing"
jq -e '
  .turns[0].payload.report as $rep |
  (($rep.grid | length) == 7) and (($rep.grid[0] | length) == 8) and
  (["strong","weak","sparse"] | index($rep.variance_note.kind)) != null and
  (
    ($rep.fatigue_band == null) or
    (($rep.fatigue_band.weeks_at_top | type == "number") and ($rep.fatigue_band.weeks_at_top >= 4))
  )
' "$GET_JSON" >/dev/null || bad "GET: timing invariants"
rm -f "$GET_JSON"

echo ""
echo "smoke-answer-timing: OK (static + pytest + live)"
