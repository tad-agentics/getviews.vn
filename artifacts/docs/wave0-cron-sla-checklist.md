# Wave 0 — Cron SLA & corpus-health checklist

**Wave:** Incremental V1 Roadmap Wave 0 (W0-3)  
**Related:** [`incremental-v1-roadmap.md`](../plans/incremental-v1-roadmap.md) · [`corpus-health.sql`](../sql/corpus-health.sql) · [`claim_tiers.py`](../../cloud-run/getviews_pipeline/claim_tiers.py)

Run this checklist after deploy or weekly pre-launch. Record pass/fail + date in QA notes or `agent-workspace/ACTIVE_CONTEXT.md`.

---

## 1. Corpus adequacy (human / SQL)

| Step | Action | Pass criteria |
|------|--------|---------------|
| 1.1 | Run [`corpus-health.sql`](../sql/corpus-health.sql) in Supabase SQL Editor | Query returns 16 niche rows; hero niches ≥ `reference_pool` (5 videos/30d) |
| 1.2 | GET `/admin/corpus-health` (admin JWT) | JSON lists niches with `highest_passing_tier`; no 5xx |
| 1.3 | Spot-check 5–8 hero niches from `BATCH_PRIORITY_NICHE_IDS` | Each hero ≥ `basic_citation` (20/30d) or documented thin + humility copy |

---

## 2. Nightly batch cron SLA

Verify in Supabase **`cron.job_run_details`** (last 24h) — jobs should complete with HTTP 2xx on batch pod.

| Job (representative) | Batch path | Pass |
|----------------------|------------|------|
| Nightly ingest | `/batch/index` or ingest loop | 2xx |
| Class MV refresh | `/batch/refresh-class-intelligence` (or equivalent post-pivot) | 2xx |
| Hook effectiveness | `/batch/hook-effectiveness` | 2xx |
| Morning ritual | `/batch/morning-ritual` | 2xx |
| Scene intelligence | scene-intel refresh cron | 2xx |

**4xx watcher:** `cron-pg-net-batch-http-4xx-watch` hourly — check `admin_pg_net_batch_http_4xx_events` empty or triaged.

**Vault alignment:** `cloud_run_api_url` → **batch** service URL; `cloud_run_batch_secret` = batch pod `BATCH_SECRET`. Mismatch → silent cron 401.

---

## 3. TD-7 extract parity (W0-4)

Run locally before merge:

```bash
cd cloud-run && pytest tests/test_hi9_extraction_models.py tests/test_cohort_assignment_parity.py tests/test_corpus_boost_w0.py tests/test_channel_diagnose_ingest.py -q
```

| Check | Pass criteria |
|-------|---------------|
| HI-9 prompt/schema | `test_hi9_extraction_models.py` green |
| Cohort assignment parity | `test_cohort_assignment_parity.py` green |
| Boost + ref pool | `test_corpus_boost_w0.py` green |
| Channel credits | 3× `decrement_credit` on cache miss |

---

## 4. Wave 0 verification log

| Item | Verified | Date | Notes |
|------|----------|------|-------|
| W0-1 Channel billing 3× | | | FE `CREDIT_COST=3`; BE `CHANNEL_DIAGNOSE_CREDIT_COST=3` |
| W0-2 Doc hygiene | | | utilization map header + feature-map cross-link |
| W0-3 Cron SLA | | | This checklist |
| W0-4 TD-7 pytest | | | §3 commands |
| W0-5a Ref pool filter | | | `test_corpus_boost_w0.py` |
| W0-5b M1 columns | | | migrations `20260520000000`, `20260730000000` |

---

*Update this file when cron job names or batch paths change — mirror [`feature-map.md`](../docs/feature-map.md) §12.*
