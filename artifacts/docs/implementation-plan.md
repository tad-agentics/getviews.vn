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

| Wave | Moment at end of wave | Effort | Critical deps | Status |
|---|---|---|---|---|
| **1** | "The pipeline can no longer fail silently, and it's harvesting 2.5× more videos than before." | 5–7d | Wave 0 ✓ | ✅ shipped |
| **2** | "Ideas report shows your next 5 videos with hook + opening line + content angle." | 9–10d | Wave 1 hook_type eval passing + corpus at 3 niches ≥ 200 | ✅ shipped |
| **2.5** | "Every generated shot shows up to 3 real creator scenes from the same niche with match-signal chip." | ~8d | Wave 2 on live | ✅ shipped |
| **3** | "Diagnosis reports surface execution_tip. Viral-score formula backtested; DEFERRED per ρ = 0.14 < 0.35 gate." | 5–7d | Wave 2 on live ≥ 3 days | ✅ shipped (score deferred) |
| **4** | "Paste two URLs → side-by-side diagnosis with delta summary." (viral-score pill CUT — see `artifacts/docs/viral-alignment-score.md` §9) | 5–7d | Wave 3 design doc approved | planned |
| **5+** | Growth continuation — Phase 2/3, taxonomy expansion decision, Axis 4/5 residuals. Includes re-running the viral-score backtest when any §11 trigger fires. | ongoing | Wave 4 on live ≥ 1 week | planned |

**Total calendar to survey-validated product: ~30–35 working days (~6–7 weeks) solo @ 4h/day effective.**

**Wave 4 scope reduced** from "Compare + viral-score BUILD" to
"Compare-only" after Wave 3 PR #5's backtest (ρ = 0.14 on 352-video
sample). See the design doc's §9 verdict and §11 re-evaluation
triggers for when to re-open the score BUILD.

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

## Wave 2 — Ideas as a content calendar ("5 video tiếp theo")

**End-of-wave moment:** *"A creator opens the Ideas report and sees 5 specific videos laid out like a calendar — hook template, opening line, content angle, lifecycle pill — all populated from their niche's real data."*

**Why now:** 82% of surveyed creators endorsed this exact framing (highest endorsement rate of any probe). The data layer (hook_effectiveness populated, patterns weekly counts refreshed, niche_insights already 11-day-stale-but-usable) already exists — this wave is predominantly a **framing + data-wiring** change, not a new data pipeline.

### Scope

| Track | Item | Axis |
|---|---|---|
| BE | Layer 0 injection — wire `niche_insights.insight_text` + `execution_tip` into Ideas narrative generation | 2 (state-of-corpus Appendix B Gap 2) |
| BE | Ideas payload enrichment — `opening_line`, `content_angle`, `lifecycle_stage` per finding | — |
| BE | Ideas prompt engineering — Gemini Flash-Preview emits the new structured fields | — |
| FE | IdeasBody reframe to "5 VIDEO TIẾP THEO" calendar layout | — |
| FE | Home screen surfacing of Ideas with niche-prepopulated quick-link | — |

### Backend PRs

#### `layer0-narrative-injection` · ~1.5d · Axis 2 Gap 2
- **Problem:** `niche_insights` table has 11 rows (one per niche), refreshed weekly by `/batch/layer0`. The most actionable fields (`insight_text`, `execution_tip`) are populated but never surface in any Answer-session report. This is state-of-corpus Appendix B Gap 2 — flagged, not yet fixed.
- **Fix:** extend the Pattern + Ideas narrative generators to read `niche_insights` and inject `execution_tip` into the final report payload.
  - Identify the exact narrative builder functions. Session context said `fill_pattern_narrative` + `fill_ideas_narrative` but those names came from a docstring — confirm via `grep -rn "fill_.*narrative\|build_pattern\|build_ideas" cloud-run/getviews_pipeline/` before editing.
  - Wire a lookup: `fetch_niche_insight(niche_id)` → inject `insight_text` into the preamble, `execution_tip` into the "what to do" slot.
  - Graceful degradation: if `niche_insights` row is missing or > 14 days old, skip injection rather than fail.
- **Critical files:**
  - `cloud-run/getviews_pipeline/pipelines.py` — session context says `_get_niche_insight()` exists at line ~1012, called from the `video_diagnosis` flow at line 1238. Reuse or generalize this function for Pattern + Ideas.
  - Narrative generation modules (confirm exact names via grep): likely `cloud-run/getviews_pipeline/answer_session.py` or a `reports/` sub-package.
- **Test:** unit test that a niche with a populated `insight_text` produces a report that contains it verbatim; a niche without one produces a valid report that omits the injection.

#### `ideas-next5-payload-schema` · ~1d · —
- **Schema change:** extend `IdeasPayload` Pydantic model — each finding now carries:
  - `rank: int` (1..5)
  - `hook_phrase: str` (existing, rename if needed for clarity)
  - `opening_line: str` (new — Vietnamese example of the first spoken line, 6–12 words)
  - `content_angle: str` (new — one-line angle, e.g. "So sánh 2 loại kem chống nắng cùng ngân sách")
  - `lifecycle_stage: Literal["early", "peak", "decline"]` (new — pulled from pattern data per hook)
  - `execution_tip: str | None` (from Layer 0 injection above)
  - `sample_size: int` (existing)
- **Critical files:**
  - `cloud-run/getviews_pipeline/report_*.py` or schema module (session context showed Pydantic V2 ConfidenceStrip, DiagnosticPayload, LifecyclePayload, ReportV1 envelope — IdeasPayload lives in the same location).
  - Wherever the Ideas-specific orchestrator lives (pipelines.py or answer_session.py).
- **Back-compat:** the new fields must be `Optional` on the way up so existing fixtures + in-flight sessions don't crash; FE gates rendering on presence.

#### `ideas-gemini-prompt-upgrade` · ~1–2d · —
- **Problem:** current Ideas prompt emits hook_phrase + sample_size per finding. It doesn't emit `opening_line` or `content_angle`.
- **Fix:** update the prompt template to require those fields in structured output (Pydantic-validated via `response_mime_type="application/json"` + schema), with concrete Vietnamese examples in the prompt.
- **Fallback:** if Gemini returns a malformed response, fill `opening_line` and `content_angle` from deterministic templates (e.g. "Mở bằng: [hook_phrase]...", "[hook_phrase] × [content_format]") so the renderer never sees null.
- **Critical files:**
  - `cloud-run/getviews_pipeline/prompts.py` (session context mentions this is the prompt home)
  - `cloud-run/getviews_pipeline/gemini.py` or wherever the Ideas-specific Gemini caller lives
- **Test:** golden-prompt test — fixture input niche produces a structured output passing the new Pydantic schema. Dogfood on 3 real niches and review hand-rated.

### Frontend PRs

#### `ideas-5next-reframe` · ~1d · —
- **Current:** `IdeasBody.tsx` renders findings as a generic ranked hook list with kicker `Ý TƯỞNG NỘI DUNG`.
- **Target:** reframe as a content calendar.
  - Kicker: `5 VIDEO TIẾP THEO` (mono 10px, accent-deep).
  - Section title (`.gv-tight` 28px): `Lịch quay tuần này` or similar — Vietnamese natural phrasing.
  - Each finding renders as a numbered card (1–5) with:
    - Top row: rank number `(.gv-bignum` small) + lifecycle pill (early/peak/decline)
    - Body: hook template in mono, opening line as a Vietnamese quote (gv-serif-italic), content angle as default body text
    - Bottom: sample_size + `execution_tip` if present (from Layer 0 injection)
  - Respect the design-system.md rules: no emoji, no colored left-border accents, use `<Card variant="paper">`, 18px radius, real data only (no lorem ipsum).
- **Critical files:**
  - `src/components/v2/answer/ideas/IdeasBody.tsx` (main renderer — session context confirmed path)
  - `src/components/v2/answer/ideas/` sibling components if any (SubCard, etc.)
- **Copy rules:** `.cursor/rules/copy-rules.mdc` — no forbidden openers (Chào bạn/Tuyệt vời/Wow/Đây là/Dưới đây là), no forbidden words (tuyệt vời/hoàn hảo/bí mật/công thức vàng/bùng nổ/siêu hot). Formula: *state the pattern → give the specific video*.

#### `home-ideas-quick-link` · ~0.5d · —
- **Target:** add a card on the Home screen with:
  - Kicker: `LỊCH QUAY TUẦN NÀY` (mono 10px)
  - Title: creator's niche pre-filled (e.g. "Skincare")
  - Body: "5 video tiếp theo bạn nên làm, dựa trên 7 ngày gần nhất trong ngách."
  - CTA: "Mở báo cáo" → navigates to a pre-populated Ideas session.
- **Critical files:**
  - Home route: `src/routes/_app/` (session context mentions `_app` layout + home route — grep for Home- or Pulse- prefixed screens)
  - New card component in `src/components/v2/` (follow the `<Card variant="paper">` + `<SectionHeader>` pattern already established)

### Dependencies from Wave 1

- **hook_type eval** passing ≥ 0.85 (so we trust the hook_type labels flowing into Ideas).
- **Phase 1 corpus growth** live — 3 niches at 200+ videos each. Session target: Skincare (113), Review đồ ăn (128), Gym/Fitness (106) are already near/above 100; Phase 1 should push at least Skincare and Review đồ ăn above 200 in 7 days.
- **Layer 0 weekly cron** healthy (Wave 0 scheduled it; verify before this wave starts that `niche_insights` has rows < 14 days old).

### Validation gate → Wave 3

- **Focused gate** (per reviewer correction): 3 pre-selected niches — Skincare, Review đồ ăn, Gym/Fitness — each at 200+ videos, produce Ideas reports with 5 cards each, every card has populated `hook_phrase` + `opening_line` + `content_angle` + `execution_tip`.
- **Internal dogfood:** 3 team members generate Ideas in their primary niche, rate cards 4+/5 on "would actually help me make a video next week."
- **No fixture data:** `ConfidenceStrip` shows real `sample_size ≥ 30` for all 3 niches (not the low-confidence fixture fallback path).

### Risk flags

- **Layer 0 injection could fail gracefully on stale/missing rows and nobody notices.** Guard with a log warning at INFO level + a `batch_job_runs`-style metric so operators see "N of M reports injected".
- **Gemini prompt for `opening_line` could produce generic or repeat across findings.** Validation: structured-output test asserting distinct `opening_line` values across the 5 ranks.
- **Home quick-link adds a new home-card pattern.** Keep it on-brand (no new typography, reuse existing `<Card>` + `<SectionHeader>` + `<Btn>` primitives from `src/components/v2/`).
- **Calendar could slip.** Ideas enrichment is the single longest PR (2–3d alone). If prompt engineering stalls, the template fallback keeps the wave shippable at slightly lower quality.

### Calendar

9–10 working days. BE blocks ~5d (Layer 0 + schema + prompt), FE blocks ~1.5d (IdeasBody + home card), plus 2–3d dogfood + fix loop. Can parallelize BE + FE once the payload schema PR lands (1 day in).

---

## Wave 3 — diagnosis polish + viral-score DESIGN

**End-of-wave moment:** *"Diagnosis reports surface the niche's execution_tip prominently, and we have a pre-committed viral-score formula validated against historical data — no feature shipped yet, but the spec is approved."*

**Why now:** Reviewer correctly flagged that shipping a viral-score with a hand-waved formula erodes trust faster than no score. This wave produces the *spec*, validates it against retrospective corpus data (backtest), and gets sign-off — so Wave 4's build is implementation-only, not design-during-build. In parallel, this wave polishes the `video_diagnosis` flow (the #1 pay-signal feature from the survey) using the Layer 0 injection from Wave 2 + survey-informed copy tweaks.

### Scope

| Track | Item | Axis |
|---|---|---|
| BE | Diagnosis polish — inject `execution_tip` into video_diagnosis flow (reuses Wave 2 work) | 2 |
| BE | Diagnosis copy tightening — align to survey voice ("peer expert, not product pitch") | — |
| Design doc | Viral-alignment score FORMULA — written, calibrated, backtested on `video_corpus` | — |
| BE | Backtest harness — new module that runs the proposed formula over historical rows and reports score distribution | 4 |
| FE | Diagnosis `execution_tip` surface pattern | — |

### Backend PRs

#### `diagnosis-execution-tip-injection` · ~0.5d · Axis 2
- The Wave 2 `layer0-narrative-injection` generalized `_get_niche_insight()` (from `pipelines.py:1012`). Reuse it in the video_diagnosis flow.
- `cloud-run/getviews_pipeline/pipelines.py:1238` already calls `_get_niche_insight` in the diagnosis flow — but the fetched data isn't surfaced to the user in `report_diagnostic.py` payload. Wire it through: add `niche_execution_tip: str | None` to `DiagnosticPayload`.
- **Critical files:**
  - `cloud-run/getviews_pipeline/pipelines.py` (existing diagnosis orchestrator)
  - `cloud-run/getviews_pipeline/report_diagnostic.py` (or wherever `DiagnosticPayload` lives — session context confirmed this is its own file)

#### `diagnosis-copy-tightening` · ~0.5d · —
- Dogfood 5 real diagnosis sessions, mark every line that reads "product-pitch" or "guru" rather than "peer expert in a Zalo group." Rewrite.
- Test against the `.cursor/rules/copy-rules.mdc` forbidden-word + forbidden-opener list.
- **Critical files:**
  - `cloud-run/getviews_pipeline/prompts.py` (`build_diagnosis_narrative_prompt` is the likely target — confirmed via `gemini.py` references in session context)
  - Vietnamese copy slots in `src/components/v2/answer/diagnostic/DiagnosticBody.tsx` for any UI-literal strings.

#### `viral-score-backtest-harness` · ~1d · Axis 4
- **Purpose:** before committing to a formula, run the proposed scoring on the last 200 videos in the corpus and report:
  - Score distribution (histogram) — should NOT be all clustered at 70-80 (the reviewer's warning about unreliable spread)
  - Correlation with actual `views / creator_velocity.avg_views` (breakout_multiplier) — the score should predictively order videos
  - Behavior on low-sample niches — graceful "insufficient data" vs a noisy score
- **New module:** `cloud-run/getviews_pipeline/viral_alignment_backtest.py`
- **Integration:** called via a new admin trigger `/admin/trigger/viral_score_backtest` (mirror existing admin trigger pattern from `routers/admin.py`). Stores results as a one-off `batch_job_runs` row with `job_name='viral_score_backtest'` for easy query.
- **Critical files:**
  - new `cloud-run/getviews_pipeline/viral_alignment_backtest.py`
  - `cloud-run/getviews_pipeline/routers/admin.py` — add `_admin_run_viral_score_backtest` runner + endpoint following the exact pattern we established in Wave 0

### Design doc

#### `viral-alignment-score-formula.md` · ~2d · —
- **Location:** `artifacts/docs/viral-alignment-score.md`
- **Required sections:**
  1. **Purpose:** what question does the score answer? (Explicit framing: "how well does this video align with what's currently winning in its niche" — NOT "will this go viral.")
  2. **Formula v1 candidate:** exact math. Proposed starting point:
     ```
     score = 100 × w_hook × hook_alignment
           + 100 × w_format × format_alignment
           + 100 × w_time × time_alignment
     where
       hook_alignment   = (# of top-30 niche videos w/ same hook_type) / 30
       format_alignment = (# of top-30 w/ same content_format) / 30
       time_alignment   = 1 - min(1, |posting_hour - niche_peak_hour| / 6)
       w_hook=0.5, w_format=0.3, w_time=0.2 (initial, to be calibrated)
     ```
  3. **Top-30 definition:** top-30 by `breakout_multiplier DESC` in the submitted video's niche, rolling 30d window.
  4. **Low-sample graceful degradation:** if niche has < 30 rows with `breakout_multiplier`, return `score=null, reason="insufficient_data"` — NO partial score.
  5. **Calibration tables:** score-to-tier mapping decided AFTER backtest (no arbitrary 80=green):
     - Tier thresholds picked so "top 20% of backtested videos" map to the top UI tier, middle 60% to middle tier, bottom 20% to low tier.
  6. **Backtest results:** paste distribution + correlation numbers from the backtest harness. Threshold for approval: score must correlate with `breakout_multiplier` at Spearman ρ ≥ 0.35 across the 200-video sample.
  7. **Reasoning bullets spec:** 3 Vietnamese bullets, each tied to one of the 3 dimensions. Deterministic templating (not Gemini-generated), so every bullet is auditable.
- **Exit criteria:** doc committed + Spearman ρ ≥ 0.35 demonstrated + formula approved by you. Wave 4 does NOT start until this lands.

### Frontend PR

#### `diagnosis-execution-tip-surface` · ~0.5d · —
- Thread the new `niche_execution_tip` field through `DiagnosticBody.tsx` — render inside the "What to do next" slot as a distinguished callout (brutalist card, `.gv-surface-brutal--compact`, kicker `GỢI Ý NGÁCH`).
- **Critical files:**
  - `src/components/v2/answer/diagnostic/DiagnosticBody.tsx`

### Dependencies from Wave 2

- `layer0-narrative-injection` helper exists (reused here).
- Corpus has at least 3 niches with ≥ 200 videos each AND populated `breakout_multiplier` on > 50% of their rows (needed for backtest validity).

### Validation gate → Wave 4

- Design doc `viral-alignment-score.md` committed with backtest results.
- Spearman ρ ≥ 0.35 between score and `breakout_multiplier` on 200-video sample.
- Score distribution shows meaningful spread — at least 20% of backtested videos in each tier (no > 60% single-tier dominance).
- `diagnosis-execution-tip-injection` live for ≥ 3 days with no regression complaints.
- Diagnosis copy dogfooded 5 sessions, zero forbidden-word / forbidden-opener flags.

### Risk flags

- **Backtest reveals the formula is bad.** Very possible on first iteration. Buffer: 2d spec writing can loop up to 3×. Each loop adjusts weights or adds a dimension (e.g. creator_tier, video_duration bucket) and re-backtests.
- **Spearman ρ could be < 0.35 even after multiple iterations** if the signal genuinely isn't there at current corpus size. In that case, Wave 4's score BUILD is cut (or deferred) and Wave 4 becomes Compare-only.
- **Diagnosis copy dogfood could surface deeper prompt problems** (not just phrasing). If so, the copy-tightening PR grows — buffer 1–2 extra days.

### Calendar

5–7 working days. Design doc is the critical path (~2–3d writing + 1d backtest + 1–2d iteration). BE + FE sub-PRs fit alongside.

---

## Wave 4 — Compare intent (score BUILD cut — see §4 note)

**End-of-wave moment:** *"A creator pastes two TikTok URLs and gets
side-by-side diagnosis with a delta summary — same-tier analysis for
both videos, one-sentence Vietnamese verdict on what's different."*

**Scope change vs original plan:** the viral-alignment score BUILD is
CUT from this wave. Wave 3 PR #5 backtested the proposed formula on
352 scoreable videos and measured ρ = 0.14 against breakout_multiplier
(gate: ≥ 0.35). See `artifacts/docs/viral-alignment-score.md` §9
verdict. Wave 4 ships Compare-only; the score re-opens under a later
wave when any of the §11 re-evaluation triggers fires (Wave 2.5
enrichment propagated, corpus 10K+, a niche 200+ breakout-scored,
breakout formula revised, or new candidate dimension shipped).

**Why now:** Compare reuses the now-polished `video_diagnosis`
orchestration from Wave 3 + the Wave 2.5 reference-video plumbing.
It's not in the pay-signal top 3 per the survey, which is fine — the
value is as the "I can see what I'm missing" follow-up move after the
single-video diagnosis lands for a creator.

### Scope

| Track | Item | Axis |
|---|---|---|
| BE | `compare_videos` intent in intent router | — |
| BE | Compare orchestration — parallel `video_diagnosis` + delta summary | — |
| BE | `ReportV1` schema extension: `kind: "compare"` variant | — |
| FE | Compose UI — detect 2 URLs, show confirmation chip | — |
| FE | `CompareBody.tsx` — side-by-side diagnostic layout | — |

**CUT from original Wave 4 scope:**
- ~~Viral-alignment score — build to Wave 3 spec~~
- ~~Viral-score pill on `DiagnosticBody`~~

### Backend PRs

#### `compare-videos-intent` · ~1d · —
- **Intent detection:** extend `cloud-run/getviews_pipeline/intent_router.py` — when message contains ≥ 2 TikTok URLs (existing URL regex can be extracted via grep), return intent `compare_videos`.
- Also extend the frontend tier-1 router mirror at `src/routes/_app/intent-router.ts` to detect the same pattern (required because frontend decides whether to route to `/api/chat` vs Cloud Run; compare needs Cloud Run).
- **Critical files:**
  - `cloud-run/getviews_pipeline/intent_router.py`
  - `src/routes/_app/intent-router.ts` + its test `intent-router.test.ts` (CLAUDE.md mandates extending the test).

#### `compare-orchestration` · ~1.5–2d · —
- **New pipeline:** `cloud-run/getviews_pipeline/pipelines.py` gets `run_compare_pipeline(url_a, url_b, ...)`.
  - Calls `run_video_diagnosis(url_a)` + `run_video_diagnosis(url_b)` via `asyncio.gather` (parallel).
  - After both return, assembles a `ComparePayload` with:
    - `left: DiagnosticPayload`
    - `right: DiagnosticPayload`
    - `delta: {retention_gap: float, scene_count_diff: int, hook_alignment: Literal["match","conflict"], verdict: str}`
    - `delta.verdict` is a 1-sentence Vietnamese summary: "Video trái giữ 72% → top 20%. Video phải giữ 41% → dưới sàn. Khác biệt chính: hook face-to-camera vs text-overlay."
- **Streaming:** the SSE stream must emit `left` and `right` progressively as each diagnosis completes, then `delta` at the end — for a better UX than waiting for both to finish silently. Pattern: re-use whatever progressive streaming primitive `video_diagnosis` uses today.
- **Critical files:**
  - `cloud-run/getviews_pipeline/pipelines.py`
  - `cloud-run/getviews_pipeline/report_compare.py` (new, houses `ComparePayload`)
  - `cloud-run/getviews_pipeline/answer_session.py` — add `compare` to `select_builder_for_turn` (session context confirmed this is the dispatcher)
  - Pydantic schema update in whichever module houses `ReportV1` discriminator — add `kind: Literal["compare"]` variant.

<!--
  `viral-alignment-score-impl` intentionally removed — score BUILD
  cut per Wave 3 PR #5 verdict. When re-opened, the runnable reference
  is `viral_alignment_backtest.compute_viral_score()` — already the
  canonical formula; a production module would be a thin reshape
  around it.
-->

### Frontend PRs

#### `compose-two-url-chip` · ~0.5d · —
- When the compose input contains ≥ 2 TikTok URLs (detected by the existing URL pattern in `src/lib/` — grep `tiktok.com`), show a pre-submit chip "So sánh 2 video" using `<Chip variant="accent">` so the user confirms the intent before SSE starts.
- **Critical files:**
  - Compose component — grep `src/components/` for the composer Surface (session context: `gv-surface-brutal`).
  - `src/routes/_app/intent-router.ts` for detection mirror.

#### `compare-body-component` · ~1.5d · —
- **New file:** `src/components/v2/answer/compare/CompareBody.tsx`
- **Layout:**
  - Desktop (`min-[900px]:`): 2-column side-by-side. Each column renders a slim `<DiagnosticBody>` variant (re-export a `compact` prop on existing DiagnosticBody rather than duplicating).
  - Mobile (< 900px): stacked. Sticky column header shows "A" / "B" labels so the user tracks which one they're scrolling.
  - Delta summary bar pinned to the top: `<Card variant="brutal">` with kicker `KHÁC BIỆT CHÍNH`, 1-sentence verdict.
- **Progressive reveal:** if streaming emits `left` first, render it + show a skeleton for `right`; fill as it arrives.
- **Respect design-system.md:** no emoji, 18px radius, `<Card variant="paper">` for inner content, no new typography utilities.
- **Critical files:**
  - new `src/components/v2/answer/compare/CompareBody.tsx`
  - adjust `src/components/v2/answer/diagnostic/DiagnosticBody.tsx` to accept a `compact: boolean` prop.

<!--
  `viral-score-pill` FE PR intentionally removed — see the BE-side
  note above. Re-opens together with `viral-alignment-score-impl`.
-->

### Dependencies from Wave 3

- `viral-alignment-score.md` committed (✅ shipped — verdict: DEFER).
- Diagnosis polish + execution_tip surface live (since Compare reuses `DiagnosticBody`). ✅ shipped.

### Validation gate → Wave 5+

- **Compare:** 5 internal compare sessions run end-to-end across different niches. Response payload < 100KB (two diagnostics doubles payload — verify not hitting SSE chunk limits).
- **Dogfood:** 3 team members rate 4+/5 that the compare report teaches them something new about their content vs a competitor's.
- **No regressions:** `DiagnosticBody` single-video flow + existing reports (Pattern, Ideas, Timing, Lifecycle) unchanged in look and performance.

### Risk flags

- **Compare SSE payload could hit chunk-size limits.** Mitigation: the progressive reveal requires chunked emission anyway; size per chunk stays bounded.
- **Compare UX on mobile could feel cramped.** Stacked layout with sticky A/B labels is the safer choice; avoid a tab-switcher (adds friction for side-by-side comparison).
- **Delta verdict could read like hype** ("Video trái vượt trội…"). Route every generated delta sentence through the Wave 3 PR #3 `voice_lint` helper before shipping — forbidden-word / peer-expert gate applies.

### Calendar

**Revised: 5–7 working days** (was 7–10). Compare BE + FE ≈ 4–5d, 1–2d dogfood + polish. Score BE+FE (originally 2–3d) is removed.

---

## Wave 5+ — ongoing (no fixed calendar)

**Goal:** keep compounding quality + growth after the 4 survey-informed waves ship. Pick items opportunistically; each is 0.5–1d and safe to ship in isolation.

### Growth continuation (Axis 1)

- **Phase 2 — thin-niche prioritization** · ~1d
  - Pre-ingest query ranks niches by `(target - current_count)` and grants thin niches a 2–3× quota multiplier.
  - Critical files: `cloud-run/getviews_pipeline/corpus_ingest.py` — `_pick_hashtags_for_pool_fetch` + `run_batch_ingest`.
  - Exit: per-niche allocation logged in ingest summary; thinnest niches close the gap faster than richest.
- **Phase 2 — cron cadence 1×/d → 4×/d** · ~0.25d
  - Update `cron-batch-ingest` schedule in `cron.job`: `0 20 * * *` → `0 */6 * * *`.
  - Verify ED burn stays within 5000/day cap (each run ~500–700 units at `BATCH_VIDEOS_PER_NICHE=25`).
- **Phase 3 — add 5–10 new niches** · ~0.5d per niche
  - Candidates: K-pop / Âm nhạc (separate from Chị đẹp), Học tiếng, Crypto/Web3, Xe máy/Moto culture, Nội thất (split from Nhà cửa).
  - Each: `niche_taxonomy` row + curated signal_hashtags + spot-check ingest.

### Axis 4 quality discipline

- **Expand content_format golden set 27 → 60** · ~1d
  - Hand-curate 33 more items focused on the buckets currently at < 2 representatives (pov, dance, faceless, outfit_transition).
  - Raise CI floor to 0.97 once 60-item accuracy holds.
- **`cta_type` classifier golden set** · ~0.5d
  - Mirror `content_format_golden.json`; ~20 items across the 7 cta_type labels.
- **`history → story` substring bug fix** · ~15min
  - Known classifier miss surfaced during Wave 0 eval-harness PR. Update the storytelling regex to use word boundaries.

### Axis 5 observability residual

- **Daily health digest** · ~1d
  - New Supabase Edge cron `cron-daily-health-digest` queries `batch_job_runs` + corpus stats + `gemini_calls` + ED burn from the last 24h, formats a Vietnamese-language digest, fires via Resend.
  - Follows the existing cron-email pattern (see `cron-prune-webhooks` / `cron-expiry-check`).

### Axis 2 open product decision

- **Taxonomy expansion — gameplay / comedy_skit / lesson / highlight** · shipped 2026-04-25
  - Decision: greenlit. Design doc at `artifacts/docs/taxonomy-expansion.md` (Wave 5+ scaffold + 4 buckets + build plan + gates).
  - Build PR: `claude/wave5-taxonomy-expansion-build` — 4 new buckets in `classify_format`, FORMAT_ANALYSIS_WEIGHTS + Vietnamese prompt snippets, golden set 54 → 66 (+12 items, 3 relabels), 24 regression tests.
  - Eval lift: 49/54 = 0.9074 → 63/66 = 0.9545. All 4 new buckets at 100% recall. MIN_ACCURACY floor raised 0.88 → 0.92, MIN_CORE_RECALL 0.5 → 0.8.
  - **Post-merge ops:** kick `POST /admin/run/reclassify-format` (regex-only catch-up over `other`/NULL rows, ~45s), then `SELECT refresh_niche_intelligence()`. Measure §8.3 gates from the design doc — record outcome in `artifacts/docs/taxonomy-expansion.md` decision log.

---

## End-to-end verification protocol

For each wave, validate against BOTH the exit criteria in the wave's own section AND the global checks below.

### Global checks (run after each wave)

```sql
-- 1. Pipeline health — no stuck jobs
SELECT job_name, status, started_at
FROM public.batch_job_runs
WHERE status = 'running'
  AND started_at < NOW() - INTERVAL '30 minutes';
-- Expect: 0 rows. Any running-for-too-long is a zombie.

-- 2. Observability continuity — no silent cron days
SELECT date_trunc('day', started_at) AS d,
       COUNT(*) FILTER (WHERE job_name = 'batch/ingest')      AS ingest_runs,
       COUNT(*) FILTER (WHERE job_name = 'batch/refresh')     AS refresh_runs,
       COUNT(*) FILTER (WHERE status = 'failed')              AS failed_runs,
       SUM((summary->>'error_types')::jsonb::text != '{}' AND (summary->>'error_types') IS NOT NULL)::int AS error_runs
FROM public.batch_job_runs
WHERE started_at > NOW() - INTERVAL '7 days'
GROUP BY 1
ORDER BY 1 DESC;
-- Expect: ingest_runs ≥ 1/day, refresh_runs ≥ 1/day, failed_runs = 0 OR matching alert fire.

-- 3. Eval harness regression — content_format accuracy holds
-- Run locally: cd cloud-run && python -m pytest tests/test_classifier_eval.py
-- Expect: 4/4 passed, accuracy ≥ 0.95.

-- 4. Corpus growth — trending up, not stalled
SELECT date_trunc('day', indexed_at) AS d, COUNT(*) AS new_videos
FROM public.video_corpus
WHERE indexed_at > NOW() - INTERVAL '14 days'
GROUP BY 1
ORDER BY 1 DESC;
-- Expect: rolling 7-day sum trending up post-Wave 1 Phase 1.

-- 5. hook_effectiveness freshness
SELECT MAX(computed_at) AS latest FROM public.hook_effectiveness;
-- Expect: < 8 days old (weekly analytics cron writes).
```

### Per-feature dogfood protocol

Every wave ends with a structured dogfood session:

1. **3 reviewers**, each in a different real niche they understand.
2. **5 sessions** per reviewer against the wave's headline feature.
3. **Rate each output on 1-5:**
   - Accuracy: does it say true things about this niche?
   - Specificity: could I act on this today?
   - Voice: would this work in a Vietnamese creator Zalo group?
4. **Wave passes** at median 4+/5 across all 15 sessions.
5. **Fail → fix + re-dogfood.** No shipping a wave on 3/5 average.

---

## Consolidated risk register

| Risk | Wave | Mitigation | Buffer |
|---|---|---|---|
| hook_type accuracy < 0.85 on first eval | 1 | Wave 1.5 prompt-engineering PR before Wave 2 starts | 2–3 extra days |
| ED daily burn exceeds 5000 | 1 | `batch_job_runs.summary->'error_types'` catches `EnsembleDailyBudgetExceeded`; throttle `BATCH_VIDEOS_PER_NICHE` down | alert fires before data loss |
| Layer 0 injection silently skipped | 2 | INFO-level log + metric "N of M reports injected" | visible in dogfood |
| Ideas prompt emits generic `opening_line` | 2 | Structured-output assertion: distinct values across 5 ranks | test gate |
| Viral-score backtest ρ < 0.35 | 3 | ~~Iterate formula up to 3×~~ ✅ **Activated** — backtest measured ρ = 0.14; Wave 4 score BUILD cut per `artifacts/docs/viral-alignment-score.md` §9 | Wave 4 reduced to Compare-only |
| Compare SSE payload exceeds chunk limits | 4 | Progressive per-diagnostic reveal; bounded per-chunk size | verify on first 3 sessions |
| Taxonomy decision unresolved | 5+ | 37% 'other' stays as-is until greenlit | not blocking other waves |

---

## Calendar summary

| Wave | Calendar | Cumulative | End-of-wave creator promise |
|---|---|---|---|
| 1 | 5–7d | 5–7d | Pipeline can't fail silently; corpus growing 2.5× |
| 2 | 9–10d | 14–17d | Ideas = 5 videos with hook + opening + angle |
| 3 | 5–7d | 19–24d | Diagnosis surfaces execution_tip; viral-score spec approved |
| 4 | 7–10d | 26–34d | Compare A vs B + viral-alignment pill on diagnosis |
| 5+ | ongoing | — | Growth + discipline continuation |

**~30–35 working days solo @ 4h/d effective. ~3.5 weeks with parallel FE + BE hands.**

Every wave has a single-sentence promise a Vietnamese creator would read and nod. That's the bar.

---

## Critical file reference (for execution)

### Backend (Cloud Run)

| Area | File | Used in |
|---|---|---|
| Intent routing | `cloud-run/getviews_pipeline/intent_router.py` | Wave 4 |
| Frontend intent mirror | `src/routes/_app/intent-router.ts` + `intent-router.test.ts` | Wave 4 |
| Pipelines orchestrator | `cloud-run/getviews_pipeline/pipelines.py` | Waves 2, 3, 4 |
| Answer session dispatcher | `cloud-run/getviews_pipeline/answer_session.py` (`select_builder_for_turn`) | Wave 4 |
| Prompts | `cloud-run/getviews_pipeline/prompts.py` | Waves 2, 3 |
| Gemini caller | `cloud-run/getviews_pipeline/gemini.py` | Waves 1, 2 |
| Classifier | `cloud-run/getviews_pipeline/corpus_ingest.py` (`classify_format`, `_classify_cta`) | Wave 1 audit |
| Eval harness | `cloud-run/getviews_pipeline/eval_classifier.py` | Waves 1, 5+ |
| Admin triggers | `cloud-run/getviews_pipeline/routers/admin.py` | Wave 3 backtest trigger |
| Niche insight fetcher | `cloud-run/getviews_pipeline/pipelines.py:_get_niche_insight` (line ~1012) | Waves 2, 3 |

### Frontend (React SPA)

| Area | File | Used in |
|---|---|---|
| Ideas report body | `src/components/v2/answer/ideas/IdeasBody.tsx` | Wave 2 |
| Diagnostic body | `src/components/v2/answer/diagnostic/DiagnosticBody.tsx` | Waves 3, 4 |
| Compare body (new) | `src/components/v2/answer/compare/CompareBody.tsx` | Wave 4 |
| Viral pill (new) | `src/components/v2/ViralAlignmentPill.tsx` | Wave 4 |
| v2 primitives | `src/components/v2/` (Card, Btn, Chip, SectionHeader, Kicker) | every wave |
| Landing + auth | `src/routes/_index/LandingPage.tsx`, `src/routes/_auth/login/route.tsx` | Wave 1 copy fix |
| Design system reference | `artifacts/docs/design-system.md` | every FE PR |
| Copy rules | `.cursor/rules/copy-rules.mdc` | every wave |

### Migrations (chronological queue)

| # | File | Wave |
|---|---|---|
| 1 | `supabase/migrations/20260510000000_alert_rule_cron_failures.sql` | 1 |
| 2 | `supabase/migrations/20260510000001_gemini_calls_success.sql` | 1 |
| 3 | `supabase/migrations/20260510000002_hashtag_expansion_4_niches.sql` | 1 |
| 4 | (possible) schema updates for `IdeasPayload` — via Pydantic, no DB migration | 2 |
| 5 | (possible) new table for eval run history if DB persistence lands | 5+ |

---

*End of plan. Each wave is a commit in this branch's history — `git log` reads as a coherent argument from context → strategy → waves.*





