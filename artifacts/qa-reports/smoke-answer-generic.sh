#!/usr/bin/env bash
# Phase C.5.5 — Generic + multi-intent merge: static + pytest + optional live.
#
# **Static (always):** grep Generic UI primitives + PatternSubreports wiring
# + design audit artifact; pytest covering fixture / cap_paragraphs / off_taxonomy
# / pick_broad_evidence / build_generic_report + multi-intent merge pytest.
#
# **Live (optional):** `POST /answer/sessions` with `intent_type:
# "follow_up_unclassifiable"`, `format: "generic"`, SSE turn, then GET session.
# Invariants:
#   - payload.kind == "generic"
#   - confidence.intent_confidence == "low"
#   - confidence.niche_scope is null
#   - off_taxonomy.suggestions.length == 3
#   - narrative.paragraphs.length ∈ [1, 2] and each ≤ 320 chars
#   - evidence_videos.length == 3
#
# Also smoke-tests the multi-intent merge by creating a Pattern session
# whose query contains a timing cue; asserts `subreports.timing` populates
# (when CLOUD_RUN_URL is reachable + corpus is rich enough).
#
# Live:
#   export JWT="…"
#   export CLOUD_RUN_URL="https://….run.app"
#   ./artifacts/qa-reports/smoke-answer-generic.sh
#
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "== pytest: report_generic (cap + off_taxonomy + build flow) =="
(cd "$ROOT/cloud-run" && python3 -m pytest tests/test_report_generic.py -q)

echo "== pytest: multi_intent_merge (§A.4 Report + timing) =="
(cd "$ROOT/cloud-run" && python3 -m pytest tests/test_multi_intent_merge.py -q)

echo "== grep: Generic body components wired in ContinuationTurn =="
grep -q 'GenericBody' src/components/v2/answer/ContinuationTurn.tsx
grep -q 'OffTaxonomyBanner' src/components/v2/answer/generic/GenericBody.tsx
grep -q 'NarrativeAnswer' src/components/v2/answer/generic/GenericBody.tsx
grep -q 'GenericEvidenceGrid' src/components/v2/answer/generic/GenericBody.tsx
grep -q 'Fallback' src/components/v2/answer/generic/GenericBody.tsx

echo "== grep: PatternSubreports wired in PatternBody =="
grep -q 'PatternSubreports' src/components/v2/answer/pattern/PatternBody.tsx

echo "== grep: C.5.4 design audit artifact =="
test -f artifacts/qa-reports/phase-c-design-audit-generic.md
grep -qi 'PASS' artifacts/qa-reports/phase-c-design-audit-generic.md

echo "== grep: no legacy tokens in src/components/v2/answer/generic/ + multi/ =="
if grep -rnE 'var\(--purple\)|var\(--ink-soft\)|var\(--border-active\)|--gv-purple|variant="purple"|#[0-9a-fA-F]{3,8}|rgba?\(' \
    src/components/v2/answer/generic/ src/components/v2/answer/multi/; then
  echo "FAIL: legacy tokens found in Generic/multi surfaces" >&2
  exit 1
fi

if [[ -z "${CLOUD_RUN_URL:-}" || -z "${JWT:-}" ]]; then
  echo ""
  echo "smoke-answer-generic: OK (static + pytest; set CLOUD_RUN_URL + JWT for live)"
  exit 0
fi

AUTH=( -H "Authorization: Bearer ${JWT}" )

bad() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

run_turn_and_capture_payload() {
  # Usage: run_turn_and_capture_payload <format> <intent_type> <query> <kind> → prints payload JSON
  local FMT="$1" INTENT="$2" QUERY="$3" KIND="$4"
  CREATE_JSON="$(mktemp)"
  code_create="$(curl -sS -o "$CREATE_JSON" -w '%{http_code}' -X POST "${AUTH[@]}" \
    -H 'Content-Type: application/json' \
    -d "$(jq -cn --arg q "$QUERY" --arg i "$INTENT" --arg f "$FMT" '{initial_q:$q, intent_type:$i, format:$f}')" \
    "${CLOUD_RUN_URL%/}/answer/sessions")"
  if [[ "$code_create" != "200" ]]; then
    cat "$CREATE_JSON" >&2
    rm -f "$CREATE_JSON"
    bad "create session → HTTP $code_create"
  fi
  SID="$(jq -r '.id // empty' "$CREATE_JSON")"
  rm -f "$CREATE_JSON"
  [[ -n "$SID" ]] || bad "create session → missing id"

  SSE="$(mktemp)"
  code_turns="$(curl -sS -N --max-time 180 -o "$SSE" -w '%{http_code}' -X POST "${AUTH[@]}" \
    -H 'Content-Type: application/json' \
    -d "$(jq -cn --arg q "$QUERY" --arg k "$KIND" '{query:$q, kind:$k}')" \
    "${CLOUD_RUN_URL%/}/answer/sessions/${SID}/turns")"
  if [[ "$code_turns" != "200" ]]; then
    cat "$SSE" >&2
    rm -f "$SSE"
    bad "append turn → HTTP $code_turns"
  fi

  PAYLOAD_JSON="$(mktemp)"
  python3 - "$SSE" <<'PY' >"$PAYLOAD_JSON"
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    for line in f:
        s = line.strip()
        if not s.startswith("data: "):
            continue
        try:
            obj = json.loads(s[6:])
        except json.JSONDecodeError:
            continue
        if obj.get("error"):
            print(obj["error"], file=sys.stderr)
            sys.exit(2)
        pl = obj.get("payload")
        if pl is not None:
            json.dump(pl, sys.stdout)
            sys.stdout.write("\n")
            sys.exit(0)
sys.exit(1)
PY
  rm -f "$SSE"
  cat "$PAYLOAD_JSON"
  rm -f "$PAYLOAD_JSON"
}

echo ""
echo "== live: POST /answer/sessions (generic + follow_up_unclassifiable) =="
G_PAYLOAD="$(run_turn_and_capture_payload generic follow_up_unclassifiable "smoke C.5.5 random broad query" primary)"

jq -e '.kind == "generic"' <<<"$G_PAYLOAD" >/dev/null || bad "payload not generic"
kind_conf="$(jq -r '.report.confidence.intent_confidence' <<<"$G_PAYLOAD")"
[[ "$kind_conf" == "low" ]] || bad "intent_confidence must be low (got $kind_conf)"

niche="$(jq -r '.report.confidence.niche_scope // "NULL"' <<<"$G_PAYLOAD")"
[[ "$niche" == "NULL" || "$niche" == "" ]] || bad "niche_scope must be null (got $niche)"

n_sugg="$(jq '.report.off_taxonomy.suggestions | length' <<<"$G_PAYLOAD")"
[[ "$n_sugg" == "3" ]] || bad "off_taxonomy.suggestions must have 3 entries (got $n_sugg)"

n_para="$(jq '.report.narrative.paragraphs | length' <<<"$G_PAYLOAD")"
[[ "$n_para" -ge 1 && "$n_para" -le 2 ]] || bad "narrative.paragraphs must be 1-2 (got $n_para)"

max_len="$(jq '[.report.narrative.paragraphs[] | length] | max' <<<"$G_PAYLOAD")"
[[ "$max_len" -le 320 ]] || bad "narrative.paragraphs[i].length must be ≤ 320 (got max $max_len)"

n_ev="$(jq '.report.evidence_videos | length' <<<"$G_PAYLOAD")"
[[ "$n_ev" == "3" ]] || bad "evidence_videos.length must be 3 (got $n_ev)"

echo ""
echo "== live: POST /answer/sessions (pattern + content_calendar — merge timing) =="
P_PAYLOAD="$(run_turn_and_capture_payload pattern content_calendar "Tuần này post gì khi nào trong ngách Tech?" primary)"

jq -e '.kind == "pattern"' <<<"$P_PAYLOAD" >/dev/null || bad "payload not pattern"
has_sub="$(jq -r '.report.subreports | type' <<<"$P_PAYLOAD")"
if [[ "$has_sub" == "object" ]]; then
  has_timing="$(jq -r '.report.subreports.timing | type' <<<"$P_PAYLOAD")"
  if [[ "$has_timing" == "object" ]]; then
    v_kind="$(jq -r '.report.subreports.timing.variance_note.kind' <<<"$P_PAYLOAD")"
    case "$v_kind" in
      strong|weak|sparse) ;;
      *) bad "subreports.timing.variance_note.kind invalid: $v_kind" ;;
    esac
  fi
fi

echo ""
echo "smoke-answer-generic: OK (static + pytest + live — Generic + multi-intent merge)"
