# HI-12 — BE/FE wellness mapping + inverse helper

- **Status:** Completed
- **Severity:** Medium — silent wrong-niche corpus rows for wellness creators
- **Sprint:** Sprint 2 — HIGH
- **Discovered:** 2026-05-16 — deep pipeline audit + conflict review
- **Location:** `cloud-run/getviews_pipeline/profile_niches.py` + `src/lib/profileNiches.ts`
- **Symptom:** Python-side wellness niche string was `"Lifestyle & Wellness"`, TypeScript-side was `"Health & Wellness"` — the legacy bridge `legacyNicheIdForCreatorNiche` produced different IDs.
- **Root cause:** String was defined independently in each runtime without a shared source of truth.
- **Proposed fix:** Aligned both to `"Lifestyle & Wellness"` and verified `legacyNicheIdForCreatorNiche()`/`legacy_niche_id_for_creator_niche()` return identical values.
- **Estimated effort:** 30 min
- **$ impact:** Prevents mis-classified wellness corpus rows; no direct cost impact.
- **Verification:** `npm run typecheck` passes; Python `legacy_niche_id_for_creator_niche("Lifestyle & Wellness")` returns same int as TypeScript counterpart.

**Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md` — search task ID in plan frontmatter todos.
