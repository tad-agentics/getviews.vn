# ME-18 — Carousel ingest ratio

- **Status:** Partial (2026-05-16) — **`BATCH_CAROUSELS_BY_NICHE`** + `_carousels_per_night_for_niche` in `corpus_ingest`; `deep_pool` uses `min(per_niche_base×2, 12)` per niche. **Still required:** 14-day corpus SQL ratio, EnsembleData trending sample, tune env to match real-world carousel share (plan ±3pp).
- **Severity:** MEDIUM (corpus representativeness)
- **Sprint:** Sprint 3 — MEDIUM / polish
- **Locations:**
  - `cloud-run/getviews_pipeline/settings.py` — `batch_carousels_by_niche`
  - `cloud-run/getviews_pipeline/corpus_ingest.py` — `_parse_carousels_by_niche`, `_carousels_per_night_for_niche`, `ingest_niche` cap, `run_batch_ingest` deep_pool
  - `cloud-run/.env.example`
  - Tests: `cloud-run/tests/test_thin_niche_prioritization.py`
- **Symptom:** Uniform carousel cap under-samples carousel-heavy verticals.
- **Verification:** `cd cloud-run && .venv/bin/python -m pytest -q tests/test_thin_niche_prioritization.py`. **Corpus vs trending ratio SQL + operator notes:** `artifacts/docs/two-axis-niche-cutover-runbook.md` § ME-18 appendix.

**Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md`
