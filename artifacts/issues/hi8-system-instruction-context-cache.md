# HI-8 — system_instruction + context cache

- **Status:** **PASS** (QA 2026-05-16, `artifacts/qa-reports/hi8-baseline.json`) — extraction + synthesis (`diag_v1`, `diag_v2`, `diag_carousel_v2`, `intent_markdown`, `channel_diagnose`) on `system_instruction` + optional `client.caches.create` keyed by `sha256(kind|model|system_text)`. Knowledge stays on `system_instruction` (dynamic per message).
- **Severity:** (see plan body)
- **Sprint:** Sprint 2 — HIGH
- **Discovered:** 2026-05-16 — deep pipeline audit + conflict review
- **Locations:**
  - `cloud-run/getviews_pipeline/config.py` — `GEMINI_EXTRACTION_CONTEXT_CACHE` (default on), `GEMINI_SYNTHESIS_CONTEXT_CACHE` (default off), `GEMINI_CONTEXT_CACHE_TTL_SEC`
  - `cloud-run/getviews_pipeline/gemini.py` — `_get_extraction_cached_content_name`, `_configure_extraction_generate_config`, `_get_synthesis_cached_content_name`, `_apply_synthesis_context_for_model`, `_generate_content_models` (new `synthesis_cache_*` kwargs, per-fallback-model rebuild)
  - `cloud-run/getviews_pipeline/gemini_cost.py` — `log_gemini_call(used_context_cache=…)`
  - `cloud-run/getviews_pipeline/routers/video.py` — channel diagnose uses helper
- **Carry-overs (low):**
  - Extraction cache binds `GEMINI_EXTRACTION_MODEL` and does not rebuild per fallback model. Dormant — `GEMINI_EXTRACTION_FALLBACKS` defaults to []. Mirror synthesis pattern before configuring any extraction fallback.
  - Cold-slot `caches.create` race — loser cache lives until TTL; cost negligible.
- **Verification:** `pytest -q` cloud-run 1942 passed, 2 skipped; new tests `tests/test_gemini_hi8_synthesis_cache.py` + signature assertion in `tests/test_gemini_cost.py`.

**Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md`
