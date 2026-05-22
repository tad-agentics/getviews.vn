# Two-axis niche ops runbook — HI-11 + ME-18

> **Canonical taxonomy:** [`two-axis-niche-model.md`](two-axis-niche-model.md)  
> **Archived (PR1→PR6 cutover, completed 2026-05-13):** [`archive/two-axis-niche-cutover-pr1-pr6.md`](archive/two-axis-niche-cutover-pr1-pr6.md)

---

## HI-11: Two-axis niche resolver (shadow → `route`)

> **Production (2026-05-17+):** `NICHE_RESOLVER_MODE=route` on batch + user pods. Code default if unset remains `shadow` (rollback path).

**Scope:** Batch corpus ingest (`corpus_ingest.py`) chooses `content_class_id` (+ `ingest_loop_niche_id`) when Gemini HI-9 `niche_classification` is present. Phase C dropped `video_corpus.niche_id` — see [`two-axis-niche-model.md`](two-axis-niche-model.md) §8.

### Code reference

| Piece | Location |
|-------|-----------|
| Env flag | `NICHE_RESOLVER_MODE=shadow\|route` — `cloud-run/getviews_pipeline/config.py` |
| Shadow telemetry | `_niche_resolution_shadow_fields` — `corpus_ingest.py` |
| Route override | `_route_niche_and_class_override` — `corpus_ingest.py` |
| Junction lookup | `junction_content_class.content_class_id_for_creator_niche_format` |
| TD-6 gate | `creator_niche_has_content_class()` — reject route when class ∉ junction |
| Confidence floor | `_GEMINI_NICHE_CONFIDENCE_FLOOR = 0.6` |

- **`shadow`:** Hashtag/class map stays canonical; telemetry columns populated. Cloud Logging: `niche shadow disagree`.
- **`route`:** If confidence ≥ 0.6 + `junction_has_pair` + TD-6 pass → write junction `content_class_id`. Else hashtag ladder.

### Rolling automated eval

Nightly: `hi11_rolling_eval.py` → `artifacts/qa-reports/hi11-rolling-eval.json`.

| Metric | Promote threshold (7-night rolling median) |
|--------|---------------------------------------------|
| Hashtag class map agreement | ≥ **85%** |
| Junction miss (conf ≥ 0.6) | ≤ **5%** |
| Hook-type outlier vs class MV | ≤ **10%** |

### Shadow observation (rollback drill)

1. Set **`NICHE_RESOLVER_MODE=shadow`** on batch (+ user if aligned). Redeploy.
2. Daily SQL:

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

```sql
SELECT
  video_id,
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

3. Cloud Logging (batch): `[corpus] niche shadow disagree`, `[corpus] junction miss`, `hi11_junction_reject`.

### Manual 100-row audit (pre-flip gate)

1. Stratified sample of **100** recent rows.
2. Label: **`agree`** | **`gemini_better`** | **`legacy_better`** | **`both_wrong`**.
3. **Sign-off:** `(agree + gemini_better) / 100 ≥ 0.8`.

### Routing flip + post-flip hygiene

1. Set **`NICHE_RESOLVER_MODE=route`**. Deploy batch + user pods.
2. **Revert:** `shadow` + redeploy — no migration required.
3. After flip: run MV refresh chain per [`two-axis-niche-model.md`](two-axis-niche-model.md) §9 (`refresh_content_class_intelligence` → tier → stats).
4. **ME-17 backfill:** `POST /batch/backfill-classification` (cron `cron-backfill-classification`).

### QA / tests

- `cloud-run/tests/test_hi11_route_niche_resolution.py`
- `cloud-run/tests/test_corpus_ingest_junction_warn.py`
- `artifacts/qa-reports/hi11-confidence-threshold-eval.json`

---

## ME-18 appendix — Carousel share vs trending

Corpus carousel mix vs trending sample — tune `BATCH_CAROUSELS_BY_NICHE` when corpus `carousel_pct` lags trending by >3pp.

### Corpus carousel share (last 14 days)

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
JOIN niche_taxonomy n ON vc.ingest_loop_niche_id = n.id
WHERE vc.indexed_at > now() - interval '14 days'
GROUP BY n.name_vn
ORDER BY carousel_pct DESC;
```

### Trending cross-check (manual)

Sample top trending posts per ingest bucket; compare carousel % to SQL above. Adjust `settings.batch_carousels_by_niche` + redeploy batch.
