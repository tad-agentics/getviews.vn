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


