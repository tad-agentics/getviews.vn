# sprint1-commerce-intent

**Plan:** diagnosis-first (`diagnosis-first_plan_—_full_12-section_taxonomy_coverage_02458d1e.plan.md`)
**Status:** complete (backend slice)
**Scope:** §0 Commerce Intent — `commerce_intent` on extraction + five signal extractors + legacy promotion path.

## QA

- **Verdict:** PASS_WITH_CONCERNS — `artifacts/qa-reports/sprint1-commerce-intent-baseline.json`
- **Follow-up:** Five labeled commerce TikToks through full extract → diagnose + evaluator on objective/CTA/disclosure copy.

## Taxonomy source

- **Tracked:** `artifacts/docs/short-form-video-taxonomy-vietnam.md` (§0 = `commerce_intent` semantics). Code refs: `prompts.py` comment above `_VIDEO_EXTRACTION_CORE_VI`, `CommerceIntent` docstring in `models.py`.

## Acceptance notes

- Schema + prompt + unit-tested extractors: done.
- Plan acceptance “5 commerce fixtures” at diagnosis layer: deferred (documented in QA findings).
