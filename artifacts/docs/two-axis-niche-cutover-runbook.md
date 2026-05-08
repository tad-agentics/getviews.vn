# Two-axis niche cutover (PR1 → PR6)

## Verified migration chain (2026-05-10 — 2026-05-13)

| Step | File | Date (UTC prefix) |
|------|------|-------------------|
| PR1 schema | `supabase/migrations/20260510000004_two_axis_niche_pr1_schema.sql` | May 10 |
| PR2 corpus | `supabase/migrations/20260511000000_two_axis_niche_pr2_corpus.sql` | May 11 |
| PR3 profile | `supabase/migrations/20260512000002_two_axis_niche_pr3_profile.sql` | May 12 |
| PR6 drop legacy column | `supabase/migrations/20260513000001_two_axis_niche_pr6_drop_primary_niche.sql` | May 13 |

PR3 adds and backfills `profiles.creator_niche_id` while keeping `profiles.primary_niche`. PR6 runs `ALTER TABLE profiles DROP COLUMN primary_niche` — **data in that column is gone** unless you restore from backup.

## Cloud Run / FE contract (PR5 / PR6)

Before **any** database client runs PR6:

- Profile reads must use **`creator_niche_id`** only (PostgREST `select=` must not list `primary_niche`).
- Legacy analysis still filters `video_corpus.niche_id`; resolve UX bucket → representative taxonomy id with:
  - **Python:** `getviews_pipeline.profile_niches.legacy_niche_id_for_creator_niche()` / `resolve_legacy_niche_from_profile_row()`
  - **TypeScript:** `legacyNicheIdForCreatorNiche()` in `src/lib/profileNiches.ts`  
  The dict/switch **must stay identical** across languages.

Smoke check on the deployed revision: `GET /health` exposes `morning_ritual_profile_select`; it must be the constant from `morning_ritual.PROFILE_SELECT_RITUAL_BATCH` (no `primary_niche`).

## Deploy order (safe)

**Do not** apply PR6 while an old revision that `select`s `primary_niche` still serves traffic.

Recommended:

1. Apply **PR1, PR2, PR3** (`supabase db push` through `20260512000002_*`).
2. **Deploy** Cloud Run (user + batch) and the Vercel app build that only rely on `creator_niche_id` for profile niche (PR5-style paths: `deps.py`, `morning_ritual.py`, `channel_analyze.py`, `routers/video.py`, etc.).
3. Smoke-test profile/niche flows against **pre-PR6** DB (both columns may still exist).
4. Apply **PR6** (`20260513000001_*`).
5. Follow-up migrations (e.g. `20260630000002_*` trigger cleanup) as needed.

**Risk:** If PR6 runs while old pods still query `primary_niche`, PostgREST returns errors for profile reads until new pods take over. Minimize the window (pre-built revision, fast rollout) or use the sequence above.

## “All migrations first, then deploy”

That ordering is only safe if **no** service hits the DB between PR6 completion and the new revision taking 100% traffic (maintenance mode / blue-green with instant cutover). The default staging path is **PR1–PR3 → deploy PR5-capable images → PR6**.

## `legacy_niche_id_for_creator_niche` retention

Keep this mapping for at least **30 days after PR6** (stability window). Longer term it stays until analysis pipelines pivot off `video_corpus.niche_id` / representative legacy id (see `CLAUDE.md` niche section). Removing it early breaks `/home/*`, `/channel/*`, batch jobs, and any code path that still filters corpus by legacy `niche_id`.

## Related cleanup (not part of the four-migration chain)

- `supabase/migrations/20260630000002_drop_primary_niche_sync_trigger_pr6.sql` — removes stray `primary_niche` sync trigger/function if still present.
