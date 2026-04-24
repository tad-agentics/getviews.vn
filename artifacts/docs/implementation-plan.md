# GetViews — implementation plan (revised)

**Version:** 2026-05-09 (incorporates creator-survey signal + reviewer feedback)
**Supersedes:** earlier ad-hoc roadmap. Each wave below is self-contained with exit criteria.

---

## Context

Two inputs reshape the roadmap:

1. **Creator survey (n≈22)** surfaced a clear pay-signal ranking:
   - #1 Phân tích video viral/flop (32%) — single-video diagnosis
   - #2 Dự đoán video nào dễ viral (18%) — viral prediction
   - #3 Viết hook (18%)
   - #4 Gợi ý idea content (14%)
   - #5 Viết script (5%)

   Plus 82% endorsement of "5 video tiếp theo bạn nên làm (kèm hook)".

2. **Reviewer critique** flagged 6 concrete planning errors in the earlier draft:
   hook_type eval was mis-sequenced (inside Wave 2, should block Wave 2); Compare-two-videos was over-weighted from probing signal vs pay signal; viral-score formula was hand-waved; validation gates leaned on niches that don't yet have enough data; the Layer 0 injection work (state-of-corpus Appendix B Gap 2) was missing; calendar estimates were tight.

This plan incorporates all accepted feedback and sequences waves so each one ends with a single concrete promise a Vietnamese creator would read and nod.

**North star:** *"Tell me what video to make next, and tell me why the last one worked or flopped."*

---

## Principles

1. **Pipeline-first, product-second.** Every new feature depends on a populated aggregate. Never ship a feature whose underlying table is empty.
2. **One wave = one unambiguous moment.** At the end of each wave, a creator can say a specific thing about the product that wasn't true before.
3. **BE before FE for data features; FE before BE for framing features.** "5 next videos" is framing-heavy → FE leads. "Compare two videos" is a new intent → BE leads.
4. **Every classifier change carries its own golden-set expansion.** Axis 4 discipline is baked into the wave that touches the classifier, not a separate track.
5. **Cap work-in-flight to 2 waves.** Ship wave N → validate on live for ~3 days → start wave N+1. No parallel multi-wave waterfall.

---

## Wave 0 — baseline shipped today (reference only)

Don't re-do these. These are now load-bearing for everything below.

### Data pipeline

| Table / signal | Before | After | Source |
|---|---|---|---|
| `hook_effectiveness` rows | 0 | 123 | PR #109 (`hook_effectiveness_compute`) + smoke fire via `/batch/analytics` |
| `creator_velocity` rows | 0 | 133 | PR #122 (`creator_velocity_handle_niche_unique`) + smoke fire |
| `video_corpus.breakout_multiplier` populated | 0/1,220 | 526/1,558 | same analytics pass |
| `video_corpus.last_refetched_at` populated | 0 | 234+ (growing daily) | PR #114 (`corpus_refresh`) + daily cron |
| `batch_job_runs` rows | 0 | writes every `/batch/*` run | PR #113 (`batch_observability`) |

### Code / migrations

| Module | What | PR |
|---|---|---|
| `cloud-run/getviews_pipeline/hook_effectiveness_compute.py` | Weekly aggregate `hook_effectiveness` | #109 |
| `cloud-run/getviews_pipeline/batch_observability.py` | `record_job_run` context manager | #113 |
| `cloud-run/getviews_pipeline/corpus_refresh.py` | Daily metadata-only refresh + resilience (retry/cooldown/error-type capture) | #114 + #121 |
| `cloud-run/getviews_pipeline/content_format_reclassify.py` | Regex catch-up on `content_format='other'` | #115 |
| `cloud-run/getviews_pipeline/eval_classifier.py` + `eval_data/content_format_golden.json` | 27-item golden set, `evaluate()` scorecard, CI floor 0.95 | #116 + #117 |
| `cloud-run/getviews_pipeline/routers/admin.py` | Admin triggers for refresh/reclassify/layer0 | #120 |
| `supabase/migrations/2026050900000{0-5}_*.sql` | Unique constraints, `last_refetched_at`, `batch_job_runs`, cron docs | #109, #114, #113, #122 |

### Infrastructure

| Item | Status |
|---|---|
| Vault secrets (`cloud_run_batch_secret`, `cloud_run_api_url`) | Seeded |
| 4 data-pipeline crons (`cron-batch-ingest`, `cron-batch-refresh`, `cron-batch-analytics`, `cron-batch-layer0`) | Scheduled in `cron.job`, firing |
| EnsembleData plan | Upgraded 1500 → 5000 units/day |
| Cloud Run build | Up-to-date with `main` + resilience PR |

---

## Wave summary — what each wave delivers

| Wave | Moment at end of wave | Effort | Critical deps |
|---|---|---|---|
| **1** | "The pipeline can no longer fail silently, and it's harvesting 2.5× more videos than before." | 5–7d | Wave 0 ✓ |
| **2** | "Ideas report shows your next 5 videos with hook + opening line + content angle." | 9–10d | Wave 1 hook_type eval passing + corpus at 3 niches ≥ 200 |
| **3** | "Diagnosis reports surface execution_tip + viral-score formula is specified and validated on historical data (no shipping yet)." | 5–7d | Wave 2 on live ≥ 3 days |
| **4** | "Paste two URLs → side-by-side diagnosis. Every diagnostic carries a 0-100 viral-alignment pill with 3 reasoning bullets." | 7–10d | Wave 3 design doc approved |
| **5+** | Growth continuation — Phase 2/3, taxonomy expansion decision, Axis 4/5 residuals. | ongoing | Wave 4 on live ≥ 1 week |

**Total calendar to survey-validated product: ~30–35 working days (~6–7 weeks) solo @ 4h/day effective.**

Each wave's detailed breakdown follows in its own section below.

---
