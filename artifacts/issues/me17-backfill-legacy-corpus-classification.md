# ME-17 — Backfill legacy classification

- **Status:** Done (code + migration + tests); **prod:** apply `20260720000000_cron_batch_backfill_classification.sql`, confirm batch Vault URL + deploy Cloud Run before relying on cron.
- **Severity:** MEDIUM — bimodal corpus until `niche_resolution_source IS NULL` drains
- **Sprint:** Sprint 3 — MEDIUM
- **Locations:**
  - `cloud-run/getviews_pipeline/classification_backfill.py`
  - `cloud-run/getviews_pipeline/routers/admin.py` — `POST /admin/backfill-classification`, `POST /admin/trigger/backfill_classification`
  - `cloud-run/getviews_pipeline/routers/batch.py` — `POST /batch/backfill-classification`
  - `supabase/migrations/20260720000000_cron_batch_backfill_classification.sql`
  - Tests: `cloud-run/tests/test_me17_classification_backfill.py`
- **Symptom:** Legacy rows lack `content_context` / `niche_classification` and shadow columns.
- **Verification:** `pytest cloud-run/tests/test_me17_classification_backfill.py`; ops: `SELECT COUNT(*) FROM video_corpus WHERE niche_resolution_source IS NULL` trends to 0 over ~14 nights after cron live.

**Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md` — ME-17.
