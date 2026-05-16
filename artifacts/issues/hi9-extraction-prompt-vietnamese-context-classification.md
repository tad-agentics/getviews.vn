# HI-9 — VIDEO_EXTRACTION_PROMPT two-axis + Pydantic

- **Status:** **PASS** (QA 2026-05-16, `artifacts/qa-reports/hi9-baseline.json`)
- **Severity:** (see plan body)
- **Sprint:** Sprint 2 — HIGH
- **Discovered:** 2026-05-16 — deep pipeline audit + conflict review
- **Locations:**
  - `cloud-run/getviews_pipeline/models.py` — `ContentContext`, `NicheClassification`, `VideoAnalysis`, `CarouselAnalysis` (Optional HI-9 fields; `extra="ignore"`)
  - `cloud-run/getviews_pipeline/two_axis_taxonomy.py` — 16 niche slugs, 12 `format_axis` slugs, `build_extraction_niche_glossary_block()`, `extract_subject_matter_from_analysis_json`
  - `cloud-run/getviews_pipeline/prompts.py` — `build_video_extraction_system_instruction`, `build_carousel_extraction_system_instruction` (Vietnamese core + HI-9 enrichment + few-shot examples)
  - `cloud-run/getviews_pipeline/gemini.py` — `analyze_video` / carousel path use Pydantic JSON schemas + `ThinkingConfig(thinking_budget=0)` via extraction config
  - `cloud-run/getviews_pipeline/cross_format.py` — `_FORMAT_AXIS_LABEL_VI` aligned to seeded axes (removed obsolete `vlog_destination` key)
- **Carry-over:** Junction seed covers **55** distinct `(creator_niche_slug, format_axis)` pairs — not the full 192 Cartesian grid. Runtime now emits `[corpus] junction miss …` WARN in `corpus_ingest._niche_resolution_shadow_fields` whenever Gemini emits an uncovered pair, so HI-11 routing can downgrade deterministically rather than write NULL `content_class_id`. Constant `JUNCTION_NICHE_FORMAT_PAIRS` in `two_axis_taxonomy.py` is pinned by `test_hi9_junction_constant_matches_migration_parse` so migrations + code cannot drift silently.
- **Verification:** `pytest` cloud-run 1945 passed, 2 skipped; `tests/test_hi9_extraction_models.py`, `tests/test_hi9_junction_seed.py`.

**Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md`
