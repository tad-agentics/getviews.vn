# HI-13 — Batch API corpus ingest

- **Status:** **Implemented** (feature-flagged). Code: `corpus_ingest.py` + `gemini.py` batch helpers; migration `20260516120001_hi13_gemini_calls_is_batch.sql`.
- **Enable:** `CORPUS_INGEST_USE_GEMINI_BATCH=true` (+ optional `CORPUS_BATCH_POLL_*`) on batch pod. See `artifacts/integrations/gemini-batch-api.md`.
- **Sprint:** Sprint 2 — HIGH
- **Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md` — frontmatter may still list **hi13** as cancelled; treat as superseded by this shipped flag until plan YAML is amended.
