# Front-End Audit — GetViews.vn (2026-06-10)

Five parallel deep-audits over the React SPA (SSE/answer, data layer, routing/auth,
payments/admin, design-system/a11y) plus build-level signal (bundle, knip,
typecheck). Every Critical/High re-verified by hand; agent ratings recalibrated.
**FIXED** = repaired in the commit alongside this report.

## Verified ground truth
- `npm run typecheck` ✅ (0 errors, token check clean)
- frontend tests ✅ (see suite run)
- `npx knip`: 3 unused files, 56 unused exports (mostly intentional `*Keys` query-key
  exports + label constants) — see hygiene section
- `database.types.ts` was **6 weeks stale** (last gen 2026-05-27) — regenerated against
  live schema this pass

## CRITICAL — FIXED

### FE-C1 · `database.types.ts` 6 weeks stale → silent runtime drift — FIXED
Generated 2026-05-27; missing `refund_credit` RPC, `corpus_ingest_runs`,
`expected_cron_jobs`, and still declared the dropped `credit_transactions.session_id`.
This is the class of bug that 400s at runtime with **zero typecheck signal** —
exactly how the Phase C landing-stats break happened. Regenerated from the live
schema (`mcp generate_typescript_types`); typecheck stays green, confirming no code
depended on the stale shape.

### FE-C2 · Credits not refetched when the server says 402/error → user sees phantom loss — FIXED
`useSessionStream.ts:316` (402 insufficient_credits) and the mid-stream error path
(`:711`) didn't invalidate `["credits"]` — so after the server's 2026-06-10 refund
landed, the UI still showed the deducted balance until a manual refresh. On a paid
product that reads as "you charged me and gave nothing." Both paths now invalidate
profile + credits. (402 also now refetches so the user sees their true balance, not
our stale-high cache.)

### FE-C3 · Payment-success animated the OLD balance (webhook race) — FIXED
`PaymentSuccessScreen` read `useProfile()` once (staleTime: Infinity) and the PayOS
webhook grants credits *after* the user lands — so the success screen animated the
pre-grant number. Added a bounded poll (every 2.5s, max 20s) that invalidates the
profile until the balance moves, then stops. This is the single highest user-trust
fix in the FE.

## CRITICAL/HIGH — recalibrated DOWN after verification (no fix needed)

- **Open-redirect "backslash bypass"** (agent: Critical): real but low-severity — the
  `/app` allowlist already blocks it from reaching anything but in-app paths
  (`/\evil.com` fails `startsWith("/app")`). Hardened anyway (FE-H1 below) since it's
  one line + tests.
- **SSE decoder "data loss on EOF"** (agent: Critical): real but rare — only bites when
  a stream's *final* chunk splits a multi-byte UTF-8 char AND nothing flushes. Fixed
  (FE-H2) but not critical-severity in practice (streams end on ASCII `}`/newline).
- **Admin route "structure leak"** (agent: High): **not a bug** — panels render only
  after `isAdmin===true`; loading/non-admin states render empty shells. Endpoint URLs
  in a bundle are inherent to any SPA and the server enforces `require_admin`.
- **Double-click → duplicate order code** (agent: High): **safe** — `subscriptions.payos_order_code`
  has a UNIQUE constraint, so a same-millisecond `Date.now()` collision fails the
  second insert cleanly; FE also guards with a `submitting` flag.

## HIGH — FIXED

### FE-H1 · Redirect sanitizer backslash hardening — FIXED
Added `/^\/[\\/]/` rejection + `/%5c` decode coverage to `sanitizePostLoginPath`, with
3 new test cases. Defense-in-depth behind the existing `/app` allowlist.

### FE-H2 · SSE decoder flush on stream EOF — FIXED
Both `useSessionStream.ts` and `useChannelDiagnose.ts` now `decoder.decode()` (no-arg
flush) on the `done` branch so a trailing partial multi-byte Vietnamese char isn't
dropped.

## MEDIUM / LOW — FIXED in this pass
- Unused-lib input font sizes: `select.tsx` `text-sm`→`text-base`, dropped
  `textarea.tsx` `md:text-sm` (both are unconsumed library components — all *real*
  input surfaces already use `text-[17px]`/`text-base`, so this is pre-emptive, not a
  live iOS-zoom bug as rated).
- `corpusNicheFilter` silent `[]` on query failure: kept the fail-soft (browse falls
  back to unscoped by design) but added a DEV warning so a real failure is
  distinguishable from "niche genuinely has no classes".

## MEDIUM / LOW — backlog (rationale, not silence)

| # | Finding | Where | Disposition |
|---|---|---|---|
| FE-M1 | Profile credit invalidation uses prefix key `["profile"]` not `queryKeys.profile(userId)` — works via TanStack prefix-match but fragile | `useSessionStream.ts`, `useChannelDiagnose.ts` | Works today; tighten when query-keys are next refactored |
| FE-M2 | `select("*")` on `profiles`/`subscriptions`/`credit_transactions` (wide rows, profile polls every 4s) | `useProfile.ts:38` etc. | Column-list the polled queries; ~10-20% payload trim |
| FE-M3 | Profile 4s poll has no aggressive retry — a transient blip stalls processing-state UI 4s | `useProfile.ts:48` | Add `retry: 3` while `is_processing` |
| FE-M4 | `logUsage` swallows insert errors in prod (analytics blind spot) | `logUsage.ts:25` | Route to error tracking once Sentry/GCP lands (backend H-1) |
| FE-M5 | `idle-timeout` keeps `streamId`/`lastSeq` → reload can auto-resume; double-charge only if replay buffer also missed (server lock + refund mitigate) | `useSessionStream.ts:609` | Low real risk given TD-3 lock; revisit with disconnect telemetry |
| FE-M6 | OAuth callback collapses all provider errors to one generic message | `_auth/callback/route.tsx` | Pass `error`/`error_description` through for better UX |
| FE-M7 | `create-payment` error codes (`SERVER_ERROR` etc.) collapsed to one toast | `CheckoutScreen.tsx` | Map codes → distinct Vietnamese copy |
| FE-M8 | Admin panels show generic error on batch-pod 404 when `VITE_CLOUD_RUN_BATCH_URL` unset | `EnsembleCreditsPanel.tsx` | Map 404 → "batch URL chưa cấu hình" |
| FE-M9 | ZaloPay shown in pricing labels but unselectable (type/schema/webhook all omit it) behind `VITE_ZALOPAY_ENABLED` | `PricingScreen.tsx` | Remove the label or finish the integration before enabling the flag |
| FE-L1 | `Btn` size `md` is `h-10` (40px) <44px touch target, used on mobile composer submit | `v2/Btn.tsx:30` | Add `min-h-[44px]` |
| FE-L2 | History cursor lacks `(updated_at, id)` tie-breaker — identical timestamps could skip a row | `useHistoryUnion.ts:39` | Tuple cursor |
| FE-L3 | TTL comments say 120s/90s; real is 60s server / 45s client | `sseResume.ts`, `AnswerScreen.tsx` | Comment-only fix |
| FE-L4 | 2 unused files + hardcoded payment-icon hex in `CheckoutScreen` config | knip / `CheckoutScreen.tsx:42` | Tokenize colors; delete dead files |

## What's genuinely strong (verified)
- **SSE engine**: line-buffer reassembly with `stream:true`, the carried-payload retry
  pattern (partial first attempt + replay second resolves to success), rolling
  idle-timeout. Robust and well-tested.
- **Mutations**: optimistic update + rollback everywhere; niche change cascades to
  `daily_ritual`; logout does `queryClient.clear()` (no cross-user leakage on shared
  devices).
- **Auth**: JWKS-style session-expired listener with signout dedup; layout guard;
  sanitized post-login redirect; Facebook popup-blocker detection with VN copy.
- **Payments**: price authority is server-side (FE display-only, no FE→BE trust),
  webhook idempotency correct, admin gating layered (client UX + server `require_admin`).
- **Design system**: check-tokens clean, breakpoint hierarchy respected, Vietnamese
  copy clean (no forbidden words/openers), JetBrains Mono on numerics, ✓/✕ not emoji,
  icons individually imported, motion stubbed off the landing path.
- **Intent router**: 100+ test cases incl. the competitor-detection regression guard
  and TikTok short-link variants.

## FE grade: B+ → A- after this pass
Strong architecture and discipline; the real risks were a stale types file (silent
drift vector), two credit-sync gaps that read as theft to a paying user, and the
payment-success webhook race. All three fixed. Remaining items are observability and
polish, not correctness.
