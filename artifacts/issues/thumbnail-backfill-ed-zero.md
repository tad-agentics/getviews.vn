# Thumbnail backfill — `from_ed=0` investigation (2026-05-25)

## Run result (production)

`POST /batch/backfill-thumbnails?ed_fallback=true` (2026-05-25):

| Counter | Value |
|---------|------:|
| `from_frame` | 681 |
| `from_cdn` | 0 |
| `from_ed` | 0 |
| `nulled` | 3,786 |
| `total` | 4,467 |

## Root cause (not a single bug)

### 1. CDN path never ran (`from_cdn=0`)

Step 2 mirrors `thumbnail_url` only when it is a **non-R2** URL. Most candidates had:

- Phantom R2 URLs (`…/thumbnails/{id}.png` in Postgres, object missing on R2) → **skipped**
- Already `NULL` after prior attempts → **skipped**

So ~3,786 rows went straight to ED fallback with no CDN attempt.

### 2. R2 frame path mostly phantom (`from_frame=681`)

HEAD audit on 146/146 sampled `NULL + frame_urls` rows: **0%** live objects at `frames/`, `thumbnails/`, or `videos/`. Ingest wrote `frame_urls` and Gemini `analysis_json` during Apr 27–May 10 spike; R2 bytes did not persist.

### 3. ED fallback (`from_ed=0`) — three failure modes

After code fix (2026-05-25), backfill exposes counters:

- `ed_missing_post` — `fetch_post_multi_info` did not return that `aweme_id` (deleted/private/geo-blocked TikTok)
- `ed_no_cover` — post returned but no extractable cover URL
- `ed_upload_failed` — cover fetched but `download_and_upload_thumbnail` failed (CDN 403, proxy, transcode)

**Prior gap:** `_cover_url_from_ensemble_post` only checked `origin_cover`/`cover`, not `dynamic_cover`/`ai_dynamic_cover` or carousel slides. Fixed via shared `ensemble.cover_url_from_aweme_detail()` (same as `corpus_context.refresh_stale_thumbnails`).

## Remediation shipped

1. **Migration** `20260831000000_clear_phantom_frame_urls.sql` — `frame_urls = '{}'` where `thumbnail_url IS NULL`
2. **`cover_url_from_aweme_detail`** — wider cover field ladder + carousel slide fallback
3. **Backfill telemetry** — `ed_missing_post`, `ed_no_cover`, `ed_upload_failed` in JSON response

## Next ops step

Re-run backfill on null-thumb rows only (after batch redeploy):

```bash
POST /batch/backfill-thumbnails?ed_fallback=true&limit=500
```

Inspect new counters to see whether ED returns posts or upload fails. Full heal for phantom cohort likely requires **re-ingest** (re-download MP4 → frames + WebP), not backfill alone.
