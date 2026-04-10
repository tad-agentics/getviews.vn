# Foundation Concerns
> Logged: 2026-04-09 | Source: Backend `f83aa55` + Frontend `81b99f2`
> Status: OPEN — resolve before Wave 1 features are deployed to staging

---

## BLOCKING (must fix before auth / chat-core can function)

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

### N-2 — `database.types.ts` is a stub, not fully generated
**Source:** Backend agent
**Impact:** TypeScript will not catch type mismatches between code and actual DB schema. Feature agents use `api-types.ts` (manually maintained) for now — this is sufficient for Wave 1 dev.
**Action:** After confirming remote schema is clean, run:
```bash
npx supabase gen types typescript --project-id lzhiqnxfveqttsujebiv > src/lib/database.types.ts
```
Do this before the first QA pass.

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

### N-6 — `AppLayout.tsx` uses mock data
**Source:** Frontend agent
**Impact:** `AppLayout` (BottomNav, header, credit display) still renders mock profile/session data. This is intentional — it will be replaced when `chat-core` feature wires `useProfile()` and `useAuth()`. No action until chat-core is dispatched.
**Action:** Resolved automatically during `/feature chat-core` dispatch.

### N-7 — `SUPABASE_JWT_SECRET` not yet set in `.env.local`
**Source:** Setup pre-flight
**Impact:** Cloud Run Python service (`cloud-run/getviews_pipeline/`) cannot validate user JWTs for the SSE `/stream` endpoint. Video intents (①③④) will fail auth check.
**Action:** Supabase Dashboard → Settings → API → **JWT Settings** → copy JWT Secret → add to `.env.local`:
```
SUPABASE_JWT_SECRET=<your-jwt-secret>
```
Also add to Cloud Run service env vars in GCP when deploying. Not needed until `chat-core` feature is deployed.

---

## DEFERRED (Wave 2 or later)

| Item | When needed | Notes |
|---|---|---|
| ZaloPay in CheckoutScreen | Before billing launch | Confirm PayOS supports ZaloPay; currently UI shows icon but backend not wired |
| PWA screenshots in `manifest.json` | Before production deploy | `screenshots` array is empty — add after real screens are built |
| Monday weekly email Edge Function | Wave 2 | Content generation deferred; cron + template scaffolded |
| Cloud Run service deploy to GCP | Before chat-core (video intents) | Python pipeline in `cloud-run/` is local only |
| `GEMINI_API_KEY`, `PAYOS_*`, `RESEND_API_KEY` in Supabase secrets | Before respective features land | Edge Functions will fail without these secrets |

---

## Summary

| Priority | Count | Items |
|---|---|---|
| BLOCKING | 1 | B-1 (OAuth config) |
| NON-BLOCKING | 7 | N-1 through N-7 |
| DEFERRED | 5 | Wave 2+ |

**Minimum to proceed with Wave 1 local dev:** None — all concerns are non-blocking for local development. OAuth (B-1) is required to test auth flow end-to-end.
