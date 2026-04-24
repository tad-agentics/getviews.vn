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

## Wave 1 — observability + corpus growth + hook_type eval

**End-of-wave moment:** *"The pipeline can no longer fail silently, and it's harvesting 2.5× more videos than before."*

**Why now:** Wave 2 depends on hook_type classifier accuracy being known (currently unknown). Wave 1 pulls that eval forward so if accuracy is below floor, we fix prompts before building features on top. Also closes the biggest latent observability gap (we *write* failures to `batch_job_runs` but nothing *reads* them) and unlocks the first real corpus growth flip.

### Scope

| Track | Item | Axis |
|---|---|---|
| BE | Alert rule on cron failures | 5 |
| BE | `gemini_calls.success` + `error_code` column | 5 |
| BE | `cta_type` + `face_appears_at` silent-skip audit | 2 |
| BE | `hook_type` classifier eval harness (golden set + CI gate) | 4 |
| BE | Phase 1 corpus growth — `BATCH_VIDEOS_PER_NICHE 10→25` + hashtag expansion for 4 undersized niches | 1 |
| FE | Marketing copy truth ("46.000+" → reality) | 1 |

### Backend PRs

#### `alert-rule-cron-failures` · ~0.5d · Axis 5
- **Migration:** new row in `admin_alert_rules` (table already exists per session context)
  - `rule_key: 'cron-batch-failure-7d'`
  - `sql_probe`: `SELECT COUNT(*) FROM batch_job_runs WHERE status='failed' AND started_at > NOW() - INTERVAL '7 days'`
  - `threshold: >0`
  - `severity: 'warning'`
  - `notify_channel: 'email:ops'`
- **Supabase Edge Function** (existing — reuse `cron-evaluate-alerts` pattern from session context): add handler for this rule → Resend email in Vietnamese.
- **Critical files:**
  - `supabase/functions/cron-evaluate-alerts/` (or whichever handler evaluates alert_rules today)
  - new migration `supabase/migrations/20260510000000_alert_rule_cron_failures.sql`
- **Test:** manually mark a `batch_job_runs` row `status='failed'`, run `/admin/evaluate-alerts`, verify email sent.

#### `gemini-calls-success-column` · ~0.5d · Axis 5
- **Migration:** `ALTER TABLE gemini_calls ADD COLUMN success boolean NOT NULL DEFAULT true`, `ADD COLUMN error_code text NULL`.
- **Wire-up:** in `cloud-run/getviews_pipeline/gemini.py`, every call-site that logs a `gemini_calls` row sets `success=True` on 200, `success=False, error_code=<type_name>` on exception.
- **Critical files:**
  - `cloud-run/getviews_pipeline/gemini.py` — grep for `gemini_calls.*insert` / `_record_gemini_call`
  - new migration `supabase/migrations/20260510000001_gemini_calls_success.sql`
- **Test:** force a Gemini 500 in a dev run; verify `success=false, error_code='InternalServerError'`.

#### `cta-face-detect-silent-skip-audit` · ~0.5–1d · Axis 2
- **Investigation, then fix:**
  - `cta_type` populated on 30% of rows. Grep `gemini.py` + `analysis_core.py` for the extraction prompt + normalization. Likely: Gemini returns `null` more often than expected, and we store null rather than applying a regex fallback.
  - `face_appears_at` populated on 79%. 21% silent skip means Gemini either doesn't return the field or the field is coerced to null somewhere.
- **Critical files:**
  - `cloud-run/getviews_pipeline/gemini.py`
  - `cloud-run/getviews_pipeline/analysis_core.py`
  - `cloud-run/getviews_pipeline/corpus_ingest.py` (row assembly)
- **Output:** either a fix PR or an explicit doc entry "these gaps are real; source of truth is Gemini's visual extraction limits" so Wave 2 doesn't build on false expectations.

#### `hook-type-eval-harness` · ~1–2d · Axis 4
- Mirror the `content_format` harness exactly:
  - Hand-curate golden set in `cloud-run/getviews_pipeline/eval_data/hook_type_golden.json` — ~30 items across the 13 hook_type labels (question, shock_stat, bold_claim, curiosity_gap, etc.)
  - Labels assigned by reading transcripts + first-frame visual, NOT by trusting existing `video_corpus.hook_type` values (same "DB has noise" reality that drove the content_format golden set).
  - New runner: `evaluate_hook_type()` in `cloud-run/getviews_pipeline/eval_classifier.py` (reuses the existing `EvalScorecard` dataclass).
  - New pytest gate in `cloud-run/tests/test_hook_type_eval.py` with `MIN_ACCURACY = 0.85` as the *initial* floor (conservative given unknown baseline).
- **Critical files:**
  - `cloud-run/getviews_pipeline/eval_classifier.py` (extend)
  - `cloud-run/getviews_pipeline/eval_data/hook_type_golden.json` (new)
  - `cloud-run/tests/test_hook_type_eval.py` (new)
- **Exit branch:** if accuracy ≥ 0.85 → Wave 2 unblocked. If < 0.85 → Wave 1.5 prompt-engineering PR on `hook_type` extraction in `gemini.py` before Wave 2 starts.

#### `phase1-corpus-growth` · ~0.5d · Axis 1
- **Env flip:** `gcloud run services update getviews-pipeline --region asia-southeast1 --update-env-vars BATCH_VIDEOS_PER_NICHE=25`
- **Hashtag expansion** — 4 undersized niches (live-DB numbers as of 2026-05-09):
  - Tài chính / Đầu tư: 21 → 70 hashtags
  - Chị đẹp: 23 → 70
  - Bất động sản: 24 → 70
  - Nấu ăn / Công thức: 25 → 70
  - **How:** query `niche_taxonomy.signal_hashtags` for each, curate additions using a Gemini Flash-Lite prompt seeded from top-performing tags in neighboring niches, commit as 4 SQL UPDATEs.
  - **Critical files:** new migration `supabase/migrations/20260510000002_hashtag_expansion_4_niches.sql`
- **Validation:** trigger `/admin/trigger/ingest` with `deep_pool=true` once after the env flip; verify `batch_job_runs.summary->'total_inserted'` > previous baseline.

### Frontend PR

#### `landing-corpus-copy-truth` · ~0.5h · Axis 1
- **Problem:** landing + auth screens claim "46.000+ videos". Actual: 1,558. 30× lie → legal/trust risk.
- **Fix options** (pick whichever is safer):
  - A) Dynamic: read `video_corpus` COUNT during prerender (landing is prerendered; `/` route in `react-router.config.ts`), inject the number.
  - B) Static safe placeholder: "~2.000 video Vietnamese creators, đang tăng mỗi ngày."
- **Critical files:**
  - `src/routes/_index/LandingPage.tsx`
  - `src/routes/_auth/login/route.tsx`
- Prefer Option A — it auto-tracks Phase 1/2/3 growth, never lies again.

### Dependencies from Wave 0

All of Wave 0 already shipped. Wave 1 only depends on tonight's first autonomous cron cycle landing cleanly (validates observability + refresh fix in a real-cron-fire context, not just manual smokes).

### Validation gate → Wave 2

- `batch_job_runs.summary->'total_inserted'` on daily ingest cron > 400 for 3 consecutive days.
- Zero silent cron failures in a 7-day window (`failures_7d = 0` OR `failures_7d > 0` with matching alert firing — either proves the observability loop closed).
- `gemini_calls.success` populated on 100% of new rows.
- `hook_type` eval accuracy ≥ 0.85 (or a merged Wave 1.5 fix that achieves it).
- `cta_type` + `face_appears_at` gaps either closed or documented.
- Landing copy reflects reality (not 46K×).

### Risk flags

- **`hook_type` accuracy could be < 0.70.** If so, Wave 1 stretches to include prompt work. Buffer: Wave 1 calendar 5–7d can absorb up to ~3d of Wave 1.5.
- **Phase 1 env flip could hit ED cap.** 25 videos/niche × 21 niches = 525 videos per ingest, ED cost roughly 2× current. With 5000/day cap and 3465 currently unused daily, there's headroom. Watch `batch_job_runs.summary->'error_types'` for `EnsembleDailyBudgetExceeded` the first 2 days.
- **`cta_type` / `face_appears_at` root cause could be Gemini model limits** (not a fixable code bug). If so, the output is a doc entry, not a fix PR — reset expectations rather than burn time chasing.

### Calendar

5–7 working days. Parallelizable: the 4 BE PRs + 1 FE PR can run in any order; the only ordering constraint is `hook-type-eval-harness` must complete before Wave 2 starts.

---

