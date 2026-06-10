# Cloud Run Pipeline — Deep Audit (2026-06-10)

Scope: all ~75k lines / 187 modules of `cloud-run/`, audited in five slices
(batch ingest, live video path, Gemini layer, SSE/routers/session, report
builders) plus production-side evidence (cron run history, `net._http_response`,
live schema). Every Critical/High was re-verified by hand before inclusion;
agent findings that didn't survive verification were downgraded and are noted
as such. Items marked **FIXED** were repaired in the same commit as this report.

## Production evidence found during the audit

### P-1 · `corpus_ingest_queue` never existed — nightly cron 500ing, silent data loss — **FIXED**
The single worst find, and it was invisible in code review: migration
`20260721000000_corpus_ingest_queue.sql` **collided on version number** with
`gemini_calls_cached_content_tokens` — Supabase records one row per version,
so the queue migration was silently never applied. Confirmed in prod:
`schema_migrations` has `20260721000000 = gemini_calls_cached_content_tokens`,
and the table was absent. Consequences for ~7 weeks:
- `cron-batch-process-ingest-queue` (01:30 UTC nightly) failed with PGRST205 —
  visible only in `net._http_response`, while `cron.job_run_details` said
  "succeeded" (pg_net fire-and-forget).
- The live-reference enqueue (`pipelines.py:1042`) failed on every diagnosis —
  swallowed by its `except: logger.warning` — so high-view reference videos
  discovered during live analysis **never reached the corpus**.

**Fix shipped:** DDL re-applied as `20260906000000_corpus_ingest_queue_repair`
(applied to prod; local file renamed with a repair note), drain endpoint
re-fired for validation. This is also the textbook argument for the
`cron-inventory-watch` + destructive-migration checklist added earlier today —
plus a new rule: **migration version numbers must be unique; check
`schema_migrations` for the version before applying.**

### P-2 · Unexplained 500 at 03:40 UTC (plain `Internal Server Error`)
One pg_net response with a non-JSON body — i.e., the pod crashed before
FastAPI could answer (or the request hit a dead revision). No scheduled job
matches 03:40. Worth one look in Cloud Run logs; if it recurs, the alert
policies from `create-alert-policies.sh` will catch it.

## Critical / High (code)

### C-1 · Five event-loop-blocking Supabase calls in async handlers — **FIXED**
`routers/video.py` ran sync `.execute()` directly on the event loop at
lines 188, 215 (refresh endpoint), 451, 522 (`_run_channel_diagnose`), and the
7-day cache lookup in the SSE generator. supabase-py is synchronous; each call
froze **all 20 concurrent SSE streams** for its full latency. All five now go
through `run_sync`. (Verified by hand; the rest of the routers were already
disciplined about this.)

### C-2 · Effective paid concurrency was 5, not 20 — **FIXED**
`run_sync` and dozens of `run_in_executor(None, …)` sites share asyncio's
default executor: `min(32, cpu+4)` = **5 threads on the 1-vCPU user pod**.
A paid turn occupies one thread for minutes (`answer.py:207`), so users 6+
queued invisibly behind heartbeats while Cloud Run admitted 20 requests.
Fixed by sizing the default executor to 40 threads at lifespan startup in
`main.py` — covers every call site on both pods.

### C-3 · Gemini Batch API submission bypassed the daily budget gate — **FIXED**
Every live call site checks `check_gemini_daily_budget()`, but
`run_corpus_extraction_batch_file_job` (`gemini.py:2534`) submitted batch jobs
with no gate — a runaway ingest loop could queue unbounded spend that only
appears in `gemini_calls` hours later. Gate added before submission.
(The sub-agent also claimed the sync fallback path was ungated — **wrong on
verification**: the fallback goes through `analyze_video`, which checks the
budget at `gemini.py:478`.)

### H-1 · ffmpeg audio extraction had no timeout — **FIXED**
`asr_vietnamese.py:59`: `subprocess.run` without `timeout` — a corrupted
stream wedges ffmpeg and holds a worker slot for the full 900s request
timeout. Now `timeout=60` + `TimeoutExpired` handled.

### H-2 · Video downloads unbounded on RAM-backed /tmp — **FIXED**
`ensemble.download_video` streamed to `/tmp` (tmpfs = RAM on Cloud Run) with
no size cap; `r2.py` enforces 60MB only *after* download. A livestream VOD
could OOM the 2Gi pod. Now capped at 60MB via Content-Length pre-check +
mid-stream counter. Frame cleanup in `r2.py:_cleanup_frames` also no longer
swallows errors silently (leaked frames = leaked RAM — now logged).

### H-3 · Ingest double-run = double Gemini spend (downgraded from agent's "Critical: duplicate rows")
There is no run marker/lock on `/batch/ingest`; if a shift double-fires, the
`on_conflict="video_id"` upsert prevents duplicate **rows** (agent's claim
overstated) but the full Gemini extraction re-runs and last-writer clobbers.
Cost exposure, not integrity. Backlog: a `corpus_ingest_runs` marker table
keyed `(utc_day, shift)`.

### H-4 · Client disconnect doesn't cancel paid work
On both SSE endpoints, if the client drops mid-stream, the producer task
(Gemini work) runs to completion — money burned for a viewer who left. Locks
and refunds behave correctly (verified: `finally` releases on generator
cancellation), so this is cost, not correctness. Backlog: poll
`request.is_disconnected()` in the heartbeat loop and cancel the task.

## Medium (backlog, in priority order)

| # | Finding | Where |
|---|---|---|
| M-1 | `video_corpus` upsert and `video_shots` dual-write are two statements — failure between them leaves shot-less rows; no post-batch orphan check | `corpus_ingest.py:2755-2816` |
| M-2 | Wall-clock abort skips MV refresh; heal depends on `cron-batch-post-processing` whose own failure is a warning, not an alert | `corpus_ingest.py:4133-4149` |
| M-3 | Turn append has no Idempotency-Key (session create does); TD-3 lock blocks same-user races but a retry after lock release can duplicate a turn | `routers/answer.py` |
| M-4 | Thin-cohort honesty gaps: per-hook findings can render with `uses=2`; `baseline_views` falls back to `1.0` → absurd "+49,900%" deltas possible on empty niches | `report_pattern_compute.py:445-511`, `report_pattern.py:453` |
| M-5 | Pydantic validation failure after synthesis surfaces as generic stream error; not separately logged/counted | `report_types.py:668`, `answer_session.py` |
| M-6 | `report_ideas_compute.fetch_corpus_window` missing the `quality_tier` filter Pattern applies — low-quality user-ingested videos can bias Ideas | `report_ideas_compute.py:322` |
| M-7 | ASR (GCP STT) cost logged but not charged/accounted against the user's turn — margin leak per video analysis; product decision needed | `asr_vietnamese.py:244` |
| M-8 | Same-URL concurrent analyses from two tabs both pay and both run (no URL-level in-flight dedupe; per-user lock covers one user only — two *different* users analyzing the same URL still double-run) | `video_analyze.py` cache path |
| M-9 | Skipped awemes (missing `aweme_id`, etc.) counted but not attributed — ED contract drift would be undebuggable; thin-cohort fallback to global percentiles is silent | `corpus_ingest.py:1700`, `corpus_instructiveness.py:273` |
| M-10 | TD-7 live/batch extraction parity asserted by shared code paths but has no integration test pinning it | `prompts.py:1265` |

Low items (not enumerated here in full): missing `max_output_tokens` on
`generate_niche_insight`, "median" anglicism in one VN template, in-memory
HI-11 reject counter lost on pod restart, dead `_ADMIN_LOGS_ENABLED` flag,
TikHub USD cost not logged alongside its budget counter.

## What's genuinely strong (verified, not taken on faith)

- **Cost-aware retry discipline**: Gemini retries only on 503/overloaded,
  never on 429 — deliberate, documented, prevents token-billing amplification.
- **Spend accounting**: every call (live and batch) lands in the
  `gemini_calls` table with model-correct pricing incl. batch discount and
  context-cache rates; the daily-budget read is DB-backed and pod-restart-safe.
- **SSRF defense**: short-URL resolution validates every redirect hop against
  a TikTok host allowlist; tests cover metadata IP and RFC1918 — implementation
  matches the tests.
- **LLM-output parsing**: three-tier JSON recovery (fence → bracket-slice →
  raw) + pydantic schema enforcement; prompt-injection surface is bounded
  (2000-char captions, 40 hashtags, structured output schema).
- **TD-3/TD-4 mechanics**: locks released in `finally` on all exit paths
  (incl. generator cancellation), replay buffer TTL/sweeper correct, JWKS
  cache with stale-while-revalidate, pod-role router mounting is clean.
- **Honesty invariants in reports**: fixture data can't leak to production
  (the 2026-04-22 `@demo` regression is explicitly guarded), empty corpora
  produce empty-state reports, sample floors are centralized and enforced.

## Updated slice grades

| Slice | Grade | One-liner |
|---|---|---|
| Gemini layer | **A-** | Best-engineered slice; batch gate was the one real hole (now closed) |
| SSE/session/routers | **B+ → A-** | Architecture right; the executor ceiling and 5 blocking calls were silent throughput killers (now fixed) |
| Report builders | **B+** | No criticals; honesty machinery real; thin-cohort edges need tightening (M-4) |
| Live video path | **B+** | SSRF/streaming/refunds solid; resource caps were missing (now fixed) |
| Batch ingest | **B-** | Works nightly, but most silent-failure surface area: no run marker, in-memory counters, swallow-and-continue error style |
| Ops coupling (pg_cron→pg_net) | **C → B-** | P-1 proves the failure mode; inventory watch + 4xx watch now cover it, but `net._http_response`'s ~6h TTL means evidence evaporates — consider persisting batch call outcomes |

## Recommended next two sprints

1. **Deploy these fixes** (executor, blocking calls, budget gate, timeouts,
   caps) — they're committed but inert until the image ships.
2. M-1 + H-3: ingest run marker + post-batch orphan check (one day, kills the
   two biggest batch risks).
3. H-4 disconnect cancellation (half day; direct Gemini cost saving).
4. M-4 + M-5: thin-cohort gating + validation-failure observability (the
   product's credibility rests on the "no fabricated confidence" promise).
5. M-3 turn Idempotency-Key; M-6 quality_tier parity (small).
