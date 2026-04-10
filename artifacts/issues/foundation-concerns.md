# Foundation → Wave 2 Concerns
> Logged: 2026-04-09 | Updated: 2026-04-10 | Source: Foundation + all Wave 1–2 features + Cloud Run pipeline
> Status: **Cloud Run deployed and healthy.** Remaining items are env var wiring in Vercel, PWA assets, Facebook OAuth, and post-deploy verifications.

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
**Impact:** `supabase/seed.sql` uses fake UUIDs — cannot be applied to remote DB directly. Valid for local `supabase db reset` only.
**Action:** For remote testing, create real users via Google login, then seed data tied to those UUIDs.

### N-4 — PayOS HMAC signature algorithm not validated against live PayOS
**Source:** Backend agent
**Impact:** If PayOS signs differently than expected (sorted keys, different encoding), all payments will be rejected at the webhook.
**Action:** Test with a real PayOS sandbox payment before billing launch. Verify against [PayOS docs](https://payos.vn/docs/tich-hop-cong-thanh-toan/).

### N-5 — PWA icons + OG image missing
**Source:** Frontend agent
**Impact:** PWA install fails silently. OG share card missing on social.
**Action (human):** Create and place:
- `public/og-image.png` (1200×630)
- `public/icons/icon-192.png` + `icon-192-maskable.png`
- `public/icons/icon-512.png` + `icon-512-maskable.png`
- `public/screenshots/chat-mobile.png` (390×844)

### N-8 — Supabase Realtime not enabled on `profiles` table
**Source:** Auth backend agent
**Impact:** `useProfile` Realtime subscription is inert — queries work, but live cache invalidation on profile changes won't fire.
**Action (human):** Supabase Dashboard → Database → Replication → enable `profiles` for Realtime.

### N-10 — MCP tokens in `.cursor/mcp.json` readable in-session
**Source:** Auth backend agent
**Status:** DEFERRED — low risk for solo dev. `.cursor/mcp.json` is gitignored. Revisit when onboarding first teammate: rotate tokens + migrate to `~/.zshrc` env vars or macOS Keychain.

### N-12 — `VITE_CLOUD_RUN_API_URL` ✅ RESOLVED
**Source:** Chat-core QA agent
**Status:** RESOLVED 2026-04-10 — Cloud Run deployed, env var set in Vercel. Video intents (`video_diagnosis`, `competitor_profile`, `own_channel`) now route to Cloud Run pipeline.
**Action:** Redeploy triggered in Vercel to pick up the new env var.

### N-13 — `structured_output` not yet rendered in ChatScreen
**Source:** Chat-core frontend agent
**Impact:** ChatScreen renders `content` as plain text. Structured diagnosis components (DiagnosisRow, HookRankingBar) show mock data, not real pipeline output.
**Action:** Wave 2 — update ChatScreen to read `structured_output` when present.

### N-19 — `video_corpus` first batch complete ✅
**Source:** Explore QA agent
**Status:** RESOLVED 2026-04-10 — Batch ingest ran against niche_id=1 ("Shopee affiliate reviews"): 10 videos inserted, 0 failed, MV refreshed. Cloud Scheduler (`getviews-corpus-ingest`) runs nightly at 02:00 ICT.

### N-20 — R2 bucket must be public for corpus media to load
**Source:** Explore backend agent
**Impact:** `video_url` and `thumbnail_url` stored are TikTok CDN URLs (not R2) — R2 not used in current pipeline. ExploreScreen thumbnails load from TikTok CDN directly.
**Status:** Non-issue for current implementation. R2 only needed if we cache videos locally.

### N-21 — `trending_keywords` populated ✅
**Source:** Explore QA agent
**Status:** RESOLVED 2026-04-10 — `niche_intelligence` materialized view refreshed after first batch run. TrendScreen aside will show real data on next load.

### N-22 — `niche_intelligence` auto-refresh scheduled ✅
**Source:** Trends backend agent
**Status:** RESOLVED 2026-04-10 — `refresh_niche_intelligence()` SECURITY DEFINER RPC created. Called automatically at end of every batch ingest. Cloud Scheduler triggers nightly at 02:00 ICT.

### N-26 — `noreply@getviews.vn` sender not yet verified in Resend
**Source:** Billing backend agent
**Impact:** Emails may fail or land in spam if sender domain is unverified.
**Action (human):** Resend Dashboard → Domains → verify `getviews.vn` or add `noreply@getviews.vn` as verified sender.

### N-27 — CheckoutScreen diverges from Make (intentional)
**Source:** Billing QA agent
**Status:** Intentional deviation — Make has mock QR/VNPay/Dialog; live version uses PayOS redirect (correct for production). No action needed unless QR display is required.

### N-29 — PaymentSuccessScreen `creditsDelta` edge case
**Source:** Billing QA agent
**Impact:** If navigated without `creditsDelta` state, heading may show total credits instead of delta. Low risk — PayOS redirect already loses state, fallback copy handles it.
**Action:** Deferred — fix when wiring PayOS webhook Realtime callback.

### N-30 — `useUpdateProfile` optimistic update skips on cold cache
**Source:** Settings QA agent
**Impact:** Virtually never triggered — SettingsScreen only renders niche selector after profile loads.
**Action:** Deferred.

### N-31 — No Vitest coverage for settings flows
**Source:** Settings QA agent
**Action:** Add 3–4 regression tests: logout dialog, `useUpdateProfile` optimistic rollback, free vs paid copy. Low priority.

### N-33 — Cron + email functions not yet verified end-to-end
**Source:** Email-cron QA agent
**Impact:** `RESEND_API_KEY` is now set. Functions have not been invoked live yet.
**Action:** After deploy — `supabase functions invoke cron-expiry-check --project-ref lzhiqnxfveqttsujebiv` and verify Resend dashboard. Repeat for each cron.

### N-38 — Cloud Run session store not shared across instances
**Source:** Cloud Run audit
**Impact:** In-process dict fails on multi-instance scale-out — duplicate pipeline costs, no cross-request context.
**Action:** Keep `--max-instances=1` for MVP. Replace with Redis/Firestore before scaling.

### N-39 — Cloud Run env vars set ✅
**Source:** Cloud Run audit
**Status:** RESOLVED — all 5 required env vars (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `GEMINI_API_KEY`, `ENSEMBLE_DATA_API_KEY`, `SUPABASE_JWT_SECRET`) set via `gcloud run services update`. Health check confirms all keys present.

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
| Monday weekly email Edge Function | Post Wave 2 | Content generation deferred |
| Cloud Run deploy to GCP | ✅ Done — 2026-04-10 | `getviews-pipeline-00002-2lj` live at `asia-southeast1.run.app` |
| PayOS Realtime → in-app payment detection | Post-billing | Currently relies on redirect + page reload |
| `own_channel` full account audit | Post MVP | Routes to `run_video_diagnosis` for MVP |
| `structured_output` rendering in ChatScreen (N-13) | Wave 2 | Plain text render only for now |
| Redis/Firestore session store for Cloud Run (N-38) | Before scaling >1 instance | In-process dict fine at `--max-instances=1` |

---

## Summary

| Priority | Count | Items |
|---|---|---|
| BLOCKING | 0 | — |
| NON-BLOCKING | 12 | N-1, N-3, N-4, N-5, N-8, N-10, N-13, N-20, N-26, N-27, N-29, N-30, N-31, N-33, N-38, N-40 |
| DEFERRED | 8 | Post-MVP |

**Resolved since last update:**
- ✅ B-1 (Google OAuth) — 2026-04-10
- ✅ N-11 (Gemini API key in Vercel) — 2026-04-10
- ✅ N-25 (PayOS secrets in Supabase) — 2026-04-10
- ✅ N-26 partial (RESEND_API_KEY set) — 2026-04-10; sender verify still pending
- ✅ N-32 (pg_cron + 4 cron jobs) — 2026-04-10
- ✅ N-39 (Cloud Run env vars) — 2026-04-10; all 5 keys confirmed via `/health`
- ✅ Cloud Run deploy — 2026-04-10; `getviews-pipeline-00002-2lj` live in `asia-southeast1`, health check green
- ✅ N-12 (`VITE_CLOUD_RUN_API_URL`) — 2026-04-10; set in Vercel, video intents now route to Cloud Run
- ✅ N-19 (video_corpus first batch) — 2026-04-10; 10 videos ingested for niche_id=1, nightly scheduler active
- ✅ N-21 (trending_keywords) — 2026-04-10; niche_intelligence view refreshed post-batch
- ✅ N-22 (MV auto-refresh) — 2026-04-10; refresh_niche_intelligence() RPC + Cloud Scheduler running
