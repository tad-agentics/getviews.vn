# Ops Runbook — GetViews.vn

Created from the 2026-06-10 audit (findings H-1, H-6, M-9). Keep this in sync
with `system-design.md` — this file is the "what do I do at 2am" companion.

## Backup & disaster recovery

- **Database:** Supabase project `lzhiqnxfveqttsujebiv` (ap-southeast-2).
  Daily automated backups on the paid plan; PITR is an upgrade away.
  **Action item (untested):** run a restore drill into a Supabase branch
  project once, document timing here. Until a drill has been done, treat
  restore as unproven.
- **What is rebuildable vs not:**
  - Rebuildable from pipelines: `video_corpus`, MVs, pattern decks, channel
    caches (nightly ingest re-derives them — slowly).
  - **NOT rebuildable:** `profiles`, `subscriptions`, `credit_transactions`,
    `processed_webhook_events`, `answer_sessions`/`answer_turns`. These are
    the customer + money tables — they're the reason backups matter.
- **R2 media:** thumbnails/frames are re-derivable (backfill endpoint +
  re-ingest), no backup needed. Lifecycle: `cron-batch-r2-janitor`
  (Sun 18:00 UTC) prunes orphans; `cron-batch-backfill-thumbnails`
  (Sun 19:00 UTC) re-mirrors anything still referenced.

## Alerting

Bootstrap: `cloud-run/scripts/create-alert-policies.sh` (GCP monitoring
policies: user-pod 5xx spike, `REFUND FAILED` log metric, Gemini budget
blocks). Existing: hourly `cron-pg-net-batch-http-4xx-watch` for cron→Cloud
Run auth breakage. PayOS webhook errors: Supabase Dashboard → Edge Functions
→ payos-webhook → logs (no alert API yet — check after every pricing change
and weekly otherwise).

## pg_cron inventory (source of truth: `SELECT jobname, schedule FROM cron.job`)

As of 2026-06-10, 25 jobs. The schedule lives in the DB, not in migrations —
when adding/changing one, write the migration AND verify `cron.job` matches.
Highlights (UTC):

| Job | Schedule | Purpose |
|---|---|---|
| cron-batch-ingest / -shift-b / -shift-c | 20:00 / 21:30 / 23:00 daily | nightly corpus ingest (3 shifts) |
| cron-batch-post-processing | 23:30 daily | MV heal if shift c aborts |
| cron-batch-backfill-thumbnails | Sun 19:00 | **thumbnail self-heal** (added 2026-06-10) |
| cron-batch-r2-janitor | Sun 18:00 | R2 orphan prune |
| cron-pg-net-batch-http-4xx-watch | hourly :23 | cron auth breakage watch |
| cron-reset-processing | every 5 min | TD-3 stuck-lock sweeper |
| cron-expiry-check / cron-reset-free-queries | 02:00 / 17:00 daily | credit expiry / free quota reset |

Failure triage: `SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 20;`
then `SELECT status_code, content::text FROM net._http_response ORDER BY id DESC LIMIT 20;`
(pg_net responses are where 401/404s hide — `job_run_details` shows success
for a scheduled POST even when the HTTP call failed).

## Thumbnails (root-caused 2026-06-10)

Lifecycle: EnsembleData cover (signed, expiring TikTok CDN URL) → mirrored at
ingest to R2 `thumbnails/{video_id}.webp` → FE candidate cascade
(`src/lib/r2.ts`) → browser `onError` reports to `thumbnail_failures`.

Failure classes and their fixes:
1. **Legacy NULL cohort** (3,649 rows from Apr 20–May 18, pre mirror-at-ingest,
   nulled by the 2026-05-25 manual backfill): healed incrementally by the
   weekly backfill cron retrying fresh ED covers; rows whose source video is
   deleted/private stay NULL by design (FE placeholder).
2. **Phantom R2 URLs** (DB → R2 URL, object missing; 171 browser reports in
   30d): the backfill endpoint HEAD-verifies every R2-prefixed row and
   re-uploads — also now weekly.
3. **r2.dev in production:** `VITE_R2_PUBLIC_URL` / `R2_PUBLIC_URL` point at
   `pub-….r2.dev`, which Cloudflare rate-limits and doesn't CDN-cache.
   **Action item:** attach a custom domain (e.g. `media.getviews.vn`) to the
   bucket in the Cloudflare dashboard, then update both env vars (Vercel +
   both Cloud Run pods) and redeploy. No code change needed.

Monitoring: `SELECT count(*) FROM thumbnail_failures WHERE failed_at > now() - interval '7 days';`
— sustained >50/week means the cron is failing; check `net._http_response`.

## Credits / refunds

`decrement_credit` (user-scoped, subtract-only) runs before paid work;
`refund_credit` (service-role-only, migration 20260902000000) compensates on
failure and writes a `credit_transactions` row with `reason='refund'`.
A logged `REFUND FAILED` line (alert above) means the compensation itself
failed → refund manually:
`SELECT refund_credit('<user_id>', <amount>);` as service role, or via the
admin panel.

## JWT validation (Cloud Run)

Preferred: JWKS (asymmetric) via `SUPABASE_JWKS_URL`-derived endpoint; legacy
fallback `SUPABASE_JWT_SECRET` (HS256). `X-Batch-Secret` header auth on
`/batch/*` is deprecated for removal Q3-2026 (migrate Cloud Scheduler to OIDC
admin JWTs); comparison is timing-safe as of 2026-06-10.

## Deploys

`cloud-run/deploy.sh` now health-gates: probes `/health` on the new revision
for 60s and routes traffic back to the previous revision on failure. Don't
use `SKIP_BUILD=1` with images that haven't passed CI.
