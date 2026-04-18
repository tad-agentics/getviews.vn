# Corpus health

A single answer to the question "is the corpus thick enough for the claim the
synthesis prompt is about to make?" — served two ways:

- `GET /admin/corpus-health` on the Cloud Run service (JSON, per niche)
- `artifacts/sql/corpus-health.sql` as a bookmarked Supabase SQL Editor query

Both are mirrors of the same thresholds in
`cloud-run/getviews_pipeline/claim_tiers.py` (`CLAIM_TIERS`). If you change a
threshold there, update the SQL too.

## Why

Before viral-pattern-fingerprint / comment-sentiment / thumbnail-analysis
shipped, one global guardrail (`SPARSE_THRESHOLD = 20`) covered every claim
the pipeline made. Those features split the claim surface into tiers with
very different sample requirements — citing a top-5 video list is safe at 5
videos, but citing "42% of top performers open with a face" needs ~30 before
the percentage is anything better than directional.

A per-tier view lets us:

- Keep synthesis prompts from over-claiming on thin niches.
- Watch corpus growth and see when specific niches cross a tier boundary.
- Decide whether to delay a feature launch or ship it gated.

## The tiers

| Tier | Threshold (videos in niche, 30d) | Why |
|------|----------------------------------:|-----|
| `reference_pool`     |   5 | Show 3 references without bottom-scrape |
| `basic_citation`     |  20 | Matches legacy "feels representative" bar |
| `niche_norms`        |  30 | Binary features reach ~±10% precision |
| `hook_effectiveness` |  50 | 14 hook types × ≥5 per bucket (relaxed) |
| `trend_delta`        | 100 | Two 50-video week windows for deltas |

Tiers are strictly nested — passing a higher tier implies the lower ones.
`highest_passing_tier` names the most demanding tier a niche currently
clears; `"none"` means the niche has <5 videos in the last 30 days.

Two extra tiers gate pattern talk instead of niche talk:

| Tier | Threshold | Why |
|------|----------:|-----|
| `pattern_spread`      | 10 instances in the week          | Rule out 2-instance coincidences |
| `cross_niche_spread`  | 10 instances **and** ≥2 niches    | Rule out same-niche duplication |

## JSON endpoint

```
GET /admin/corpus-health
Header: X-Batch-Secret: <BATCH_SECRET env>
```

Response shape:

```json
{
  "ok": true,
  "as_of": "2026-04-18T09:00:00+00:00",
  "summary": {
    "niches_total": 21,
    "videos_7d_total": 87,
    "videos_30d_total": 701,
    "videos_90d_total": 1840,
    "tier_histogram": {
      "none": 0,
      "reference_pool": 2,
      "basic_citation": 4,
      "niche_norms": 12,
      "hook_effectiveness": 3,
      "trend_delta": 0
    }
  },
  "niches": [
    {
      "niche_id": 4,
      "name_en": "food-reviews",
      "name_vn": "Review do an",
      "videos_7d": 6,
      "videos_30d": 48,
      "videos_90d": 132,
      "last_ingest_at": "2026-04-18T02:10:00+00:00",
      "last_pattern_at": "2026-04-17T23:45:00+00:00",
      "claim_tiers": {
        "reference_pool": true,
        "basic_citation": true,
        "niche_norms": true,
        "hook_effectiveness": false,
        "trend_delta": false
      },
      "highest_passing_tier": "niche_norms"
    }
  ]
}
```

Fails open on the `video_patterns` table — if that query blows up,
`last_pattern_at` is simply omitted; the tier computation still works.

## SQL bookmark

`artifacts/sql/corpus-health.sql` is a paste-and-run version of the same view
for the Supabase SQL Editor. Use it when you want a live look without
deploying or when debugging the endpoint itself.

## Operating guidance

- **After a nightly ingest**: glance at `tier_histogram`. If anything dropped
  a tier since yesterday, check `last_ingest_at` — the niche may be starving.
- **Before a synthesis change**: if the change introduces a new claim type,
  pick its tier before writing the prompt, then sanity-check the histogram
  to see how many niches would gate the claim today.
- **When corpus grows**: the tier you're gating at is where you stop seeing
  improvements for "free" — the next tier up is the next target.
