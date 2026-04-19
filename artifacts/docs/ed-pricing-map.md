# EnsembleData — units per endpoint (working map)

**Status:** Placeholder until confirmed against **current** EnsembleData billing docs or dashboard “usage breakdown” export. Tune env vars in [`cloud-run/getviews_pipeline/config.py`](../../cloud-run/getviews_pipeline/config.py) (`ED_UNIT_*`) to match your account.

## Purpose

Convert **HTTP request counts** (from `[ed-meter]` logs) into **`est_units`** for alerts and reconciliation.

## Default assumptions (override via env)

These defaults are **conservative guesses** — replace after you verify with ED:

| Endpoint key (log) | Env var | Default `est_units` per **request** | Notes |
|--------------------|---------|-------------------------------------|--------|
| `tt/keyword/search` | `ED_UNIT_KEYWORD_SEARCH` | `1.0` | If ED bills extra per post when `get_author_stats=true`, increase after measurement. |
| `tt/hashtag/posts` | `ED_UNIT_HASHTAG_POSTS` | `1.0` | Often dominant in batch pool. |
| `tt/post/info` | `ED_UNIT_POST_INFO` | `1.0` | URL-based diagnosis. |
| `tt/post/multi-info` | `ED_UNIT_POST_MULTI_INFO` | `1.0` | If ED bills per id in batch, set to `ids_per_request` fraction in code later. |
| `tt/user/posts` | `ED_UNIT_USER_POSTS` | `1.0` | |
| `tt/user/search` | `ED_UNIT_USER_SEARCH` | `1.0` | |
| `tt/post/comments` | `ED_UNIT_POST_COMMENTS` | `1.0` | |

## How to calibrate

1. Run one controlled `/batch/ingest` with `[ed-meter]` enabled.
2. Read **delta units** on the ED dashboard for the same UTC hour/day.
3. Solve for per-endpoint weights so `sum(count[e] * weight[e]) ≈ delta_units` (least squares or manual).

## `post/multi-info` chunk tuning

`REINGEST_MULTI_CHUNK` (default `12`) trades **request count** vs **payload size**. If ED bills **per aweme id** regardless of chunking, larger chunks reduce HTTP overhead only, not units. If ED bills **per HTTP call** only, maximize chunk within URL limits. **Measure** after `ed-pricing-map` is known.
