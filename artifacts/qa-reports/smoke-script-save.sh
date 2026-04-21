#!/usr/bin/env bash
# Phase D.1.1 — smoke POST /script/save + GET /script/drafts[/:id] +
# POST /script/drafts/:id/export?format=copy|pdf.
#
# Pass criteria (per phase-c-plan.md C.8.1 / phase-d-plan.md D.1.1):
#   1. POST /script/save returns 200 + {draft_id, draft}
#   2. GET /script/drafts lists the freshly saved draft at the top
#   3. GET /script/drafts/:id returns the same draft shape
#   4. POST /script/drafts/:id/export?format=copy returns 200 text/plain
#   5. POST /script/drafts/:id/export?format=pdf returns 200 application/pdf
#      OR 503 with error=pdf_unavailable (WeasyPrint not installed yet)
#
# Usage:
#   export JWT="eyJhbGci..."
#   export CLOUD_RUN_URL="https://getviews-api-xxxxx.run.app"
#   export NICHE_ID=3
#   ./artifacts/qa-reports/smoke-script-save.sh

set -euo pipefail

: "${CLOUD_RUN_URL:?Set CLOUD_RUN_URL to the deployed Cloud Run service URL.}"
: "${JWT:?Set JWT to a real user access_token (Supabase session).}"
: "${NICHE_ID:?Set NICHE_ID matching the users primary_niche.}"

AUTH=(-H "Authorization: Bearer $JWT")
CT=(-H "Content-Type: application/json")

# ── 1. Save ─────────────────────────────────────────────────────────────────

body=$(jq -cn --argjson niche_id "$NICHE_ID" '{
  topic: "Smoke draft",
  hook: "Mình test smoke",
  hook_delay_ms: 1200,
  duration_sec: 32,
  tone: "Chuyên gia",
  shots: [
    {t0:0,  t1:3,  cam:"Cận mặt",        voice:"Hook smoke",  viz:"",  overlay:"BOLD CENTER",  intel_scene_type:"face_to_camera"},
    {t0:3,  t1:8,  cam:"Cắt nhanh",      voice:"B-roll smoke",viz:"",  overlay:"SUB-CAPTION",  intel_scene_type:"product_shot"},
    {t0:8,  t1:16, cam:"Side-by-side",   voice:"Demo smoke",  viz:"",  overlay:"STAT BURST",   intel_scene_type:"demo"},
    {t0:16, t1:24, cam:"POV",            voice:"POV smoke",   viz:"",  overlay:"LABEL",        intel_scene_type:"face_to_camera"},
    {t0:24, t1:30, cam:"Cận tay",        voice:"Chi tiết",    viz:"",  overlay:"NONE",         intel_scene_type:"action"},
    {t0:30, t1:32, cam:"Câu hỏi",        voice:"CTA smoke",   viz:"",  overlay:"QUESTION XL",  intel_scene_type:"face_to_camera"}
  ],
  niche_id: $niche_id
}')

tmp_save=$(mktemp)
trap 'rm -f "$tmp_save" $tmp_list $tmp_get $tmp_copy $tmp_pdf 2>/dev/null' EXIT
tmp_list=$(mktemp); tmp_get=$(mktemp); tmp_copy=$(mktemp); tmp_pdf=$(mktemp)

code=$(curl -sS -o "$tmp_save" -w '%{http_code}' "${AUTH[@]}" "${CT[@]}" -X POST \
  --data "$body" "$CLOUD_RUN_URL/script/save")
if [[ "$code" != "200" ]]; then
  echo "FAIL POST /script/save → HTTP $code" >&2
  cat "$tmp_save" >&2
  exit 1
fi
draft_id=$(jq -r '.draft_id // empty' < "$tmp_save")
if [[ -z "$draft_id" ]]; then
  echo "FAIL /script/save missing draft_id" >&2
  cat "$tmp_save" >&2
  exit 1
fi
echo "OK /script/save draft_id=$draft_id"

# ── 2. List ─────────────────────────────────────────────────────────────────

code=$(curl -sS -o "$tmp_list" -w '%{http_code}' "${AUTH[@]}" \
  "$CLOUD_RUN_URL/script/drafts?limit=5")
if [[ "$code" != "200" ]]; then
  echo "FAIL GET /script/drafts → HTTP $code" >&2; cat "$tmp_list" >&2; exit 1
fi
top_id=$(jq -r '.drafts[0].id // empty' < "$tmp_list")
if [[ "$top_id" != "$draft_id" ]]; then
  echo "FAIL /script/drafts top id=$top_id (expected $draft_id)" >&2
  cat "$tmp_list" >&2
  exit 1
fi
echo "OK /script/drafts lists saved draft first"

# ── 3. Get single ───────────────────────────────────────────────────────────

code=$(curl -sS -o "$tmp_get" -w '%{http_code}' "${AUTH[@]}" \
  "$CLOUD_RUN_URL/script/drafts/$draft_id")
if [[ "$code" != "200" ]]; then
  echo "FAIL GET /script/drafts/:id → HTTP $code" >&2; cat "$tmp_get" >&2; exit 1
fi
if ! jq -e '.draft.id == "'"$draft_id"'" and (.draft.shots | length) == 6' < "$tmp_get" >/dev/null; then
  echo "FAIL /script/drafts/:id shape" >&2; cat "$tmp_get" >&2; exit 1
fi
echo "OK /script/drafts/:id returns the saved draft"

# ── 4. Export copy ──────────────────────────────────────────────────────────

code=$(curl -sS -o "$tmp_copy" -w '%{http_code}' "${AUTH[@]}" "${CT[@]}" -X POST \
  --data '{"format":"copy"}' "$CLOUD_RUN_URL/script/drafts/$draft_id/export")
if [[ "$code" != "200" ]]; then
  echo "FAIL export copy → HTTP $code" >&2; cat "$tmp_copy" >&2; exit 1
fi
if ! grep -q '\[KỊCH BẢN\] Smoke draft' "$tmp_copy"; then
  echo "FAIL export copy missing header" >&2; cat "$tmp_copy" >&2; exit 1
fi
echo "OK export format=copy returns text/plain"

# ── 5. Export pdf (200 or 503 acceptable) ──────────────────────────────────

code=$(curl -sS -o "$tmp_pdf" -w '%{http_code}' "${AUTH[@]}" "${CT[@]}" -X POST \
  --data '{"format":"pdf"}' "$CLOUD_RUN_URL/script/drafts/$draft_id/export")
case "$code" in
  200)
    # First 4 bytes should be %PDF.
    head -c 4 "$tmp_pdf" | grep -q '%PDF' || {
      echo "FAIL export pdf body is not a PDF" >&2
      head -c 80 "$tmp_pdf" >&2
      exit 1
    }
    echo "OK export format=pdf returns application/pdf"
    ;;
  503)
    if jq -e '.error == "pdf_unavailable"' < "$tmp_pdf" >/dev/null; then
      echo "OK export format=pdf returned 503 pdf_unavailable (WeasyPrint missing)"
    else
      echo "FAIL export pdf 503 but no pdf_unavailable marker" >&2
      cat "$tmp_pdf" >&2
      exit 1
    fi
    ;;
  *)
    echo "FAIL export pdf → HTTP $code" >&2; cat "$tmp_pdf" >&2; exit 1
    ;;
esac

echo "PASS smoke-script-save"
