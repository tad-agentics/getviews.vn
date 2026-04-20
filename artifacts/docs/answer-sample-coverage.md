# Answer sample coverage (Phase C.0.3)

**Purpose:** Per-niche corpus density vs §C.0.3 floors before adaptive window policy.

## Floors (from phase-c-plan)

| Format | `sample_size` floor | Below floor |
|--------|---------------------|-------------|
| Pattern | 30 | HumilityBanner; thin TL;DR + evidence only |
| Ideas | 60 | HumilityBanner; 3 blocks; skip StopDoing |
| Timing | 80 | HumilityBanner; hide cells &lt; 5; top-3 list only |
| Generic | n/a | OffTaxonomyBanner; shorter narrative |

## Adaptive policy

1. Prefer **7d** window; if below Pattern floor, widen to **14d** automatically.
2. If still thin after 14d, degrade narrative to **Generic** or exclude niche from `/answer` until corpus catches up (product decision per deploy).

## Data sources

- `niche_intelligence` (materialized / refreshed)
- `video_corpus`
- `corpus_hashtag_yields_14d()` — see migration `20260429180000_corpus_hashtag_yields_rpc.sql`

## Niche × format table

| niche_id | label | 7d_n | 14d_n | Pattern_ok | Ideas_ok | Timing_ok | Notes |
|----------|-------|------|-------|------------|----------|-----------|-------|
| *TBD* | — | — | — | — | — | — | Populate via SQL audit job pre-C.2 |

> **Stub:** Run `SELECT` aggregations per active niche before C.2 ship; this document is the checklist location.
