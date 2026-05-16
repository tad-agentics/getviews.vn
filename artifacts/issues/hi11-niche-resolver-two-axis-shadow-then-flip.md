# HI-11 — Two-axis resolver shadow → flip

- **Status:** Partial (2026-05-16) — **opt-in `NICHE_RESOLVER_MODE=route`** + junction-derived `content_class_id` in batch ingest; default **shadow** unchanged. Calendar shadow observation + 100-row audit + MV/hook gate still required before treating plan todo as complete.
- **Severity:** HIGH (quality / corpus attribution)
- **Sprint:** Sprint 2 — HIGH
- **Locations:**
  - `cloud-run/getviews_pipeline/config.py` — `NICHE_RESOLVER_MODE`
  - `cloud-run/getviews_pipeline/junction_content_class.py` — seed parse → `content_class_id_for_creator_niche_format`
  - `cloud-run/getviews_pipeline/corpus_ingest.py` — `_route_niche_and_class_override`, `_build_corpus_row` overrides, pattern `route_nid`
  - Tests: `tests/test_hi11_route_niche_resolution.py`
  - QA: `artifacts/qa-reports/hi11-baseline.json` (**PASS_WITH_CONCERNS**)
- **Symptom:** (plan) Hashtag-only resolver disagrees with Gemini two-axis classification.
- **Verification:** `cd cloud-run && uv sync --extra dev && .venv/bin/python -m pytest -q` — green; keep **shadow** in prod until audit.
- **Runbook (ops):** `artifacts/docs/two-axis-niche-cutover-runbook.md` — **Part B — HI-11** (daily SQL, 100-row gate, flip checklist, ME-17 handoff).
- **Architecture note:** `artifacts/docs/system-design.md` § “Niche model” — HI-11 bullet.

**Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md`
