#!/usr/bin/env bash
# Phase C.1.6 — smoke checks for /app/answer wiring (no live Cloud Run).
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

echo "== grep: backend list_sessions scope =="
grep -q 'scope: str' cloud-run/getviews_pipeline/answer_session.py
grep -q 'next_cursor' cloud-run/main.py

echo "smoke-answer-shell: OK"
