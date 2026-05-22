# Changelog — GetViews.vn

## 2026-05-22 — Docs: resync feature-map-v1 with two-axis as-built

- **`feature-map-v1.md`:** Header `8969f3e`; §3 Morning Signal + Tier III copy; CrossNiche lane; §8 taxonomy 16×82 + HI-11 route prod; §13A/B shipped vs open gates; D12 two-axis done.
- **`feature-map.md`:** As-built inventory synced (prior commit `8969f3e`).

## 2026-05-22 — Docs: archive PR1–PR6 cutover, trim HI-11 runbook

- Archive `two-axis-niche-cutover-pr1-pr6.md` (completed 2026-05-13 cutover).
- Runbook → HI-11 + ME-18 ops only; Phase C SQL fix (`ingest_loop_niche_id`).
- Audit: keep `taxonomy-expansion.md`, `hashtag-class-map-v2.md` (orthogonal to niche-model SSOT).

## 2026-05-22 — Taxonomy v2 (Art & Craft, Comedy restore, AI class)

- **Migration:** `20260824000000_taxonomy_v2_art_comedy_ai.sql` — UX `art_craft` (17), restore `comedy` (5), classes 80–82, junction + legacy ingest 13/29.
- **BE/FE parity:** `two_axis_taxonomy.py`, `profile_niches.py`, `profileNiches.ts`, `junction_content_class.py`; junction counts 56 video + 80 carousel = 136.
- **Doc:** `two-axis-niche-model.md` — 16 active niches, 82 classes.

## 2026-05-22 — Merge taxonomy doc into two-axis-niche-model.md

- Gộp `two-axis-taxonomy-final-v1.md` → `two-axis-niche-model.md` (§2–5 taxonomy tables, §13 sign-off); xóa file taxonomy riêng.
- Cập nhật cross-link `productionFriction.ts` → §3.2.

## 2026-05-22 — Migration apply + stats MV recreate fix

- **Applied remote:** `20260823000000`–`000003` on Getviews.vn (`lzhiqnxfveqttsujebiv`).
- **Fix:** `20260823000004` — `000001` CASCADE dropped `creator_niche_content_class_stats`; recreated + refreshed MVs (`cci_rows=62`, `stats_rows=150`).

## 2026-05-22 — Pre-deploy QA fixes (two-axis)

- **Cross-niche lane:** `useCrossNicheBreakouts` no longer requires non-empty junction — empty junction shows global breakouts; unit tests for PostgREST exclude filter.
- **MV RLS:** `creator_niche_content_class_stats` — `SELECT` grant aligned to `authenticated` only (removed `anon`).
- **Test:** `ChannelScreen.test.tsx` — niche switch assertion matches query param (4, not retired id 5).

## 2026-05-22 — Wave T formal sign-off + corpus ingest fix

- **Wave T signed:** `two-axis-taxonomy-final-v1.md` status line + expanded Sign-off evidence table; `two-axis-taxonomy-audit.json` (`wave_t_signed`, triage status); `wave-t-baseline.json` QA gate PASS.
- **Fix:** `corpus_ingest.py` — restore `_run_weekly_analytics()` (body was orphaned after `return summary`, breaking Sunday weekly analytics); batch log now includes `hi11_junction_reject`.
- **§8.1 MV chain:** No pg_cron stagger migration needed — `run_ingest_post_processing()` already calls `_refresh_corpus_intelligence_mvs()` serially post-ingest.

## 2026-05-22 — Phase 2 resilience scaffold (§T2.2)

- **Doc:** `two-axis-taxonomy-final-v1.md` §T2.2 — algorithm drift, creative friction, active learning hooks.
- **FE:** `productionFriction.ts` + energy toggle on `MorningSignalStrip`; `pickMorningSignals` filters by low friction when "Quay nhẹ hôm nay".
- **ACQE:** `_export_hook_marker_candidates`, `_export_taxonomy_drift_candidates` → `hook-marker-candidates.json`, `taxonomy-drift-candidates.json`.

## 2026-05-22 — Taxonomy feedback fixes (doc + code)

- **Doc:** `two-axis-taxonomy-final-v1.md` — wellness legacy bridge → 26; §T4 format_axis vocabulary; §T3.1 trade-offs; §T2.1 intentional sparse cells (Art/Craft, Comedy/Skit, AI/Automation gaps); lifestyle primary promotion documented.
- **Migration:** `20260823000003_taxonomy_feedback_fixes.sql` — `comedy_observational` format_axis → `observational_relatable`; lifestyle primary for classes 24–27, 69–74.
- **BE:** `two_axis_taxonomy.py`, `junction_content_class.py` (retire + feedback migrations), `cross_format.py`, `models.py`.
- **FE:** `fetchContentClassIdsForCreatorNiche(..., { primaryOnly })`; Morning Signal uses primary-only junction scope.

## 2026-05-22 — Two-axis enhancement (Wave T, D, 1a, 3a, 3b, Phase 2 FE)

- **Wave T:** `artifacts/docs/two-axis-taxonomy-final-v1.md` — Outcome A: 14 active UX niches, 79 content classes; retirement map comedy/pets_home → lifestyle.
- **Wave D:** Consolidated `artifacts/docs/two-axis-niche-model.md` (TOC §1–11); updated `system-design.md` §354 (14 active, Phase C, 3 MVs, refresh chain, no niche_intelligence fallback); archived `niche-taxonomy-ingest-ui-pipeline.md` → `archive/`.
- **Wave 1a:** `artifacts/qa-reports/junction-invalid-triage-v1.json` — 22-row decision tree (reclassify vs defer Wave 4).
- **Wave 3a:** `class-intelligence-ui-spec.md`; migration `20260823000001_content_class_intelligence_velocity.sql`; `useClassMorningSignals`, `MorningSignalStrip` (Max-2-Card), extended `useContentClassIntelligence`; unit tests `classMorningSignals.test.ts`.
- **Wave 3b:** `CrossNicheBreakoutLane` on Explore (cap 3 tiles outside junction).
- **Phase 2 FE:** `peer_percentile_label` + carousel save ≥3% hint in `FlopDiagnosisStrip` (forward-compatible; no BE RPC yet).

## 2026-05-22 — Two-axis enhancement backend (Waves 1b–1d, 2, 3c, 4, Phase 2 BE)

- **Wave T (BE):** `artifacts/qa-reports/two-axis-taxonomy-audit.json` — code-truth counts; 22 junction-invalid baseline documented.
- **Wave 1b:** TD-6 hard gate + `hi11_junction_reject` metric in `corpus_ingest.py`; `creator_niche_has_content_class()` in `junction_content_class.py`.
- **Wave 1c:** `artifacts/qa-reports/hi11-confidence-threshold-eval.json` — recommend confidence floor 0.6.
- **Wave 1d:** ACQE junction proposal export + >0.5% junction-invalid alert in `class_quality_engine.py`.
- **Wave 2:** `report_diagnostic`, `corpus_context`, `video_niche_benchmark` — `content_class_intelligence` reads; deprecated `fetch_niche_intelligence_sync` shim.
- **Wave 3c:** `20260823000000_creator_niche_content_class_stats_mv.sql`; `morning_ritual` MV class anchor.
- **Wave 4:** `20260823000002_wave4_approved_junction_edges.sql` — 6 secondary junction edges.
- **Phase 2 BE:** `peer_percentile`, `carousel_diagnosis_thresholds` in `video_niche_benchmark.py`.

## 2026-05-21 — Content-class pivot Phase C (`video_corpus.niche_id` dropped)

- **Migration:** `20260822000001_phase_c_drop_video_corpus_niche_id.sql` — backfill `ingest_loop_niche_id`, update RPCs (`upsert_video_corpus_batch`, `corpus_hashtag_yields_14d`, `daily_corpus_growth_by_niche`, timing/pattern/channel helpers), recreate class MVs without `SELECT *`, drop `niche_id` column + indexes.
- **Batch:** upsert never sends `niche_id`; corpus row builder omits legacy column.
- **Cloud Run:** `video_corpus` filters use `ingest_loop_niche_id` (taxonomy loop bucket).
- **FE:** browse filters are `content_class_id IN (...)` only — no `video_corpus.niche_id` fallback.
- **Post-deploy:** run nightly batch ingest (or manual `/batch/ingest`) so MVs repopulate after migration.

## 2026-05-19 — Content-class pivot Round B (trends class + legacy MV drop)

- **FE:** `useTopPatterns` + `TrendingSoundsSection` scoped by junction `content_class_id`; removed `VITE_CORPUS_BROWSE_*` dual-path flags; `corpusNicheFilter` class-only when junction non-empty.
- **BE:** `sound_aggregator` loops `content_class_ingest_targets`; ticker/trend_velocity/pipelines read class-scoped `trending_sounds`; benchmark drops legacy niche-first branch; corpus ingest skips `niche_intelligence` refresh.
- **Migration:** `20260821000001_round_b_class_trends_cleanup.sql` — `trending_sounds.content_class_id`, truncate + drop `niche_id`; DROP `niche_intelligence` MV + `refresh_niche_intelligence()`.
- **Superseded by Phase C (2026-05-21):** `video_corpus.niche_id` dropped; use `content_class_id` + `ingest_loop_niche_id`.

## 2026-05-21 — Docs housekeeping Round A (pivot SSOT sync)

- **SSOT banners** on 10 secondary docs → link `system-design.md` §9 + `niche-taxonomy-ingest-ui-pipeline.md` §10.
- **Stale fixes:** `supabase-pipeline-table-audit` (dropped `channel_formulas`, niche MV refresh off), `feature-map-v1` launch gates, `feature-map` `/channel/analyze` removed, `system-design` Phase 2 cleanup marked DONE, HI-11 runbook prod `route`, `project.mdc` channel endpoint.
- **Code smell (no behavior change):** `routers/video.py` module docstring — drop deleted `/channel/analyze` reference.

## 2026-05-21 — Docs: pivot production state sync

- **`system-design.md` §9 + §12.1:** HI-11 prod `route`; browse/thin-banner defaults; full pivot env stack + rollback; class loop default on.
- **`CLAUDE.md`:** niche model bullets aligned with promoted flags.
- **`niche-taxonomy-ingest-ui-pipeline.md`:** §5.1 browse order, §5.4 thin fallback, §10 phase table.

## 2026-05-21 — Content-class pivot Phase 4 promoted

- **Batch defaults:** `CORPUS_WRITE_NICHE_ID=false` (upsert omits `niche_id`); `REFRESH_NICHE_INTELLIGENCE_MV=false` (skip legacy MV; class MVs still refresh).
- **FE default:** `VITE_CORPUS_BROWSE_CLASS_ONLY` opt-out (`"false"` re-enables legacy `niche_id` AND on browse).
- **Docs:** `system-design.md` §9 niche bullets + §12.1 class loop default updated to production pivot state.
- **Rollback:** set `CORPUS_WRITE_NICHE_ID=true`, `REFRESH_NICHE_INTELLIGENCE_MV=true`, `VITE_CORPUS_BROWSE_CLASS_ONLY=false`.

## 2026-05-21 — Content-class pivot flags promoted (default on)

- **Cloud Run defaults:** `CORPUS_SCORE_COHORT=class`, `CORPUS_INGEST_LOOP=class`, `LIVE_COHORT_CLASS_FIRST=true` in `settings.py` + batch/user pod env.
- **FE default:** `VITE_CORPUS_BROWSE_CLASS_FIRST` opt-out (`"false"` disables); Phase 4 sunset now also default-on (see entry above).
- **Rollback:** set env back to `legacy` / `niche` / `false` on batch+user pods and `VITE_CORPUS_BROWSE_CLASS_FIRST=false` on Vercel.

## 2026-05-21 — Content-class pivot gap closure (audit follow-up)

- **Migration:** `20260820000004_content_class_pivot_gaps.sql` — `acqe_run_state.discovery_relax_active`, `content_class_trend_velocity`.
- **Hashtag v2:** `hashtag_class_map.py` — class map fetch wired into `_fetch_niche_pool`; prune/yield/expand nightly; Thin/Dormant auto discovery relax via target tier.
- **ACQE:** auto-merge duplicate format_axis classes (post cold-start); cohort outlier flagging; peer sanity log-only.
- **HI-11:** shadow re-classify agreement; 7-night rolling median gate in artifact.
- **Peers:** `select_niche_peer_creators` + `creator_tier` fallback chain; channel diagnose passes tier from live followers.
- **Consumers:** `morning_ritual` junction class grounding; `trend_velocity` class-keyed upsert when ingest loop class-first.
- **Tests:** 28 pivot pytest cases (was 21).

## 2026-05-21 — Content-class corpus pivot Phase 4 (sunset bridge)

- **Migration:** `20260820000003_content_class_pivot_phase4.sql` — `content_class_intelligence.claim_tier`, `content_class_stats_for_creator_niche`, `content_class_channel_benchmarks(class_id, tier)`.
- **Batch:** `CORPUS_WRITE_NICHE_ID=false` omits `niche_id` on upsert; `REFRESH_NICHE_INTELLIGENCE_MV=false` skips legacy MV refresh.
- **Channel:** `_fetch_niche_benchmarks` prefers class+tier RPC when `content_class_id` known.
- **FE:** `VITE_CORPUS_BROWSE_CLASS_ONLY` drops legacy `niche_id` AND on browse (see P1 entry).
- **Docs:** system-design niche sunset flags; pipeline §10 Phase 4 row.

## 2026-05-21 — Content-class corpus pivot Phase 0–3 (backend)

- **Migrations:** `20260820000000_content_class_pivot_phase0.sql` (provenance cols, `content_class_ingest_targets`, `acqe_run_state`, upsert RPC); `20260820000001_hashtag_class_map.sql`; `20260820000002_content_class_tier_intelligence_mv.sql`.
- **ACQE:** `class_quality_engine.py` — nightly viability tiers, assignment flags, cold-start policy; wired in `run_ingest_post_processing`.
- **HI-11 rolling eval:** `hi11_rolling_eval.py` — agreement/junction/outlier metrics.
- **Ingest:** `ingest_loop_*` on aweme pre-score; `fetch_ingest_targets()` when `CORPUS_INGEST_LOOP=class` (default `niche`); class dedup re-upsert; `hashtag_class_map` learn on upsert.
- **Score cohort:** `CORPUS_SCORE_COHORT`, `ContentClassViewStats`, class pre-score in `corpus_instructiveness.py`; `LIVE_COHORT_CLASS_FIRST` in `video_niche_benchmark.py`.
- **Docs/SQL:** `content-class-pivot-metrics.sql`, `hashtag-class-map-v2.md`; pipeline §10; system-design §9+§12.1.

## 2026-05-21 — Content-class corpus browse pivot (FE P1 + P4)

- **Flags:** `VITE_CORPUS_BROWSE_CLASS_FIRST`, `VITE_CORPUS_BROWSE_CLASS_ONLY` in `src/lib/env.ts`.
- **Filter:** `corpusNicheFilter.ts` — `shouldUseClassFirstBrowse`, class-only sunset; Xu hướng + Home breakouts + `useVideoCorpus` pass junction aggregate sample.
- **Hook:** `useContentClassIntelligence.ts` — sum `content_class_intelligence.sample_size` for junction classes; Trends thin-claim banner uses aggregate, not `niche_intelligence`.
- **Diagnosis UI:** `FlopDiagnosisStrip` / `ScoreCard` — cohort copy from `benchmark_axis` + optional `cohort_label` / `category_label`.

## 2026-05-20 — Remove calendar kill gate from ingest spec

- **Docs:** Dropped `corpus-ingest-criteria-v1.md` §11 (2026-06-15 kill gate); Tier 3a/3b and optional phases gated by env + shadow metrics + human sign-off only. `system-design.md` §12.1 + `settings.py` descriptions updated. Plan files: metric-gated sequencing, no calendar deadline.

## 2026-05-20 — Corpus ingest criteria (instructiveness selection)

- **Spec + code:** [`corpus-ingest-criteria-v1.md`](corpus-ingest-criteria-v1.md); `corpus_instructiveness.py`, `corpus_boost_suspect.py`; `CORPUS_INGEST_MODE` (`legacy`|`shadow`|`purity`), R1/R2/R3, shadow logging, post-extract Tier 3, migration `20260520000000_corpus_ingest_criteria_columns.sql` (`boost_attribution`, `reference_eligible`, `ingest_relaxation_tier`).
- **Consumers:** `morning_ritual` breakout-weighted grounding; `corpus_context` ref pool sort; `hook_effectiveness_compute` breakout weight; Trends virals rail `breakout_multiplier ≥ 2`.
- **Docs:** `system-design.md` §12.1 live + TD-8 note; Phase D0–D2 cross-links; QA baseline [`corpus-ingest-criteria-baseline.json`](../qa-reports/corpus-ingest-criteria-baseline.json).
- **Deploy:** set `CORPUS_INGEST_MODE=shadow` → observe 3–7 nights → flip `purity` + `BATCH_VIDEOS_PER_NICHE=15` + `KEYWORD_SEARCH_AUTHOR_STATS=true` on batch pod.

## 2026-05-20 — Corpus ingest criteria v1 spec + Phase D0 doc stub

- **New:** [`corpus-ingest-criteria-v1.md`](corpus-ingest-criteria-v1.md) — canonical instructiveness formula, Tier 0–3, R1/R2/R3, shadow gate matrix, Minh rubric, env defaults, flip checklist.
- **Docs:** `system-design.md` §12.1 planned stub + Update Protocol bullets; cross-links in `feature-map.md`, `product-value-audit.md` PVA-009, `corpus-research-practitioner-compass.md`, `CLAUDE.md`.
- **Code:** not yet — `CORPUS_INGEST_MODE=legacy` until Phase 2 flip.

## 2026-05-19 — Music vs lifestyle ingest split (option C)

- **Migration** `20260729000000_music_dance_ingest_niche_28.sql`: new `niche_taxonomy` id 28 (Âm nhạc · Vũ đạo); rebadge `video_corpus` rows with `content_class_id` 28/29 off bucket 27; drop music classes from lifestyle junction; `map_legacy_niche_to_creator_niche` 22→15, 28→15.
- **Code:** `legacyNicheIdForCreatorNiche(15)→28`, shared `corpusNicheFilter.ts`, Xu hướng grid/counts + Home breakouts filter `content_class_id` AND `niche_id`; `corpus_ingest` niche 28 content-class routing; lifestyle ingest no longer maps dance→29.

## 2026-05-19 — Corpus ingest quality gates ×2

- **Batch video:** `BATCH_MIN_VIEWS` 10k→20k, `BATCH_MIN_ER` 1.0%→2.0%; carousel `BATCH_CAROUSEL_MIN_LIKES` 500→1k; live reference queue 50k→100k views (`settings.py` defaults). Redeploy batch pod to apply on Cloud Run.

## 2026-05-19 — News aggregator blocklist (FPT Play + 28international)

- **Blocklist:** `28international`, `fptplay.sports`, `fptplay.bongdaviet`, `bongdavadoisong` in `creator_blocklist.py` + migration `20260728000001_remove_news_aggregator_fpt28.sql` (purge existing corpus rows).

## 2026-05-19 — Retire comedy + pets_home UX niches

- **Migration** `20260728000000_retire_comedy_pets_home_niches.sql`: deactivate `creator_niches` id 5 (Hài · Giải trí) and 13 (Thú cưng · Nhà cửa); merge users + junction into lifestyle (4); legacy ingest buckets 13/19/20 → new `niche_taxonomy` id 27 (Đời sống · Tâm sự).
- **Code:** `two_axis_taxonomy.py`, `profileNiches.ts`, `profile_niches.py`, `corpus_ingest.py` — 14 active UX buckets; lifestyle maps to legacy 27.

## How to use

- Add one row per deviation discovered during build — takes 30 seconds
- Do NOT edit specs mid-build — log the deviation here instead
- BLOCKING = can't continue the current feature without resolving this → fix before marking the feature complete
- NON-BLOCKING = log and continue → batch-fix before pre-handoff review (after all features pass QA)
- Move to RESOLVED when fixed, including the commit hash

## Active

| Feature | What changed | Blocking? | Fixed? | Commit |
|---|---|---|---|---|
| Docs / corpus utilization | **Tracked audit:** `artifacts/docs/corpus-gemini-utilization-audit.md` (ingest tiers A–D, ~50–65% utilization). Cross-links in `feature-map.md`, `system-design.md` §12. Cursor plan updated for `subject_matter` proximity (`6a69ab3`). | NO | Yes | e5b54a1 |
| Docs / corpus utilization | **§7 recalibration:** dead vs misclassified fields (`key_messages` trim-safe; `audio_track_role`/`text_overlays`/`commerce_intent` not dead); v6 input path; trim/ablation strategy. | NO | Yes | — |
| Video answer / embedded tiles cache | **finalize-lite:** `EMBED_CONTRACT_VERSION` + `repair_diagnosis_vi_embedded_tiles` on corpus cache hit and on-demand `cached_response` repair (schema v3); re-persist `video_diagnostics`. **FE:** `evidence_anchors` (`aweme_id`) fallback; session/`?q=` video mismatch banner. **Proximity:** corpus peer `content_context.subject_matter` in `_content_proximity_score`. | NO | Yes | — |
| Answer session delete | **Hard delete:** `DELETE /answer/sessions/:id` + RLS `answer_sessions_delete_own`; Studio/history「Xoá」removes session + `answer_turns` (replaces `archived_at` soft-hide). Migration `20260726000000`. Does not purge `video_diagnostics` cache rows. | NO | Yes | 3011f55 |
| Answer sidebar titles | **Option A:** after video diagnosis synthesis, promote `answer_sessions.title` from `narrative_vi.headline_vi` when title still matches auto-truncated `initial_q` (preserves manual `patch_session` renames). | NO | Yes | 6332eb2 |
| Video answer / reference tiles | **Off-topic embedded refs:** annotate `content_proximity_score` on synthesis pool picks; post-synthesis `_sanitize_diagnosis_embedded_tiles` keeps only proximity ≥1 ids resolved from pool; FE `mapDiagnosisEmbeddedTiles` drops orphan aweme hints. | NO | Yes | 61570d7 |
| Video answer / v6 cutover (pre-launch) | **Single FE path:** `resolveDiagnosisSections` + `DiagnosisSectionRenderer` only — removed pre-v6 `van_de_chinh`, numbered flop rows, `ket_luan_nhanh` callout, `CrossFormatPanel`, duplicate posting/channel cards. **BE default:** `GETVIEWS_DIAGNOSIS_SECTION_MODE=1` (set `=0` to opt out). **Cache:** `TRUNCATE video_diagnostics` via `20260725000000_clear_video_diagnostics_v6_cutover.sql`. Cloud Run user redeployed (`getviews-pipeline-user-00121-vgh`). | NO | Yes | 2c61bf1 |
| Video answer / on-demand | **Caption vs hook split:** `meta.caption` + `meta.hook_phrase`; `title` = first line of TikTok desc. **Extraction:** `CAPTION_TIKTOK` prefix + tagline-vs-rhetorical-hook rule (TD-7, batch + live). **Finalize:** `user_stats.caption` from desc; `select_synthesis_references_for_video` + evidence block; `resolve_live_niche_id` ladder + `curnon.official` → niche 3. **Cache:** `response_schema_version=2` invalidates stale on-demand rows (~1h). FE: overlay uses `caption`, copy uses `hook_phrase`. | NO | Yes | — |
| Infra / Cloud Run CI | **Build context trim:** `.gcloudignore` + `.dockerignore` exclude `cloud-run/.venv`, tests, `src/`, `artifacts/`, etc. (~160 MB → ~15–25 MB upload). **CI:** `.github/workflows/cloud-run-build.yml` runs Cloud Build on `main` (path-filtered); deploy locally with `SKIP_BUILD=1 ./cloud-run/deploy.sh`. Setup: `cloud-run/docs/ci-cloud-run-build.md`. `cloudbuild.yaml`: optional `_TAG_SHA`, `--cache-from` prior image. | NO | Partial (needs `GCP_SA_KEY` + `GCP_PROJECT_ID` GitHub secrets) | — |
| Batch ingest + cron dedup | **Ingest:** Cloud Run image now COPYs PR1/PR6/HI-16 migration SQL; `junction_content_class._repo_root()` resolves `/app` or repo root. **Cron:** paused duplicate GCP Scheduler `getviews-corpus-ingest` + `getviews-morning-ritual` (pg_cron remains canonical). **Layer0:** `NICHE_INSIGHT_UPSERT_COLUMNS` allow-list — no `cross_niche_signals`. Deploy: repo-root `gcloud builds submit -f cloud-run/Dockerfile`. | NO | Yes | — |
| Pattern section audit | **`pattern_deck_synth`:** grounding cân bằng theo `niche_spread` (legacy `niche_id`), lọc HI-9 `creator_niche_slug`, cross-niche prompt dùng `niche` + `primary_subjects` (bỏ `subject_matter`). **`report_pattern`:** thin path gộp `subreports`; `ConfidenceStrip.window_days` = `max(window_days,14)` + `effective_window_days` từ `load_pattern_inputs`. **`report_pattern_gemini`:** `system_instruction` tách khỏi user prompt; quy tắc micro-element khi placeholder. **FE:** `VideoThumbnail.objectFit`, `PatternModal` VN copy + hover→TikTok embed, `TrendsPatternGrid` hint VN, `EvidenceGrid` nhãn `% tương tác`, `patternFormat` optional chaining WoW, `PatternCard` bỏ ↑ view. | NO | Yes | — |
| Timing heatmap (ICT + integrity) | **Heatmap buckets** use `Asia/Ho_Chi_Minh` in `report_timing_compute.build_heatmap_grid`; **`timing_top_window_streak`** migration `20260518130000_timing_top_window_streak_ict_posted_at.sql` aligns on `COALESCE(posted_at, indexed_at, created_at)` + ICT. **Thin sample (&lt;80)** builds a **real** grid from corpus with forced sparse variance (not `build_thin_corpus_timing_report` fixture). **`fill_timing_narrative`** receives `variance["detail"]` (was wrong key `note`). **`_lowest_window_from_grid`** ignores zero cells. **FE:** `src/lib/timingGridLabels.ts`, VN copy (`Lưới khung giờ (ICT)`, trung vị), `PatternSubreport` aria/kicker; **TimingHeatmap** drops `maskBelowFive` (show numbers for cells ≥5 only). | NO | Yes | — |
| V6 evidence-first section quality | **Shorter v6 prose** (150–200 từ/section, tổng ~900–1200) trong `diagnose_prompts.py`; **content-proximity** rank + **`fetch_content_targeted_refs`** (ED) khi top picks overlap 0; **`REFERENCE_EVIDENCE`** thêm format + niche; **`corpus_ingest_queue`** (`20260721000000`) + `reference_ingest_min_views` + enqueue async + mirror thumbnail R2 (tới 3 URL CDN); **`POST /batch/process-ingest-queue`**; **`ingest_source`** mở rộng `reference_live_search`; corpus ref có **desc** từ transcript/topics; FE tiles có **border-t** trong `DiagnosisSectionRenderer`. | NO | Yes | — |
| Diagnosis-first / Sprint 6 §6 (patch) | **`sound_lifecycle_phase` for `peak`:** `_LIFECYCLE_SALIENCE["peak"]=0.52` so stable plateau (infer + radar) is not dropped; claim/suggested_fix copy distinguishes peak from decline/parody. Test: `test_sound_lifecycle_peak_from_trending_profile`. | NO | Yes | 0f29b52 |
| Diagnosis-first / taxonomy (§0–§12) | **`artifacts/docs/short-form-video-taxonomy-vietnam.md` added** — Vietnam SFV scoring taxonomy (commerce gate §0, hooks §3, compliance §10, personas §11, etc.). Source for diagnosis-first plan Sprint 1+ alignment; wired in code via `prompts.py` / `CommerceIntent` docstrings + `test_short_form_video_taxonomy_vietnam_section0_tracked`. | NO | Yes | — |
| Diagnosis-first / Sprint 2 §3 hooks | **Vietnam hook taxonomy (models → ingest → diagnosis templates).** `HookType` expanded; optional `hook_layering`, `hook_body_contract`, `dialect_detected`, `price_anchor_manipulation_suspected`; alias `price_shock` → `gia_soc`. `signals/hook.py` new extractors; `corpus_ingest.py` `_HOOK_TYPE_ALIASES` + normalization; `prompts.py` / `output_redesign.py` / `enum_labels_vi.py` / `script_data.py` / `pattern_fingerprint.py` / `morning_ritual.py` / `signals/commerce.py` (authority set aligns with §3; `gia_soc` excluded from under-150k mismatch). Frontend labels: `src/lib/constants/hook-names-vi.ts`. Tests: `test_hook_signals_sprint2.py`. Docs blurb: `df919d4`. | NO | Yes | cc0e09b |
| Diagnosis-first / Sprint 2 §3 (v6 section pool) | **`hook_analysis` section** in `diagnose_sections.SECTION_POOL`: emits when any `hook_analysis` manifest signal has salience ≥0.7 (plan gate); default title `PHÂN TÍCH HOOK`. Signals `hook_first_frame_non_product`, `hook_type_niche_mismatch`, `hook_layering_single`, `hook_body_contract_violated` use `section_id=hook_analysis` (dialect 0.6 remains `diagnosis`; `hook_gia_soc_price_anchor_risk` remains `compliance`). Tests: `test_diagnosis_v6_helpers`, `test_hook_signals_sprint2`. QA: `artifacts/qa-reports/sprint2-vietnamese-hooks-baseline.json`. **Offline acceptance:** `cloud-run/tests/test_hook_sprint2_acceptance_fixtures.py` (six hook-type fixtures + mixed + label map). | NO | Yes | 0d4fc73 |
| Diagnosis-first / Sprint 3 §11 personas + slang | **Creator personas + consistency + slang on `VideoAnalysis`.** Six slugs (`chuyen_gia`, `ban_than`, …); optional `persona_consistency_signals` (`speech_register` field, accepts JSON key `register`); `slang_terms_used` / `slang_freshness_score`; `vietnamese_slang.py` lexicon merge after Gemini/batch JSON parse. **`signals/persona.py`** + registry; **`persona` section** in `diagnose_sections` (salience ≥0.55). Channel **`dominant_creator_persona`** from corpus mode (≥2 agreeing rows). Tests: `test_persona_signals_sprint3.py`. QA: `artifacts/qa-reports/sprint3-personas-slang-baseline.json`. | NO | Yes | 3014e2d |
| Diagnosis-first / Sprint 4 §10 compliance | **`compliance.py`** — §10 restricted-phrase scan (VO, overlays, caption) + numeric neo giá ≥5×; **`signals/compliance.py`** — restricted (1.0 high / 0.82 medium-only), price anchor 0.85, Ad Law disclosure 0.9 on **`compliance`** section, shadowban/cheo heuristic 0.7 (`retention_end_pct` as 0–100). **`gemini.py`** passes `collect_compliance_flags` into v6 ctx; **`video_analyze.py`** enriches `user_stats` (caption, ER, retention, creator median). Tests: `test_compliance_signals_sprint4.py`. QA: `artifacts/qa-reports/sprint4-compliance-baseline.json`. | NO | Yes | a9c35e7 |
| Diagnosis-first / Sprint 5 §9 + §2 engagement/context | **`golden_hours.py`** (ICT); **`signals/engagement.py`** — bình luận ghim không lọt VO, `loop_architecture_score` tích cực; **`signals/context_signals.py`** — trượt khung giờ vàng, heuristic tương tác chéo (ER vs median + retention / `views_vs_avg_ratio`). **`VideoAnalysis.loop_architecture_score`** + prompt; **`user_stats`** thêm `posted_at`, `views_vs_avg_ratio`; **`meta.created_at`** corpus. Tests: `test_golden_hours.py`, `test_engagement_context_sprint5.py`. QA: `artifacts/qa-reports/sprint5-engagement-context-baseline.json`. | NO | Yes | 547fce6 |
| Diagnosis-first / Sprint 6 §6 sound | **`infer_sound_lifecycle_phase`** in `layer0_sound.py`; **`sound_aggregator.py`** persists `lifecycle_phase` + `commercial_music_library_eligible`; migration **`20260720000000_trending_sounds_sprint6_sound_intel.sql`**; **`Music.music_id`** (Ensemble); **`VideoAnalysis`**: `audio_track_role`, `sound_dialect_audio`, `sound_layering`; **`signals/sound.py`** + registry; **`sound` section** in `diagnose_sections`; **`corpus_context`** `sound_radar` + trending profile lookups; **`pipelines`** enriches `niche_meta` + `user_stats`. Tests: `test_sound_sprint6.py`. QA: `artifacts/qa-reports/sprint6-sound-baseline.json` (PASS_WITH_CONCERNS). | NO | Yes | 0ae74e1 |
| Diagnosis-first / Sprint 7 §7 + §4 triggers/script | **`AffiliateScriptPhases`** + **`livestream_funnel_demo`**, **`share_trigger_type`**, **`save_trigger_type`** on `VideoAnalysis`; **`prompts.py`** §4/§7 extraction; **`signals/triggers.py`** (sự thật trần trụi heuristic + share/save); **`signals/script.py`** (5-phase affiliate gap, livestream demo too complete); **`script_structure` section** + titles; registry wiring; **`api-types`** `VideoDiagnosisSectionId` extended. Tests: `test_sprint7_triggers_script.py`. QA: `artifacts/qa-reports/sprint7-triggers-script-baseline.json`. | NO | Yes | b96f575 |
| Diagnosis-first / Sprint 9 §8 Douyin (diagnosis) | **`DouyinOriginBlock`** + `vietnam_adoption_stage` + `migration_fit_assessment` on `VideoAnalysis`; **`douyin_match.py`** queries ``douyin_video_corpus`` (hook + mapped creator niche → Douyin niche id) before synthesis; **`signals/douyin.py`**; **`douyin_origin` section** (emit floor 0.45); env **`GETVIEWS_DOUYIN_ORIGIN_MATCH`**. **Deferred to DevOps:** cron thaw, TikHub cost gate, ≥20% calibration. Tests: `test_sprint9_douyin.py`. QA: `artifacts/qa-reports/sprint9-douyin-baseline.json`. | NO | Partial | cb5af3b |
| Diagnosis-first / Sprint 10 §12 Shop conversion metrics | **`signals/performance.py`** — `commerce_performance_conversion_override` (salience 1.0, section `commerce`) when Shop/API order density contradicts flop/average tier or views far below creator median; **`video_analyze`** merges `meta.commerce_conversion` / `meta.shop_order_count` into `user_stats` (no Gemini order counts). Tests: `test_sprint10_commerce_performance.py`. **Deferred:** 50-fixture eval, narrative-quality scoring, v5→v6 prod flip (plan gates). QA: `artifacts/qa-reports/sprint10-commerce-metrics-baseline.json`. | NO | Partial | 289b077 |
| Diagnosis-first / Sprint 8 §1 + §5 metadata/editing | **`VideoAnalysis`** §1: `safe_zone_status`, `tiktok_account_type_heuristic`, `trending_vpop_sound`; §5: `color_grading_style`, `text_overlay_font_size_tier`, `text_overlay_color_emphasis`. **`signals/metadata.py`**, **`signals/editing.py`**; registry; **`metadata`** + **`editing`** sections in `diagnose_sections` (editing gate min salience 0.4). **`prompts.py`** extraction bullets. **`api-types`** `VideoDiagnosisSectionId`. Tests: `test_sprint8_metadata_editing.py`. QA: `artifacts/qa-reports/sprint8-metadata-editing-baseline.json`. | NO | Yes | 9ead6b8 |
| Diagnosis-first / plan tracking | **Issue stubs** for remaining todos: `sprint3-personas-slang` through `sprint10-commerce-metrics-final-qa`, plus `substrate-corpus-ingest`, `substrate-pattern-freshness`, `substrate-layer0bd` under `artifacts/issues/`. Sprint 9 Douyin stub notes TikTok-only product scope — confirm before implementation. | NO | Yes | 920e02b |
| Diagnosis-first / Sprint 1 §0 | **`CommerceIntent` + `commerce_intent` on `VideoAnalysis`.** Extraction prompt `_VIDEO_EXTRACTION_CORE_VI` adds §0 object (objectives, price tier, creator type, verbal CTA, disclosure). **`signals/commerce.py`** — conversion objective, verbal CTA gap, under-150k vs authority-hook mismatch, disclosure (structured + legacy `brand_deal`/`affiliate`), creator-type vs `content_context` consistency, plus **legacy** `promotion_type` + `cta` when `commerce_intent` absent. Tests: `test_commerce_signals_sprint1.py`, HI-9 prompt + `commerce_intent` round-trip. QA **PASS_WITH_CONCERNS** (`artifacts/qa-reports/sprint1-commerce-intent-baseline.json`) — five TikTok fixture end-to-end diagnosis acceptance deferred. | NO | Partial (fixture/eval follow-up) | cf55b0d |
| Diagnosis-first / Sprint 0 FE | **`diagnosis_vi` render path on answer video body.** Shared `SectionProseBlocks`; channel `SectionRenderer` deduped to same primitive; `DiagnosisSectionRenderer` maps embedded tiles via `reference_videos` and loose `next_video` → `NextVideoCard`. When `narrative_vi.diagnosis_vi.sections` is non-empty, **VideoBody** iterates sections and **skips** the flat `van_de_chinh` block to avoid duplicate prose. Types: `DiagnosisViV6`, `DiagnosisSectionVi`, `_schema_version` on `NarrativeVi`. Tests: `VideoBody.test.tsx`, `DiagnosisSectionRenderer.test.tsx`. | No | Yes | 8b3373c |
| Diagnosis-first / Sprint 0 BE | **Conditional-section v6 synthesis path (flagged).** When `GETVIEWS_DIAGNOSIS_SECTION_MODE=1`, `synthesize_diagnosis_v2` runs signal manifest → `select_sections_to_emit` → `build_diagnosis_v6_user_prompt` → leading JSON `diagnosis_vi`; `_v6_section_body_and_narrative` fills markdown `diagnosis` body plus legacy `narrative_vi` keys + `_schema_version: "v6"`. Default env off — production unchanged. New tests: `tests/test_diagnosis_v6_helpers.py`. QA **PASS_WITH_CONCERNS** (`artifacts/qa-reports/sprint0-narrative-refactor-baseline.json`) — SSE section stream, FE SectionRenderer, 20-fixture eval deferred. | No | Partial (canary before prod flag) | ccb1c52 |
| Layer 0 simplification (Phase 2) | **Promoted Module 0D (hashtag discovery) from weekly to daily.** Was Sunday-only inside `_run_weekly_analytics`; moved into `run_ingest_post_processing` so it runs every nightly batch. New high-performing hashtags discovered in the corpus now flow into `niche_taxonomy.signal_hashtags` within ≤24h instead of ≤7 days, tightening the corpus self-improvement loop. Cost is bounded by `MAX_CANDIDATES_PER_RUN=60` and the steady-state corpus returns 0 candidates on most days, so worst-case ~$0.70/week (vs ~$0.10/week before). Net diff: +31/-18 LOC, single block moved. 17/17 post-processing tests pass. | No | ✅ 2026-05-17 | — |
| Layer 0 simplification (Phase 1) | **Sunset Module 0C (cross-niche format migration).** Critical evaluation found 0C wrote `niche_insights.cross_niche_signals` JSONB on every weekly cron run but ZERO consumers anywhere — no FE, no other cloud-run module, no Edge Function, no SQL view, no RLS policy. 8/78 lifetime rows populated (10%). Pure write-only. Removed: `layer0_migration.py` (-198 LOC), `CROSS_NICHE_*` symbols in `layer0_prompts.py`, call sites in `corpus_ingest._run_weekly_analytics`, `routers/batch.batch_layer0`, `routers/admin._admin_run_layer0`. Migration `20260719000005_drop_niche_insights_cross_niche_signals.sql` drops the column. Net diff: -276 / +4 LOC. 18/18 layer0-related tests pass. | No | ✅ 2026-05-17 | — |
| Infra / Cloud Run | **Batch pod env vars wiped + restored** (2026-05-17). `./deploy.sh batch` ran with `gcloud run deploy --image … --update-env-vars SERVICE_ROLE=batch` and reduced batch pod from 20 env vars → 1 (lost BATCH_SECRET, SUPABASE_*, GEMINI_API_KEY, ENSEMBLE_DATA_API_KEY, R2_*, NICHE_RESOLVER_MODE, GEMINI_DAILY_USD_*, ED_BATCH_*, GCP_STT_VI_ENABLED). Next nightly batch ingest would have hard-failed. Restored all 21 vars on rev `getviews-pipeline-batch-00086-xq9` via `--env-vars-file`. `deploy.sh` updated: bare `gcloud run deploy` first (preserves env block), then additive `gcloud run services update --update-env-vars SERVICE_ROLE=…` to pin role. | Yes | ✅ 2026-05-17 | — |
| Cron / trend_velocity | **Silent failure since table creation fixed**. `cron-batch-trend-velocity` (Tue 05:30 ICT) was returning HTTP 200 with `{"ok":false, "errors":["upsert: …42P10 no unique or exclusion constraint…"]}` every week. `trend_velocity` table had 0 lifetime inserts. Root cause: missing `UNIQUE(niche_id, week_start)` on the table; Python upsert needs it. Migration `20260719000002_trend_velocity_unique.sql`. Manual backfill verified: `{"ok":true, "niches_processed":18, "rows_upserted":18}`. L2.2 Sound Radar (accelerating/peaking/cooling buckets on FE pattern reports) now has data. | Yes | ✅ 2026-05-17 | — |
| Schema / orphan cleanup | **Dropped `niche_daily_sounds`** — created in 20260504000000_adopt_orphan_tables.sql, never written, never read (0 grep hits in cloud-run / supabase/functions / api / src). Sound logic in `layer0_sound.py:33` explicitly says "No niche_daily_sounds needed" (uses self-join on `trending_sounds.week_of` instead). Migration `20260719000004_drop_niche_daily_sounds_orphan.sql`. | No | ✅ 2026-05-17 | — |
| Cron / cadence | **3 daily crons downgraded to weekly** based on input-change frequency: `cron-channel-diagnoses-prune` (daily 02:15 UTC → Sun 02:15 UTC; channel_diagnoses TTL is already 7d), `cron-starter-creators-reseed` (daily 22:45 UTC → Sun 22:45 UTC; ED hashtag pool barely changes week-over-week), `cron-daily-health-digest` (daily 01:00 UTC → Mon 01:00 UTC; matches Monday-of-week mental model). Migration `20260719000003_downgrade_crons_to_weekly.sql`. Cuts cron noise ~6×/week each. | No | ✅ 2026-05-17 | — |
| ME-18 / Carousel Ingest | **Root-cause fix: carousel detection always returned 0.** TikTok's mobile API omits `image_post_info.images` from feed/list responses. `detect_content_type()` always returned "video" on raw hashtag feed objects. Fix: when first-pass finds 0 carousels, `_fetch_carousel_pool` now batch-calls `fetch_post_multi_info()` on all aweme IDs (50/chunk) to get full detail objects with `image_post_info`, then re-filters. `BATCH_CAROUSELS_BY_NICHE` set per-niche on batch pod (beauty:8, fashion:6, edu:6, …). Commit: d38486b | No | ✅ 2026-05-17 | d38486b |
| HI-11 / Niche Router | **NICHE_RESOLVER_MODE flipped to `route`** on both batch + user pods (2026-05-17). Pre-flip audit: 293 shadow rows, avg confidence 0.908, Sports→Travel mapping confirmed correct (`travel` = "Du lịch · Thể thao" per creator_niches taxonomy). `niche_intelligence` MV refreshed post-flip. New ingest runs will canonically update `niche_id` + `content_class_id` from Gemini's two-axis output. | No | ✅ 2026-05-17 | — |
| Infra / Cost | **Gemini daily cap set**: `GEMINI_DAILY_USD_MAX=15` + `GEMINI_DAILY_USD_ENFORCE=true` on batch pod (rev 00081). Prevents runaway ingest spend. User-facing pod intentionally uncapped (credit layer is the guard). Documented in `system-design.md §17`. | No | ✅ 2026-05-17 | 0b6db5f |
| Infra / R2 | **R2 bucket name corrected**: `getviews-media` (non-existent) → `getviews-frames` (real bucket, 30 GB). Both `config.py` default and Cloud Run env updated on batch + user pods. Frames now upload successfully. | Yes | ✅ 2026-05-17 | 0b6db5f |
| Infra / Memory | **Batch pod OOM fix**: 4 GiB → 8 GiB. Previous runs crashed mid-ingest at ~4.1 GiB (parallel MP4 downloads + Gemini fan-out). All 18 niches failed with `inserted=0` due to OOM. | Yes | ✅ 2026-05-17 | 0b6db5f |
| Infra / HI-13 | **Gemini Batch API disabled**: `gemini-3.1-flash-lite` returns HTTP 400 on `batchGenerateContent` — model does not support JSONL Batch API. `CORPUS_INGEST_USE_GEMINI_BATCH=false` set on batch pod. Pipeline falls back to concurrent sync analysis. Re-enable when model supports batch. | No | ✅ 2026-05-17 | 0b6db5f |
| Infra / HI-14 | **GCP Speech-to-Text disabled**: `GCP_STT_VI_ENABLED=false` on both batch + user pods (rev batch-00082, user-00079). API was returning 403 (service disabled) then 400 (inline audio too long for GCS-less path). Disabled to stop noisy warnings and avoid accidental charges if API is later enabled. Re-enable with a proper GCS URI flow when HI-14 is revisited. | No | ✅ 2026-05-17 | — |
| Pipeline audit remediation | **ME-15 (fix)** — `_generate_content_models` transient retry branch now calls `log_gemini_call(success=False, tokens_in=0, tokens_out=0, error_code=f'{ExcClass}_attempt_N')` before `time.sleep(delay)`. Previously only the final exhausted failure was logged; 503 bursts were invisible on cost dashboard. Regression: `TestTransientRetryLogging` (2 tests) — 32/32 pass. QA baselines backfilled for 12 completed tasks (hi10, hi12, hi13, hi14, hi16, hi18, me12, me14, me15, me16, me18, me19). Issue files + plan mirror synced. | NO | Yes | — |
| Pipeline audit remediation | **DOC-1 (Sprint 2 checkpoint)** — Doc sweep: `system-design.md` adds `vietnamese_asr_cache`, HI-14/HI-15 component notes, **TD-6** (junction parity for `route`) + **TD-7** (live vs batch extraction parity); `CLAUDE.md` niche model + cost ceiling; `project.mdc` cost + HI-14; `project-plan.md` remediation tracker; runbook Part B ↔ plan “Phase 7” cross-ref. **Human:** post–HI-11 flip, remove “until flip” caveats in a Sprint 3 consolidation pass. | NO | Partial (rolling DOC-1) | 036f3df |
| Pipeline audit remediation | **HI-13** — Optional nightly corpus **video** extraction via Gemini **Batch API** JSONL file source (`CORPUS_INGEST_USE_GEMINI_BATCH`, `CORPUS_BATCH_POLL_*`); carousels unchanged; sync `analyze_video` fallback; `gemini_calls.is_batch` + batch-tier `cost_usd`. Migration `20260516120001_hi13_gemini_calls_is_batch.sql`. Tests: `test_hi13_batch_jsonl_record.py`, `test_gemini_cost` batch pricing. **Human:** apply migration; enable env on batch pod after pilot. | NO | Partial (deploy + observe) | — |
| Pipeline audit remediation | **ME-17** — Legacy corpus: `classification_backfill.py` (`backfill_row_with_gemini`, `run_classification_backfill`); `POST /admin/backfill-classification` + `POST /admin/trigger/backfill_classification`; `POST /batch/backfill-classification` (cron); migration `20260720000000_cron_batch_backfill_classification.sql` (`cron-backfill-classification`, 04:00 UTC, body `batch_size=3500`). Rows `niche_resolution_source IS NULL`, `indexed_at DESC`; writes `analysis_json` + shadow columns (`gemini_two_axis`). Tests: `test_me17_classification_backfill.py`. **Human:** apply migration; confirm batch Vault URL. | NO | Partial (deploy + COUNT NULL → 0 over ~14 nights) | 77a3f74 |
| Pipeline audit remediation | **ME-19** — `SlideAnalysis`: optional `swipe_anchor`, `layout` (ME-19 enums). `CarouselAnalysis`: `audio_track_role`, `dominant_color_palette`, `slide_pacing_score` (0–1). `CAROUSEL_EXTRACTION_PROMPT` instructions updated. Tests: `test_me19_carousel_swipe_psychology.py`, gate + HI-9 prompt asserts. Backward compat: all new fields optional / null. | NO | Partial (manual viral sample eval deferred) | — |
| Pipeline audit remediation | **HI-11 (ops runbook)** — `artifacts/docs/two-axis-niche-cutover-runbook.md` **Part B**: shadow vs `route`, daily SQL, Cloud Logging signals, 100-row audit gate (≥80% agree+gemini_better), flip checklist (MV refresh, hook effectiveness, ME-17 handoff). `system-design.md` niche § — HI-11 summary + runbook link. Issue `hi11-niche-resolver-two-axis-shadow-then-flip.md` updated. **Prod:** calendar observation + audit still required before `NICHE_RESOLVER_MODE=route`. | NO | Partial (docs complete; human gate open) | — |
| Pipeline audit remediation | **ME-20** — `format_creator_format_history_for_diagnosis`: verdict only if `multiplier` ≥ 1.5 (carousel stronger) or ≤ 0.7 (video stronger); shared helper for carousel + video paths; `synthesize_diagnosis_v2` + `finalize_video_narrative_layer` accept `creator_format_history_block`. Tests: `tests/test_me20_format_history_diagnosis.py`. QA **PASS_WITH_CONCERNS** (`artifacts/qa-reports/me20-baseline.json`) — manual “sample 10” diagnoses deferred. | NO | Yes | 31fd063 |
| Pipeline audit remediation | **ME-18 (tuning hook)** — `BATCH_CAROUSELS_BY_NICHE` env (`legacy_niche_id:count`, comma-separated; `count` may be `0`). `ingest_niche` / `deep_pool` use `_carousels_per_night_for_niche` (per-niche map → else `BATCH_CAROUSELS_PER_NICHE`). **Investigation SQL + trending notes:** `artifacts/docs/two-axis-niche-cutover-runbook.md` § ME-18 appendix. **Still required:** run SQL + EnsembleData sample audit before production tuning. Tests: `test_thin_niche_prioritization`. | NO | Partial (audit + tune values) | — |
| Pipeline audit remediation | **HI-17** — Carousels **do not** call HI-14 GCP STT (`sync_prepare_vietnamese_asr_supplement` only on `_analyze_video` / `analyze_aweme_from_path`). Comments in `analysis_core._analyze_carousel`, `asr_vietnamese.sync_prepare_vietnamese_asr_supplement`, `gemini.analyze_carousel` tie HI-15 hook FPS + STT to **video-only**. Regression: `tests/test_hi17_carousel_skips_hi14_asr.py`. QA **PASS** (`artifacts/qa-reports/hi17-baseline.json`). | NO | Yes | — |
| Pipeline audit remediation | **HI-11 (routing path, opt-in)** — `NICHE_RESOLVER_MODE=shadow\|route` (default **shadow**). **route** applies high-confidence Gemini two-axis + junction to `video_corpus.niche_id` + `content_class_id`; hashtag baseline preserved for `_niche_resolution_shadow_fields`; pattern fingerprint uses final niche. New `junction_content_class.py` (migration-parse map, duplicate `format_axis` tie-break). QA **PASS_WITH_CONCERNS** (`artifacts/qa-reports/hi11-baseline.json`). **Prod:** keep shadow until manual audit + plan flip gate. | NO | Partial (calendar / MV gate still plan) | — |
| Pipeline audit remediation | **HI-11 (shadow junction axis)** — `_niche_resolution_shadow_fields` passes `content_type` from `_build_corpus_row`; junction-miss WARN uses the same format axis as `_route_niche_and_class_override` (video: `format_axis` only — ignores stray `carousel_format_axis`; carousel: `carousel_format_axis` then `format_axis`). Tests in `test_corpus_ingest_junction_warn.py`. | NO | Yes | — |
| Pipeline audit remediation | **HI-15** — `analyze_video` sends **two** video Parts (full clip @ `GEMINI_VIDEO_BASE_FPS` + first `GEMINI_HOOK_WINDOW_END_SEC` @ clamped `GEMINI_HOOK_WINDOW_FPS` 3–5) via per-Part `types.VideoMetadata`; Vietnamese user turn via `build_video_extraction_user_turn_vi` (aligned with clamped window + base FPS). `GEMINI_HOOK_WINDOW_DUAL_PART=false` restores single-Part behaviour. `analyze_carousel` asserts no `Part.video_metadata` (HI-17 prep). QA **PASS** (`artifacts/qa-reports/hi15-baseline.json`). | NO | Yes | 81cc241 |
| Pipeline audit remediation | **HI-8 (full)** — Synthesis/diagnosis/intent/channel-diagnose now route through `_generate_content_models(synthesis_cache_kind=…, synthesis_cache_system_text=…)`; per-fallback-model `client.caches.create` keyed by `sha256(kind\|model\|system_text)`; `gemini_text_only` stays on `system_instruction` (per-message). New env: `GEMINI_SYNTHESIS_CONTEXT_CACHE` (default off) + `GEMINI_CONTEXT_CACHE_TTL_SEC`. QA **PASS**. | NO | Yes | c9a3f28 |
| Pipeline audit remediation | **HI-8** — Video + carousel **extraction**: static instructions via `build_*_extraction_system_instruction` on `GenerateContentConfig` (`system_instruction` or explicit `cached_content` from `client.caches.create` when `GEMINI_EXTRACTION_CONTEXT_CACHE` is on); short user turns (`VIDEO_EXTRACTION_USER_TURN_VI`, `CAROUSEL_EXTRACTION_USER_PREFIX_VI` + tail). QA **PASS_WITH_CONCERNS** (synthesis explicit cache optional). | NO | Yes | a37b856 |
| Pipeline audit remediation | **HI-18** — Downstream use of HI-9: `_HI9_SYNTHESIS_HINT` in video + carousel diagnosis narrative prompts; `VideoErrorsExtractionInput` + `extract_video_errors` prompt use flattened `content_context_subject_matter` + `niche_classification_*`; morning ritual + pattern deck grounding JSON includes `subject_matter` when `analysis_json` has it (`extract_subject_matter_from_analysis_json`). | NO | Yes | c99df15 |
| Pipeline audit remediation | **HI-9 (completion)** — Few-shot ví dụ (beauty / food / comedy) + carousel pointers; `JUNCTION_NICHE_FORMAT_PAIRS` constant + `junction_has_pair()` + runtime `[corpus] junction miss` WARN in `corpus_ingest._niche_resolution_shadow_fields` so HI-11 can downgrade deterministically; `test_hi9_junction_seed.py` pins constant to PR1+PR6 migration parse; `cross_format` label map drops orphan `vlog_destination` (seed axis is `vlog_daily`); HI-8 internal rename (`use_synth_cache` → `apply_synthesis_static_system`) + regression test that `synthesis_cache_system_text` always merges as `system_instruction` even when `GEMINI_SYNTHESIS_CONTEXT_CACHE=false`. QA **PASS**. | NO | Yes | ea77fa9 |
| Pipeline audit remediation | **HI-9** — `ContentContext` / `NicheClassification` on `VideoAnalysis` + `CarouselAnalysis`; `two_axis_taxonomy` glossary; Vietnamese `VIDEO_EXTRACTION_PROMPT` / `CAROUSEL_EXTRACTION_PROMPT`; tests + schema contract. | NO | Yes | cb29567 |
| Pipeline audit remediation | **HI-6 / HI-7** — `call_site` labels; `report_generic_gemini` → `_generate_content_models`. | NO | Yes | 695c922 |
| Pipeline audit remediation | **HI-5** — `extract_video_errors`: `GEMINI_EXTRACTION_MODEL` + `GEMINI_EXTRACTION_FALLBACKS`, `ThinkingConfig(thinking_budget=0)`, `call_site="extract_video_errors"` (stops synthesis-tier + thinking-token inflation on diagnosis). | NO | Yes | — |
| Pipeline audit remediation | **CR-4** — `gemini_cost` + `ensemble`: track daemon insert threads, `atexit` drain with **8s** join budget (Cloud Run SIGTERM telemetry loss). | NO | Yes | — |
| Pipeline audit remediation | **CR-3** — Per-aweme `_ingest_niche_id` stash + pop in `_ingest_candidate_awemes`; removed mid-loop `niche_id` mutation (video + carousel gates). | NO | Yes | — |
| Pipeline audit remediation | **CR-2** — `cron-batch-ingest`: `net.http_post` `timeout_milliseconds` **300000 → 3120000** (52 min) via migration `cron.alter_job` on `cron.job`; sync docs-only migration comment + data-pipeline runbook Step 4. No-op if job absent (local). | NO | Yes | — |
| Pipeline audit remediation | **CR-1** — Paginated `_load_all_existing_video_ids_sync` (`.range` 1000-row pages); one dedup snapshot per `run_batch_ingest`; `ingest_niche(..., existing_video_ids=)`. Fixes PostgREST 1000-row silent cap + per-niche refetch. | NO | Yes | — |
| Pipeline audit remediation | **Cloud Run Ruff + test compatibility.** `pyproject.toml`: `line-length=120`; E501 exemptions for tests + prompt-heavy pipeline files; assorted F821/F841/E402/UP fixes across services. `video_analyze.py` re-exports `_dedupe_lang_market_hook_errors`, `_summarise_retention_curve`, `_summarise_niche_row`, `_FORBIDDEN_PHRASES_VI` for tests after extraction refactor. Validation: `ruff check getviews_pipeline tests`; `pytest` passes. | NO | Yes | 33aa169 |
| Pipeline audit remediation | **Plan execution started** (`/implement-plan`): canonical plan mirrored to `.cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md`; **31** scaffold issue files under `artifacts/issues/` (CR/HI/ME/EXP/research/DOC/verify) per plan Tracking section; `agent-workspace/ACTIVE_CONTEXT.md` seeded. | NO — planning scaffold only | Partial (scaffold only) | f74f622 |
| Channel Diagnosis v2 | **`channel_diagnoses` v2 columns**: `score_card`, `verdict_tiles`, `hashtag_insights`, `next_video`, `channel_persona`, `peer_source` added (migrations `20260718000000` p25 RPC + `20260718000001` v2 cols). | NO — additive | Yes | 78999fa |
| Channel Diagnosis v2 | **`score_card` SSE event** emitted after step 4 (benchmarks), before first `section_start`. Carries deterministic P25/P50/P75 metrics + template captions from `render_score_card_captions`. Cache replay re-emits all v2 fields. | NO — new event | Yes | 78999fa |
| Channel Diagnosis v2 | **`select_niche_peer_creators`** replaces `fetch_ugc_creators` — two-axis peer selection via `video_corpus` (`content_class_id` → `niche_only` fallback → `thin`). `peer_source` enum tracks which tier was used. | NO — richer data | Yes | 78999fa |
| Channel Diagnosis v2 | **`derive_channel_persona`** computes `dominant_content_class_id` + `dominant_format` + `content_class_label` from `map_legacy_corpus_to_content_class` RPC. `channel_persona` stored in DB + returned in payload. | NO — new field | Yes | 78999fa |
| Channel Diagnosis v2 | **`compute_hashtag_insights`** (synthetic, not Gemini) + `hashtag_caption_for_insight` — top-5 hashtags by `avg_views_with / avg_views_without` ratio, injected as `hashtag_insights` on `section_start`. | NO — new section | Yes | 78999fa |
| Channel Diagnosis v2 | **`select_verdict_tiles`** — peak + 2 most recent public videos, deduped by `video_id`; injected as `embedded_tiles` on `verdict` `section_start`. | NO — new data | Yes | 78999fa |
| Channel Diagnosis v2 | **`derive_next_video_concept`** — deterministic seed (hook formula + format + peer title) injected as `next_video` on `next_video` `section_start`; Gemini narrative follows inline. | NO — new section | Yes | 78999fa |
| Channel Diagnosis v2 | **Mandatory LLM sections relaxed** to `{ verdict, recommendations }` only. `next_video` is synthetically injected; `hashtag_insights` is fully synthetic. Prevents fallback cascade when Gemini omits optional sections. | NO — reliability fix | Yes | 78999fa |
| Channel Diagnosis v2 | **Frontend** — new components `ScoreCard.tsx` (5-metric grid + skeleton), `HashtagInsightsBlock.tsx`, `NextVideoCard.tsx`; `SectionRenderer` routes by `section_id`; `NumberedRecommendation` groups hero / regular / anti; `ChannelScreen` mounts `ScoreCard` above sections with skeleton. | NO — new UI | Yes | 78999fa |
| Channel Diagnosis v2 | **`useChannelDiagnose` hook** — handles `score_card` SSE event; exposes `scoreCard`, `channelPersona`, `peerSource`; falls back to terminal `payload` for cache-replay completeness. | NO — hook update | Yes | 78999fa |
| Northstar v1.3 update | **Explore screen added** (§11): visual browse grid + R2 inline video playback + Video detail modal + Videos to Copy sidebar. Free for all tiers (0 credits). This is a new screen not in the current screen-specs — requires Phase 2 amendment before /phase4. | YES — new screen | No | — |
| Northstar v1.3 update | **Batch cost corrected**: $55/mo → $42/mo due to 720p/30s proxy optimization. Proxy step: 1.8GB/day → 1.0GB/day. R2 now stores full 720p/30s video clips. `video_corpus` gains `video_url` column. | NO — infra only | No | — |
| Northstar v1.3 update | **Wave 2 scope** renamed "Intelligence + Explore": Explore page promoted to Wave 2 deliverable. Rate limiting scope updated to include Explore (100/day). | NO — planning only | No | — |
| Figma phase | **ExploreScreen added** (`/app/explore`): 2-column video grid with niche/date/sort filters + VideoDetailModal (inline player, similar videos, "Phân tích" CTA). Implements northstar §11. Free (0 credits). Screen spec added. | NO — new screen, Wave 1 | No | — |
| Figma phase | **LearnMoreScreen added** (`/app/learn-more`): static resources + legal hub (About, Docs, Changelog, Creator Academy, Terms, Privacy, Refund). Accessible from SettingsScreen + sidebar. Screen spec added. | NO — new screen, low complexity | No | — |

## Resolved

| Feature | What changed | Resolved | Commit |
|---|---|---|---|
| Explore / Trends | **Trending This Week retired**: removed `TrendingSection`, `useTrendingCards`, `trending_cards.py`, and the `corpus_ingest` weekly hook. `trending_cards` table + Monday Edge digest unchanged. | 2026-04 | — |
| Figma phase | **OnboardingScreen dropped**: niche selection moved inline to ChatScreen first session. `/onboarding` route redirects to `/app`. No frontend work needed for this screen. | 2026-04 (Figma phase) | — |
| Phase 4 audit | **ChatMessage TypeScript interface consolidated**: removed individual `diagnosis_rows`, `hook_rankings`, etc. fields; replaced with `structured_output: StructuredOutput \| null` typed union to match DB schema. Added `ThumbnailItem` interface. | 2026-04-09 | — |
| Phase 4 audit | **TrendScreen data hooks added** to Section 9: `useNicheIntelligence`, `useTrendVelocity`, `useHookEffectiveness`, `useFormatLifecycle`. | 2026-04-09 | — |
| Phase 4 audit | **SSEToken interface added** to Section 4 (stream_id + seq + delta + done + error). | 2026-04-09 | — |
| Phase 4 audit | **NicheTaxonomy, NicheIntelligence, TrendVelocity, HookEffectiveness, FormatLifecycle TypeScript interfaces added** to Section 4. | 2026-04-09 | — |
| Phase 4 audit | **BillingPeriod type expanded**: added `overage_10 \| overage_30 \| overage_50` to match DB CHECK constraint. | 2026-04-09 | — |
| Phase 4 audit | **IntentType enum expanded**: added `format_lifecycle` to match Figma Make session intent label. | 2026-04-09 | — |
| Phase 4 audit | **niche_intelligence schema expanded**: added `video_count_7d` and `trending_keywords` columns for TrendScreen. | 2026-04-09 | — |
| Phase 4 audit | **TD-5 added**: documents upfront credit grant model (PayOS one-time → credits deposited at PAID webhook, no monthly top-up cron). | 2026-04-09 | — |
| Phase 4 audit | **Overage pack 30 credits added** (350,000đ / 11,700đ per credit). | 2026-04-09 | — |
| Phase 4 audit | **Overage 50-credit price corrected**: 600,000đ → 550,000đ. | 2026-04-09 | — |
| Phase 4 audit | **ZaloPay noted in screen-specs**: Figma Make PaymentMethodRow includes ZaloPay. Confirm PayOS supports before launch. | 2026-04-09 | — |
| Phase 4 audit | **seed.sql trend_velocity extended**: added niches 8 (Gym/Fitness) and 17 (Gaming). | 2026-04-09 | — |
| Two-axis niche refactor | **`profiles.primary_niche` dropped** (PR6 applied 2026-05-13). Cloud Run + FE migrated to `creator_niche_id`. `legacyNicheIdForCreatorNiche()` resolver in `src/lib/profileNiches.ts` and `profile_niches.py` bridges corpus queries. Retain mapping until 2026-06-13. | 2026-05-13 | — |
| v5 pipeline refactor | **Two-Core Architecture shipped**: `run_extraction_core` (static pixel analysis, immutable, 1 Gemini call) + `run_video_diagnosis_core` (cohort-comparative narrative, 1h TTL, 2 Gemini calls). Replaces single monolithic pipeline. `video_diagnostics` table now caches diagnosis layer separately from `video_corpus`. | 2026-05-13 | — |
| v5 pipeline refactor | **`_schema_version: "v5"` marker added** to backend response. Frontend `isV5Report()` uses this as primary signal; sentence-count heuristic is fallback only. | 2026-05-13 | — |
| v5 pipeline refactor | **`admin_flush_video_diagnostics_cache` RPC added** (migration `20260513070000_*`). Admin-only, accepts TikTok URL, deletes matching `video_diagnostics` rows. Used by acceptance tests to force fresh analysis. | 2026-05-13 | — |
| v5 UI layout audit | **VideoBody layout changes**: "Vấn đề chính" → "Vấn đề cốt lõi"; error rows numbered 1/2/3 (replaces severity label + timestamp); "Fix" chip → "Sửa:" inline label; "Cần làm gì khác" prose → `NextStepsSection` bullet list; "Lỗi cấu trúc" section header removed (self-labelled by numbers); `ChannelProofBlock` rewritten to show `@handle` title + 2-cell FormatRangeCell (best vs analyzed format). | 2026-05-13 | 461ad56 |
| v5 UI layout audit | **`CreatorComparisonUnavailable` empty state removed**: no longer renders the dashed "not enough data" box when `creator_comparison` is null — `ChannelProofBlock` already covers channel data. | 2026-05-14 | 767cc4c |
| v5 prompt engineering | **Channel-first diagnosis voice**: `van_de_chinh` now opens with the creator's own channel data (top_videos / per_format_views) as sentence 1, then contrasts what this specific video does differently. `loi_chinh_narrative.narrative` sentence 2 now requires channel data comparison. Voice guide updated with CHANNEL-FIRST mandatory principle + audit-form anti-patterns + channel-first few-shot examples. | 2026-05-14 | a3255b3 |
| v5 prompt engineering | **Error titles and fix instructions sharpened**: title ≤10 words (was ≤5), em-dash allowed for contrast; fix must have 2 parts — specific action at timestamp + quoted concrete example. | 2026-05-13 | — |
| Playwright acceptance | **Phase 4.5 v5 acceptance test added** (`tests/v5-acceptance.spec.ts`, 10 criteria, `v5-acceptance` project in `playwright.config.ts`). C2 updated for "Vấn đề cốt lõi" label; C5 updated for "Sửa:" vs legacy "Fix". | 2026-05-13 | 461ad56 |
