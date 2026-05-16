# HI-18 — Wire content_context into diagnosis + errors + few-shot

- **Status:** Landed (2026-05-16)
- **Severity:** (see plan body)
- **Sprint:** Sprint 2 — HIGH
- **Discovered:** 2026-05-16 — deep pipeline audit + conflict review
- **Location:** `output_redesign.py` (`_HI9_SYNTHESIS_HINT`, video + carousel narrative builders), `services/extraction.py` (`VideoErrorsExtractionInput` + `extract_video_errors` prompt), `morning_ritual.py` (`_build_prompt` grounding), `pattern_deck_synth.py` (`analysis_json` in grounding + trimmed rows), `two_axis_taxonomy.py` (`extract_subject_matter_from_analysis_json`)
- **Symptom:** HI-9 fields in `analysis_json` were ignored by synthesis / error extraction / few-shot prompts.
- **Root cause:** Prompts did not instruct the model to use the new keys; error extractor input omitted them; ritual/pattern grounding only sent hooks.
- **Proposed fix:** (shipped) Narrative hint block; flatten HI-9 into errors LLM JSON + guidance paragraph; optional `subject_matter` per grounding video.
- **Verification:** `uv run pytest` (cloud-run); commits `c99df15` (wiring) builds on `cb29567` (HI-9 schema).

**Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md` — search task ID in plan frontmatter todos.
