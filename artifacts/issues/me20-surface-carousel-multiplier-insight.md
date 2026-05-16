# ME-20 — Surface carousel multiplier

- **Status:** Done (implementation + tests local)
- **Severity:** polish / diagnosis quality
- **Sprint:** Sprint 3 — MEDIUM
- **Discovered:** 2026-05-16 — deep pipeline audit + conflict review
- **Location:** `cloud-run/getviews_pipeline/corpus_context.py` (`format_creator_format_history_for_diagnosis`, `aggregate_creator_format_history_from_rows`, `get_creator_format_history_sync`); `pipelines.py` (carousel + video diagnosis); `gemini.py` (`synthesize_diagnosis_v2` prefix); `video_analyze.py` (`finalize_video_narrative_layer`)
- **Symptom:** Carousel path showed format-history copy; video path did not; “carousel wins” fired for any `multiplier > 1.0` (noisy).
- **Root cause:** Inline carousel-only block; no shared gating; video synthesis omitted the block.
- **Proposed fix:** Shared markdown helper with 1.5 / 0.7 gates; pass the same block into video `synthesize_diagnosis_v2` and narrative finalize.
- **Verification:** `pytest tests/test_me20_format_history_diagnosis.py`; full cloud-run suite green. Changelog row in `artifacts/docs/changelog.md`.
- **QA:** PASS_WITH_CONCERNS (`artifacts/qa-reports/me20-baseline.json`). **Concern:** unit tests do not replace plan’s optional “sample 10” live diagnosis spot-checks for LLM copy fidelity.
- **Commit:** `31fd063`

**Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md` — ME-20.
