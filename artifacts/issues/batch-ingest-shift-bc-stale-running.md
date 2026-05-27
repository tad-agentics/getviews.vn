# batch-ingest-shift-bc-stale-running

**Opened:** 2026-05-27  
**Severity:** Medium (observability + partial nightly coverage)  
**Status:** Mitigated (rows closed manually); fix deferred

## Symptom

`batch_job_runs` for `batch/ingest` shifts **B** and **C** on 2026-05-27 stayed `status='running'` with `summary=null` for hours after cron fired.

## What actually happened

| Shift | Row ID | Ingest evidence | Row state |
|-------|--------|-----------------|-----------|
| B | `2781855d-64e4-402e-96ea-8d8954345cf1` | ~53 videos, 04:52–05:19 ICT | Stale — process killed ~60m |
| C | `932086f4-7db5-43c1-94ef-1b669d5fc30d` | ~66 videos, 06:20–06:46 ICT | Stale — likely killed during/after ingest + inline post-processing |

Corpus and `gemini_calls` prove real ingest. Coverage was **partial** vs ~11/10 classes per shift (unlike shift A: 10 classes, 139 videos, `ok`).

Standalone `batch/post-processing` at 06:59 ICT completed (`ok`) — MV not blocked.

## Root cause

1. Batch Cloud Run service timeout **3600s** (`deploy.sh`).
2. `record_job_run` only `_finalize`s after `run_batch_ingest()` returns (`routers/batch.py`).
3. `obs_summary` is populated **after** `run_batch_ingest` — no partial summary on timeout.
4. Shift **C** runs `run_ingest_post_processing` inline when final shift — can push total wall time past 60s after ingest ends.

Hard kill → no `async with` exit → row stuck `running`.

## Mitigation (2026-05-27)

Manually set both rows to `failed` with `finished_at = started_at + 3600s` and audit note in `error` + minimal `summary` JSONB.

## HI-13 dashboard always 0 (root cause found 2026-05-27)

Production batch pod has `CORPUS_INGEST_USE_GEMINI_BATCH=true`. Gemini Batch API **does run** nightly (`gemini_calls.video_extraction_batch` e.g. 146 lines during shift A 27/05).

**Bug:** `ingest_niche()` copied only `inserted/skipped/failed/errors` from `_ingest_candidate_awemes` sub-result — **not** `hi13_*` counters. `run_batch_ingest` rolls up `res.hi13_batch_line_ok` from `ingest_niche` return → always 0 in `batch_job_runs.summary.hi13` → admin panel shows 0.

**Fix:** `_merge_sub_ingest_result()` + use in `ingest_niche` (see `corpus_ingest.py`). Regression: `cloud-run/tests/test_ingest_niche_hi13_merge.py`.

## Recommended fixes (pick one or combine)

1. **Deploy HI-13 merge fix** — required for dashboard truth; ingest already uses Batch API when flag on.
2. **Incremental observability** — PATCH `batch_job_runs.summary` after each niche batch inside `run_batch_ingest`; `_finalize` on any exit path including `SIGTERM` handler.
3. **Never inline post-processing on shift C** — rely on `cron-batch-post-processing` only (already exists); removes 15–30+ min tail risk on ingest request.
4. **Raise batch timeout** only if cost acceptable — does not fix partial class coverage; shifts exist to stay under cap.
5. **Stable shift ordering** — `fetch_ingest_targets_sync` should `.order("content_class_id")` (or `priority, content_class_id`) so planned slices are reproducible in ops queries.

## Acceptance criteria for code fix

- [ ] No `batch/ingest` row remains `running` > 65 minutes after `started_at` without alert
- [ ] On Cloud Run timeout, row is `failed` with `aborted_early` / `ingest_shift` in summary
- [ ] Shift B/C nightly: either `ok` with `niche_results` or `failed` with partial summary — never null summary after 60m
