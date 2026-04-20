# Phase C.2.1 — Implementation audit

**Date:** 2026-04-20  
**Plan ref:** `phase-c-plan.md` §C.2 milestones item 1.

## Checklist (C.2.1)

| Deliverable | Status |
|-------------|--------|
| `pattern_wow_diff_7d` RPC migration | **Done** — `supabase/migrations/20260430000001_pattern_wow_diff_7d.sql` (stable signature; returns zero rows until `video_patterns` is wired to niche/week slices in a later sub-phase). |
| `report_pattern.py` module beyond C.1 fixture | **Done** — `fetch_pattern_wow_diff_rows`, `wow_rows_to_wow_diff`, `build_thin_corpus_pattern_report`, `build_pattern_report` merges WoW from RPC + fixture base. |
| Pydantic `PatternPayload` (§J) | **Done** — `cloud-run/getviews_pipeline/report_types.py` (pre-existing); WhatStalled invariant unchanged. |
| Pytest: empty / thin-corpus / full / WhatStalled-empty | **Done** — `cloud-run/tests/test_report_pattern.py` (12 tests). |

## Behaviour notes

- **Empty WoW:** Stub RPC yields no rows → `wow_diff` is three empty lists; `build_pattern_report` still validates once merged into full payload.
- **Thin corpus:** `build_thin_corpus_pattern_report()` sets `sample_size = 12`, explicit `what_stalled_reason`, `what_stalled = []` — satisfies schema + §5 empty-stalled rule.
- **Full:** `build_fixture_pattern_report()` — unchanged contract for C.1/C.2 consumers.
- **WhatStalled-empty:** Existing invariant tests + thin-corpus path.
- **Resilience:** `fetch_pattern_wow_diff_rows` logs and returns `[]` if Supabase env/client fails (local/tests without secrets).

## Deferred (by design — C.2.2+)

- Real SQL body for `pattern_wow_diff_7d` reading `video_patterns` (current schema uses `weekly_instance_count` / `niche_spread`, not the plan’s illustrative `week_end` / `instance_count_7d` — needs a reconciled migration before swapping the stub).
- `_compute_findings`, `_compute_what_stalled`, Gemini, credits — **C.2.2**.

## Verdict

**C.2.1: PASS** — RPC present, report module skeleton + WoW merge path, tests green (`pytest tests/test_report_pattern.py`).
