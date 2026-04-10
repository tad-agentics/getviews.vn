# Foundation → Wave 2 Concerns
> Logged: 2026-04-09 | Updated: 2026-04-10 | Source: Foundation `f83aa55`/`81b99f2` + Auth `89dc2ca`/`fd2203f`/`a2661f6` + Chat-core `9b8bdd0`/`df0b02c`/`3e1da07` + History `e8bc480`/`c4cd6da`/`c30f2f3` + Explore `9f09947`/`beff235`/`304f866`/`20572ac` + Trends `58a6446`/`b28a9a7`/`ddaf839` + Billing `f62ca14`/`d706777`/`5b1c433`/`93a30b7` + Settings `322649a`/`09a81a8`/`8086be5`/`6dc6708` + Email-cron `31a2b70`/`54568ab`/`27a292b` + Cloud Run `c75a8d3`/`2f3f32e` + Cloud Run tasks `05b6129`/`726a277`/`d0c9325`/`5b48206`/`16dcaac`/`1ad5aa4`/`71e5832`/`553d566`
> Status: **Wave 2 COMPLETE** — Cloud Run pipeline complete with full credit gate, RLS-scoped client, structured error handling, and deploy tooling. Open items are staging-deploy gates and post-deploy verifications.

---

## BLOCKING (must fix before end-to-end testing is possible)

### B-1 — OAuth providers not configured in Supabase Dashboard
**Source:** Backend agent — Step 4
**Impact:** Facebook and Google login buttons return error. Auth feature cannot be tested.
**Action required by human:**
1. Supabase Dashboard → Authentication → Providers → **Facebook**
   - Enable Facebook provider
   - Paste App ID + App Secret from Meta Developer Console
   - Meta redirect URI to whitelist: `https://lzhiqnxfveqttsujebiv.supabase.co/auth/v1/callback`
2. Supabase Dashboard → Authentication → Providers → **Google**
   - Enable Google provider
   - Paste Client ID + Client Secret from Google Cloud Console → OAuth 2.0 → Web client
   - Google redirect URI to whitelist: `https://lzhiqnxfveqttsujebiv.supabase.co/auth/v1/callback`
3. Supabase Dashboard → Authentication → **URL Configuration**
   - Site URL: `https://getviews.vn` (or staging preview URL)
   - Additional redirect URLs: `https://lzhiqnxfveqttsujebiv.supabase.co/auth/v1/callback`

---

## NON-BLOCKING (fix before production deploy, not required for local dev)

### N-1 — Migration history chunk names vs local files
**Source:** Backend agent
**Impact:** `supabase migration list` output may show additional chunk names from MCP batched applies, out of sync with the 6 local `.sql` files. Does not affect remote DB state — tables and RLS are correctly applied. Cosmetic mismatch in CLI history only.
**Action:** Run `supabase migration repair` or `supabase migration list` to reconcile before first production deploy. No immediate action needed.

### N-3 — Seed data without matching `auth.users` rows
**Source:** Backend agent
**Impact:** `supabase/seed.sql` inserts profile rows that reference fake UUIDs in `auth.users`. These cannot be applied to the remote DB directly (FK constraint on `profiles.id → auth.users.id`). Seed works for local `supabase db reset` (which bypasses auth) but not for remote seeding.
**Action:** For remote testing, create real test users via Supabase Auth (Facebook/Google login in staging), then manually seed data tied to those real UUIDs. Seed SQL is valid for local dev only.

### N-4 — PayOS HMAC signature verification needs validation against live PayOS
**Source:** Backend agent
**Impact:** `payos-webhook` Edge Function uses SHA-256 HMAC on the raw request body. If PayOS signs differently (e.g., sorted keys, different encoding), signatures will fail and all payments will be rejected.
**Action:** Before billing feature launch, test the webhook with a real PayOS sandbox payment. Confirm signature algorithm against [PayOS developer docs](https://payos.vn/docs/tich-hop-cong-thanh-toan/). Update `supabase/functions/payos-webhook/index.ts` if needed.

### N-5 — Hero LCP image missing (`public/og-image.png` + PWA icons)
**Source:** Frontend agent
**Impact:** Landing page has no hero image, reducing visual impact and LCP score. PWA icons referenced in `manifest.json` (`public/icons/icon-192.png`, etc.) do not exist — PWA install will fail silently.
**Action (human):** Create and place:
- `public/og-image.png` (1200×630) — OG share card
- `public/icons/icon-192.png` + `icon-192-maskable.png`
- `public/icons/icon-512.png` + `icon-512-maskable.png`
- `public/screenshots/chat-mobile.png` (390×844, form_factor: "narrow") — for PWA install sheet

### N-8 — Supabase Realtime not enabled on `public.profiles`
**Source:** Auth backend agent (`89dc2ca`)
**Impact:** `useProfile` subscribes to Realtime changes on the `profiles` table to invalidate the TanStack Query cache when profile data changes. If Realtime is not enabled for the table in the Dashboard, the subscription is inert — queries still work but live invalidation does not fire. No error is thrown.
**Action (human):** Supabase Dashboard → Database → Replication → enable `profiles` table for Realtime.
Not required for Wave 1 dev (queries work without it), but needed before any feature that updates the profile (e.g., settings, NicheSelector write-back).

### N-10 — Secrets in `.cursor/mcp.json` accessible in-session
**Source:** Auth backend agent (`89dc2ca`)
**Impact:** The Supabase access token and Vercel token stored in `.cursor/mcp.json` are readable by any agent operating in the workspace session. This is a low risk in a solo dev environment but becomes a concern if the repo is shared or if any agent logs/outputs token values.
**Action:** No immediate action required. Before onboarding team members: rotate tokens and migrate to OS keychain or environment-variable-based MCP auth. `.cursor/mcp.json` is already in `.gitignore`.

### N-11 — `GEMINI_API_KEY` not set in Vercel
**Source:** Chat-core backend agent (`9b8bdd0`)
**Status:** Key set in `.env.local` and `cloud-run/.env`. Text intents will work in local dev.
**Remaining action:** Add to Vercel project before staging deploy: Dashboard → Project → Settings → Environment Variables → `GEMINI_API_KEY`. Also set `GEMINI_SYNTHESIS_MODEL` (defaults to `gemini-3.1-flash-lite-preview`).

### N-12 — `VITE_CLOUD_RUN_API_URL` unset: video intents fall through to `/api/chat`
**Source:** Chat-core QA agent (adversarial check)
**Impact:** When `VITE_CLOUD_RUN_API_URL` is not set in `.env.local`, video intents (video_diagnosis, competitor_profile, own_channel) are sent to `/api/chat` (Vercel Edge text endpoint) instead of Cloud Run. The text endpoint has no video understanding capability — responses will be meaningless or errors.
**Action:** For local video intent testing, deploy the Cloud Run service and set:
```
VITE_CLOUD_RUN_API_URL=https://<your-cloud-run-url>
```
Not blocking for Wave 1 dev if video intents are not being tested. Required before staging demo.

### N-13 — `structured_output` column not yet parsed by ChatScreen
**Source:** Chat-core frontend agent (`df0b02c`) — concern flagged
**Impact:** `api/chat.ts` writes the full Gemini text to `chat_messages.content`. The `structured_output` JSONB column is now populated by the Cloud Run pipeline (Task 3), but `ChatScreen.tsx` still renders `content` as plain text — structured components (DiagnosisRow bars, HookRankingBar widths) show Make's mock data or empty states rather than real data.
**Action:** Update `ChatScreen.tsx` to read from `structured_output` when present (falls back to `content` for plain text intents). Wave 2 enhancement.

### N-19 — `video_corpus` table has no data in remote DB
**Source:** Explore QA agent (`304f866`)
**Impact:** ExploreScreen at `/app/trends` shows the empty state on first load because `video_corpus` has 0 rows in the remote Supabase project. The Cloud Run pipeline populates this table via `ensemble.py` → `analysis_core.py` → R2 upload → Supabase insert.
**Action:** Required before staging demo. Either (a) deploy the Cloud Run pipeline and run a batch ingest, or (b) seed a small set of test rows manually in Supabase Dashboard for early QA. Not blocking for local dev.

### N-20 — `video_corpus.video_url` and `thumbnail_url` are R2 URLs — not signed
**Source:** Explore backend agent (`9f09947`)
**Impact:** `video_url` and `thumbnail_url` in `video_corpus` point to Cloudflare R2 public bucket URLs. If the R2 bucket is set to private, all `<img>` and `<video>` elements in ExploreScreen will 403.
**Action (human):** Confirm R2 bucket (`getviews-corpus`) is set to **public** in Cloudflare dashboard, or implement signed URL generation before production. Not blocking for Wave 2 dev.

### N-21 — Desktop aside `trending_keywords` empty until Cloud Run batch runs
**Source:** Explore QA agent (`304f866`) → Addressed in trends frontend (`b28a9a7`)
**Status:** Desktop `<aside>` shows `trending_keywords` from `niche_intelligence` as pill badges when available. Falls back to "Đang cập nhật…" placeholder when null.
**Remaining:** `trending_keywords` is often empty until Cloud Run batch job runs and refreshes `niche_intelligence`. Full aside content depends on N-19 (Cloud Run deploy).

### N-22 — `niche_intelligence` materialized view not auto-refreshed
**Source:** Trends backend agent (`58a6446`)
**Impact:** `niche_intelligence` is a Postgres materialized view populated by the Cloud Run batch job. It is not scheduled for auto-refresh. Until Cloud Run deploys and runs the batch, the view returns stale or empty rows.
**Action:** Before staging demo — deploy Cloud Run pipeline and set up a Cloud Scheduler job or `pg_cron` to call `REFRESH MATERIALIZED VIEW niche_intelligence` nightly after the batch run.

### N-25 — `PAYOS_CLIENT_ID`, `PAYOS_API_KEY`, `PAYOS_CHECKSUM_KEY` not set in Supabase secrets
**Source:** Billing backend agent (`f62ca14`)
**Impact:** `create-payment` and `payos-webhook` Edge Functions will throw on any payment attempt in staging/production.
**Action (human):** In Supabase Dashboard → Edge Functions → Secrets, set:
```
PAYOS_CLIENT_ID=<from PayOS merchant dashboard>
PAYOS_API_KEY=<from PayOS merchant dashboard>
PAYOS_CHECKSUM_KEY=<from PayOS merchant dashboard>
```
Required before any end-to-end billing test.

### N-26 — `RESEND_API_KEY` not set in Supabase secrets
**Source:** Billing backend agent (`f62ca14`) — `send-email` Edge Function
**Impact:** Receipt emails and expiry reminder emails (cron) will fail silently. Credits are still granted, but users receive no receipt.
**Action (human):** Supabase Dashboard → Edge Functions → Secrets → set `RESEND_API_KEY`. Also verify the `from` address (`noreply@getviews.vn`) is registered as a verified sender in Resend.

### N-27 — CheckoutScreen UI diverges from Make (QR mock removed, VNPay → VietQR)
**Source:** Billing QA agent (`5b1c433`)
**Impact:** Make's `CheckoutScreen.tsx` has a mock QR code block, a VNPay option, and a success confirmation Dialog that were not ported. The ported version uses live PayOS redirect flow (correct for production) but differs visually from Make's mockup.
**Status:** Intentional deviation — the mock QR/VNPay/Dialog in Make is design scaffolding; the real payment flow is PayOS redirect. No functional impact.
**Action:** None for now. If a QR display is needed (for bank transfer), implement when PayOS sandbox credentials are available.

### N-29 — PaymentSuccessScreen: state missing `creditsDelta` edge case
**Source:** Billing QA agent (`5b1c433`) — Pass 4 finding
**Impact:** If navigated without `creditsDelta`, the heading uses `profile.deep_credits_remaining` (total) instead of the delta — can show "Đã thêm 40 deep credits" when only 10 were added.
**Status:** Low risk — PayOS return URL redirect loses all state, so the screen already falls back to copy that doesn't show a count. Deferred to post-billing when wiring PayOS webhook Realtime callback.

### N-30 — `useUpdateProfile` optimistic update skips when profile not yet cached
**Source:** Settings QA agent (`8086be5`)
**Impact:** Extremely rare: if the user changes their niche before the first `useProfile` query resolves, the optimistic update is skipped — the UI shows the old chip until the server responds.
**Status:** Deferred. SettingsScreen renders the niche selector only after profile loads, so this is virtually never triggered.

### N-31 — No Vitest coverage for settings flows (logout dialog, niche change)
**Source:** Settings QA agent (`8086be5`)
**Action:** Add 3–4 regression tests: `logout dialog confirm/cancel`, `useUpdateProfile optimistic rollback on error`, `SettingsScreen free-tier vs paid-tier copy`. Low priority.

### N-32 — pg_cron not enabled on `lzhiqnxfveqttsujebiv` — cron jobs not scheduled
**Source:** Email-cron backend agent (`31a2b70`) + QA agent (`54568ab`)
**Impact:** All four cron functions will never fire automatically. Subscriptions will not auto-expire, free query counts won't reset, webhooks won't be pruned, and stuck `is_processing` flags won't clear.
**Action (human):** Before staging deploy — Supabase Dashboard → Database → Extensions → enable `pg_cron`. Then Dashboard → Database → Cron Jobs → create 4 jobs:
- `cron-expiry-check`: `0 2 * * *` (9AM ICT)
- `cron-reset-free-queries`: `0 17 * * *` (midnight ICT)
- `cron-prune-webhooks`: `0 20 * * 0` (Sunday 3AM ICT)
- `cron-reset-processing`: `*/5 * * * *` (every 5 min)
Each job must include `Authorization: Bearer <SUPABASE_SERVICE_ROLE_KEY>` header.

### N-33 — Live invocation of cron + email functions not yet verified
**Source:** Email-cron QA agent (`54568ab`)
**Impact:** Functions have not been invoked end-to-end. Verification of Resend delivery, subscription expiry logic, and reminder email formatting requires deployed Edge Functions + `RESEND_API_KEY` secret set.
**Action:** After deploy — run `supabase functions invoke cron-expiry-check --project-ref lzhiqnxfveqttsujebiv` and verify response JSON + check Resend dashboard. Repeat for each cron function.

### N-38 — Cloud Run in-process session store not shared across instances
**Source:** Cloud Run audit (`2f3f32e`)
**Impact:** `session_store.py` uses a Python dict (in-process). If Cloud Run scales to >1 instance, a reconnect replay on a different instance returns cache-miss and re-runs the full pipeline — duplicate Gemini + EnsembleData costs. Cross-request session context won't accumulate across instances.
**Action:** Before scaling Cloud Run above 1 instance — replace the in-process store with a Redis or Firestore session backend, or set `--max-instances=1` in `deploy.sh`. Currently `deploy.sh` already uses `--max-instances=5` — keep at `--max-instances=1` for MVP.

### N-39 — Cloud Run needs `SUPABASE_URL` + `SUPABASE_ANON_KEY` env vars before GCP deploy
**Source:** Cloud Run audit (`2f3f32e`) → Partially updated by Tasks 2–3
**Impact:** The `/stream` endpoint now uses `user_supabase(access_token)` (RLS-scoped, anon key) — not service role. `SUPABASE_ANON_KEY` must be set in Cloud Run env vars for `user_supabase()` to build the client. `SUPABASE_URL` is also required.
**Action:** Before deploying to GCP Cloud Run — set via `gcloud run services update` or Cloud Run console:
```
SUPABASE_URL=https://lzhiqnxfveqttsujebiv.supabase.co
SUPABASE_ANON_KEY=<same as VITE_SUPABASE_PUBLISHABLE_KEY>
```
Note: `SUPABASE_SERVICE_ROLE_KEY` is no longer required for the `/stream` handler (removed in Task 3). It is still needed if service-role operations are added in future.

---

## DEFERRED (Wave 2 or later)

| Item | When needed | Notes |
|---|---|---|
| ZaloPay in CheckoutScreen | Before billing launch | Gated behind `VITE_ZALOPAY_ENABLED=true`; PayOS must confirm ZaloPay support |
| PWA screenshots in `manifest.json` | Before production deploy | `screenshots` array is empty — add after real screens are built |
| Monday weekly email Edge Function | Post Wave 2 | Content generation deferred; not in current cron suite |
| Cloud Run service deploy to GCP | Before staging video demo (see N-12) | Python pipeline in `cloud-run/` is local only; video intents fall back to text endpoint until deployed |
| PayOS Realtime webhook → in-app payment detection | Post-billing | Currently relies on PayOS redirect + page reload; no in-app detection |
| `own_channel` true account audit (`@handle` + `fetch_user_posts`) | Post MVP | Current impl routes to `run_video_diagnosis` with user-supplied URL — correct for MVP. Full "Soi Kênh" needs `ensemble.fetch_user_posts()` pipeline. |
| `structured_output` rendering in ChatScreen (N-13) | Wave 2 | Cloud Run now writes `structured_output`; ChatScreen still renders plain text |
| Redis/Firestore session store for Cloud Run (N-38) | Before scaling >1 instance | In-process dict is fine for `--max-instances=1` |

---

## Summary

| Priority | Count | Items |
|---|---|---|
| BLOCKING | 1 | B-1 (OAuth config) |
| NON-BLOCKING | 19 | N-1, N-3, N-4, N-5, N-8, N-10, N-11, N-12, N-13, N-19, N-20, N-21, N-22, N-25, N-26, N-27, N-29, N-30, N-31, N-32, N-33, N-38, N-39 |
| DEFERRED | 8 | Post Wave 2 (including N-13, N-37 full impl, N-38 full impl) |

**Staging deploy gates (human action required):**
1. **B-1** — Configure Google + Facebook OAuth providers in Supabase Dashboard
2. **N-25** — Set `PAYOS_CLIENT_ID`, `PAYOS_API_KEY`, `PAYOS_CHECKSUM_KEY` in Supabase Edge Function secrets
3. **N-26** — Set `RESEND_API_KEY` in Supabase Edge Function secrets + verify sender in Resend
4. **N-32** — Enable pg_cron in Supabase Dashboard → configure 4 cron jobs pointing to deployed Edge Function URLs
5. **N-39** — Set `SUPABASE_URL` + `SUPABASE_ANON_KEY` as Cloud Run environment variables before GCP deploy
