# GetViews.vn — Full Codebase Audit (2026-06-10)

Scope: all three runtimes (React SPA, Vercel Edge `api/`, Cloud Run Python), Supabase
migrations + Edge Functions, CI/CD, deploy scripts, tests, dependency and secret hygiene.
Every Critical/High finding below was verified against the actual code (file:line cited);
claims that could not be reproduced were downgraded or discarded.

## Verified ground truth (ran in this audit)

| Check | Result |
|---|---|
| `npm run typecheck` | ✅ pass (0 errors, token check clean) |
| `npm run test` (vitest) | ✅ 1,086 tests / 136 files pass |
| `pytest` (cloud-run) | ⚠️ **2,404 pass, 2 FAIL** (see C-2) |
| `npm audit --omit=dev` | 5 vulns (3 high, 2 moderate) — all in dev-tool chains (`@react-router/dev` → `ws` etc.) |
| Tracked secrets scan | ✅ clean — only public anon keys (`src/lib/env.ts:7` local-demo key, `tests/v5-acceptance.spec.ts:20` published anon key) |
| `.env` files in git | ✅ none — only `*.env.example` |

---

## CRITICAL

### C-1 · Credits are charged even when the analysis fails (TD-1 violation)
**Where:** `cloud-run/getviews_pipeline/answer_session.py:519-525` (deduct) vs `:545-733` (build + error paths)

`append_turn` deducts 1–3 credits via `decrement_credit` RPC **before** any report builder
runs. Every failure path afterwards (`RuntimeError` at :674, generic `Exception`/Gemini 429
at :704) re-raises **without refunding**. `grep -ri refund cloud-run/` returns nothing —
the `credit_transactions.reason` enum has a `'refund'` value that no code ever uses.

Concrete user-facing bugs today:
- Compare turn: 2 credits deducted at :521-522, then `missing_video_url` raised at :642 —
  a user pasting one malformed link **deterministically loses 2 credits**.
- Gemini 429 / quota exhaustion mid-build: user sees the Vietnamese error message and still
  pays full price.

**Fix:** wrap the builder dispatch in try/except and compensate on failure:

```python
charged = 0
# ... set charged in each _deduct_credits branch ...
try:
    inner = <builder dispatch>
except BaseException:
    if charged:
        _refund_credits(_user_client(), charged)   # new RPC: increment + ledger row reason='refund'
    raise
```

Add a `refund_credit(p_user_id, p_amount)` SECURITY DEFINER RPC (mirror of
`decrement_credit`, writes `credit_transactions` with `reason='refund'`), and an
integration test: Gemini 429 mid-build ⇒ balance unchanged. Check
`POST /channel/diagnose` (`routers/video.py` ~:1015) for the same gap — its deduct happens
inside the lock but failure paths likewise have no compensation.

This is a showstopper for a paid product: it converts every transient Gemini/EnsembleData
outage into silent customer theft and support tickets.

### C-2 · Test suite is red at HEAD — CI gate is being bypassed
**Where:**
- `cloud-run/tests/test_channel_diagnose_ingest.py:243` — expects trajectory `breakout`, code returns `stagnant`
- `cloud-run/tests/test_embedded_tiles_sanitize.py:252` — expects prose `"tối ưu 3 giây đầu"`, code now emits the redesigned copy

Both are drift from the recent report-redesign commits (`b3ff9bb`…`28b351b`): code/copy
changed, tests weren't updated — and the changes landed anyway. CI (`.github/workflows/ci.yml`)
does run `pytest -q` on PRs to main, so either these commits were pushed directly to main or
the failing check wasn't enforced.

**Fix:** (1) update the two tests to the new thresholds/copy (or fix the regression if the
trajectory change was unintended — verify which one is the truth before "fixing the test");
(2) turn on GitHub branch protection: require `verify` + `cloud-run` checks, forbid direct
pushes to main.

---

## HIGH

### H-1 · No error tracking / alerting on the paid paths
OTel traces exist (`cloud-run/getviews_pipeline/telemetry.py`) but there is no Sentry/GCP
Error Reporting, no alert policy on Cloud Run 5xx, payment-webhook failures, or Gemini
quota exhaustion. The only alert in the system is the pg_net batch 4xx watch. When the
PayOS webhook starts failing at 2am, nobody finds out until users complain.

**Fix (1 day):** GCP Error Reporting via `google.cloud.logging` setup (or Sentry SDK in
both FastAPI and the React app), plus 3 GCP Monitoring alert policies: Cloud Run
`request_count{status>=500} > 5/min`, webhook function error rate, Gemini 429 log-based
metric. Wire to email/Telegram.

### H-2 · Payment Edge Functions have zero tests
`supabase/functions/payos-webhook/index.ts` (HMAC verify, idempotency via
`processed_webhook_events`, `decrement_and_grant_credits` RPC ordering) and
`create-payment/index.ts` have **no test coverage at all**, while the code encodes
order-sensitive invariants (RPC **before** idempotency-marker insert — documented at
webhook :80-94 as a previously-shipped bug). A refactor can silently re-introduce
"customer paid, credits never granted".

**Fix:** Deno tests for: invalid signature → 401; duplicate event → no double grant;
RPC failure → marker NOT written (retry succeeds); happy path grants once. Run
`deno test` in CI.

### H-3 · Deploys can skip every quality gate; no health check or rollback
`cloud-run/deploy.sh` (deploy at :74-123): `SKIP_BUILD=1 ./deploy.sh` deploys whatever
image is referenced without tests; after `gcloud run deploy` there is no `/health` probe,
no traffic canary, no automatic rollback. A revision missing an env var deploys "green"
and serves 500s.

**Fix:** in deploy.sh, after deploy: poll `https://$URL/health` for 60s; on failure run
`gcloud run services update-traffic --to-revisions=PREV=100`. Refuse `SKIP_BUILD` unless
the image tag was produced by CI.

### H-4 · `vercel.json` ships no security headers and no cache policy
Confirmed: file contains only `installCommand` + SPA rewrites. Missing
`Strict-Transport-Security`, `X-Frame-Options`/`frame-ancestors`, `X-Content-Type-Options`,
CSP, and — most operationally painful — an explicit `Cache-Control: no-cache` on
`index.html` (stale-shell failure mode for a PWA that streams SSE; the SW `prompt` update
mode makes this worse if users ignore the banner).

**Fix:** add a `headers` block: `index.html` → `max-age=0, must-revalidate`; hashed
`/assets/*` → `immutable`; HSTS + nosniff + frame-ancestors 'none' globally; CSP at least
in report-only mode to start.

### H-5 · `BATCH_SECRET` compared with non-timing-safe `==`
`cloud-run/getviews_pipeline/deps.py:171`:
```python
if batch_secret and provided_secret == batch_secret:
```
Header-based shared secret on an internet-reachable endpoint compared with `==`.
**Fix:** `hmac.compare_digest(provided_secret, batch_secret)` (one line; do it before the
planned Q3-2026 OIDC migration, not instead of it). Note the PayOS webhook already does
this correctly with `timingSafeEqual`.

### H-6 · No documented/tested backup & DR story
No backup retention statement, no tested restore procedure, no R2 lifecycle rules (orphan
frames rely on a `/batch/r2-janitor` cron that can fail silently).
**Fix:** confirm Supabase PITR/backup tier, run one restore drill into a branch project,
add real R2 lifecycle rules in Cloudflare (not only the janitor), document in
`system-design.md`.

---

## MEDIUM

| # | Finding | Where | Fix |
|---|---|---|---|
| M-1 | Gemini daily budget guard is advisory by default (`gemini_daily_usd_max=0`, `enforce=False`) — a runaway loop can blow the $80–90/mo ceiling | `cloud-run/getviews_pipeline/settings.py:78-85` | Enforce by default in prod, or refuse startup when `USD_MAX>0` and `ENFORCE=false` |
| M-2 | No upper bounds / lockfile for Python deps (`fastapi>=0.115`, `pydantic>=2.0`…); image rebuilds are non-reproducible | `cloud-run/pyproject.toml` | pip-tools/uv lock + upper bounds; pin Docker base images to digest |
| M-3 | SSE capacity: user pod `--concurrency 20`, `min-instances 1`, `--timeout 600s` while streams run minutes | `cloud-run/deploy.sh:89-92` | Load-test; raise timeout to 900s and tune concurrency before marketing pushes |
| M-4 | Missing composite index for corpus browse filters (class + indexed_at/views) | `useVideoCorpus.ts:75-101`, migration `20260511000000` | `CREATE INDEX ... ON video_corpus(content_class_id, indexed_at DESC) WHERE content_class_id IS NOT NULL` (verify with EXPLAIN first) |
| M-5 | `credit_transactions.session_id` lost its FK when `chat_sessions` was dropped with CASCADE — column is now unconstrained and semantically dead | `20260830000001_phase_c_drop_chat_sessions.sql:102` | Migration: drop column or re-point to `answer_sessions(id)` |
| M-6 | No structured logging / request-id correlation in Cloud Run | `routers/*.py` | structlog or contextvar request_id; makes H-1 alerts actionable |
| M-7 | Supabase RPC calls have no retry/backoff on transient errors (deduct path raises straight to user) | `answer_session.py:493-507` | One retry with jitter on transport errors only (never on `insufficient_credits`) |
| M-8 | No React error boundary at the `/app` layout level — render error = white screen | `src/routes/_app/` | Add a layout-level ErrorBoundary with Vietnamese fallback copy |
| M-9 | cron schedules live only in the Supabase Dashboard (migrations contain commented-out copies) — opaque to git, silent if unscheduled | `20260410000015`, `20260509000001` | Export live `cron.job` rows into a checked-in runbook; add a weekly "cron ran" assertion to the 4xx watch |

## LOW / HYGIENE

- **Doc drift in CLAUDE.md:** references `api/chat.ts` Edge function and `vercelEdgeDev`
  Vite plugin (`CLAUDE.md:104,111`) — neither exists (`api/` = `_cors.ts`,
  `landing-stats.ts` only). Stale docs steer future agents/devs wrong; update in the next
  commit touching architecture.
- **Dead mobile-era code in `shared/`:** `shared/api/supabase.ts` + `supabase-context.ts`
  create a second Supabase client factory, violating the single-client rule. Verified
  unused by `src/` — delete them.
- **Dead tsconfig alias:** `~/*: ./app/*` in `tsconfig.app.json` — no `app/` dir exists.
- **`_deduct_credits(u: Any, ...)`** and similar loose hints in `answer_session.py`.
- **Oversized modules:** `corpus_ingest.py` (~5.9k lines), `video_analyze.py` (~3.6k),
  `gemini.py`/`pipelines.py` (~2.3k each) — split before they become unreviewable.
- **`npm audit`:** 3 high / 2 moderate, all under dev tooling (`@react-router/dev`→`ws`
  etc.); `npm audit fix` on a quiet day.

## What's in genuinely good shape (verified)

- **RLS discipline:** financial tables service-role-only; `increment_free_query_count`
  privilege-escalation hole was found and fixed (`20260828000002`); all SECURITY DEFINER
  functions pin `search_path` (`20260504000006`).
- **PayOS webhook design:** timing-safe HMAC, dual-layer idempotency, correct RPC→marker
  ordering (the *code* is right; it just has no tests — H-2).
- **`decrement_credit`:** single atomic conditional UPDATE — race-safe, no overdraft.
- **Frontend architecture compliance:** code-splitting on all `/app/*` leaves, single
  Supabase client in `src/`, centralized env via Zod, TanStack-only server state, SSE
  resume (TD-4) implemented with replay buffer + dedupe + telemetry, auth listener
  race-handling is careful.
- **CI exists and is real:** typecheck + 1,086 vitest + ruff + pytest on PRs (the gap is
  enforcement and deploy-time bypass, not absence).
- **Niche parity (TD-7):** Python `legacy_niche_id_for_creator_niche` matches the TS twin.

## Priority order (CTO view)

**Week 1 — revenue integrity & not flying blind**
1. C-1 credit refund on failure (+ test) — both paid paths.
2. C-2 fix the 2 red tests; enable branch protection with required checks.
3. H-1 error tracking + 3 alert policies.
4. H-5 `hmac.compare_digest` (15 minutes).
5. H-4 vercel.json headers + index.html cache-control.

**Week 2–3 — payment & deploy hardening**
6. H-2 webhook/create-payment tests in CI.
7. H-3 deploy health-check + rollback; kill untested `SKIP_BUILD` path.
8. H-6 backup/DR drill + R2 lifecycle.
9. M-1 budget enforcement default, M-2 dependency pinning.

**Pre-scale**
10. M-3 SSE load test & Cloud Run tuning, M-4 corpus indexes, M-6 structured logging,
    M-8 error boundary, remaining hygiene items.

---

## Resolution log (2026-06-10, same day)

| Finding | Status | How |
|---|---|---|
| C-1 credit refund | ✅ Fixed | `refund_credit` RPC (migration `20260902000000`, service-role-only, ledger row `reason='refund'`; applied to prod) + `credits.refund_credits()` wired into `append_turn` failure paths and `/channel/diagnose` task-failure/error paths. 7 new tests in `test_credit_refund_on_failure.py`. |
| C-2 red tests | ✅ Fixed | Trajectory tests: fixtures carry absolute timestamps; froze `_now` at 2026-05-10 in all six tests (root cause: 30-day window emptied as wall-clock passed). Copy test updated to redesigned narratives + distinctness assertion. Also fixed 25 pre-existing ruff errors so the CI `cloud-run` job is green. Branch protection still needs enabling in GitHub settings (org-level action). |
| H-1 alerting | ✅ Script shipped | `cloud-run/scripts/create-alert-policies.sh` (user-pod 5xx, `REFUND FAILED` log metric, Gemini budget blocks). Run once with `GCP_PROJECT_ID`/`NOTIFY_EMAIL`. |
| H-2 payment tests | ✅ Fixed | Webhook refactored to injectable `handler.ts` (byte-identical behavior); 11 Deno tests incl. signature reject, duplicate 23505, RPC-before-marker ordering invariant; new CI `edge-functions` job runs them. |
| H-3 deploy safety | ✅ Fixed | `deploy.sh` now probes `/health` 60s post-deploy and routes traffic back to the previous revision on failure. User-pod timeout 600→900s (M-3). |
| H-4 headers/cache | ✅ Fixed | `vercel.json`: HSTS, nosniff, X-Frame-Options DENY, Referrer-Policy, Permissions-Policy; `index.html` & non-asset paths `max-age=0, must-revalidate`; `/assets/*` immutable. CSP deferred — needs an origin inventory first (do as report-only). |
| H-5 timing-safe compare | ✅ Fixed | `hmac.compare_digest` in `deps.py`. |
| H-6/M-9 DR + cron runbook | ✅ Documented | `artifacts/docs/ops-runbook.md` (restore drill still to be performed). |
| M-1 budget guard | ✅ Fixed (downgraded) | Real enforcement (`config.py`) was already `$15/day, enforce=True`; the `settings.py` duplicate (0/False) only drove a misleading startup warning. Aligned. |
| M-2 dep pinning | ✅ Fixed | Upper bounds on all cloud-run deps; `python:3.12.8-slim` pinned. |
| M-4 corpus indexes | ✅ Fixed | `20260904000000` composite `(content_class_id, indexed_at DESC)` + `(content_class_id, views DESC)`; applied to prod. |
| M-5 orphan `session_id` | ⏸ Deferred | Column is data-bearing history; dropping or re-pointing needs a product decision. |
| M-7 RPC retry | ❌ Rejected | Blind retry of `decrement_credit` on transport error can double-charge (the first call may have committed). The refund path now compensates the failure mode this targeted. |
| M-8 error boundary | ✅ Fixed | RR7 `ErrorBoundary` export in `root.tsx` (Vietnamese copy, reload + về Sảnh CTA). |
| Doc drift / dead code | ✅ Fixed | CLAUDE.md `api/chat.ts`/`vercelEdgeDev` refs corrected; deleted `shared/api/supabase.ts`, `supabase-context.ts`, `shared/hooks/useAuthState.ts`; dead `~/*` tsconfig alias removed; `npm audit fix` → 0 vulnerabilities. |
| **NEW: landing-stats 400** | ✅ Fixed | `api/landing-stats.ts` still selected `video_corpus.niche_id` (dropped in Phase C) — the landing thumbnails query 400'd in production. Switched to `ingest_loop_niche_id`. |

### Missing thumbnails — root cause & resolution

Verified against production (9,290 corpus rows):
1. **39% of corpus had NULL `thumbnail_url`** (3,649 rows, Apr 20–May 18 cohort):
   ingest predated mirror-at-ingest; signed TikTok CDN URLs expired; the 2026-05-25
   manual backfill nulled what it couldn't recover. New ingest is healthy (0% NULL
   since May 25).
2. **All 171 browser-reported failures (30d) were phantom R2 URLs** — DB points at
   R2, object missing (same class as the documented `frames/` phantom issue).
3. **Root cause of persistence: the self-healing endpoint
   `/batch/backfill-thumbnails` was never scheduled** — it HEAD-verifies every R2
   row and retries NULLs with fresh ED covers, but only ran when someone remembered.

Fix shipped: weekly pg_cron `cron-batch-backfill-thumbnails` (Sun 19:00 UTC, right
after the R2 janitor; migration `20260903000000`, applied to prod) + immediate
manual run triggered 2026-06-10 (verified healing: NULLs 3,649→3,616 within
minutes). Remaining infra action (documented in ops-runbook): move
`R2_PUBLIC_URL`/`VITE_R2_PUBLIC_URL` off rate-limited `pub-*.r2.dev` onto a custom
domain (`media.getviews.vn`) — env change only, no code.
