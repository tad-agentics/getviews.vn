# Pipeline Audit & Hardening Report (Answer/Channel)

Date: 2026-05-12  
Scope: Cloud Run Answer/Channel pipeline, frontend orchestration, Supabase contract parity, feature-scoped FE/UX.

## 1) Contract Matrix (FE ↔ Runtime ↔ DB)

### A. Answer session create (`POST /answer/sessions`)

- Frontend payload source:
  - `CreateAnswerSessionBody.format` in `src/lib/answerApi.ts`
  - `AnswerSessionRow.format` in `src/lib/api-types.ts`
  - Both include: `pattern|ideas|timing|generic|lifecycle|diagnostic|video|script`
- Runtime validator:
  - `AnswerSessionCreateBody.format` `Literal[...]` in `cloud-run/getviews_pipeline/routers/answer.py`
  - Includes `script` in current repo.
- DB constraint:
  - `answer_sessions_format_check` includes `script` in `supabase/migrations/20260512000003_answer_sessions_script_format.sql`.

Result: **Parity exists in repository**.  
Observed operational weak link: FE/runtime drift is possible when Cloud Run revision lags FE deploy.

### B. Answer append turn (`POST /answer/sessions/{id}/turns`)

- Frontend turn kinds: `primary|timing|creators|script|generic` in `src/hooks/useSessionStream.ts`.
- Runtime `AnswerTurnAppendBody.kind` `Literal[...]` matches in `cloud-run/getviews_pipeline/routers/answer.py`.
- Billing path:
  - Script: 3 decrements in `cloud-run/getviews_pipeline/answer_session.py`.
  - Primary non-script: 1 decrement.

Result: **Contract aligned**.

### C. Channel analyze (`GET /channel/analyze`)

- Frontend query params in `src/hooks/useChannelAnalyze.ts`:
  - `handle` (normalized)
  - `force_refresh`
  - optional `creator_niche_id`
- Runtime in `cloud-run/getviews_pipeline/routers/video.py`:
  - `handle` required
  - `force_refresh` bool
  - `creator_niche_id` optional, `ge=1`, `le=64`

Result: **Mostly aligned**.  
Minor mismatch risk: FE accepts any `>=1` while BE rejects `>64`.

### D. Channel user search (`GET /channel/user-search`)

- Frontend in `src/hooks/useChannelUserSearch.ts`: `keyword` from debounced input, enabled when `len >= 2`.
- Runtime in `cloud-run/getviews_pipeline/routers/video.py`: `keyword` min_length=2, max_length=64.

Result: **Aligned**.

## 2) Failure Taxonomy & Error-Shaping Audit

### Critical finding F-001 (High)
- Surface: FE error parsing
- Files:
  - `src/lib/cloudRunErrors.ts`
  - `src/routes/_app/answer/AnswerScreen.tsx`
  - `src/lib/errorMessages.ts`
- Problem:
  - `readErrorDetail()` only extracts `detail` when it is a **string**.
  - FastAPI validation often returns `detail` as an **array**.
  - FE then throws raw JSON text; `pickAnswerErrorCode()` cannot classify; falls back to `start_failed`.
- Impact:
  - Users get generic copy ("Không tạo được phiên...") instead of precise validation errors.
  - Operational debugging is slower.
- Recommendation:
  - Parse `detail: [{type, loc, msg, input}]` and map to stable codes (e.g. `invalid_payload`).
  - Preserve raw structured payload in logs/telemetry.

### High finding F-002 (High)
- Surface: Deploy/runtime drift
- Files:
  - `src/lib/answerApi.ts`
  - `cloud-run/getviews_pipeline/routers/answer.py`
  - release process (`cloud-run/deploy.sh`)
- Problem:
  - FE and Cloud Run enum evolution can diverge (already observed for `format="script"`).
- Impact:
  - Production 422 despite “correct” FE behavior.
- Recommendation:
  - Add pre-release contract gate: compare FE enum union vs runtime `Literal`.
  - Block FE release if Cloud Run revision hash/version gate not satisfied.

### Medium finding F-003 (Medium)
- Surface: Channel error shaping inconsistency
- Files:
  - `src/hooks/useChannelAnalyze.ts`
  - `src/hooks/useChannelUserSearch.ts`
  - `src/lib/errorMessages.ts`
- Problem:
  - Some hooks use `readErrorDetail`, others throw raw `res.text()`.
  - Status-specific mapping is inconsistent.
- Impact:
  - Uneven UI copy quality and harder support triage.
- Recommendation:
  - Introduce shared Cloud Run client adapter for auth + status + payload parsing.

## 3) Dead Code / Smell / Duplication Audit

### Duplication hotspots

1. **Enum duplication across FE/BE/DB**
   - `format` appears in TS unions, Python `Literal`, SQL check constraints.
   - High drift risk.

2. **Error code mapping duplicated**
   - `ANSWER_ERROR_CODES` in `AnswerScreen.tsx` + branches in `analysisErrorCopy()` + status checks in hooks.
   - Multiple sources of truth for the same semantics.

3. **Cloud Run fetch boilerplate duplicated in hooks**
   - 401 handling + `readErrorDetail` + ad-hoc status parsing repeated in multiple hooks.

### Code smells

- Smell S-001: Raw backend body surfaced as error string path (`new Error(text || HTTP...)`) in channel search hook.
- Smell S-002: Frontend boundary checks diverge from backend (`creator_niche_id` max).
- Smell S-003: PWA warning path for `__spa-fallback.html` suggests precache/fallback mismatch:
  - `vite.config.ts` uses `navigateFallback: "/__spa-fallback.html"`
  - `scripts/append-pwa-precache-index.mjs` only appends `index.html` entry.

## 4) Invariant Validation (TD checks)

### TD-1 Atomic credit deduction
- Verified:
  - SQL function `decrement_credit()` is single-statement guarded update in `supabase/migrations/20260409000002_profiles.sql`.
  - Runtime checks `rpc.data is None` (not falsy) in `answer_session.py` and `channel_analyze.py`.

Status: **Pass**.

### TD-3 Concurrent request guard
- Verified in Vercel Edge (`api/chat.ts`):
  - `begin_processing` lock before paid intent deduction.
  - `end_processing` on error and on completion.

Status: **Pass** (for inspected path).

### TD-4 SSE replay/reconnect
- Verified:
  - Server replay buffer logic in `routers/answer.py`.
  - Client persistence + resume window in `src/lib/sseResume.ts`.

Status: **Pass**.

### Idempotency (session create)
- Verified:
  - L1 in-memory + L2 DB mapping in `answer_session.py`.

Status: **Pass**, with operational drift caveat (runtime version alignment still required).

## 5) FE/UX Feature Audit (Answer/Channel)

### Answer (`/app/answer`)
- Strengths:
  - Clear loading/skeleton/empty/error/follow-up state layout in `AnswerScreen.tsx`.
  - Retry and fallback blocks exist.
- Gaps:
  - 422 validation paths collapse into generic copy due F-001.
  - Repeated failing bootstrap attempts can feel like “stuck loop” from user perspective when `?q=` persists.

### Channel (`/app/channel`)
- Strengths:
  - Good empty-state entry and guided input.
  - Error card with retry action.
- Gaps:
  - Inconsistent error detail decoding between analyze vs user-search hooks.
  - User-search quota and validation errors could use tighter copy specialization.

## 6) Prioritized Backlog (Owners + Verification)

### P0
1. **Normalize FastAPI validation errors (422)**
   - Owner: Frontend
   - Files: `src/lib/cloudRunErrors.ts`, `src/routes/_app/answer/AnswerScreen.tsx`, `src/lib/errorMessages.ts`
   - Verify:
     - unit tests for array `detail` parsing
     - UI shows `invalid_payload` copy for malformed `format`

2. **Contract drift guard FE↔Cloud Run**
   - Owner: Backend + Frontend
   - Files: `src/lib/answerApi.ts`, `cloud-run/getviews_pipeline/routers/answer.py`, tests
   - Verify:
     - CI contract test fails when enums diverge
     - release checklist requires deployed Cloud Run revision match

### P1
3. **Shared Cloud Run hook adapter**
   - Owner: Frontend
   - Scope: unify 401/402/404/429/422 parsing and named errors for hooks.
   - Verify:
     - refactor in `useChannelAnalyze`, `useChannelUserSearch`, `useScriptGenerate`, etc.

4. **Align creator_niche_id bound checks**
   - Owner: Frontend
   - Scope: cap FE query param to BE range.
   - Verify:
     - unit tests for boundary values.

5. **PWA fallback/precache consistency**
   - Owner: Frontend/Platform
   - Files: `vite.config.ts`, `scripts/append-pwa-precache-index.mjs`
   - Verify:
     - no `non-precached-url` console error for `__spa-fallback.html`.

## 7) Release Gates

1. FE/BE contract test pass for enums and payload shapes (`format`, turn kinds, known errors).
2. Supabase migration parity check (linked + prod) for touched constraints.
3. Staging smoke:
   - Answer primary generic
   - Answer script session create
   - Channel analyze with and without `creator_niche_id`
   - Channel user-search + quota path
4. Cloud Run revision pin/check recorded before FE promote.
5. Post-release telemetry watch window (24h): 422 rate, `start_failed` fallback rate, retry success.

## 8) Risk Register Summary

- High:
  - F-001 422 array-detail parsing blind spot
  - F-002 FE/runtime deployment drift
- Medium:
  - F-003 Error-shaping inconsistencies across hooks
  - PWA fallback/precache mismatch warning

---

Status signal: **DONE_WITH_CONCERNS**
- Completed contract, taxonomy, smell/duplication, invariants, FE/UX, backlog, and release-gate audit.
- Primary concerns remain runtime contract drift and non-specific validation error handling.
