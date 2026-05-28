# Marketing Corpus Pick API

Server-only endpoint for the marketing team: returns one random high-performing TikTok video from the corpus (10 niches, >100k views, weighted priority), runs a **basic / win** video diagnosis, and returns thumbnail + metadata + full analysis.

**Do not call from the browser.** Use a server script or automation with the Supabase **service_role** JWT stored in a secret manager.

## Endpoint

```
POST https://<project-ref>.supabase.co/functions/v1/marketing-corpus-pick
```

### Headers

| Header | Value |
|--------|--------|
| `Authorization` | `Bearer <SUPABASE_SERVICE_ROLE_JWT>` |
| `apikey` | `<SUPABASE_ANON_OR_PUBLISHABLE_KEY>` |
| `Content-Type` | `application/json` |

Body: `{}` (empty JSON object).

### Client timeout

Set **≥ 120 seconds**. Typical latency is **20–40 seconds** (Gemini diagnosis on cache miss).

## Example (curl)

```bash
curl -sS -X POST \
  "https://YOUR_PROJECT.supabase.co/functions/v1/marketing-corpus-pick" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{}' \
  --max-time 120
```

## Success response (200)

```json
{
  "video_id": "7638917857404783890",
  "tiktok_url": "https://www.tiktok.com/@creator/video/7638917857404783890",
  "thumbnail_url": "https://media.getviews.vn/thumbnails/7638917857404783890.webp",
  "creator_handle": "@creator",
  "views": 250000,
  "caption": "...",
  "hook_phrase": "...",
  "creator_niche": {
    "id": 3,
    "slug": "food",
    "name_vn": "Ẩm thực · Ăn uống",
    "priority_weight": 3
  },
  "analysis": {
    "analysis_depth": "basic",
    "mode": "win",
    "narrative_vi": {
      "van_de_chinh": "...",
      "loi_chinh_narrative": [],
      "dinh_huong_chien_luoc": []
    },
    "diagnosis": "...",
    "performance_tier": "hit",
    "hook_phases": [],
    "flop_issues": null,
    "meta": { "creator": "@creator", "views": 250000 }
  },
  "picked_at": "2026-05-28T12:00:00+00:00"
}
```

## Errors

| HTTP | `error` | Meaning |
|------|---------|---------|
| 401 | `Unauthorized` | Missing or invalid service_role JWT |
| 404 | `marketing_pool_exhausted` | No eligible videos left (all picked or filters too tight) |
| 502 | `analysis_failed` | Pipeline did not produce `narrative_vi` — video **not** recorded as picked; safe to retry |
| 502 | `batch_unreachable` | Edge could not reach Cloud Run batch pod |

## Selection rules

- **Views:** `> 100_000`
- **Niches (weighted):** Ẩm thực, Hài, Làm đẹp, Thời trang (weight 3); Gym, Nuôi con (2); BĐS, Kinh doanh, Ô tô, Sức khoẻ (1)
- **Exclusion:** `video_id` never returned before (table `marketing_video_picks`)
- **Analysis:** `run_video_analyze_pipeline` at `basic` depth, `win` mode — same engine as in-app video diagnosis; **no user credits charged**

## Ops / deploy

1. Apply migration `20260901000000_marketing_video_picks.sql`
2. Deploy batch Cloud Run pod (route `POST /batch/marketing-corpus-pick`)
3. Supabase Edge secrets: `CLOUD_RUN_BATCH_URL` (batch service URL), `BATCH_SECRET`, optional `R2_PUBLIC_URL`
4. `supabase functions deploy marketing-corpus-pick`

## Reset pick history (manual)

To allow re-picking videos, delete rows from `marketing_video_picks` via Supabase SQL editor (service role). No admin UI in v1.
