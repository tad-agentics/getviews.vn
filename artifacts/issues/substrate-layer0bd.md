# substrate-layer0bd

**Plan:** diagnosis-first plan — full 12-section taxonomy coverage  
**Status:** shipped (code + cron)  
**Scope:** Layer 0B sound enrichment + 0D hashtag map.  
**0D:** Hashtag discovery runs **daily** from `run_ingest_post_processing` (not weekly-only); see changelog / `corpus_ingest` post-processing path.  
**0B:** `trending_sounds` refreshed by standalone **`cron-batch-sound-aggregate`** — `supabase/migrations/20260630000000_cron_batch_sound_aggregate.sql` (weekly slot; avoids ingest-timeout skip). Sprint 6 adds `lifecycle_phase` / CML fields via `layer0_sound.py` + `sound_aggregator.py`.  
**Acceptance:** `trending_sounds` `week_of` advances after cron; hashtag map queryable for diagnosis (`hashtag_niche_map` / yields RPC).
