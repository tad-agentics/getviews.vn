# HI-8 — system_instruction + context cache

- **Status:** **PASS_WITH_CONCERNS** (QA 2026-05-16, `artifacts/qa-reports/hi8-baseline.json`) — **extraction**: Phase A (`system_instruction` or `cached_content`) + Phase B optional `client.caches.create` keyed in-process. Knowledge/diagnosis/canvas already use `system_instruction`; explicit `caches.create` for those routes is optional follow-up.
- **Severity:** (see plan body)
- **Sprint:** Sprint 2 — HIGH
- **Discovered:** 2026-05-16 — deep pipeline audit + conflict review
- **Location:** `cloud-run/getviews_pipeline/prompts.py` (`build_video_extraction_system_instruction`, `build_carousel_extraction_system_instruction`, short user turns, `*_PROMPT` aliases), `gemini.py` (`_configure_extraction_generate_config`, `analyze_video`, `analyze_carousel`), `config.py` (`GEMINI_EXTRACTION_CONTEXT_CACHE`).
- **Historical (synthesis Phase A):** Static voice + `_DOMAIN_KNOWLEDGE` on `GenerateContentConfig(system_instruction=…)`; per-request pieces in user message (`_prefix_user_sections`).
- **Concerns (low):** Plan §HI-8 header lists synthesis files — this landing commit is **extraction-heavy** for explicit cache; see QA findings.
- **Estimated effort:** (see plan Sequencing)
- **$ impact:** (see plan impact table)
- **Verification:** `pytest` (cloud-run) + `npm run typecheck`; see QA baseline.

**Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md` — search task ID in plan frontmatter todos.
