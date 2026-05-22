# Data Utilization Map V1 — GetViews.vn

> **Pivot SSOT (2026-05-21+):** Cohort canonical = `(content_class_id, creator_tier)`; browse/filter = junction `content_class_id` — [`system-design.md`](system-design.md) §9 · [`two-axis-niche-model.md`](two-axis-niche-model.md).

**Version:** 1.1 (as-built resync)  
**Last updated:** 2026-05-22  
**Code baseline:** `main` @ `8ad7ab0` (Wave 0 shipped)  
**Status:** As-built FIELD × feature matrix + V1 gap markers (`🔨`)  
**Vision:** [`feature-map-v1.md`](feature-map-v1.md) v2.0 FINAL  
**Incremental SSOT:** [`incremental-v1-roadmap.md`](../plans/incremental-v1-roadmap.md) — Wave 0 ✅ · Wave 1 ✅ @ `e3b5d01` · Wave 2+ open  
**As-built routes:** [`feature-map.md`](feature-map.md)  
**Technical audit:** [`corpus-gemini-utilization-audit.md`](corpus-gemini-utilization-audit.md) (tier A–D, trim-safe)  
**Schema source:** [`models.py`](../../cloud-run/getviews_pipeline/models.py) `VideoAnalysis` · [`corpus_ingest.py`](../../cloud-run/getviews_pipeline/corpus_ingest.py) `_build_corpus_row`

---

## Ràng buộc (Objective 5)

> **Mỗi field extract phải phục vụ ít nhất một feature sản phẩm.** Không “orphan data” — không field trong prompt/schema mà không có đường đi UI, batch aggregate, hoặc signal.

**Mục tiêu chặt V1:** field Gemini trong production prompt nên phục vụ **F2 hoặc F1 + ≥1 cột khác** (F4/F5/F6/STU/F7/BAT), trừ mục §8 Orphans đã có action (trim / wire / defer).

**Invariant:** Live ingest và on-demand extract **cùng contract** — TD-7 ([`system-design.md`](system-design.md) §10). Mọi field mới → thêm hàng vào bảng này **trước** merge.

### As-built vs V1 vision

| Ký hiệu trong bảng | Nghĩa |
|--------------------|--------|
| Ô bình thường (`bench`, `MV`, …) | **Shipped** — có consumer trong code hoặc cron today |
| **`🔨`** trong cột Ghi chú | Vision / roadmap item — **chưa** wire end-to-end |
| §7 depth split | **V1 target** — `analysis_depth` basic/deep **chưa** trong FE/BE/migrations |

**Prod pivot defaults (2026-05-21):** `CORPUS_SCORE_COHORT=class`, `CORPUS_INGEST_LOOP=class`, `LIVE_COHORT_CLASS_FIRST=true`, `CORPUS_WRITE_NICHE_ID=false`, `REFRESH_NICHE_INTELLIGENCE_MV=false`, HI-11 `route` on batch + user pods.

---

## Cột feature (map F1–F8 + Studio)

| Cột | ID | Mô tả |
|-----|-----|--------|
| **F2** | F2 | Video **Cơ bản** — whitelist §4.2, manifest cap 3, Win default từ Xu hướng (**🔨** depth param) |
| **F1** | F1 | Video **Chuyên sâu** — full `SECTION_POOL` + `boost_attribution` + cap 5 (**🔨** depth param) |
| **F5** | F5 | Soi kênh **Nhanh** — card ED + 1–2 finding P0 (**🔨** `channel_findings`) |
| **F4** | F4 | Soi kênh **Sâu** — SSE memo + trajectory/score_card (**🔨** `channel_findings[]` §5.3) |
| **F6** | F6 | **Xu hướng** — công thức viral + kho video (class-first browse) |
| **STU** | Studio §3.1 | **Gợi ý hôm nay** I Morning Signal · II hooks · III within-niche breakouts |
| **F7** | F7 | **Script Studio** — hook, shot list, scene intel, ritual prefill |
| **BAT** | F8 | **Batch / data plane** — MV, cron, claim tiers, M1/M2 hygiene |

*Post-V1 (compare, douyin route, text chat) — không có cột; field chỉ phục vụ chúng → §8 defer.*

---

## Legend ô

| Ký hiệu | Nghĩa |
|---------|--------|
| `bench` | Benchmark vs ngách / peer corpus |
| `pattern` | Pattern kênh / format mix / distribution |
| `leader` | Top performer / viral leader trong feed |
| `anchor` | Neo hook/CTA/shot cho script hoặc ritual |
| `audit` | Chẩn đoán / flag trong synthesis section |
| `timing` | Timing spec (hook window, CTA giây) |
| `spec` | Spec quay (shot list, pacing, overlay) |
| `show` | Hiển thị trực tiếp UI (tile, strip, card) |
| `rollup` | Aggregate N video theo `creator_handle` (kênh) |
| `feed` | Feed Xu hướng / pattern deck / explore sort |
| `MV` | Materialized view / nightly batch job |
| `gate` | Gate section / claim tier / eligibility |
| `teaser` | Manifest tính đủ; F2 **không** synthesize section (§4.2 upsell — **🔨** until `analysis_depth`) |
| `ref` | Reference pool / proximity ranking |
| `—` | Không consumer cột này (giải thích §8 nếu vẫn extract) |

---

## §1 — Hook & production (Gemini extract)

| FIELD | F2 | F1 | F5 | F4 | F6 | STU | F7 | BAT | Ghi chú |
|-------|----|----|----|----|----|-----|----|-----|---------|
| `hook_type` | bench | bench | pattern | pattern | leader | anchor | anchor | MV | `hook_effectiveness`; signals `hook_*`; STU Tier II `HooksTable` |
| `hook_phrase` | show | show | — | history | show | anchor | anchor | — | F6 kho; STU breakouts; F7 opening line |
| `hook_analysis.hook_layering` | teaser | audit | — | — | — | — | spec | — | Signal `hook_layering_single` |
| `hook_analysis.hook_body_contract` | teaser | audit | — | — | — | — | spec | — | Signal `hook_body_contract_violated` |
| `hook_analysis.hook_timeline[]` | timing | timing | — | — | — | — | timing | — | JSON → v6 prompt; **🔨** P1 pacing signals |
| `hook_analysis.first_frame_type` | audit | audit | — | — | — | — | spec | — | Signal `hook_first_frame_non_product` |
| `hook_analysis.face_appears_at` | timing | timing | — | — | — | — | timing | MV | Promoted col; hook stats aggregate |
| `hook_analysis.first_speech_at` | timing | timing | — | — | — | — | timing | MV | Guards + cohort hook norms |
| `hook_analysis.dialect_detected` | gate | audit | flag | rollup | — | — | — | — | `dialect` col; signals hook/sound/persona |
| `hook_analysis.price_anchor_manipulation_suspected` | gate | audit | — | rollup | — | — | — | — | Compliance `hook_gia_soc_*` |
| `hook_analysis.hook_notes` | — | audit | — | — | — | — | — | — | Prompt + synthesis context only |
| `scenes[]` (type, start, end) | teaser | audit | — | pattern | — | — | spec | MV | `scene_count`, `video_duration`; `scene_intelligence` refresh |
| `scenes[].framing/pace/overlay_style/subject/motion/description` | — | audit | — | — | — | — | spec | MV | `video_shots/` + script matcher (F7) |
| `transitions_per_second` | teaser | audit | — | pattern | feed | — | spec | MV | `signals/editing.py`; **🔨** full P1 backlog |
| `text_overlays[]` | teaser | audit | — | — | — | — | spec | — | `text_overlay_count`; `pattern_fingerprint`; editing signals |
| `text_overlay_font_size_tier` | teaser | audit | — | — | — | — | spec | — | `signals/editing.py` |
| `text_overlay_color_emphasis` | teaser | audit | — | — | — | — | spec | — | `signals/editing.py` |
| `safe_zone_status` | teaser | audit | — | rollup | — | — | spec | — | Section `metadata`; gate commerce UI |
| `color_grading_style` | teaser | audit | — | — | — | — | spec | — | `editing_color_grading_niche_mismatch` |
| `energy_level` | — | teaser | — | — | — | — | — | MV | `pattern_fingerprint` fingerprint only |
| `has_human_speaking_to_camera` | gate | audit | — | — | — | — | spec | — | Manifest / guards |
| `has_expressed_opinion_or_question` | gate | audit | — | — | — | — | spec | — | Engagement / hook heuristics |

---

## §2 — Commerce, CTA, compliance

| FIELD | F2 | F1 | F5 | F4 | F6 | STU | F7 | BAT | Ghi chú |
|-------|----|----|----|----|----|-----|----|-----|---------|
| `commerce_intent.conversion_objective` | gate | audit | — | rollup | feed | — | spec | — | `is_commerce`; signals `commerce_*` |
| `commerce_intent.product_price_tier` | teaser | audit | — | rollup | — | — | spec | — | P1 `commerce_price_tier_structure` |
| `commerce_intent.creator_type` | teaser | audit | — | rollup | — | — | spec | — | `commerce_creator_type_inconsistent` |
| `commerce_intent.verbal_cta_present` | gate | audit | — | rollup | — | — | spec | — | `commerce_verbal_cta_missing` |
| `commerce_intent.verbal_cta_quote` | — | audit | — | — | — | — | anchor | — | Synthesis evidence |
| `commerce_intent.disclosure_present` | gate | audit | rollup | rollup | — | — | spec | — | **🔨** channel `channel_ad_law_*` aggregate |
| `commerce_intent.disclosure_form` | gate | audit | rollup | rollup | — | — | spec | — | Compliance signals |
| `cta` (raw) | gate | audit | — | — | — | anchor | spec | — | → `cta_type` promoted |
| `promotion_type` | gate | audit | — | rollup | — | — | spec | — | Promoted; `commerce_promotion_detected` |
| `affiliate_script_phases.*` | teaser | audit | — | — | — | — | spec | — | `script_affiliate_five_phase_gap` |
| `livestream_funnel_demo` | teaser | audit | — | — | — | — | spec | — | `script_livestream_demo_too_complete` |
| `compliance_flags` (derived) | gate | audit | rollup | rollup | — | — | — | — | Restricted phrase, price anchor, disclosure |

---

## §3 — Persona, sound, engagement

| FIELD | F2 | F1 | F5 | F4 | F6 | STU | F7 | BAT | Ghi chú |
|-------|----|----|----|----|----|-----|----|-----|---------|
| `creator_persona` | gate | audit | pattern | rollup | — | — | spec | — | `persona_*` signals; channel persona block |
| `persona_consistency_signals.*` | — | teaser | — | rollup | — | — | — | — | **Orphan** — **🔨** F4 P2 `channel_persona_drift` |
| `tone` | bench | audit | pattern | pattern | feed | — | spec | MV | Promoted; F6 sort |
| `slang_terms_used` | — | audit | — | rollup | — | — | — | — | `persona_slang_dated` |
| `slang_freshness_score` | — | audit | — | rollup | — | — | — | — | **🔨** P2 `channel_slang_staleness` |
| `target_audience` | show | show | — | — | — | — | spec | — | Promoted; `ContextStrip` |
| `pain_points` | show | show | — | — | — | — | spec | — | Promoted; `ContextStrip` |
| `style_tags` | show | show | — | — | — | — | spec | — | Promoted; `ContextStrip` |
| `audio_transcript` | bench | bench | — | history | — | — | anchor | — | `transcript_snippet`; guards; proximity |
| `audio_track_role` | teaser | gate | — | rollup | — | — | spec | — | **Gate** section `sound` (`diagnose_sections`) |
| `sound_layering` | teaser | audit | — | — | — | — | spec | — | `sound_layering_thin_mukbang` |
| `sound_dialect_audio` | teaser | audit | — | — | feed | — | spec | — | `sound_dialect_audio_mismatch`; `trending_sounds` |
| `trending_vpop_sound` | teaser | audit | — | rollup | feed | — | — | — | `metadata_business_vpop_cml_friction` |
| `share_trigger_type` | teaser | audit | — | — | — | — | spec | — | `trigger_share_*` |
| `save_trigger_type` | teaser | audit | — | — | — | — | spec | — | **🔨** W0 `win_*` hit-tier backlog |
| `loop_architecture_score` | teaser | audit | — | — | — | — | — | — | `engagement_loop_architecture` |
| `trigger_*` (su_that, share, save archetypes) | gate | audit | — | — | — | — | spec | — | `signals/triggers.py` → `diagnosis` |

---

## §4 — Context, niche, Douyin

| FIELD | F2 | F1 | F5 | F4 | F6 | STU | F7 | BAT | Ghi chú |
|-------|----|----|----|----|----|-----|----|-----|---------|
| `content_context.subject_matter` | ref | ref | — | — | feed | anchor | — | MV | Proximity ref; `daily_ritual`; pattern deck |
| `content_context.creator_role` | teaser | audit | — | — | — | — | spec | — | Commerce vs role mismatch signal |
| `content_context.content_purpose` | teaser | audit | — | — | feed | — | — | — | `pattern_fingerprint`, deck synth |
| `content_context.language_register` | — | audit | — | — | — | — | spec | — | Persona / synthesis |
| `content_context.primary_subjects` | — | teaser | — | — | — | — | — | — | Synthesis JSON only — weak |
| `content_context.setting` | — | teaser | — | — | — | — | spec | — | Script / synthesis |
| `content_context.products_mentioned` | teaser | audit | — | — | — | — | spec | — | Commerce context |
| `content_context.topical_hashtags_implied` | — | teaser | — | — | feed | — | — | — | Metadata backlog P1 |
| `niche_classification.creator_niche_slug` | gate | gate | — | — | feed | — | — | MV | HI-11 route; telemetry cols on row |
| `niche_classification.format_axis` | bench | bench | pattern | pattern | leader | — | spec | MV | → `content_format` / `content_class_id` |
| `niche_classification.confidence` | gate | gate | — | — | — | — | — | BAT | `niche_resolution_confidence` |
| `topics[]` | bench | bench | — | — | feed | — | — | MV | Promoted; ref desc; sound signals |
| `key_messages[]` | — | — | — | — | — | — | — | — | **Orphan** — trim-safe (§8) |
| `content_direction.what_works` | — | teaser | — | — | feed | anchor | — | MV | `pattern_fingerprint`, `video_patterns` |
| `content_direction.suggested_angles` | — | teaser | — | — | — | anchor | spec | — | Ritual / script angles |
| `douyin_origin` | — | audit | — | — | feed | — | — | — | Null at TikTok ingest; on-demand `douyin_match` |
| `vietnam_adoption_stage` | — | audit | — | — | feed | — | — | — | Optional F6 block |
| `migration_fit_assessment` | — | audit | — | — | — | — | — | — | `douyin_migration_poor_fit` |
| `tiktok_account_type_heuristic` | teaser | audit | — | rollup | — | — | — | — | `metadata_*` signals |

---

## §5 — Promoted corpus + EnsembleData + F8 columns

*Không phải Gemini field riêng — “data plane” mà mọi feature đọc. Taxonomy **16 × 82**; Phase C dropped `video_corpus.niche_id` — dùng `ingest_loop_niche_id` + `content_class_id`.*

| FIELD | F2 | F1 | F5 | F4 | F6 | STU | F7 | BAT | Ghi chú |
|-------|----|----|----|----|----|-----|----|-----|---------|
| `views` | bench | bench | show | score | sort | breakout | — | M1 | ED; boost M1; diagnosis benchmarks |
| `likes` / `comments` / `shares` / `saves` | bench | bench | show | score | sort | — | — | M1 | ER, boost heuristic |
| `engagement_rate` | bench | bench | show | score | feed | — | — | M1/MV | Promoted; cohort percentiles |
| `breakout_ratio` / `breakout_multiplier` | bench | bench | show | score | feed | breakout | — | M1 | Ingest + live; STU `useTopBreakouts`; Trends rails |
| `creator_median_views` | bench | bench | show | score | — | — | — | — | `ContextStrip`; channel baseline |
| `content_format` | bench | bench | pattern | pattern | leader | anchor | spec | MV | Regex + HI-9; `format_distribution` |
| `content_class_id` | gate | gate | — | pattern | feed | — | — | MV | Two-axis canonical cohort; browse filter |
| `ingest_loop_niche_id` | ref | ref | — | pattern | feed | anchor | spec | MV | Ingest loop bucket (replaces legacy `niche_id` col) |
| `ingest_loop_content_class_id` | — | — | — | — | feed | — | — | BAT | Loop provenance; class ingest telemetry |
| `class_assignment_tier` / `class_assignment_disagreement` | — | — | — | — | — | — | — | BAT | HI-11 / validated subset gates |
| `score_cohort_mismatch` | — | audit | — | — | — | — | — | BAT | Loop class ≠ resolved class flag |
| `cta_type` | gate | audit | — | — | feed | — | spec | — | From `cta` + classifier |
| `is_commerce` | gate | audit | rollup | rollup | feed | — | spec | — | Batch filter commerce cohorts |
| `dialect` (promoted) | gate | audit | flag | rollup | — | — | — | — | From `dialect_detected` |
| `hashtags` / `caption` | bench | bench | — | history | feed | — | — | MV | Proximity; `metadata_hashtag_*` |
| `sound_id` / `sound_name` / `is_original_sound` | teaser | audit | — | rollup | feed | — | spec | MV | `sound_*` signals; `trending_sounds` |
| `posting_hour` / `posted_at` | teaser | audit | — | rollup | feed | — | — | MV | `context_golden_hour_*` |
| `creator_followers` / `creator_tier` | show | bench | show | score | feed | — | — | MV | Explore tiles; `content_class_tier_intelligence` |
| `text_overlay_count` / `scene_count` / `video_duration` | bench | audit | — | pattern | feed | — | spec | MV | Derived from extract |
| `transcript_snippet` | bench | bench | — | — | — | — | — | gate | Promoted 500 chars; full-text search **🔨** F8 |
| `niche_resolution_source` / `_confidence` / `inferred_creator_niche_id` | — | — | — | — | feed | anchor | — | BAT | HI-11 telemetry |
| `boost_attribution` | — | audit | flag | rollup | filter | — | — | MV | **Batch ✅** ingest; **🔨** live M3 user video |
| `reference_eligible` | ref | ref | — | ref | filter | — | — | MV | **✅** M2 — `fetch_corpus_reference_pool` when `corpus_boost_hard_reject`; **🔨** channel peers W4 |
| `ingest_relaxation_tier` | — | — | — | — | — | — | — | BAT | Ingest policy telemetry |
| `stats_history` | — | audit | — | rollup | — | — | — | M4 | **🔨** §4.7 P1 cron re-fetch |
| `distribution_shape` | — | audit | — | — | — | — | — | M4 | Derived from `stats_history` |
| `distribution_*` (hashtag cluster annotations) | teaser | audit | — | — | feed | — | — | MV | `annotate_distribution` at ingest |
| `peer_percentile` (derived at diagnosis) | show | show | — | — | — | — | — | MV | **✅** `finalize_niche_meta_peer_tier` when axis `content_class_tier` |

---

## §6 — Batch aggregates (rows / MV — không nằm trong `VideoAnalysis`)

| AGGREGATE / TABLE | F2 | F1 | F5 | F4 | F6 | STU | F7 | BAT | Nguồn field | As-built |
|-------------------|----|----|----|----|----|-----|----|-----|-------------|----------|
| `content_class_intelligence` | bench | bench | — | score | feed | show | — | MV | views, ER, hooks, formats by `content_class_id` | **✅** Morning Signal, Trends thin banner, diagnosis `benchmark_axis=content_class` |
| `content_class_tier_intelligence` | bench | bench | — | score | — | — | — | MV | `(content_class_id, creator_tier)` peer band | **✅** BE + `peer_percentile` label → `FlopDiagnosisStrip` |
| `creator_niche_content_class_stats` | — | bench | — | — | feed | — | — | MV | Junction rollup for browse gates | **✅** refreshed nightly |
| `hook_effectiveness` | bench | bench | — | pattern | leader | anchor | anchor | MV | `hook_type`, views, ER | **✅** STU Tier II, script, pattern reports |
| `video_patterns` | bench | bench | — | pattern | feed | anchor | spec | MV | `content_format`, corpus peers | **✅** F6 grid + STU |
| `niche_intelligence` | bench | bench | — | score | — | — | — | MV | Legacy bridge | **Bridge only** — `REFRESH_NICHE_INTELLIGENCE_MV=false` |
| `niche_meta` / percentiles (live fetch) | bench | bench | — | score | — | — | — | MV | `fetch_video_benchmark_with_axis` class→tier→niche fallback | **✅** on-demand diagnosis |
| `daily_ritual` | — | — | — | — | — | show | anchor | MV | Top corpus + ritual templates | **✅** STU Tier I `StudioHero` |
| `scene_intelligence` | — | teaser | — | — | — | — | spec | MV | `scenes[]` enrichment nightly | **✅** F7 panel |
| `creator_velocity` | — | — | show | score | — | — | — | MV | ED rollup by handle | **✅** channel score card inputs |
| `trending_sounds` | teaser | audit | — | — | feed | — | spec | MV | `sound_id`, lifecycle | **✅** |
| `claim_tiers` | gate | gate | gate | gate | gate | gate | gate | gate | Sample size gates | **✅** `ConfidenceStrip`, corpus-health |
| `channel_diagnoses` (cached memo) | — | — | — | show | — | — | — | — | Output F4 | **✅** 7d cache; **🔨** findings inject |
| `video_shots` (R2 + matcher) | — | teaser | — | — | — | — | spec | MV | `scenes[]` frames | **✅** |

### §6.1 Class-first surfaces (as-built @ `8ad7ab0`)

| Surface | Data read | Filter / cohort |
|---------|-----------|-----------------|
| **STU Tier I** `MorningSignalStrip` | `content_class_intelligence` via `useClassMorningSignals` | Primary junction classes only |
| **STU Tier II** `HooksTable` | `hook_effectiveness` + patterns | `useTopPatterns` scoped to creator niche |
| **STU Tier III** `BreakoutGrid` | `video_corpus` | `content_class_id IN junction`; `breakout_multiplier ≥ 1` |
| **F6 Kho video** `ExploreScreen` | `video_corpus` | `applyVideoCorpusNicheFilter` class-first; thin banner = sum junction `sample_size` |
| **F6 Cross-niche** `CrossNicheBreakoutLane` | `video_corpus` | `content_class_id NOT IN` user junction |
| **F6 TrendsRail** | `useTrendsRailVideos` | Within `ingest_loop_niche_id` — 7d + viral rails |
| **F1/F2 diagnosis** | `fetch_video_benchmark_with_axis` | tier MV → class MV → niche fallback |
| **F4 channel peers** | `video_corpus` by handle | Class+tier fallback chain; **no** `reference_eligible` filter yet |

---

## §7 — Depth split (F2 whitelist vs F1-only) — **V1 vision 🔨**

**Not in code:** no `analysis_depth` param, no F2 section whitelist enforcement, no separate cache key. Today all video diagnoses use **one depth** (full section pool path).

**Target (unchanged from vision):** cùng một lần extract — `analysis_depth` chỉ đổi synthesis ([`feature-map-v1.md`](feature-map-v1.md) §4.0, §4.12).

### F2 synthesize (whitelist §4.2) — target

| `section_id` | Fields chính đi qua manifest |
|--------------|------------------------------|
| `diagnosis` | triggers, performance, win W0, baseline |
| `compliance` | commerce disclosure, restricted phrase, price anchor |
| `hook_analysis` | `hook_*`, timeline, layering, dialect |
| `niche_pattern` | `hook_type`, `content_format`, refs (`reference_eligible`) |
| `next_video` | format, CTA, win replicable |

### F1-only synthesize (F2 = `teaser` hoặc manifest-only) — target

| `section_id` | Fields chính |
|--------------|--------------|
| `distribution` | hashtags, caption, sound_original, engagement, golden hour |
| `douyin_origin` | `douyin_origin`, adoption, migration |
| `channel_pattern` | channel baseline, breakout vs kênh |
| `commerce` | full `commerce_intent` |
| `metadata` | safe_zone, account heuristic, hashtag volume |
| `editing` | color, overlays, transitions, b-roll mix |
| `sound` | lifecycle, CML, layering, audio hook window |
| `persona` | persona, tone, slang, dialect tension |
| `script_structure` | affiliate phases, livestream funnel |
| `boost_attribution` | M1/M3/M4, `stats_history`, `boost_attribution` col |

**Cap manifest:** F2 = 3 signals/section · F1 = 5 — **🔨** Wave 3+.

---

## §8 — Orphans, weak fields & actions

| Field / nhóm | Verdict | Action |
|--------------|---------|--------|
| `key_messages[]` | **Orphan** | Trim after ablation — trim-safe |
| `persona_consistency_signals` | **Orphan** | **🔨** wire F4 P2 or defer |
| `peer_percentile` / `peer_percentile_label` | **Strong** | Wired W1-3 when tier MV + `creator_tier` on corpus row |
| `win_er_above_niche_p75` / `win_hook_aligns_niche_top` | **Strong** | `signals/win.py`; `tier_gate=hit`; W1-6 |
| `win_*` signals (§4.8 W0) | **Missing** | **🔨** W1-6 `signals/win.py` |
| `channel_findings[]` roll-ups | **Missing** | **🔨** W4 — aggregate `analysis_json` on handle |
| `key_timestamps[]` | Weak | Schema compat; defer |
| `energy_level` | Weak | `pattern_fingerprint` only — OK BAT |
| `hook_analysis.hook_notes` | Weak | Prompt filler |
| `content_context.primary_subjects` | Weak | Synthesis only |
| `niche_classification` on **peer** rows | Intentional skip | Ref score ignores |
| `douyin_origin` on TikTok corpus | Null at ingest | F1 on-demand only |
| Live `boost_attribution` (M3) | **Partial** | Batch col ✅; user-video heuristic **🔨** W4 |

**Không coi orphan:** `commerce_intent`, `text_overlays[]`, `audio_track_role`, `target_audience`, `pain_points`, `style_tags`.

---

## §9 — Coverage checklist (v1.1 as-built)

| Kiểm tra | Target | Kết quả @ `8ad7ab0` |
|----------|--------|---------------------|
| `VideoAnalysis` fields có ≥1 ô hoặc §8 | 100% | ✅ ~70 rows §1–§4 |
| Promoted + F8 columns có ≥1 ô | 100% | ✅ §5 (+ Phase C cols) |
| Batch aggregates có ≥1 feature | 100% | ✅ §6 (+ class MVs) |
| Class-first surfaces documented | Yes | ✅ §6.1 |
| True orphans với action | ≤5 | ✅ 2 + weak group §8 |
| Depth split | Documented | ✅ §7 marked **🔨 vision** |
| Wave 0 F8 verify | Done | ✅ ref pool + boost batch + channel 3× credit |

**Open gates (incremental roadmap):** W3 `analysis_depth` · W4 channel findings + live boost · W1-1–W1-6 ✅ (except W1-5 doc resync).

---

## Methodology (maintainer)

1. **As-built grep:** `cloud-run/getviews_pipeline/signals/`, `diagnose_sections.py`, `channel_diagnose.py`, `corpus_ingest.py` `_build_corpus_row`, `src/hooks/use*.ts`, `ContextStrip.tsx`, `FlopDiagnosisStrip.tsx`.
2. **Vision delta:** [`feature-map-v1.md`](feature-map-v1.md) §4.2, §4.7–§4.8, §5.3, §7 — mark `🔨` when not in code.
3. **Audit tier:** [`corpus-gemini-utilization-audit.md`](corpus-gemini-utilization-audit.md) §2–§7.
4. **Pivot:** [`system-design.md`](system-design.md) §9, [`two-axis-niche-model.md`](two-axis-niche-model.md) §9 MV chain.

**Carousel:** `CarouselAnalysis` (HI-16) — `FlopDiagnosisStrip` carousel save hint forward-compatible; full matrix row deferred until carousel diagnosis ships.

---

## Related

| Doc | Role |
|-----|------|
| [`feature-map.md`](feature-map.md) | As-built routes + endpoints |
| [`feature-map-v1.md`](feature-map-v1.md) | Product vision + feature IDs |
| [`incremental-v1-roadmap.md`](../plans/incremental-v1-roadmap.md) | Wave sequencing + F8 DoD |
| [`wave0-cron-sla-checklist.md`](wave0-cron-sla-checklist.md) | Ops verify BAT crons |
| [`corpus-gemini-utilization-audit.md`](corpus-gemini-utilization-audit.md) | Tier A–D, trim strategy |
| [`system-design.md`](system-design.md) | TD-7 parity, ingest architecture |
| [`product-value-audit.md`](product-value-audit.md) | Value → data gaps |
