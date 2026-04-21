#!/usr/bin/env bash
# Phase D.1.2 — smoke POST /script/generate frozen-contract shape.
#
# Runs pre/post the Gemini swap: the response shape must not change, so
# a successful Gemini upgrade leaves this smoke green in both states.
#
# Pass criteria (per phase-c-plan.md C.8.2 / phase-d-plan.md D.1.2):
#   - HTTP 200 with JSON body `{ shots: [ … ] }`
#   - Exactly 6 shots
#   - t0 == 0 on shot[0]; t1 on shot[-1] == duration
#   - Every shot has: t0, t1, cam, voice, viz, overlay, corpus_avg,
#     winner_avg, intel_scene_type, overlay_winner
#   - Positional canonical overlay + intel_scene_type (coerced by
#     _assemble_shots even if Gemini drifts)
#
# Usage:
#   export JWT="eyJhbGci..."
#   export CLOUD_RUN_URL="https://getviews-api-xxxxx.run.app"
#   export NICHE_ID=3
#   ./artifacts/qa-reports/smoke-script-generate.sh

set -euo pipefail

: "${CLOUD_RUN_URL:?Set CLOUD_RUN_URL to the deployed Cloud Run service URL.}"
: "${JWT:?Set JWT to a real user access_token (Supabase session).}"
: "${NICHE_ID:?Set NICHE_ID — must match the users primary_niche.}"

DURATION="${DURATION:-32}"
TOPIC="${TOPIC:-Review tai nghe 200k vs 2 triệu}"
HOOK="${HOOK:-Mình test xong rồi đây}"
TONE="${TONE:-Chuyên gia}"
HOOK_DELAY_MS="${HOOK_DELAY_MS:-1200}"

body=$(jq -cn \
  --arg topic "$TOPIC" \
  --arg hook "$HOOK" \
  --arg tone "$TONE" \
  --argjson hook_delay_ms "$HOOK_DELAY_MS" \
  --argjson duration "$DURATION" \
  --argjson niche_id "$NICHE_ID" \
  '{topic: $topic, hook: $hook, hook_delay_ms: $hook_delay_ms, duration: $duration, tone: $tone, niche_id: $niche_id}')

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

code=$(curl -sS -o "$tmp" -w '%{http_code}' \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -X POST \
  --data "$body" \
  "$CLOUD_RUN_URL/script/generate")
if [[ "$code" != "200" ]]; then
  echo "FAIL /script/generate → HTTP $code" >&2
  cat "$tmp" >&2
  exit 1
fi

n=$(jq '.shots | length' < "$tmp")
if [[ "$n" != "6" ]]; then
  echo "FAIL shot count = $n (expected 6)" >&2
  cat "$tmp" >&2
  exit 1
fi

t0_first=$(jq '.shots[0].t0' < "$tmp")
t1_last=$(jq '.shots[-1].t1' < "$tmp")
if [[ "$t0_first" != "0" ]]; then
  echo "FAIL shot[0].t0 = $t0_first (expected 0)" >&2
  exit 1
fi
if [[ "$t1_last" != "$DURATION" ]]; then
  echo "FAIL shot[-1].t1 = $t1_last (expected $DURATION)" >&2
  exit 1
fi

required='["t0","t1","cam","voice","viz","overlay","corpus_avg","winner_avg","intel_scene_type","overlay_winner"]'
shape_ok=$(jq --argjson req "$required" \
  '[.shots[] | (keys_unsorted | . as $ks | $req | all(. as $k | $ks | index($k) != null))] | all' < "$tmp")
if [[ "$shape_ok" != "true" ]]; then
  echo "FAIL shot shape missing required keys" >&2
  jq '.shots[0]' < "$tmp" >&2
  exit 1
fi

# Positional backbone contract — canonical overlay + intel_scene_type per slot.
expected_overlays=("BOLD CENTER" "SUB-CAPTION" "STAT BURST" "LABEL" "NONE" "QUESTION XL")
expected_scenes=("face_to_camera" "product_shot" "demo" "face_to_camera" "action" "face_to_camera")
for i in 0 1 2 3 4 5; do
  got_o=$(jq -r ".shots[$i].overlay" < "$tmp")
  got_s=$(jq -r ".shots[$i].intel_scene_type" < "$tmp")
  if [[ "$got_o" != "${expected_overlays[$i]}" ]]; then
    echo "FAIL shot[$i].overlay = $got_o (expected ${expected_overlays[$i]})" >&2
    exit 1
  fi
  if [[ "$got_s" != "${expected_scenes[$i]}" ]]; then
    echo "FAIL shot[$i].intel_scene_type = $got_s (expected ${expected_scenes[$i]})" >&2
    exit 1
  fi
done

jq '{n_shots: (.shots | length), t0_first: .shots[0].t0, t1_last: .shots[-1].t1, shot0_voice: .shots[0].voice}' < "$tmp"
echo "OK /script/generate frozen contract holds (6 shots, canonical overlays + scenes)"
