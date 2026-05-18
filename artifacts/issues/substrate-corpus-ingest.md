# substrate-corpus-ingest

**Plan:** diagnosis-first plan — full 12-section taxonomy coverage  
**Status:** shipped (code)  
**Scope:** Niche-aware corpus growth — thin niches get higher videos-per-night quota vs `CORPUS_TARGET_PER_NICHE`.  
**Implementation:** `cloud-run/getviews_pipeline/corpus_ingest.py` (`compute_thin_niche_multiplier`, `_fetch_niche_counts_sync`, allocation log on batch summary); tunables in `cloud-run/getviews_pipeline/settings.py` (`corpus_target_per_niche`, `thin_niche_max_multiplier`, `batch_videos_per_niche`).  
**Acceptance:** Batch run logs `thin_niche_allocations`; empty niche counts fail-open to uniform VPN.
