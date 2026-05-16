# HI-16 — Carousel two-axis prompt + schema

- **Status:** Implemented (2026-05-16) — migrations + Cloud Run; full pytest green
- **Sprint:** Sprint 2 — HIGH
- **Locations:**
  - `supabase/migrations/20260516190000_hi16_carousel_format_axis_junction.sql` — 5 `content_classifications` (ids 75–79) + junction CROSS JOIN all niches
  - `cloud-run/getviews_pipeline/models.py` — `CarouselNicheClassification`, `CarouselAnalysis.niche_classification`
  - `cloud-run/getviews_pipeline/two_axis_taxonomy.py` — `CAROUSEL_FORMAT_AXIS_*`, `CAROUSEL_JUNCTION_NICHE_FORMAT_PAIRS`, `VIDEO_JUNCTION_NICHE_FORMAT_PAIRS`, `build_carousel_extraction_niche_glossary_block()`
  - `cloud-run/getviews_pipeline/prompts.py` — `_HI9_ENRICHMENT_CAROUSEL`, `build_carousel_extraction_system_instruction()` uses carousel glossary only
  - `cloud-run/getviews_pipeline/corpus_ingest.py` — shadow telemetry reads `carousel_format_axis`
  - `cloud-run/getviews_pipeline/services/extraction.py` — errors input reads `carousel_format_axis`
  - `cloud-run/getviews_pipeline/output_redesign.py` — HI-9 synthesis hint mentions HI-16 carousel axis
  - Tests: `test_hi9_junction_seed.py`, `test_hi9_extraction_models.py`, `test_corpus_ingest_junction_warn.py`, `test_gate_schema_alignment.py`
- **Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md`
