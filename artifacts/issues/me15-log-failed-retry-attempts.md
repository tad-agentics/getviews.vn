# ME-15 — Log Gemini retry attempts

- **Status:** Completed
- **Severity:** Medium — telemetry blind-spot: 503 bursts invisible on cost dashboard until fix
- **Sprint:** Sprint 3 — MEDIUM / polish
- **Discovered:** 2026-05-16 — deep pipeline audit: exhausted-retry path logged, per-attempt path did not
- **Location:** `cloud-run/getviews_pipeline/gemini.py` → `_generate_content_models`, transient retry branch (~line 552)
- **Symptom:** Only the final exhausted failure emitted a `gemini_calls` row; intermediate 503 retries were invisible. Dashboard showed clean success rows during bursts.
- **Root cause:** `log_gemini_call` was only called in the `not is_transient or is_last_attempt` branch and after full chain exhaustion, not inside the recovery `time.sleep(delay)` branch.
- **Fix applied:** Added `log_gemini_call(..., success=False, tokens_in=0, tokens_out=0, error_code=f"{type(e).__name__}_attempt_{attempt+1}")` inside the transient retry branch (before `time.sleep`), wrapped in a bare `except Exception: pass` to stay non-blocking.
- **Estimated effort:** 30 min
- **$ impact:** Observability only — no cost change. Rows have `cost_usd=0` and `tokens_in=tokens_out=0`.
- **Verification:** `TestTransientRetryLogging` (2 tests) in `cloud-run/tests/test_gemini_cost.py` — all 32 tests pass.

**Canonical plan:** `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md` — search task ID in plan frontmatter todos.
