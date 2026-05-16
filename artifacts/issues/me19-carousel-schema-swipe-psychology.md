# ME-19 — Carousel swipe psychology schema

- **Status:** Done (schema + prompt + tests); manual 20-carousel sample eval deferred
- **Severity:** MEDIUM / diagnosis quality
- **Sprint:** Sprint 3 — MEDIUM
- **Discovered:** 2026-05-16 — deep pipeline audit + conflict review
- **Location:** `cloud-run/getviews_pipeline/models.py` (`SwipeAnchorType`, `SlideLayoutType`, `AudioTrackRoleType`, `SlideAnalysis`, `CarouselAnalysis`); `cloud-run/getviews_pipeline/prompts.py` (`_CAROUSEL_EXTRACTION_CORE_VI`); `cloud-run/tests/test_me19_carousel_swipe_psychology.py`
- **Symptom:** Carousel extraction described slides but not swipe motivation / audio / pacing.
- **Root cause:** Schema + prompt lacked ME-19 fields.
- **Proposed fix:** Optional Pydantic fields + Vietnamese prompt rules; legacy rows validate with nulls.
- **Verification:** `pytest tests/test_me19_carousel_swipe_psychology.py` + full cloud-run suite green.
- **Manual (plan):** Sample 20 viral carousels for `swipe_anchor` / `audio_track_role` quality — not automated.

**Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md` — ME-19.
