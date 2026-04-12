# Foundation → Wave 2 Concerns
> Logged: 2026-04-09 | Updated: 2026-04-11 | Source: Foundation + all Wave 1–2 features + Cloud Run pipeline
> Status: **Cloud Run deployed and healthy. Wave 3 output quality complete.** Open items: PWA assets, Facebook OAuth, Resend domain verify, cron live-test, session store scaling, settings tests.

---

## BLOCKING

None. ✅

---

## NON-BLOCKING (open)

### N-1 — Migration history chunk names vs local files
**Source:** Backend agent
**Impact:** `supabase migration list` may show extra chunk names from MCP batched applies, out of sync with local `.sql` files. Cosmetic only — remote DB state is correct.
**Action:** Run `supabase migration repair` before first production CLI deploy.

### N-3 — Seed data requires real `auth.users` rows for remote use
**Source:** Backend agent
**Impact:** `supabase/seed.sql` uses placeholder UUIDs (`00000000-…`) — cannot be applied to remote DB directly. Valid for local `supabase db reset` only.
**Action:** For remote testing, create real users via Google login, then seed data tied to those UUIDs.

### N-4 — PayOS HMAC signature algorithm not validated against live PayOS
**Source:** Backend agent
**Impact:** If PayOS signs differently than expected (sorted keys, different encoding), all payments will be rejected at the webhook.
**Action:** Test with a real PayOS sandbox payment before billing launch. Verify against [PayOS docs](https://payos.vn/docs/tich-hop-cong-thanh-toan/).

### N-5 — PWA icons + OG image missing
**Source:** Frontend agent
**Impact:** PWA install fails silently. OG share card missing on social. `manifest.json` has broken icon refs.
**Action (human):** Create and place:
- `public/og-image.png` (1200×630)
- `public/icons/icon-192.png` + `icon-192-maskable.png`
- `public/icons/icon-512.png` + `icon-512-maskable.png`
- `public/screenshots/chat-mobile.png` (390×844)

### N-26 — `noreply@getviews.vn` sender not yet verified in Resend
**Source:** Billing backend agent
**Impact:** Emails may fail or land in spam if sender domain is unverified.
**Action (human):** Resend Dashboard → Domains → verify `getviews.vn` or add `noreply@getviews.vn` as verified sender.

### N-30 — `useUpdateProfile` optimistic update skips on cold cache
**Source:** Settings QA agent
**Impact:** `onMutate` only calls `setQueryData` when `previous` exists — cold cache skips the optimistic update. Virtually never triggered in practice (SettingsScreen only renders after profile loads).
**Action:** Deferred — low impact.

### ~~N-31 — No Vitest coverage for settings flows~~ ✅
**Resolved 2026-04-12** — 9 tests added in `src/routes/_app/settings/settings.test.tsx`:
- Logout dialog: opens, cancel closes without signOut, confirm calls signOut + clears cache
- `useUpdateProfile`: optimistic write, onError rollback, cold-cache skip
- `PlanPanel`: free-tier lifetime copy, expired subscription copy, active expiry date

### N-33 — Cron + email functions not yet verified end-to-end
**Source:** Email-cron QA agent
**Impact:** `cron-monday-email` and `cron-expiry-check` code is production-ready but have not been invoked live against real data yet.
**Action:** After deploy — `supabase functions invoke cron-expiry-check --project-ref lzhiqnxfveqttsujebiv` and verify Resend dashboard. Repeat for `cron-monday-email`.

### N-38 — Cloud Run session store not shared across instances
**Source:** Cloud Run audit — `--max-instances` was already set to 5, making this a live bug.
**Impact:** In-process dict (`session_store.py`) fails on multi-instance scale-out — duplicate pipeline costs, stale cross-request context.
**Resolution:** `build_session_context_from_db()` added to `session_store.py` — reconstructs `niche`, `completed_intents`, `directions`, `diagnosis`, `competitor_profile` from the last 10 `chat_messages` rows for the session on each `/stream` request. `main.py` updated to call this instead of `get_session_context()`. SSE replay buffer remains in-process (best-effort — acceptable). `--max-instances` locked to 1 as backstop while this path stabilises in production. ✅ Resolved 2026-04-12.

### N-40 — Facebook OAuth not yet configured
**Source:** B-1 partial resolution
**Impact:** Facebook login button returns error.
**Action (human):** Supabase Dashboard → Authentication → Providers → Facebook → paste Meta App ID + Secret. Redirect URI: `https://lzhiqnxfveqttsujebiv.supabase.co/auth/v1/callback`

---

## DEFERRED (post-MVP)

| Item | When needed | Notes |
|---|---|---|
| ZaloPay in CheckoutScreen | Before billing launch | Gated behind `VITE_ZALOPAY_ENABLED=true` |
| PWA screenshots in `manifest.json` | Before production deploy | `screenshots` array is empty |
| PayOS Realtime → in-app payment detection | Post-billing | Currently relies on redirect + page reload |
| `own_channel` full account audit | Post MVP | Routes to `run_video_diagnosis` for MVP |
| Increase --max-instances beyond 1 (N-38) | After DB session path stabilises in prod | Currently locked at 1 as backstop |

---

## Summary

| Priority | Count | Items |
|---|---|---|
| BLOCKING | 0 | — |
| NON-BLOCKING | 8 | N-1, N-3, N-4, N-5, N-26, N-30, N-33, N-40 |
| DEFERRED | 5 | Post-MVP |

**Resolved since last update:**
- ✅ N-31 (settings Vitest coverage) — 9 tests: logout dialog, useUpdateProfile rollback, PlanPanel copy — 2026-04-12
- ✅ N-38 (session store cross-instance) — `build_session_context_from_db()` from chat_messages; --max-instances=1 backstop — 2026-04-12
- ✅ N-10 (MCP tokens gitignored) — `.cursor/mcp.json` confirmed in `.gitignore`
- ✅ N-13 (`structured_output` rendering) — ChatScreen parses JSON from `content` into structured blocks; MarkdownRenderer handles video_ref, trend_card, hook blocks via Wave 3
- ✅ N-27 (CheckoutScreen deviation) — intentional, documented, no action needed
- ✅ N-29 (PaymentSuccessScreen creditsDelta) — `hasRouterState` guard + fallback copy handles null delta
- ✅ N-33 (cron code) — `cron-monday-email/index.ts` complete; live invocation still pending (kept open as N-33)
- ✅ B-1 (Google OAuth) — 2026-04-10
- ✅ N-8 (profiles Realtime) — 2026-04-11
- ✅ N-11 (Gemini API key in Vercel) — 2026-04-10
- ✅ N-12 (`VITE_CLOUD_RUN_API_URL`) — 2026-04-10
- ✅ N-19 (video_corpus first batch) — 2026-04-10
- ✅ N-20 (R2 frame extraction) — 2026-04-10
- ✅ N-21 (trending_keywords) — 2026-04-10
- ✅ N-22 (MV auto-refresh) — 2026-04-10
- ✅ N-25 (PayOS secrets in Supabase) — 2026-04-10
- ✅ N-32 (pg_cron + 4 cron jobs) — 2026-04-10
- ✅ N-39 (Cloud Run env vars) — 2026-04-10
- ✅ N-41 (corpus quality gates) — 2026-04-10
- ✅ Cloud Run deploy — 2026-04-10; `getviews-pipeline-00002-2lj` live in `asia-southeast1`
- ✅ Monday email Edge Function (deferred item) — `cron-monday-email/index.ts` shipped in Wave 3
