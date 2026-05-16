# HI-8 — system_instruction + context cache

- **Status:** Phase A **done** (2026-05-16); Phase B **deferred**
- **Severity:** (see plan body)
- **Sprint:** Sprint 2 — HIGH
- **Discovered:** 2026-05-16 — deep pipeline audit + conflict review
- **Location:** `cloud-run/getviews_pipeline/prompts.py` (`build_voice_domain_system_instruction`, knowledge split), `gemini.py` (all diagnosis / intent / knowledge / carousel v2 call sites), `output_redesign.py` (skip voice lead-in when `voice_block` empty)
- **Symptom:** Long static voice+domain blocks duplicated in every user turn; harder to adopt Gemini context caching later.
- **Root cause:** Single string prompts mixed static system-role content with per-request JSON/data.
- **Proposed fix (Phase A shipped):** Static voice + `_DOMAIN_KNOWLEDGE` on `GenerateContentConfig(system_instruction=…)`; per-request pieces (`layer0_context`, `creator_format_history_block`, session Q&A body) stay in the user message; `_prefix_user_sections` in `gemini.py`.
- **Phase B (not shipped):** `cachedContent` — blocked on `_generate_content_models` primary+fallback chain: need per-model cache names or rebuild config per attempt; design before implementing.
- **Estimated effort:** (see plan Sequencing)
- **$ impact:** (see plan impact table) — Phase B savings still unrealized
- **Verification:** `uv run pytest` (cloud-run) + `npm run typecheck`; commit `695c922`

**Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md` — search task ID in plan frontmatter todos.
