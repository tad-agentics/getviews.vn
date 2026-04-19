# EnsembleData “units per video” — metric baseline

## Why “16.7 units / video” misleads

Corpus batch cost is dominated by **per-niche pool discovery** (keyword pages + capped hashtag fetches), which runs **before** any row is inserted. Dividing **total dashboard units** for a UTC day by **only `video_corpus` inserts** inflates the ratio when:

- Inserts are low or zero (quota exhaustion, quality gates, duplicates).
- The same day includes **on-demand** ED calls (`/tt/post/info`, `/tt/user/posts`) or **another service** sharing the API key.

## Recommended KPIs (use all three)

| KPI | Numerator | Denominator | Use when |
|-----|-----------|-------------|----------|
| **Units / batch** | ED units consumed during one `POST /batch/ingest` window (from logs: `est_units` after pricing map) | 1 batch run | Capacity planning |
| **Units / candidate analyzed** | Same | Awemes passed to Gemini analyze in that batch | True marginal cost of enrichment |
| **Units / inserted row** | Same | Rows upserted to `video_corpus` | Product ROI (only when inserts > 0) |

## Aligning dashboard ↔ Cloud Run

1. **EnsembleData dashboard** time buckets are typically **UTC midnight–midnight** (confirm in ED UI / docs).
2. **Cloud Run**: filter logs with `resource.type="cloud_run_revision"` and text payload `POST /batch/ingest` or `[ed-meter]` for the batch correlation id.
3. Match **the same UTC calendar day** when comparing daily ED totals to summed `[ed-meter] est_units` (allow ±10% drift until `ed-pricing-map` is calibrated).

## Failed requests (e.g. HTTP 495)

Treat **495 / quota** as a first-class outcome: log whether the provider still bills (check ED docs). Until confirmed, assume **failed pool fetches may still consume units** if the HTTP request completed.

## References

- Implementation: `[ed-meter]` log line in batch completion (`corpus_ingest.run_batch_ingest`, `run_reingest_video_items`).
- Theoretical pool requests: `getviews_pipeline.ed_budget.theoretical_ed_pool_requests`.
