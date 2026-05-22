# Data Utilization Map V1 — GetViews.vn

> **Pivot SSOT (2026-05-21+):** Cohort + browse runtime — [`system-design.md`](system-design.md) §9. Matrix below is **pre-implement gate (2026-05-20)** — taxonomy prod **16×82**; several F6 rows still reference `niche_intelligence` bridge paths. Resync tracked in [`incremental-v1-roadmap.md`](../plans/incremental-v1-roadmap.md) W1-5.

**Version:** 1.0  
**Last updated:** 2026-05-20 (matrix stale vs prod pivot — see roadmap W1-5)  
**Status:** Pre-implement gate — Wave 1 data architecture  
**Vision:** [`feature-map-v1.md`](feature-map-v1.md) v2.0 FINAL  
**Incremental SSOT:** [`incremental-v1-roadmap.md`](../plans/incremental-v1-roadmap.md) — F8 waves 0–5  
**Technical audit:** [`corpus-gemini-utilization-audit.md`](corpus-gemini-utilization-audit.md) (tier A–D, trim-safe)  
**Schema source:** [`models.py`](../../cloud-run/getviews_pipeline/models.py) `VideoAnalysis` · [`corpus_ingest.py`](../../cloud-run/getviews_pipeline/corpus_ingest.py) `_build_corpus_row`

---

## Ràng buộc (Objective 5)

> **Mỗi field extract phải phục vụ ít nhất một feature sản phẩm.** Không “orphan data” — không field trong prompt/schema mà không có đường đi UI, batch aggregate, hoặc signal.

**Mục tiêu chặt V1:** field Gemini trong production prompt nên phục vụ **F2 hoặc F1 + ≥1 cột khác** (F4/F5/F6/STU/F7/BAT), trừ mục §8 Orphans đã có action (trim / wire / defer).

**Invariant:** Live ingest và on-demand extract **cùng contract** — TD-7 ([`system-design.md`](system-design.md) §10). Mọi field mới → thêm hàng vào bảng này **trước** merge.

---

## Cột feature (map F1–F8 + Studio)

| Cột | ID | Mô tả |
|-----|-----|--------|
| **F2** | F2 | Video **Cơ bản** — whitelist §4.2, manifest cap 3, Win default từ Xu hướng |
| **F1** | F1 | Video **Chuyên sâu** — full `SECTION_POOL` + `boost_attribution` + cap 5 |
| **F5** | F5 | Soi kênh **Nhanh** — card ED + 1–2 finding P0 |
| **F4** | F4 | Soi kênh **Sâu** — SSE memo + `channel_findings` (§5.3, V1 build) |
| **F6** | F6 | **Xu hướng** — công thức viral + kho video |
| **STU** | Studio §3.1 | **Gợi ý hôm nay** I/II/III (`daily_ritual`, hooks, breakout) |
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
| `teaser` | Manifest tính đủ; F2 **không** synthesize section (§4.2 upsell) |
| `ref` | Reference pool / proximity ranking |
| `—` | Không consumer cột này (giải thích §8 nếu vẫn extract) |

---

## §1 — Hook & production (Gemini extract)

| FIELD | F2 | F1 | F5 | F4 | F6 | STU | F7 | BAT | Ghi chú |
|-------|----|----|----|----|----|-----|----|-----|---------|
| `hook_type` | bench | bench | pattern | pattern | leader | anchor | anchor | MV | `hook_effectiveness`; signals `hook_type_niche_mismatch`, W0 `win_hook_*` |
| `hook_phrase` | show | show | — | history | show | anchor | anchor | — | F6 kho + search_vector; F7 opening line |
| `hook_analysis.hook_layering` | teaser | audit | — | — | — | — | spec | — | Signal `hook_layering_single` |
| `hook_analysis.hook_body_contract` | teaser | audit | — | — | — | — | spec | — | Signal `hook_body_contract_violated` |
| `hook_analysis.hook_timeline[]` | timing | timing | — | — | — | — | timing | — | JSON → v6 prompt; chưa signal riêng (vision P1 pacing) |
| `hook_analysis.first_frame_type` | audit | audit | — | — | — | — | spec | — | Signal `hook_first_frame_non_product` |
| `hook_analysis.face_appears_at` | timing | timing | — | — | — | — | timing | MV | Promoted col; hook stats aggregate |
| `hook_analysis.first_speech_at` | timing | timing | — | — | — | — | timing | MV | Guards + niche `avg_first_speech_at` |
| `hook_analysis.dialect_detected` | gate | audit | flag | rollup | — | — | — | — | `dialect` col; signals hook/sound/persona |
| `hook_analysis.price_anchor_manipulation_suspected` | gate | audit | — | rollup | — | — | — | — | Compliance `hook_gia_soc_*` |
| `hook_analysis.hook_notes` | — | audit | — | — | — | — | — | — | Prompt + synthesis context only |
| `scenes[]` (type, start, end) | teaser | audit | — | pattern | — | — | spec | MV | `scene_count`, `video_duration`; `scene_intelligence` refresh |
| `scenes[].framing/pace/overlay_style/subject/motion/description` | — | audit | — | — | — | — | spec | MV | `video_shots/` + script matcher (F7) |
| `transitions_per_second` | teaser | audit | — | pattern | feed | — | spec | MV | P1 `hook_pacing_*`, `editing_cut_pace_*` |
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
| `commerce_intent.disclosure_present` | gate | audit | rollup | rollup | — | — | spec | — | P1 channel `channel_ad_law_*` |
| `commerce_intent.disclosure_form` | gate | audit | rollup | rollup | — | — | spec | — | Compliance signals |
| `cta` (raw) | gate | audit | — | — | — | anchor | spec | — | → `cta_type` promoted |
| `promotion_type` | gate | audit | — | rollup | — | — | spec | — | Promoted; `commerce_promotion_detected` |
| `affiliate_script_phases.*` | teaser | audit | — | — | — | — | spec | — | `script_affiliate_five_phase_gap` (F1 only) |
| `livestream_funnel_demo` | teaser | audit | — | — | — | — | spec | — | `script_livestream_demo_too_complete` |
| `compliance_flags` (derived) | gate | audit | rollup | rollup | — | — | — | — | Restricted phrase, price anchor, disclosure |

---

## §3 — Persona, sound, engagement

| FIELD | F2 | F1 | F5 | F4 | F6 | STU | F7 | BAT | Ghi chú |
|-------|----|----|----|----|----|-----|----|-----|---------|
| `creator_persona` | gate | audit | pattern | rollup | — | — | spec | — | `persona_*` signals; channel persona |
| `persona_consistency_signals.*` | — | teaser | — | rollup | — | — | — | — | **Weak** — P2 `channel_persona_drift` (§8) |
| `tone` | bench | audit | pattern | pattern | feed | — | spec | MV | Promoted; `tone_distribution`; F6 sort |
| `slang_terms_used` | — | audit | — | rollup | — | — | — | — | `persona_slang_dated` |
| `slang_freshness_score` | — | audit | — | rollup | — | — | — | — | P2 `channel_slang_staleness` |
| `target_audience` | show | show | — | — | — | — | spec | — | Promoted; `ContextStrip` (F2/F1) |
| `pain_points` | show | show | — | — | — | — | spec | — | Promoted; `ContextStrip` |
| `style_tags` | show | show | — | — | — | — | spec | — | Promoted; `ContextStrip`; weak in signals |
| `audio_transcript` | bench | bench | — | history | — | — | anchor | — | `transcript_snippet`; guards; proximity 200 chars |
| `audio_track_role` | teaser | gate | — | rollup | — | — | spec | — | **Gate** section `sound` (`diagnose_sections`) |
| `sound_layering` | teaser | audit | — | — | — | — | spec | — | `sound_layering_thin_mukbang` |
| `sound_dialect_audio` | teaser | audit | — | — | feed | — | spec | — | `sound_dialect_audio_mismatch`; `trending_sounds` |
| `trending_vpop_sound` | teaser | audit | — | rollup | feed | — | — | — | `metadata_business_vpop_cml_friction` |
| `share_trigger_type` | teaser | audit | — | — | — | — | spec | — | `trigger_share_*` (diagnosis) |
| `save_trigger_type` | teaser | audit | — | — | — | — | spec | — | W0 `engagement_save_*` (hit tier) |
| `loop_architecture_score` | teaser | audit | — | — | — | — | — | — | `engagement_loop_architecture` |
| `trigger_*` (su_that, share, save archetypes) | gate | audit | — | — | — | — | spec | — | `signals/triggers.py` → `diagnosis` |

---

## §4 — Context, niche, Douyin

| FIELD | F2 | F1 | F5 | F4 | F6 | STU | F7 | BAT | Ghi chú |
|-------|----|----|----|----|----|-----|----|-----|---------|
| `content_context.subject_matter` | ref | ref | — | — | feed | anchor | — | MV | Proximity ref; `morning_ritual`; pattern deck |
| `content_context.creator_role` | teaser | audit | — | — | — | — | spec | — | Commerce vs role mismatch signal |
| `content_context.content_purpose` | teaser | audit | — | — | feed | — | — | — | `pattern_fingerprint`, deck synth |
| `content_context.language_register` | — | audit | — | — | — | — | spec | — | Persona / synthesis |
| `content_context.primary_subjects` | — | teaser | — | — | — | — | — | — | Synthesis JSON only |
| `content_context.setting` | — | teaser | — | — | — | — | spec | — | Script / synthesis |
| `content_context.products_mentioned` | teaser | audit | — | — | — | — | spec | — | Commerce context |
| `content_context.topical_hashtags_implied` | — | teaser | — | — | feed | — | — | — | Metadata backlog P1 |
| `niche_classification.creator_niche_slug` | gate | gate | — | — | feed | — | — | MV | HI-11 shadow/route; **not** ref score on peers |
| `niche_classification.format_axis` | bench | bench | pattern | pattern | leader | — | spec | MV | → `content_format` / `content_class_id` |
| `niche_classification.confidence` | gate | gate | — | — | — | — | — | BAT | `niche_resolution_confidence` |
| `topics[]` | bench | bench | — | — | feed | — | — | MV | Promoted; ref desc; sound signals |
| `key_messages[]` | — | — | — | — | — | — | — | — | **Orphan** — trim-safe (§8) |
| `content_direction.what_works` | — | teaser | — | — | feed | anchor | — | MV | `pattern_fingerprint`, `video_patterns` naming |
| `content_direction.suggested_angles` | — | teaser | — | — | — | anchor | spec | — | Ritual / script angles |
| `douyin_origin` | — | audit | — | — | feed | — | — | — | Null at TikTok ingest; on-demand `douyin_match` |
| `vietnam_adoption_stage` | — | audit | — | — | feed | — | — | — | §8 douyin block (optional F6 UI) |
| `migration_fit_assessment` | — | audit | — | — | — | — | — | — | `douyin_migration_poor_fit` |
| `tiktok_account_type_heuristic` | teaser | audit | — | rollup | — | — | — | — | `metadata_*` signals |

---

## §5 — Promoted corpus + EnsembleData + F8 columns

*Không phải Gemini field riêng — nhưng là “data plane” mà mọi feature đọc.*

| FIELD | F2 | F1 | F5 | F4 | F6 | STU | F7 | BAT | Ghi chú |
|-------|----|----|----|----|----|-----|----|-----|---------|
| `views` | bench | bench | show | score | sort | breakout | — | M1 | ED; boost M1/M3; W0 win ER |
| `likes` / `comments` / `shares` / `saves` | bench | bench | show | score | sort | — | — | M1 | ER, boost heuristic |
| `engagement_rate` | bench | bench | show | score | feed | — | — | M1/MV | Promoted; percentile ngách |
| `breakout_ratio` / `breakout_multiplier` | bench | bench | show | score | feed | breakout | — | M1 | Ingest + live; channel trajectory |
| `creator_median_views` | bench | bench | show | score | — | — | — | — | `ContextStrip`; channel baseline |
| `content_format` | bench | bench | pattern | pattern | leader | anchor | spec | MV | Regex + HI-9; `format_distribution` |
| `content_class_id` | gate | gate | — | pattern | feed | — | — | MV | Two-axis; channel saturation P0 |
| `cta_type` | gate | audit | — | — | feed | — | spec | — | From `cta` + classifier |
| `is_commerce` | gate | audit | rollup | rollup | feed | — | spec | — | Batch filter commerce cohorts |
| `dialect` (promoted) | gate | audit | flag | rollup | — | — | — | — | From `dialect_detected` |
| `hashtags` / `caption` | bench | bench | — | history | feed | — | — | MV | Proximity; `metadata_hashtag_*` |
| `sound_id` / `sound_name` / `is_original_sound` | teaser | audit | — | rollup | feed | — | spec | MV | `sound_*` signals; `trending_sounds` |
| `posting_hour` / `posted_at` | teaser | audit | — | rollup | feed | — | — | MV | `context_golden_hour_*`; P2 ritual hint |
| `creator_followers` / `creator_tier` | show | bench | show | score | feed | — | — | MV | Explore tiles; channel benchmarks |
| `text_overlay_count` / `scene_count` / `video_duration` | bench | audit | — | pattern | feed | — | spec | MV | Derived from extract |
| `transcript_snippet` | bench | bench | — | — | — | — | — | gate | Search **not** indexed (F8 open) |
| `niche_id` (legacy) | ref | ref | — | pattern | feed | anchor | spec | MV | Corpus filter; HI-11 ladder |
| `niche_resolution_source` | — | — | — | — | — | — | — | BAT | HI-11 telemetry; cutover runbook |
| `niche_resolution_confidence` | — | — | — | — | — | — | — | BAT | Shadow/route audit |
| `inferred_creator_niche_id` | — | — | — | — | feed | anchor | — | BAT | Ritual niche pick |
| `boost_attribution` | — | audit | flag | rollup | filter | — | — | MV | §4.7 P0 — F1 section; ref hygiene |
| `reference_eligible` | ref | ref | — | ref | filter | — | — | MV | §4.7 M2 — peer pool |
| `stats_history` | — | audit | — | rollup | — | — | — | M4 | §4.7 P1 spike_then_flat |
| `distribution_shape` | — | audit | — | — | — | — | — | M4 | Derived from `stats_history` |
| `distribution_*` (hashtag cluster annotations) | teaser | audit | — | — | feed | — | — | MV | `annotate_distribution` at ingest |

---

## §6 — Batch aggregates (rows / MV — không nằm trong `VideoAnalysis`)

| AGGREGATE / TABLE | F2 | F1 | F5 | F4 | F6 | STU | F7 | BAT | Nguồn field |
|-------------------|----|----|----|----|----|-----|----|-----|-------------|
| `hook_effectiveness` (per niche × hook_type) | bench | bench | — | pattern | leader | anchor | anchor | MV | `hook_type`, views, ER buckets |
| `video_patterns` (structure, mechanism, examples) | bench | bench | — | pattern | feed | anchor | spec | MV | `content_format`, `content_direction`, corpus peers |
| `niche_intelligence` / `niche_meta` percentiles | bench | bench | — | score | feed | — | — | MV | views, ER, hooks, formats — §4.8.4 |
| `content_class_intelligence` (junction aggregate) | — | bench | — | score | feed | — | — | MV | F6 browse class-first gate (`sample_size` sum ≥20); thin-claim banner; diagnosis `benchmark_axis` |
| `daily_ritual` (3 videos + script prefill) | — | — | — | — | — | show | anchor | MV | Top corpus + `subject_matter` |
| `scene_intelligence` (per niche scene bars) | — | teaser | — | — | — | — | spec | MV | `scenes[]` enrichment nightly |
| `creator_velocity` | — | — | show | score | — | — | — | MV | ED rollup by handle |
| `trending_sounds` | teaser | audit | — | — | feed | — | spec | MV | `sound_id`, lifecycle |
| `claim_tiers` (reference_pool, niche_norms, …) | gate | gate | gate | gate | gate | gate | gate | gate | Sample size gates — §8.3 |
| `channel_diagnoses` (cached memo) | — | — | — | show | — | — | — | — | Output F4, not input |
| `video_shots` (R2 + matcher) | — | teaser | — | — | — | — | spec | MV | `scenes[]` frames |

---

## §7 — Depth split (F2 whitelist vs F1-only)

**Cùng một lần extract** — `analysis_depth` chỉ đổi synthesis, không re-extract ([`feature-map-v1.md`](feature-map-v1.md) §4.0, §4.12).

### F2 synthesize (whitelist §4.2)

| `section_id` | Fields chính đi qua manifest |
|--------------|------------------------------|
| `diagnosis` | triggers, performance, win W0, baseline |
| `compliance` | commerce disclosure, restricted phrase, price anchor |
| `hook_analysis` | `hook_*`, timeline, layering, dialect |
| `niche_pattern` | `hook_type`, `content_format`, refs (`reference_eligible`) |
| `next_video` | format, CTA, win replicable |

### F1-only synthesize (F2 = `teaser` hoặc manifest-only)

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

**Cap manifest vào prompt:** F2 = 3 signals/section · F1 = 5 ([`feature-map-v1.md`](feature-map-v1.md) §4.8.1).

---

## §8 — Orphans, weak fields & actions V1

| Field / nhóm | Verdict | Action V1 |
|--------------|---------|-----------|
| `key_messages[]` | **Orphan** | Trim khỏi prompt/schema sau ablation — **trim-safe** ([`corpus-gemini-utilization-audit.md`](corpus-gemini-utilization-audit.md) §7) |
| `key_timestamps[]` | Weak | Giữ schema compat; không wire UI — defer |
| `energy_level` | Weak | Chỉ `pattern_fingerprint` — OK cho BAT; không cần F2/F1 section |
| `persona_consistency_signals` | **Orphan** | Wire → F4 rollup P2 `channel_persona_drift` **hoặc** defer |
| `hook_analysis.hook_notes` | Weak | Prompt filler — giữ đến khi ablation |
| `content_context.primary_subjects` | Weak | Synthesis only — defer wire |
| `niche_classification` on **peer** rows | Intentional skip | Ref score ignores — document only |
| `douyin_origin` on TikTok corpus | Null at ingest | F1 on-demand; F6 optional block — không orphan product |
| `boost_attribution` section | V1 build | Code P0 — map đã ghi F1/BAT; không trim |

**Không coi orphan (audit recalibration):** `commerce_intent`, `text_overlays[]`, `audio_track_role`, `target_audience`, `pain_points`, `style_tags`.

---

## §9 — Coverage checklist

| Kiểm tra | Target | Kết quả (v1.0 doc) |
|----------|--------|---------------------|
| `VideoAnalysis` + nested hook/commerce fields có ≥1 ô hoặc §8 | 100% | ✅ ~70 rows §1–§4 |
| Promoted + F8 columns có ≥1 ô | 100% | ✅ §5 |
| Batch aggregates có ≥1 feature | 100% | ✅ §6 |
| Mỗi cột F2,F1,F4,F5,F6,STU,F7,BAT có ≥5 field | ≥5 | ✅ (đếm từ bảng) |
| True orphans với action | ≤5 | ✅ 2 (`key_messages`, `persona_consistency_signals`) + weak group |
| §7 depth split documented | Yes | ✅ |
| Link từ vision §8.2 | Yes | ✅ (cross-link commit) |

**Wave 1 gate:** Human sign-off file này **trước** implement §4.7 P0, `analysis_depth` cache, signal backlog ([`feature-map-v1.md`](feature-map-v1.md) §11 phase 0–1).

**Pre-launch (không traffic):** Utilization gate + ingest policy — [`feature-map-v1.md`](feature-map-v1.md) **§8.6–§8.8** (P0 fields §8.7 trỏ về bảng FIELD × feature ở trên).

---

## Methodology (cho maintainer)

1. **As-built:** grep `cloud-run/getviews_pipeline/signals/`, `diagnose_sections.py`, `channel_diagnose.py`, `script_*.py`, `src/hooks/useVideoCorpus.ts`, `ContextStrip.tsx`.
2. **V1 committed:** [`feature-map-v1.md`](feature-map-v1.md) §4.2, §4.7–§4.8, §5.3, §7.
3. **Audit tier:** [`corpus-gemini-utilization-audit.md`](corpus-gemini-utilization-audit.md) §2–§7.

**Carousel:** `CarouselAnalysis` dùng chung taxonomy HI-16 — bảng riêng khi carousel diagnosis ship; V1 video path ưu tiên bảng trên.

---

## Related

| Doc | Role |
|-----|------|
| [`feature-map-v1.md`](feature-map-v1.md) | Product vision + feature IDs |
| [`corpus-gemini-utilization-audit.md`](corpus-gemini-utilization-audit.md) | Tier A–D, trim strategy, **§9 pipeline evaluation** |
| [`system-design.md`](system-design.md) | TD-7 parity, ingest architecture |
| [`product-value-audit.md`](product-value-audit.md) | Value → data gaps |
