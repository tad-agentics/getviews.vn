# Morning Ritual

Three ready-to-shoot TikTok scripts per **followed niche** (up to three niches per
profile from `profiles.niche_ids`, else `primary_niche`), generated in batch
and stored in `daily_ritual`.

This is the hero feature of the Home screen tier **01** (“3 video tiếp theo bạn
nên làm”). The UI is `HomeSuggestionsToday` + `StudioHero` +
`useDailyRitual`.

Implementations:

- `cloud-run/getviews_pipeline/morning_ritual.py` — `run_morning_ritual_batch`
- `supabase/migrations/20260423000050_daily_ritual.sql` (PK extended in
  `20260629000000_ritual_per_niche_and_sync_primary.sql`)
- `GET /home/daily-ritual` · `POST /batch/morning-ritual` ·
  `POST /admin/trigger/morning_ritual`
- `src/hooks/useDailyRitual.ts`

## Why

“Mở app ra, biết hôm nay quay gì” is the main creator shortcut. Pulse, ticker,
and Kênh tham chiếu are supporting context for the ritual.

## Schema

Each row in `daily_ritual` (one per **user + UTC date + niche**):

```
user_id UUID
generated_for_date DATE   -- UTC
niche_id INTEGER
scripts JSONB              -- 3 × RitualScript
adequacy TEXT
grounded_video_ids TEXT[]
generated_at TIMESTAMPTZ
PRIMARY KEY (user_id, generated_for_date, niche_id)
```

`GET /home/daily-ritual?niche_id=` returns the row for the caller and resolved
niche (see `resolve_home_niche_id`).

## Generation flow

(See `morning_ritual.py` for full detail: grounding ladder → Gemini
`RitualBundle` → `upsert` with `on_conflict=user_id,generated_for_date,niche_id`.)

## Endpoints

### `GET /home/daily-ritual` (user JWT)

404 + `{ "code": "ritual_no_row" | "ritual_niche_stale" }` when missing / mismatch.

### `POST /batch/morning-ritual` (`X-Batch-Secret`)

Nightly / on-demand batch. Body:

```json
{}
```

or

```json
{ "user_ids": null }
```

= **all users** with a niche, **each (user, followed niche slot)** up to 3
niches. For smoke tests:

```json
{ "user_ids": ["<uuid-1>"] }
```

Response includes `generated`, `skipped_thin`, `failed_*`, `users_no_niche`.

### `POST /admin/trigger/morning_ritual` (user JWT + `profiles.is_admin`)

**Manual full or partial run** — same Python entrypoint as
`/batch/morning-ritual`, but authenticated as an admin user (no batch secret).

- `{}` or `{ "user_ids": null }` — **mọi user** × **mỗi ngách đang follow** (tối
  đa 3 ngách / profile), khớp cron.
- `{ "user_ids": ["<uuid>"] }` — chỉ những profile đó (vẫn lặp từng
  `niche_ids` slot).

```bash
curl -sS -X POST "https://<cloud-run>/admin/trigger/morning_ritual" \
  -H "Authorization: Bearer <admin_supabase_jwt>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Schedules (keep these aligned)

1. **GCP Cloud Scheduler (recommended in `deploy.sh`)**  
   - `getviews-morning-ritual`: `0 22 * * *`, time zone
     `Asia/Ho_Chi_Minh` — **22:00 VN** (scripts ready before the next
     morning).  
   - `POST` …`/batch/morning-ritual` with header `X-Batch-Secret: <BATCH_SECRET>`,
     body `{}`.

2. **Supabase pg_cron** (`20260526000000_pg_cron_morning_ritual_scene_intel.sql`)  
   - Example job uses **UTC** cron; if both GCP and Supabase call the same URL,
     **do not** double-charge: disable one or stagger.

Document whichever is active in the Supabase / GCP console after deploy.

## UI integration

`StudioHero` lists `ritual.scripts` (3 rows). `useDailyRitual` requires
`nicheId` and `VITE_CLOUD_RUN_API_URL`.

## Cost

Roughly **one Gemini synthesis per (user, niche)** in the batch run (not
once per user). Budget accordingly when `user_ids` is null.

## Operator fields

| Field | Meaning |
|--------|---------|
| `generated` | Successful upserts |
| `skipped_thin` | Grounding pool < 10 videos |
| `failed_schema` / `failed_gemini` / `failed_duplicate_hooks` | Model / validation |
| `users_no_niche` | No `niche_ids` or `primary_niche` |

## Tests

`cloud-run/tests/test_morning_ritual.py` (grounding ladder, no live Gemini in CI).
