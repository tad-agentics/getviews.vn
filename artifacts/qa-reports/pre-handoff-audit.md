# Pre-Handoff Audit — GetViews.vn

**Date:** 2026-04-10  
**Mode:** Pre-handoff (security-audit SKILL standard + SPA checks)  
**Verdict:** PASS — no BLOCKING security items; production dependency audit clean.

---

## 1. Security Audit Summary

### A. API keys & secret exposure
- **src/** — No matches for `GEMINI_*`, `SERVICE_ROLE`, `PAYOS_*`, `RESEND_*`, `sk-or-`, `whsec_`.
- **No `VITE_GEMINI_*`** in repo.
- **`api/chat.ts`** — `GEMINI_API_KEY` read from `process.env` only (Vercel Edge); Supabase URL/anon from server env aliases. OK.
- **`src/lib/env.ts`** — Zod-validated `VITE_SUPABASE_*` and optional `VITE_CLOUD_RUN_API_URL` only.
- **Frontend** — No `process.env` usage under `src/` (verified via search).

### B. RLS policy integrity (migrations reviewed)
| Area | Result |
|------|--------|
| `profiles` | RLS + own-row policies; `decrement_credit` SECURITY DEFINER enforces `auth.uid() = p_user_id` and `deep_credits_remaining > 0` |
| `chat_sessions` / `chat_messages` | RLS; `chat_messages` UPDATE/DELETE policies removed in `20260409000008_chat_rls_fix.sql` → immutable (deny by default) |
| `subscriptions` / `credit_transactions` | RLS; client writes denied |
| `video_corpus` | RLS SELECT only for authenticated; no INSERT policy → client cannot insert |
| `niche_taxonomy` | Authenticated read |
| Corpus aggregates (`trend_velocity`, `hook_effectiveness`, `format_lifecycle`, etc.) | Authenticated read policies in `20260409000005_corpus.sql` |
| `processed_webhook_events` | RLS enabled, no policies → service_role only |
| `processed_webhook_events` idempotency | `UNIQUE (payos_order_code, event_type)` |

### C. Payment / credit integrity
- **PayOS webhook** — HMAC-SHA256 over raw body vs `x-payos-signature` / `X-PayOS-Signature`, timing-safe compare; rejects before parse side effects.
- **`orderCode`** — Required string check before RPC.
- **`amount`** — Not cross-checked against `subscriptions.amount_vnd` in webhook handler (mitigation: business flow creates pending row with expected amount; **INFORMATIONAL** hardening opportunity).
- **Credit deduction** — `api/chat.ts` and Cloud Run `/stream` use `decrement_credit` RPC for paid paths; RPC enforces uid match + balance guard.

### D. Auth & JWT
- **`src/routes/_app/layout.tsx`** — Unauthenticated → `<Navigate to="/login" />`.
- **`api/chat.ts`** — Bearer token + `supabase.auth.getUser(token)`.
- **Cloud Run `main.py`** — `require_user`: HS256 if `SUPABASE_JWT_SECRET`, else ES256 via JWKS; requires `sub`.
- **Routes** — All `/app/*` segments registered under `layout("routes/_app/layout.tsx", [...])` in `src/routes.ts`.

### E. Input validation
- **`api/chat.ts`** — Requires `session_id`, `query`, `intent_type` (presence only; not length caps — acceptable for v1).
- **Cloud Run** — `StreamRequest` Pydantic model for body.
- **PayOS webhook** — JSON shape + `orderCode`; signature first.

### F. CORS & headers
- **`api/chat.ts`** — `Access-Control-Allow-Origin: *` for POST/OPTIONS (acceptable for Bearer-protected API).
- **Cloud Run** — `allow_origin_regex` restricts Vercel previews, `getviews.vn`, localhost (not `.*`).
- **Edge Functions** — `_shared/cors.ts` used; all functions handle OPTIONS (grep verified).

### G. Dependency vulnerabilities
- **`npm audit --omit=dev`** — **0 vulnerabilities** (production tree).
- **Full `npm audit`** — **4 high** in dev toolchain: `serialize-javascript` via `vite-plugin-pwa` → `workbox-build` → `@rollup/plugin-terser`. **Not BLOCKING** for deploy bundle; track upgrade / `npm audit fix` with breaking-change note.
- **`pip-audit`** — Not installed in environment; **INFORMATIONAL** — run in CI or local Python env before Cloud Run release.

### OWASP spot-checks
- **`dangerouslySetInnerHTML`** — `LandingPage.tsx` JSON-LD from app-controlled objects; `chart.tsx` theme CSS from internal `THEMES` config — no user HTML.
- **`eval()`** — None found in `src/`.

---

## 2. SPA-Specific Checks

| Check | Result |
|-------|--------|
| `process.env` in `src/` | None |
| Server-only secret strings in `src/` | None |
| `npm run build` | Success |
| Grep `build/client` + `build/server` for secret patterns | No matches |
| `npm test` | 11/11 passed |
| `public/manifest.json`, `robots.txt`, `sitemap.xml` | Present |
| Paywall / video intents | `useChatStream`: `VIDEO_INTENTS` = `video_diagnosis`, `competitor_profile`, `own_channel`; free intents on Edge match `FREE_INTENTS` in `api/chat.ts` (`trend_spike`, `find_creators`, `follow_up`, `format_lifecycle`). Cloud Run resets `is_processing` on errors (generator `except` and early returns). |
| `useProfile` | Uses `.maybeSingle()` |

---

## 3. Code Quality Spot-Check

- **`tsconfig.json`** — `"strict": true`.
- **`any` in `api/chat.ts`, `useChatStream.ts`, `ChatScreen.tsx`** — No `: any` in those files (typed casts / `unknown` where used).
- **`useChatStream` errors** — 402 mapped to `insufficient_credits`; other HTTP failures collapse to `stream_failed` (**INFORMATIONAL**: explicit 401 messaging could improve UX).

---

## 4. AUTO-FIX Applied

1. **`src/hooks/useChatStream.ts`** — Use `env` from `@/lib/env` for `VITE_CLOUD_RUN_API_URL` instead of raw `import.meta.env`, aligning with validated client env surface.

---

## 5. Adversarial Cross-Check

- **Dev-only npm highs** — Do not ship to browser; production audit clean → not escalated as BLOCKING.
- **Webhook amount** — Replay still needs valid HMAC + PayOS payload; financial risk is operational → INFORMATIONAL.
- **Global 500 `detail: str(exc)` on Cloud Run** — Theoretical info disclosure; handler path is rare for `/stream` (most errors become SSE error tokens). **INFORMATIONAL** — sanitize generic message in a future hardening pass.

---

## 6. Counts

| Category | Count |
|----------|-------|
| BLOCKING | 0 |
| AUTO-FIX | 1 |
| INFORMATIONAL | 7 |

---

## Related artifacts

- `artifacts/issues/foundation-concerns.md` — OAuth config, PayOS live signature validation, PWA assets, `VITE_CLOUD_RUN_API_URL` for video demos remain **operational** gates (not duplicated as new BLOCKING here).
