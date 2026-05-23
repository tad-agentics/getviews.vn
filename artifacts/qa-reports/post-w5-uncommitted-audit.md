# Post-W5 V1 Launch — Code Audit (Round 3)

**Date:** 2026-05-23  
**Scope:** Working tree after Round 2 audit fixes  
**Verdict:** **READY_FOR_HUMAN_GATES**

---

## Round 2 → Round 3 fixes applied

| Issue | Fix |
|-------|-----|
| Stale `data-utilization-map-v1.md` 🔨 rows | Shipped P1/P2/M4 rows updated (hook_timeline, transitions, disclosure, persona, slang, stats_history) |
| `database.types.ts` manual M4 patch | **Resolved** — regen from live schema after `db push` |
| Private `_fetch_niche_benchmarks` import | Renamed public `fetch_niche_benchmarks()` + legacy alias |
| Silent peer fetch failures | `logger.warning` in `_fetch_peer_corpus_rows` |
| §4.8.6 acceptance gap | `test_analysis_depth_486_sample.py` + `launch-phase2-signal-density-486.json` |
| Mixed EN/VI in `ChannelNhanhPanel` | VN labels + `hookNameVI()` for dominant hook |
| Unused `_PERSONA_DRIFT_MIN_CC_CHANGES` | Used in `cc_changes >= _PERSONA_DRIFT_MIN_CC_CHANGES` |
| `corpus-health.sql` axis mismatch | SQL comment documenting legacy `niche_spread` vs class-first corpus CTE |
| Duplicate `ChannelDepthPicker` | Documented intentional dual entry in `ChannelScreen.tsx` |
| Untracked QA JSONs | `launch-phase2-signal-density-486.json` added; other launch JSONs remain to commit with ship |

---

## Test evidence

| Suite | Result |
|-------|--------|
| `test_analysis_depth_486_sample.py` | **PASS** (deep avg 2.16 vs basic 1.86) |
| Launch pytest scope | Run before ship |
| `npm run typecheck` | Run before ship |

---

## Human gates

| Gate | Status |
|------|--------|
| `supabase db push` (`20260827000002`/`000003`) | **Done** |
| Regen `database.types.ts` | **Done** |
| Cloud Run deploy (user + batch) | **Done** — user `00165-t6s`, batch `00132-4sg` |
| pg_cron + vault verify | **PASS** — see deploy evidence below |
| `/visual-audit`, `/dogfood`, `/pre-handoff`, `/deploy` | **Pending** |

### Cron / vault evidence (2026-05-23)

| Check | Result |
|-------|--------|
| `cron-batch-stats-history-refetch` | Active, schedule `15 * * * *` (jobid 27) |
| Vault `cloud_run_api_url` | Points at batch hostname (`getviews-pipeline-batch-…run.app`) |
| Vault `cloud_run_batch_secret` | Matches Cloud Run `BATCH_SECRET` on batch pod |
| `admin_pg_net_batch_http_4xx_events(24)` | **0** recent 4xx |
| `POST /batch/ping` | **200** |
| `POST /batch/stats-history-refetch?limit=2` | **200** (was 404 pre-deploy) |
| `batch_job_runs` | `batch/stats-history-refetch` rows `status=ok` |

**Batch URL:** https://getviews-pipeline-batch-720640652377.asia-southeast1.run.app  
**User URL:** https://getviews-pipeline-user-720640652377.asia-southeast1.run.app
