# Post-W5 V1 Launch — Code Audit (Round 3)

**Date:** 2026-05-23  
**Scope:** Working tree after Round 2 audit fixes  
**Verdict:** **READY_FOR_HUMAN_GATES**

---

## Round 2 → Round 3 fixes applied

| Issue | Fix |
|-------|-----|
| Stale `data-utilization-map-v1.md` 🔨 rows | Shipped P1/P2/M4 rows updated (hook_timeline, transitions, disclosure, persona, slang, stats_history) |
| `database.types.ts` manual M4 patch | Documented in changelog — regen after `db push` still required |
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

## Human gates (unchanged)

1. `supabase db push` — migrations `20260827000000`, `20260827000001`
2. Regen `database.types.ts` from applied schema
3. Cloud Run deploy — batch + user pods
4. pg_cron + vault verify
5. `/visual-audit`, `/dogfood`, `/pre-handoff`, `/deploy`

---

## Note on commits

Working tree still uncommitted until human approves atomic commit strategy for ~58 launch files.
