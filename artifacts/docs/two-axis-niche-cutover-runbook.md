# Two-axis niche cutover (PR1 → PR6)

> **STATUS: COMPLETED — 2026-05-13.** All four migrations applied. Cloud Run and FE deployed with `creator_niche_id`. `primary_niche` column dropped. Retain this doc until 2026-06-13 (30-day window per `legacy_niche_id_for_creator_niche` retention rule).

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

---

## Part B — HI-11: Two-axis niche resolver (shadow → `route`)

> **Plan cross-ref:** In the pipeline audit remediation plan, this work is also called **Phase 7 — Gemini-driven classification (HI-9 + HI-11)**.

**Scope:** Batch corpus ingest (`corpus_ingest.py`) chooses how `video_corpus.niche_id` and `content_class_id` are written when Gemini HI-9 `niche_classification` is present. This is **independent** of the PR1–PR6 column cutover above; migrations `20260516120000_video_corpus_niche_resolution_shadow.sql` and RPC `20260719000001_upsert_corpus_niche_resolution_shadow.sql` add shadow/telemetry columns.

### Code reference (single source of truth)

| Piece | Location |
|-------|-----------|
| Env flag | `NICHE_RESOLVER_MODE=shadow\|route` (default **shadow** if unset/invalid) — `cloud-run/getviews_pipeline/config.py` |
| Shadow telemetry | `_niche_resolution_shadow_fields` — `corpus_ingest.py` |
| Route override | `_route_niche_and_class_override` + `content_class_id_override` in `_build_corpus_row` — `corpus_ingest.py` |
| Junction lookup | `junction_content_class.content_class_id_for_creator_niche_format` |
| Confidence floor | `_GEMINI_NICHE_CONFIDENCE_FLOOR = 0.6` |

- **`shadow`:** Hashtag resolver stays canonical for `niche_id` / ladder-filled `content_class_id`. Rows still get `niche_resolution_source`, `niche_resolution_confidence`, `inferred_creator_niche_id` for observability. Cloud Logging: `niche shadow disagree` when Gemini’s legacy niche would differ from the hashtag pick.
- **`route`:** If confidence ≥ 0.6, slug maps to a creator niche, `junction_has_pair` passes, and junction returns a row → write **representative legacy** `niche_id` and **junction** `content_class_id` (ladder bypassed for that row). Otherwise same as hashtag path.

### Phase 1 — Shadow observation (calendar: 3–7 days)

1. Confirm **batch** Cloud Run has `NICHE_RESOLVER_MODE=shadow` (or unset). User pod only matters if it ever batch-writes `video_corpus` with the same path — keep aligned with batch.
2. Run daily SQL in Supabase (SQL editor or admin):

**Ingest volume by resolution source (rolling 24h):**

```sql
SELECT
  niche_resolution_source,
  COUNT(*) AS n,
  ROUND(AVG(niche_resolution_confidence)::numeric, 3) AS avg_conf
FROM video_corpus
WHERE indexed_at > now() - interval '24 hours'
GROUP BY 1
ORDER BY n DESC;
```

**Recent Gemini-tagged rows (spot-check sample):**

```sql
SELECT
  video_id,
  niche_id,
  content_class_id,
  niche_resolution_source,
  niche_resolution_confidence,
  inferred_creator_niche_id,
  indexed_at
FROM video_corpus
WHERE niche_resolution_source = 'gemini_two_axis'
ORDER BY indexed_at DESC
LIMIT 50;
```

3. In **GCP Cloud Logging** (batch service), watch for:
   - `[corpus] niche shadow disagree` — expected occasionally; high burst ⇒ review hashtag map vs Gemini.
   - `[corpus] junction miss` — junction seed out of sync with `two_axis_taxonomy.JUNCTION_NICHE_FORMAT_PAIRS`; add migration rows before flipping to `route`.

### Phase 2 — Manual 100-row audit (human gate)

Before `route` in production:

1. Draw a stratified sample of **100** recent rows (mix of `gemini_two_axis` and `hashtag` / `default` as available).
2. For each row, label against TikTok caption + hook + known content: **`agree`** | **`gemini_better`** | **`legacy_better`** | **`both_wrong`**.
3. **Sign-off threshold (plan):** `(agree + gemini_better) / 100 ≥ 0.8`.

If the gate fails, do **not** flip; tune junction, prompts, or threshold in code only via a reviewed change (today: `_GEMINI_NICHE_CONFIDENCE_FLOOR` in `corpus_ingest.py`).

### Phase 3 — Routing flip + post-flip hygiene

1. Set **`NICHE_RESOLVER_MODE=route`** on **batch** Cloud Run (and user pod if it shares ingest). Deploy.
2. **Revert:** set `shadow`, redeploy — no migration required.
3. **Immediately after flip (plan deploy gate):**
   - `SELECT public.refresh_niche_intelligence();`
   - `SELECT public.refresh_content_class_intelligence();`
4. Ensure **`hook_effectiveness_compute`** runs once after MV refresh (or wait for the next batch job that invokes it).
5. **ME-17:** Enable legacy-row classification backfill — ``POST /admin/backfill-classification`` (JWT) or ``POST /batch/backfill-classification`` (cron, `X-Batch-Secret`); pg_cron ``cron-backfill-classification`` at 04:00 UTC (`20260720000000_cron_batch_backfill_classification.sql`). See `getviews_pipeline/classification_backfill.py`.

### QA / tests

- `cloud-run/tests/test_hi11_route_niche_resolution.py`
- `cloud-run/tests/test_corpus_ingest_junction_warn.py`
- Baseline: `artifacts/qa-reports/hi11-baseline.json` (**PASS_WITH_CONCERNS** — full plan still expects extended calendar + flip executed in prod).

---

## ME-18 appendix — Carousel share vs trending (investigation SQL)

Use this after HI-16 / per-niche carousel caps land to see whether the **corpus** mix matches **real** carousel prevalence. Under-sampling shows up as corpus `carousel_pct` materially below trending `carousel_pct` for the same niche bucket.

### 1) Corpus: carousel share per legacy niche (last 14 days)

```sql
SELECT
  n.name_vn,
  COUNT(*) FILTER (WHERE vc.content_type = 'carousel') AS carousels,
  COUNT(*) FILTER (WHERE vc.content_type = 'video') AS videos,
  ROUND(
    COUNT(*) FILTER (WHERE vc.content_type = 'carousel') * 100.0 / NULLIF(COUNT(*), 0),
    2
  ) AS carousel_pct
FROM video_corpus vc
JOIN niche_taxonomy n ON vc.niche_id = n.id
WHERE vc.indexed_at > now() - interval '14 days'
GROUP BY n.name_vn
ORDER BY carousel_pct DESC;
```

### 2) EnsembleData / trending (manual operator step)

The plan cross-check is **not** a SQL report: pull a **sample** of trending posts for each niche (e.g. top 100 by momentum from your ingest keyword / trending source), classify each item as **carousel vs video** from post metadata (image-post / photo album vs short video), and compute `carousel_pct` of that sample. Compare to §1: where corpus `carousel_pct` is **several points lower** than trending `carousel_pct`, raise `BATCH_CAROUSELS_BY_NICHE` for that niche (see `settings.batch_carousels_by_niche` + `corpus_ingest._carousels_per_night_for_niche`). Re-run after 14 days until corpus and trending are within the plan tolerance (±3pp).
