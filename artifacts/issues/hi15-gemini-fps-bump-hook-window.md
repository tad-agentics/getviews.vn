# HI-15 — Hook-window FPS bump

- **Status:** **PASS** (QA 2026-05-16, `artifacts/qa-reports/hi15-baseline.json`)
- **Severity:** (see plan body)
- **Sprint:** Sprint 2 — HIGH
- **Discovered:** 2026-05-16 — deep pipeline audit + conflict review
- **Locations:**
  - `cloud-run/getviews_pipeline/config.py` — `GEMINI_HOOK_WINDOW_DUAL_PART`, `GEMINI_VIDEO_BASE_FPS`, `GEMINI_HOOK_WINDOW_FPS`, `GEMINI_HOOK_WINDOW_END_SEC`
  - `cloud-run/getviews_pipeline/gemini.py` — `_build_video_extraction_content_parts`, `analyze_video` wiring; `analyze_carousel` guard (no `Part.video_metadata`)
  - `cloud-run/getviews_pipeline/prompts.py` — `build_video_extraction_user_turn_vi` (dual-mode Vietnamese; clamp-aligned seconds + base FPS copy)
  - `cloud-run/tests/test_gemini_hi15_hook_window.py`
- **Symptom:** Default ~1 FPS misses sub-second on-screen text on TikTok hooks.
- **Fix:** Two video Parts in one `generate_content`: full clip @ configurable base FPS + first N s @ 3–5 FPS via `types.VideoMetadata` (Option A). Batch + live SSE via `analyze_video` / `analysis_core._analyze_video`.
- **Verification:** `pytest` `tests/test_gemini_hi15_hook_window.py` + full cloud-run suite green.

**Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md`
