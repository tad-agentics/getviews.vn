# HI-17 — Skip ASR for carousels; FPS video-only

- **Status:** Done (2026-05-16) — architecture was already correct; documented + regression test.
- **Severity:** LOW (cost noise / clarity)
- **Sprint:** Sprint 2 — HIGH
- **Locations:**
  - `cloud-run/getviews_pipeline/analysis_core.py` — `_analyze_carousel` HI-17 comment (no `sync_prepare_*` on carousel path)
  - `cloud-run/getviews_pipeline/services/asr_vietnamese.py` — `sync_prepare_vietnamese_asr_supplement` docstring (video-only callers)
  - `cloud-run/getviews_pipeline/gemini.py` — `analyze_carousel` HI-15/HI-17 comment (FPS + STT video-only)
  - Tests: `test_hi17_carousel_skips_hi14_asr.py`, `test_gemini_hi15_hook_window.py` (Part guard)
- **Symptom:** Plan referenced Whisper/extraction early-return; actual HI-14 integration is **`analysis_core` video paths only** — carousels never invoked STT.
- **Verification:** `cd cloud-run && uv sync --extra dev && .venv/bin/python -m pytest -q cloud-run/tests/test_hi17_carousel_skips_hi14_asr.py`

**Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md`

**QA:** `artifacts/qa-reports/hi17-baseline.json` — **PASS**
