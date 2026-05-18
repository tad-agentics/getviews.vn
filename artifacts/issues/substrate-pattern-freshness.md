# substrate-pattern-freshness

**Plan:** diagnosis-first plan — full 12-section taxonomy coverage  
**Status:** playbook (ops; default schedule unchanged)  
**Scope:** Keep pattern-report evidence fresh vs `video_corpus` ingest.  
**Current cadence:** `POST /batch/pattern-decks` — daily pg_cron `cron-batch-pattern-decks` per `supabase/migrations/20260530000001_pg_cron_pattern_decks.sql` (`0 16 * * *` UTC ≈ 23:00 ICT). Staggered after pattern fingerprint work (see migration comments).  
**Audit (weekly or on incident):**
1. `cron.job_run_details` / batch logs — last `batch/pattern-decks` HTTP 200 + rows touched.
2. Spot-check: newest `video_patterns` / deck output vs newest `video_corpus.indexed_at` for a pilot niche — lag should not exceed ~24–36h routinely.
3. If lagging: options — add a **second** daily cron window (off-peak), or raise `DEFAULT_BATCH_CAP` in pattern-deck synth (cost trade-off). Do not change schedule without cost sign-off.

**Acceptance:** Criteria above documented; no code change required until audit fails threshold.
