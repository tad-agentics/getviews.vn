# Post-W5 V1 Launch — Status (infra complete)

**Date:** 2026-05-23  
**Commits:** `d25f94e` (launch) · `4632b75` (M4 migration renumber) · `b479f64` (types regen + deploy docs)  
**Verdict:** **PRE_HANDOFF_PASS** — Vercel SPA promote pending

---

## GTM gates — status (updated 2026-05-23)

| Gate | Status | Evidence |
|------|--------|----------|
| `/visual-audit` (production) | ✅ | `visual-audit-launch-2026-05-23.md`; B-01/B-02 closed |
| `/dogfood` | ✅ | `dogfood-report.md` — 0 BLOCKING (human sign-off) |
| `/pre-handoff` | ✅ | `pre-handoff-baseline.json` — **PASS** 98/100, 0 BLOCKING |
| `/deploy` Vercel SPA | ⏳ | After commit + push → DevOps promote |

---

## Launch phases 0–2c + infra — DONE

| Phase | Status | Evidence |
|-------|--------|----------|
| 0 — G3, corpus-health, BAT, humility copy | ✅ | `launch-phase0-*.json` |
| 1 — F5 full + Channel Nhanh/Sâu (D2) | ✅ | `launch-phase1-baseline.json`, `launch-phase1-d2.json` |
| /2a — Channel findings P1/P2 + video P1 signals | ✅ | `launch-phase2a-baseline.json` |
| 2b — M4 `stats_history` + cron + refetch route | ✅ | `launch-phase2b-baseline.json`; migrations `20260827000002`/`000003` applied |
| 2c — Remaining findings + SSE Layer B + P1/P2 video signals | ✅ | `launch-phase2c-baseline.json` |
| §4.8.6 signal density sample | ✅ | `launch-phase2-signal-density-486.json` |
| Audit hardening (Round 2/3) | ✅ | `fetch_niche_benchmarks`, VN labels, utilization-map sync |

---

## Infrastructure gates — DONE

| Gate | Status | Evidence |
|------|--------|----------|
| `supabase db push` | ✅ | `20260827000002`, `20260827000003` on remote |
| `database.types.ts` regen | ✅ | `b479f64` — manual M4 patch removed |
| Cloud Run deploy | ✅ | user `00165-t6s`, batch `00132-4sg` |
| pg_cron + vault parity | ✅ | See below |

### Cron / vault (2026-05-23)

| Check | Result |
|-------|--------|
| `cron-batch-stats-history-refetch` | Active, `15 * * * *` (jobid 27) |
| Vault `cloud_run_api_url` | Batch hostname (`getviews-pipeline-batch-…run.app`) |
| Vault `cloud_run_batch_secret` | Matches batch pod `BATCH_SECRET` |
| `admin_pg_net_batch_http_4xx_events(24h)` | **0** |
| `POST /batch/ping` | **200** |
| `POST /batch/stats-history-refetch?limit=2` | **200** |
| `batch_job_runs` | `batch/stats-history-refetch` → `status=ok` |

**Batch URL:** https://getviews-pipeline-batch-720640652377.asia-southeast1.run.app  
**User URL:** https://getviews-pipeline-user-720640652377.asia-southeast1.run.app

---

## Automated QA — DONE

| Suite | Result |
|-------|--------|
| `npm run typecheck` | **PASS** |
| Launch pytest scope | **PASS** (incl. `test_analysis_depth_486_sample.py`) |
| §4.8.6 deep vs basic density | deep avg **2.16** vs basic **1.86** |

---

## GTM gates — superseded

See **GTM gates — status** section at top of this file. Legacy table below kept for audit trail.

---

## GTM gates — PENDING (human) _(archived)_

| Gate | Owner |
|------|-------|
| `/visual-audit` on staging | Product Designer |
| `/dogfood` (8 hero niches + demo URL) | Human + Tech Lead |
| `/pre-handoff` security audit | QA Agent |
| `/deploy` Vercel SPA promote | DevOps + human ship-it |
