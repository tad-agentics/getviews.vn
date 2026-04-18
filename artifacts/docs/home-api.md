# Home API

The three read-only endpoints that feed the redesigned Home screen (Phase A · A1).
All are JWT-gated via the same `require_user` pattern as `/stream`.

Implementations:

- `cloud-run/getviews_pipeline/pulse.py`
- `cloud-run/getviews_pipeline/ticker.py`
- `cloud-run/main.py` (endpoint wiring)
- `supabase/migrations/20260423000049_phase_a_reference_channels.sql`

All three resolve the caller's niche from `profiles.niche_id`. If the user
hasn't completed onboarding step 1, the endpoint 404s with a Vietnamese
"chưa chọn ngách" message — the frontend should route to onboarding rather
than retry.

---

## `GET /home/pulse`

Feeds the design's **PulseCard** — the big views bignum + delta + four
supporting stats that opens the Home screen.

### Response

```json
{
  "niche_id": 4,
  "views_this_week": 42_800_000,
  "views_last_week": 36_100_000,
  "views_delta_pct": 18.6,
  "videos_this_week": 47,
  "new_creators_this_week": 9,
  "viral_count_this_week": 6,
  "new_hooks_this_week": 3,
  "top_hook_name": "POV: mở chiếc hộp này",
  "adequacy": "niche_norms",
  "as_of": "2026-04-23T02:10:00+00:00"
}
```

### Fields

| Field | Shape |
|---|---|
| `views_this_week` / `views_last_week` | `int` — sum of `video_corpus.views` for the 7-day window / the preceding 7 days |
| `views_delta_pct` | `float` — rounded to 1 dp; **0.0 when `views_last_week == 0`** (UI renders "—" for that case) |
| `videos_this_week` | `int` — count of rows in `video_corpus` for the niche in the last 7d |
| `new_creators_this_week` | `int` — distinct `creator_handle` values this week minus distinct handles last week |
| `viral_count_this_week` | `int` — videos with `breakout_multiplier >= VIRAL_BREAKOUT_THRESHOLD` (3.0) |
| `new_hooks_this_week` | `int` — active `video_patterns` whose `niche_spread` contains `niche_id` and whose `last_seen_at` is within 7d |
| `top_hook_name` | `str \| null` — display_name of the pattern with highest `weekly_instance_count` among the above |
| `adequacy` | `str` — claim-tier name (`none` / `reference_pool` / `basic_citation` / `niche_norms` / `hook_effectiveness` / `trend_delta`). Drives the UI's "soft state" when the corpus is thin; see `claim_tiers.py` |
| `as_of` | ISO-8601 timestamp of computation |

### UX guidance

- When `adequacy == "none"`, hide deltas and show a "ngách đang thưa" state.
- When `views_last_week == 0`, render "—" for the delta chip, not "0%".
- Cache for 1h on the client; the aggregator hits Supabase on every call so
  server-side caching is the right layer to add if traffic grows.

---

## `GET /home/ticker`

Feeds the marquee ticker at the top of the Home screen. Five buckets, ≤ 2
items per bucket, 7-day window, round-robin-interleaved so the marquee reads
mixed not clumped.

### Response

```json
{
  "niche_id": 4,
  "items": [
    {
      "bucket": "breakout",
      "label_vi": "BREAKOUT",
      "headline_vi": "@pxtho · 5M views · 3.4× trung bình kênh",
      "target_kind": "video",
      "target_id": "7312..."
    },
    {
      "bucket": "hook_mới",
      "label_vi": "HOOK MỚI",
      "headline_vi": "\"POV: mở chiếc hộp này\" · 42 video tuần này",
      "target_kind": "pattern",
      "target_id": "b3e1..."
    }
  ]
}
```

### Buckets

| Bucket key | Label | Source |
|---|---|---|
| `breakout` | `BREAKOUT` | Top 2 `video_corpus` rows by `breakout_multiplier ≥ 2.0` this week |
| `hook_mới` | `HOOK MỚI` | Top 2 `video_patterns` by `weekly_instance_count` that **entered** the niche this week (`first_seen_at ≥ now-7d`) |
| `cảnh_báo` | `CẢNH BÁO` | Top 2 patterns where `weekly_instance_count` dropped ≥ 40% vs `weekly_instance_count_prev`, with prev ≥ 10 (`PATTERN_SPREAD_MIN_INSTANCES`) |
| `kol_nổi` | `KOL NỔI` | Creators whose in-niche max `breakout_multiplier ≥ 2.0` this week, ranked by max-BM then total views |
| `âm_thanh` | `ÂM THANH` | Top 2 `trending_sounds` rows from the most recent `week_of` in the niche |

### Fail-open contract

Each bucket runs in a separate executor task; an exception in one leaves the
other four intact. Worst case the endpoint returns an empty `items` array —
the UI is expected to handle that (hide the ticker) rather than show an error.

### UX guidance

- The marquee should hide entirely when `items.length < 3` — a sparse ticker
  is worse than no ticker.
- `target_kind` maps to a route: `video` → video-diagnosis, `creator` →
  channel analysis, `pattern` → patterns tile on Explore, `sound` →
  trending-sounds view. `target_id` is the primary key for that record.

---

## `GET /home/starter-creators`

Feeds onboarding step 2 — the list of 10 creators from which the user picks
1–3 "kênh tham chiếu" (reference channels).

### Response

```json
{
  "niche_id": 4,
  "creators": [
    {
      "handle": "pxtho",
      "display_name": null,
      "followers": 1_240_000,
      "avg_views": 220_000,
      "video_count": 18,
      "rank": 1
    }
  ]
}
```

### Seeding

Rows are produced by the `seed_starter_creators(p_top_n := 10)` RPC, which
aggregates `video_corpus` by `(niche_id, creator_handle)` and ranks within
each niche by follower count (tiebreak: video count). The one-shot seed
runs in the migration itself; re-running is safe and will not overwrite
rows flagged `is_curated = TRUE` (the hook for future manual curation from
Settings).

### UX guidance

- A creator may have `display_name = NULL` (corpus doesn't guarantee one);
  fall back to `@handle` in the UI.
- Enforce the 1–3 selection cap client-side; `profiles.reference_channel_handles`
  has a CHECK constraint that rejects writes of length > 3.

---

## Writing back — `profiles.reference_channel_handles`

Not a new endpoint. The frontend writes directly to the `profiles` row via
Supabase's existing RLS-scoped update:

```ts
await supabase
  .from("profiles")
  .update({ reference_channel_handles: ["pxtho", "linhka", "hungvlog"] })
  .eq("id", user.id);
```

Schema constraints:

- `reference_channel_handles TEXT[] NOT NULL DEFAULT '{}'`
- `CHECK (cardinality(reference_channel_handles) <= 3)`
- GIN index on the array for per-handle membership queries later
  (e.g. "users who track @pxtho").

---

## Checklist for adding a new Home tile

If Phase B or C adds another Home tile, follow the same pattern:

1. Write a pure aggregator in `getviews_pipeline/` taking `(client, niche_id)`
   and returning a frozen dataclass with `.to_json()`.
2. Wire a `GET /home/<tile>` endpoint that resolves the caller's niche and
   delegates to the aggregator. Re-use `_resolve_caller_niche_id`.
3. Integrate `claim_tiers.flags_for_count()` into the payload when the tile
   makes statistical claims — match the `adequacy` pattern on `PulseStats`.
4. Add a fake-client pytest like `test_pulse.py` — no network, no asyncio
   plumbing unless the tile itself uses `asyncio.gather`.
5. Document the shape in this file.
