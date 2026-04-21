#!/usr/bin/env bash
# Phase D.0.i — answer-wiring live probe.
#
# Disambiguates the "answer-surface dark" triage: zero `answer_session_create`
# events over 7 days could be (1) traffic reality — no user query in prod
# classifies to `answer:{pattern|ideas|timing|generic}`, or (2) a real
# backend failure where `POST /answer/sessions` throws before logUsage fires.
#
# This script probes case (2) by:
#   1. Posting a Pattern-shape query ("Hook nào đang hot trong Tech tuần này?")
#      that's guaranteed to classify to `answer:pattern` via `trend_spike`.
#   2. Creating a session via Cloud Run `POST /answer/sessions`.
#   3. Querying Supabase for the `answer_session_create` `usage_events` row
#      that should have landed within the last 60 seconds.
#
# Pass → backend is healthy; 7-day zero is a **traffic reality** finding
#        (users aren't asking report-shape questions). Revise the sign-off
#        contract per phase-d-d0-measurement-read.md "Root causes" section.
#
# Fail → backend is broken. Escalate: check Cloud Run logs for 500 / 401 /
#        CORS on /answer/sessions; check `answer_sessions` INSERT RLS policy
#        is admitting the service role.
#
# Env required:
#   JWT                — authenticated user access_token (Supabase session)
#   CLOUD_RUN_URL      — e.g. https://getviews-pipeline-xxx.run.app
#   SUPABASE_URL       — e.g. https://lzhiqnxfveqttsujebiv.supabase.co
#   SUPABASE_KEY       — anon (public) key; the test user's JWT grants the read
#
# Usage:
#   export JWT="eyJ..."
#   export CLOUD_RUN_URL="https://getviews-pipeline-prod-xxx.run.app"
#   export SUPABASE_URL="https://lzhiqnxfveqttsujebiv.supabase.co"
#   export SUPABASE_KEY="$(pbpaste)"   # anon key from Supabase dashboard
#   ./artifacts/qa-reports/smoke-d0i-answer-wiring.sh
#
set -euo pipefail

for var in JWT CLOUD_RUN_URL SUPABASE_URL SUPABASE_KEY; do
  if [[ -z "${!var:-}" ]]; then
    echo "FAIL: env var $var is not set" >&2
    exit 1
  fi
done

# Pattern-shape query. Guaranteed to classify to `trend_spike` per
# `src/routes/_app/intent-router.ts` (keyword "hook" + "đang hot").
QUERY="Hook nào đang hot trong Tech tuần này?"
NICHE_ID="${NICHE_ID:-1}"   # 1 = Tech per niche_taxonomy seed (20260409000001).

AUTH=( -H "Authorization: Bearer ${JWT}" )
SB_AUTH=( -H "apikey: ${SUPABASE_KEY}" -H "Authorization: Bearer ${JWT}" )

bad() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

echo "== POST /answer/sessions (Pattern-shape query) =="
SESSION_JSON="$(mktemp)"
code="$(curl -sS -o "$SESSION_JSON" -w '%{http_code}' -X POST "${AUTH[@]}" \
  -H 'Content-Type: application/json' \
  -H "Idempotency-Key: $(python3 -c 'import uuid;print(uuid.uuid4())')" \
  -d "$(jq -cn \
      --arg q "$QUERY" \
      --argjson n "$NICHE_ID" \
      '{initial_q:$q, intent_type:"trend_spike", niche_id:$n, format:"pattern"}')" \
  "${CLOUD_RUN_URL%/}/answer/sessions")"

if [[ "$code" != "200" ]]; then
  echo "--- server response (HTTP $code) ---"
  cat "$SESSION_JSON" >&2
  echo "--- end response ---"
  rm -f "$SESSION_JSON"
  bad "POST /answer/sessions returned HTTP $code → **backend failure confirmed**. Escalate to Cloud Run logs."
fi

SID="$(jq -r '.id // empty' "$SESSION_JSON")"
rm -f "$SESSION_JSON"
[[ -n "$SID" ]] || bad "POST /answer/sessions 200 but no session id in response"
echo "session_id=${SID}"

# AnswerScreen's client-side `logUsage("answer_session_create")` only fires when
# the user reaches /app/answer. Our curl doesn't trigger that — but the
# server-side insert into `answer_sessions` is the authoritative signal the
# bootstrap path is healthy. We check that + verify any recent
# `answer_session_create` event from real traffic as a secondary signal.

echo ""
echo "== Verify session row in answer_sessions (30s budget) =="
found_session=""
for i in {1..6}; do
  body="$(curl -sS "${SB_AUTH[@]}" \
    "${SUPABASE_URL%/}/rest/v1/answer_sessions?id=eq.${SID}&select=id,intent_type,format,created_at" )"
  if jq -e --arg sid "$SID" '.[] | select(.id == $sid)' <<<"$body" >/dev/null 2>&1; then
    found_session="$body"
    break
  fi
  sleep 5
done
[[ -n "$found_session" ]] || bad "session id $SID not found in answer_sessions after 30s"
echo "answer_sessions row confirmed:"
jq '.' <<<"$found_session"

echo ""
echo "== Check usage_events for recent answer_session_create (60s window) =="
# The client-side logUsage call fires only from AnswerScreen. If the human runs
# this smoke script AND opens /app/answer?session=$SID in a browser tab during
# the window, the event should land. If they only run the curl probe, no
# usage_events row is expected — and that's fine: the backend-side session
# insert above is the authoritative wiring signal.
recent="$(curl -sS "${SB_AUTH[@]}" \
  "${SUPABASE_URL%/}/rest/v1/usage_events?action=eq.answer_session_create&created_at=gte.$(date -u -d '60 seconds ago' +'%Y-%m-%dT%H:%M:%SZ')&select=action,metadata,created_at&order=created_at.desc&limit=5" 2>/dev/null \
  || echo '[]')"
count="$(jq 'length' <<<"$recent")"
echo "recent answer_session_create events in last 60s: $count"
if [[ "$count" != "0" ]]; then
  echo "$recent" | jq '.'
fi

echo ""
echo "== Verdict =="
echo "✓ POST /answer/sessions succeeded (HTTP 200)"
echo "✓ answer_sessions row inserted (service-role side of the wiring is healthy)"
if [[ "$count" != "0" ]]; then
  echo "✓ usage_events.answer_session_create row fired in the 60s window"
  echo ""
  echo "Wiring is fully healthy. 7-day zero is a **traffic reality** finding:"
  echo "no production user has asked a Pattern/Ideas/Timing/Generic-shape query"
  echo "in the measurement window. Revise D.0.i sign-off contract per"
  echo "phase-d-d0-measurement-read.md 'Revised gate' section."
else
  echo "⚠ usage_events.answer_session_create did NOT fire in the 60s window."
  echo ""
  echo "This is expected if you ONLY ran the curl probe and didn't open"
  echo "/app/answer?session=${SID} in a browser tab — the client-side"
  echo "logUsage call only fires from AnswerScreen.tsx."
  echo ""
  echo "To fully verify client-side wiring: open"
  echo "  ${VITE_APP_URL:-https://getviews.vn}/app/answer?session=${SID}"
  echo "in a browser logged in as the JWT owner. The bootstrap useEffect"
  echo "will call logUsage('answer_session_create'). Re-run this script's"
  echo "last step or re-query usage_events directly to confirm."
fi
