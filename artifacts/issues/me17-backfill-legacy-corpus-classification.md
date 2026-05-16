# ME-17 — Backfill legacy classification

- **Status:** **Partial** — implementation + migration + tests on **main**; **acceptance pending:** HI-11 **route flip** per deploy gate, then ~**14 nights** successful cron (or equivalent) until `niche_resolution_source IS NULL` corpus rows are drained (~0). Plan Gantt: ME-17 after `hi11flip`, duration **14d**.
- **Severity:** MEDIUM — bimodal corpus until NULL rows drain
- **Sprint:** Sprint 3 — MEDIUM
- **Locations:**
  - `cloud-run/getviews_pipeline/classification_backfill.py`
  - `cloud-run/getviews_pipeline/routers/admin.py` — `POST /admin/backfill-classification`, `POST /admin/trigger/backfill_classification`
  - `cloud-run/getviews_pipeline/routers/batch.py` — `POST /batch/backfill-classification`
  - `supabase/migrations/20260720000000_cron_batch_backfill_classification.sql`
  - Tests: `cloud-run/tests/test_me17_classification_backfill.py`
- **Symptom:** Legacy rows lack `content_context` / `niche_classification` and shadow columns until backfill runs.
- **Verification:** `pytest cloud-run/tests/test_me17_classification_backfill.py`; **ops:** `COUNT(*)` WHERE `niche_resolution_source IS NULL` → ~0 after planned run window; Supabase cron hitting batch URL + Vault.

**Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md` — plan frontmatter **me17** stays **`pending`** until acceptance.
