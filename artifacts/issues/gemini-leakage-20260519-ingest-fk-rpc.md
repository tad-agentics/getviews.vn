# Gemini leakage + ingest recovery — 2026-05-19 batch (09:02–09:56 ICT)

## Summary

| Issue | Root cause | Wasted work | Fix |
|-------|------------|-------------|-----|
| **110 `failed`** | `niche_id=26` missing from `niche_taxonomy` (HI-11 route → wellness) | Gemini extraction + R2 upload, **no DB row** | ✅ Repair niche 26 (SQL Editor) |
| **RPC fallback ~18×** | `upsert_video_corpus_batch`: ambiguous `video_id` in PL/pgSQL | Direct upsert bypasses `COALESCE(ingest_source)` | Migration `20260724000001` |
| **37 `skipped`** | Timeout / corrupt video (separate) | Partial Gemini | Tune timeout or accept |

**Important:** Re-ingest via `/batch/reingest-videos` runs **full Gemini again** (~$0.003–0.01/video). There is no stored `analysis_json` to replay from DB.

---

## 1. Gemini API leakage (110 videos)

### What happened

1. Batch analyzed candidates (Gemini vision + optional STT).
2. Uploaded clips/thumbnails to R2 (`video uploaded to R2` logs).
3. Built rows with `niche_id=26` (HI-11 routed to wellness).
4. **Upsert failed** — FK `video_corpus_niche_id_fkey` (26 ∉ `niche_taxonomy`).
5. `result.failed += len(rows)` → **110** counted as failed.

### Confirmed shard sizes (log)

| Niche pool | R2 video clips | Upsert fail time (UTC) | Loop `niche_id` |
|------------|----------------|------------------------|-----------------|
| Education | 50 | 02:14:21 | 11 |
| Fitness | 20 | 02:33:35 | 8 |
| Sports | 40 | 02:46:52 | 21 |

### Estimate leaked spend (SQL Editor)

```sql
SELECT
  COUNT(*) AS calls,
  ROUND(SUM(cost_usd)::numeric, 4) AS usd
FROM gemini_calls
WHERE created_at >= '2026-05-19 02:02:00+00'
  AND created_at <  '2026-05-19 02:57:00+00'
  AND call_site ILIKE '%corpus%'
  AND success = true;
```

Order-of-magnitude: **110 × ~$0.003 ≈ $0.33** extraction only (excluding STT / retries).

### R2

Orphan assets may exist under `videos/{video_id}.mp4`, `frames/`, `thumbnails/` for those IDs. Janitor does not remove “no corpus row” objects automatically.

---

## 2. Recovery — re-ingest 110 videos

### Preconditions

- ✅ `niche_taxonomy.id = 26` exists (repair applied).
- Apply RPC fix (`20260724000001`) so provenance-safe upsert works.
- Have `BATCH_SECRET` and batch service URL.

### Video IDs

Extracted from Cloud Logging (`video uploaded to R2`) in time windows per failed shard.

- **128 unique IDs** in `agent-workspace/temp/reingest_payload_20260519_fk_fail.json` (gitignored)
  - Sports 40, Fitness 20, Education 68 (Education window overlaps parallel niches — trim with SQL below)

### Verify not already in corpus

```sql
-- Paste video_id array from payload or cross-check count
SELECT COUNT(*) AS missing
FROM unnest(ARRAY['7630366484220480776'::text /* , ... */]) AS v(video_id)
WHERE NOT EXISTS (
  SELECT 1 FROM video_corpus vc WHERE vc.video_id = v.video_id
);
```

### Option A — `POST /batch/reingest-videos` (recommended)

Uses **loop pool `niche_id`** (11 / 8 / 21) so Ensemble + hashtag context match original ingest. HI-11 may route to 26 again — now valid.

```bash
curl -sS -X POST "$BATCH_URL/batch/reingest-videos" \
  -H "X-Batch-Secret: $BATCH_SECRET" \
  -H "Content-Type: application/json" \
  -d @agent-workspace/temp/reingest_payload_20260519_fk_fail.json
```

Cap: **500 items/request** (payload has 128 — OK). Expect **~128 more Gemini calls** (~$0.40–1.30).

Set `"refresh_mv": true` once at end (default in payload).

### Option B — `corpus_ingest_queue`

Only if rows were enqueued (live reference path). These FK-fail batch rows were **not** auto-queued. Manual enqueue then drain:

```sql
INSERT INTO corpus_ingest_queue (aweme_id, niche_id, queued_at)
SELECT v.video_id, v.niche_id, now()
FROM (VALUES
  ('7630366484220480776', 11)
  -- ...
) AS v(video_id, niche_id)
ON CONFLICT DO NOTHING;
```

```bash
curl -sS -X POST "$BATCH_URL/batch/process-ingest-queue?limit=200" \
  -H "X-Batch-Secret: $BATCH_SECRET"
```

Same Gemini cost as Option A.

### Option C — Wait

Next nightly ingest may re-pick some URLs if still in hashtag pool and not in `existing_snapshot` — **not guaranteed** for all 110.

---

## 3. RPC `upsert_video_corpus_batch` — ambiguous `video_id`

### Symptom (prod log)

```
upsert_video_corpus_batch RPC failed ({
  'message': 'column reference "video_id" is ambiguous',
  'code': '42702',
  ...
}); falling back to direct upsert — provenance may regress
```

~**18** niche shards hit fallback during the same run (all successful inserts except the 110 FK block).

### Root cause

`20260719000001_upsert_corpus_niche_resolution_shadow.sql` — `RETURNS TABLE (video_id TEXT, action TEXT)` plus:

```sql
video_id := v_video_id;  -- clashes with video_corpus.video_id
```

### Fix

`supabase/migrations/20260724000001_fix_upsert_video_corpus_batch_ambiguous_video_id.sql`

- `#variable_conflict use_variable`
- Output columns → `out_video_id`, `out_action`
- `RETURN QUERY SELECT v_video_id, 'upserted'`

### Apply (SQL Editor if CLI blocked)

Copy migration body into SQL Editor → Run.

### Verify

```sql
SELECT upsert_video_corpus_batch(
  '[{"video_id":"test_rpc_probe","niche_id":11,"content_type":"video",
    "creator_handle":"probe","tiktok_url":"https://example.com",
    "analysis_json":{},"views":1,"likes":0,"comments":0,"shares":0,
    "engagement_rate":0,"ingest_source":"batch_nightly"}]'::jsonb
);
-- expect one row (out_video_id, upserted); then DELETE FROM video_corpus WHERE video_id = 'test_rpc_probe';
```

---

## Sequencing

1. ✅ Niche 26 repair (done via Dashboard)
2. Apply RPC fix migration (`20260724000001`)
3. Confirm RPC probe SQL passes
4. Run reingest payload (128 items; verify `missing` count first)
5. Optional: query `gemini_calls` for total batch-night spend audit
