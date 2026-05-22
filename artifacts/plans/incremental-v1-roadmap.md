# Incremental V1 Roadmap — GetViews.vn

**Version:** 1.1  
**Date:** 2026-05-22  
**Branch baseline:** `main` (as-built re-verified 2026-05-22)  
**Status:** SSOT for incremental path to V1 vision — **not** a wholesale `feature-map-v1.md` implementation plan  
**Changelog v1.1:** As-built audit — fix ref-pool vs channel-peer gaps, `peer_percentile` wiring, W1-4 done scope, handoff inventory, Compare GTM note, F8 DoD.

**Related docs:**

| Doc | Role |
|-----|------|
| [`feature-map.md`](../docs/feature-map.md) | As-built inventory — update per wave |
| [`feature-map-v1.md`](../docs/feature-map-v1.md) | V1 vision — §4 video, §5.3 channel, §8 F8, §11 build order, §13A/13B |
| [`data-utilization-map-v1.md`](../docs/data-utilization-map-v1.md) | FIELD × feature matrix, orphans, BAT column |
| [`corpus-gemini-utilization-audit.md`](../docs/corpus-gemini-utilization-audit.md) | Tier A–D, trim vs utilize |
| [`system-design.md`](../docs/system-design.md) | §9 content-class pivot, §10 TD-7 |
| [`product-value-audit.md`](../docs/product-value-audit.md) | Value → data gaps |

---

## 1. Executive summary (VI)

**Triết lý:** V1 vision trong `feature-map-v1.md` mô tả **đích** (basic/deep, Win path, `channel_findings`, full F8 gate). Roadmap này **không** ship vision một lần — mà xếp **cải tiến as-built** theo **dễ → khó**, **rủi ro thấp → cao**, luôn bám **F8**: mọi extract phải có đường đi promote → signal/MV → synthesis → UI (hoặc trim-safe đã ghi).

**Khác wholesale feature-map-v1 §11:**

| Wholesale (vision §11) | Incremental (roadmap này) |
|------------------------|---------------------------|
| Phase 0 gộp migration `analysis_depth` + M1/M2 + billing | Wave 0 **không** schema epic — chỉ billing + doc + cron SLA |
| 1a gộp depth picker + handoff + W0 signals | Wave 1 handoff/dedup/wiring; Wave 3+ mới `analysis_depth` |
| 1c `channel_findings` sớm | Wave 4 sau video utilization P0 |
| F6 reshape | **Không** — chỉ handoff query + nav/scope clarity (Home vs Trends rails) |

**North star mỗi wave:** tăng **tỷ lệ field extract → user thấy** trên Video diagnosis và Channel diagnosis, không thêm orphan; TD-7 parity giữ live/batch.

---

## 2. F8 Contract (non-negotiable)

Mọi item trong Wave 0–N phải pass checklist sau. Tham chiếu: [`data-utilization-map-v1.md`](../docs/data-utilization-map-v1.md), [`feature-map-v1.md`](../docs/feature-map-v1.md) §8, [`system-design.md`](../docs/system-design.md) §10 **TD-7**.

### 2.1 Pipeline (extract → UI)

```text
EnsembleData + Gemini 1× extract (VideoAnalysis / CarouselAnalysis)
  → L1 analysis_json (full blob) + L2 promoted cols (~25)
  → L3 derived (format regex, breakout, pattern_id)
  → nightly BAT: MV refresh, hook_effectiveness, M1/M2, scene_intelligence, …
  → on-demand: build_signal_manifest → select_sections → synthesize → FE sections
```

**Rules:**

1. **No new extract field** without a row in `data-utilization-map-v1.md` (≥1 of F2/F1/F4/F5/F6/STU/F7/BAT).
2. **Live + batch same contract** — same `prompts.py` / `models.py`; parity audit before merge (TD-7).
3. **Promote before UI-only:** field chỉ hiện UI sau khi có cột hoặc signal path (tránh đọc thẳng JSON ad hoc ngoài diagnosis).
4. **Synthesis must consume manifest:** Video — `build_signal_manifest` + `manifest_for_prompt`; Channel — target `channel_findings[]` inject (V1 build), không chỉ memo free-form.
5. **Claim humility:** `claim_tiers.py` + `artifacts/sql/corpus-health.sql` — không marketing số corpus giả.
6. **Trim-safe only:** `key_messages[]` — orphan documented; ablation trước trim ([`corpus-gemini-utilization-audit.md`](../docs/corpus-gemini-utilization-audit.md) §7–8). **Không** trim `commerce_intent`, `text_overlays`, `audio_track_role` without replacement.

### 2.2 Per-feature minimum (F8 BAT column)

| Feature | Must read from extract/corpus |
|---------|------------------------------|
| **F2 Video Cơ bản** | Manifest full; synthesize §4.2 whitelist; Win signals when `performance_tier=hit` |
| **F1 Video Chuyên sâu** | + §4.7 `boost_attribution`, cap 5 signals/section, full section pool |
| **F4 Channel Sâu** | ED posts + `video_corpus` by handle + `channel_findings` P0 (build) + peers `reference_eligible` |
| **F6 Xu hướng** | `video_patterns`, promoted cols, class MVs |
| **STU** | `daily_ritual`, `content_class_intelligence`, within-niche breakouts |
| **F8 BAT** | M1/M2 columns, cron SLA, hero niche depth §8.7 |

### 2.3 Pivot awareness (2026-05-21+)

- Cohort canonical: `(content_class_id, creator_tier)` — [`system-design.md`](../docs/system-design.md) §9.
- Taxonomy prod **16×82**; `data-utilization-map-v1.md` vẫn **2026-05-20 pre-implement** — nhiều hàng F6 bridge `niche_intelligence`, chưa có class MV rows → **resync W1-5** (không block Wave 0).
- Class MVs canonical; legacy `niche_intelligence` = bridge only.

### 2.4 F8 Definition of Done (mỗi wave item)

Khi item wire extract → user value, PR phải có:

1. **Path:** signal id (video) hoặc `finding.id` (channel) hoặc promoted col → MV/cron.
2. **Synthesis:** slot trong `manifest_for_prompt` / section gate / `<<<CHANNEL FINDINGS>>>`.
3. **Surface:** FE component hoặc claim-tier humility khi corpus mỏng.
4. **Doc:** hàng tương ứng trong `data-utilization-map-v1.md` cập nhật cùng wave commit.

---

## 3. As-built gaps (verified)

| Gap | As-built evidence | Incremental wave |
|-----|-------------------|------------------|
| Channel credit FE≠BE | `ChannelScreen.tsx` `CREDIT_COST=3`; `channel_diagnose.py` **1×** `decrement_credit` | **Wave 0** |
| Trends→Answer handoff | Navigate sites dùng `state.prefillUrl`; `AnswerScreen` chỉ đọc `q`/`session` — **không** parse `depth`/`mode`/`from` | **Wave 1** |
| No `analysis_depth` | No FE/BE param; cache `.eq("video_id")` only | **Wave 3+** |
| Home vs Trends breakout scope | ✅ Tier III copy fixed (`da76f96`). Còn: `BreakoutGrid` (`useTopBreakouts`) vs `TrendsRail` (`useTrendsRailVideos`) vs `CrossNicheBreakoutLane` — 3 surface khác hook, dễ nhầm | **Wave 1–2** |
| Answer follow-up turn 2+ | `FollowUpComposer` in `AnswerScreen.tsx` | **Gate** — Wave 5 or post-V1 |
| `channel_findings[]` P0 | Channel = memo SSE, no manifest | **Wave 4** |
| `peer_percentile` FE-only | `enrich_niche_meta_with_peer_tier()` **defined, never called**; BE không set `peer_percentile_label`; FE `FlopDiagnosisStrip` forward-compatible | **Wave 1** |
| Ref pool `reference_eligible` | ✅ Batch ingest + `fetch_corpus_reference_pool` filter (`corpus_context.py`) | **Done** — verify only |
| Channel peer ads-skew | `_run_peer_corpus_query` **không** `.eq("reference_eligible", True)` | **Wave 4** |
| Utilization map stale | Pre-implement 2026-05-20; chưa sync class MV / pivot rows | **Wave 0** doc note + **Wave 1** resync |

### 3.1 Handoff inventory (vision §4.10)

| Entry surface | Target (V1) | As-built | Wave |
|---------------|-------------|----------|------|
| Kho video / Explore card | `/app/answer?q={url}&depth=basic&mode=win&from=trends` | `navigate(..., { prefillUrl })` | W1-1 |
| `TrendsRail` row click | same + `from=trends` | `prefillUrl` only | W1-1 |
| `PatternModal` / evidence tile | `?q=` + inherit depth/mode | `prefillUrl` | W1-2 |
| `GenericEvidenceGrid` | same | `prefillUrl` | W1-2 |
| `SceneIntelligencePanel` | same | `prefillUrl` | W1-2 |
| `IdeaBlock` | same | `prefillUrl` (raw aweme_id) | W1-2 |
| Home composer / Studio | pill + depth picker (post-W3) | free-text `?q=` only | W3 |
| Compare single-side fallback | `/app/answer` + `prefillUrl` | ✅ as-built | — |

**Note:** `mode=win` today chỉ qua query heuristics trong `report_video.py` — chưa URL contract cho Answer.

---

## 4. Waves 0–5 (ease / risk ordered)

### Wave 0 — Trust, docs, cron SLA (no schema epic)

| Item | Effort | Risk | F8 utilization impact | Video diag | Channel diag | Acceptance criteria | Files touched |
|------|--------|------|----------------------|------------|--------------|---------------------|---------------|
| **W0-1** Align channel billing FE↔BE (3× both or 1× both per §10 sign-off) | S | Low | Trust — không block utilization | — | Billing honest | User charged = UI label; RPC count matches product | `ChannelScreen.tsx`, `channel_diagnose.py`, `routers/video.py`, `feature-map.md` |
| **W0-2** Doc hygiene: note utilization map pre-implement; link pivot §9 | S | Low | Maintainer gate | — | — | Roadmap + `data-utilization-map-v1.md` header warns stale; `feature-map.md` cross-link | `artifacts/docs/*.md` |
| **W0-3** Cron SLA checklist + `corpus-health` admin pass | S | Low | F8 BAT visibility | — | — | Nightly jobs in `pg_cron` return 2xx; admin panel shows hero niche tiers | `artifacts/sql/corpus-health.sql`, `admin.py`, runbook in ACTIVE_CONTEXT |
| **W0-4** TD-7 spot audit (live vs batch prompt hash / test) | S | Low | Parity invariant | Both | Both | Existing `test_*` parity green; no drift in `prompts.py` extract block | `cloud-run/tests/`, `corpus_ingest.py`, `extraction.py` |
| **W0-5a** Ref pool `reference_eligible` — **verify done** (ingest + `corpus_context.py`) | S | Low | F8 P0 video refs | Ref tiles organic | — | `fetch_corpus_reference_pool` skips `suspect_medium` when ≥5 refs; pytest green | `corpus_context.py`, `corpus_ingest.py` |
| **W0-5b** M1 `boost_attribution` columns — verify ingest + promoted cols live | S | Low | F8 BAT | Batch refs | Corpus rollup | Cols populated on nightly ingest sample | migrations, `corpus_boost_suspect.py` |

**Wave 0 exit:** billing aligned; corpus-health runnable; ref pool verified; **no** migration `analysis_depth`.

---

### Wave 1 — Handoffs, dedup UX, small wiring

| Item | Effort | Risk | F8 utilization impact | Video diag | Channel diag | Acceptance criteria | Files touched |
|------|--------|------|----------------------|------------|--------------|---------------------|---------------|
| **W1-1** Trends Explore + TrendsRail → Answer query params `depth=basic&mode=win&from=trends` | S | Low | F2 Win path entry | Corpus-hit basic demo | — | 1 tap lands Answer with params; `AnswerScreen` parses `depth`/`mode`/`from` and passes BE | `ExploreScreen.tsx`, `AnswerScreen.tsx`, `TrendsRail.tsx`, `intent-router.ts` |
| **W1-2** Align §3.1 handoff sites (PatternModal, evidence, SceneIntel, IdeaBlock) | S | Low | Consistent depth inherit | Handoff | — | All 6 navigate sites in §3.1 documented in `feature-map.md` | `PatternModal.tsx`, `GenericEvidenceGrid.tsx`, `SceneIntelligencePanel.tsx`, `IdeaBlock.tsx` |
| **W1-3** `peer_percentile` pipeline: call `enrich_niche_meta_with_peer_tier` + format `peer_percentile_label` | M | Med | F8 S1 — class×tier MV in diagnosis | FlopDiagnosisStrip shows percentile | — | Payload has numeric + label; empty → existing humility copy | `video_analyze.py`, `video_niche_benchmark.py`, `report_types.py`, `FlopDiagnosisStrip.tsx` |
| **W1-4** Home vs Trends **scope/nav** (copy ✅ `da76f96`): clarify 3 surfaces | S | Low | STU/F6 dedup UX | — | — | Tier III → within-niche; TrendsRail → 7d/viral rails; CrossNiche → cross-class; CTAs distinct | `HomeSuggestionsToday.tsx`, `TrendsRail.tsx`, `CrossNicheBreakoutLane.tsx` |
| **W1-5** Resync `data-utilization-map-v1.md` — 16×82, class MV rows, pivot §9 | M | Low | F8 gate accurate | Matrix | Matrix | Orphan count ≤5; BAT column matches cron; no false “16×82 synced” claim | `data-utilization-map-v1.md` |
| **W1-6** Win path W0 — **P0 subset (2)** of vision §4.8.3: `win_er_above_niche_p75`, `win_hook_aligns_niche_top` | M | Med | F2 utilizes extract on hit tier | §4.8 W0 | — | New `signals/win.py`; `tier_gate=hit`; unit tests; fire-rate logged | `signals/win.py`, `signals/registry.py`, tests |

**Wave 1 exit:** §3.1 handoffs spec-compliant; utilization map resynced; W0 P0 win signals tested; peer tier visible in UI.

---

### Wave 2 — Studio entry & trends integration

| Item | Effort | Risk | F8 utilization impact | Video diag | Channel diag | Acceptance criteria | Files touched |
|------|--------|------|----------------------|------------|--------------|---------------------|---------------|
| **W2-1** Studio tier I ritual → Script Studio ≤2 tap | M | Low | F7 anchor fields | — | — | Verify as-built `goWinScript` / ritual CTA; prefills hook/scenes | `HomeSuggestionsToday.tsx`, `MorningSignalStrip.tsx`, `script/route.tsx` |
| **W2-2** `ConfidenceStrip` consistent on F6 pattern + kho | S | Low | F8 claim tiers | — | — | Thin corpus → humility on all F6 cards | `TrendsPatternGrid.tsx`, `ExploreScreen.tsx`, `claim_tiers.py` |
| **W2-3** Hero niche list doc + `BATCH_PRIORITY_NICHE_IDS` align | S | Low | F8 §8.7 ingest depth | Better refs | Better peers | 5–8 niches documented; batch config matches | `feature-map-v1.md` §8.7, env docs, `corpus_ingest.py` |
| **W2-4** `subject_matter` / proximity ranking promote (audit §8) | M | Med | Ref pool quality | Proximity tiles | — | Proximity picks use promoted field; ablation logged | `video_analyze.py`, `corpus_ingest.py` |

**Wave 2 exit:** Studio→Script golden path; F6 claims tier-aware.

---

### Wave 3 — Depth epic (explicitly later / harder)

| Item | Effort | Risk | F8 utilization impact | Video diag | Channel diag | Acceptance criteria | Files touched |
|------|--------|------|----------------------|------------|--------------|---------------------|---------------|
| **W3-1** Migration `video_diagnostics.analysis_depth` + UNIQUE `(video_id, analysis_depth)` | L | High | F8 cache partition | basic/deep cache | — | §4.12.3 sketch applied; no serve wrong depth | `supabase/migrations/`, `database.types.ts` |
| **W3-2** BE `append_turn` / `build_video_report` accept `analysis_depth` | L | High | F2/F1 split | Section whitelist | — | basic ⊆ deep sections; manifest cap 3 vs 5 | `answer_session.py`, `diagnose_sections.py`, `salience.py` |
| **W3-3** FE composer Cơ bản/Chuyên sâu pills + billing 1×/2× | M | High | Product billing | — | — | **Human gate** §10; RPC matches depth | `AnswerScreen.tsx`, `HomeScreen` composer, `decrement_credit` usage |
| **W3-4** Cache upsert always sets `analysis_depth` | M | Med | No wasted re-extract | Both depths | — | Upgrade basic→deep triggers deep pass | `video_analyze.py` |

**Wave 3 exit:** §13B depth items; still 1-turn Answer unless gate approves follow-up hide.

---

### Wave 4 — Channel findings & video deep utilization

| Item | Effort | Risk | F8 utilization impact | Video diag | Channel diag | Acceptance criteria | Files touched |
|------|--------|------|----------------------|------------|--------------|---------------------|---------------|
| **W4-1** `build_channel_findings()` P0 (4 findings) + prompt inject | L | Med | F4 salience layer | — | Memo uses findings | `<<<CHANNEL FINDINGS>>>` when ≥1; no FYP% claims | `channel_diagnose.py`, new `channel_findings.py` |
| **W4-2** §4.7 M3 live `boost_attribution` on user video (ingest-only today) | M | Med | F1 deep only | Section emits | — | Heuristic in new module (e.g. `signals/distribution.py`); “có dấu hiệu” copy; **no** `signals/boost.py` yet | `signals/distribution.py`, `diagnose_sections.py` |
| **W4-3** §4.8 P0 signal backlog + remaining W0 win signals (3) | L | Med | Manifest density | More sections | — | Fire-rate logged; tests per signal id | `signals/win.py`, `signals/*.py`, tests |
| **W4-4** Channel peer sort `.eq("reference_eligible", True)` on corpus queries | M | Med | F8 M2 on channel | — | Peers not ads-skew | `_run_peer_corpus_query` + fallback chain filter §4.7.5 | `channel_diagnose.py` |

**Wave 4 exit:** §5.3 C1 + §4.7 P1 partial; channel memo evidence-backed.

---

### Wave 5 — Polish & gated cuts

| Item | Effort | Risk | F8 utilization impact | Video diag | Channel diag | Acceptance criteria | Files touched |
|------|--------|------|----------------------|------------|--------------|---------------------|---------------|
| **W5-1** Hide Answer follow-up (turn 2+) — **human gate** | M | Med | Focus F2/F1 single turn | No TimelineRail follow-up | — | V1 §4.10.1; history still works | `AnswerScreen.tsx`, `FollowUpComposer.tsx` |
| **W5-2** `key_messages` trim post-ablation | S | Low | Cost ~1–3% | — | — | Diff v6 on sample; map §8 updated | `models.py`, `prompts.py` |
| **W5-3** F5 channel quick peek on Trends card | M | Med | 1–2 P0 findings | — | Teaser | Card shows ceiling OR format entropy | Trends channel card FE + API |
| **W5-4** GTM copy + launch gate §13B sweep | M | Low | — | — | — | All §13B checkboxes evidence-linked | docs + QA baselines |

---

## 5. Video diagnosis utilization backlog

Map: extract field → signal (`signals/registry.py`) → `section_id` → UI (`VideoBody`, `DiagnosisSectionRenderer`).

### 5.1 Wired (as-built — maintain)

| Extract / promote | Signal / path | Section | UI |
|-------------------|---------------|---------|-----|
| `hook_*`, `hook_phrase` | `hook_*` | `hook_analysis`, `diagnosis` | Hook blocks, ContextStrip |
| `commerce_intent.*` | `commerce_*` | `commerce` | Commerce section |
| `tone`, `target_audience`, `pain_points` | persona/distribution | various | `ContextStrip` |
| `scenes[]` | editing, script | `editing`, F7 | Scene intel panel |
| `performance_tier` + corpus stats | performance signals | `diagnosis` | FlopDiagnosisStrip, tier badges |
| `reference_videos` + proximity | `niche_reference_anchor` | `niche_pattern` | Embedded tiles |
| `douyin_*` (on-demand) | `douyin_origin_*` | `douyin_origin` | Section when flag on |
| Batch `boost_attribution` + `reference_eligible` | ingest + ref pool filter | BAT / refs | Corpus refs only — **not** live M3 |

### 5.2 Missing / weak (incremental priority)

| Extract | Target signal/section | Wave | Notes |
|---------|----------------------|------|-------|
| `peer_percentile` + class×tier MV | `enrich_niche_meta_with_peer_tier` → label | **W1** | Function exists; **never called**; FE reads `peer_percentile_label` only |
| Win signals W0 (vision lists 5) | `win_er_*`, `win_hook_*` P0 in W1; rest W4 | W1/W4 | No `win_*` in `signals/` today |
| `boost_attribution` live M3 | `boost_*`, `distribution_*` | W4 | Batch col ✅; on-demand heuristic **not built** |
| `stats_history` M4 | `distribution_spike_then_flat` | W4+ | Cron re-fetch T+6h/24h |
| `hook_analysis.hook_timeline[]` | pacing signals (P1) | W4 | Vision §4.8 backlog |
| `transitions_per_second` | `editing_cut_pace_*` | W4 | F6 feed + F1 audit |
| `persona_consistency_signals` | channel rollup OR defer | W4–5 | Orphan §8 — wire F4 P2 or defer |
| `key_messages[]` | — | W5 | **Trim-safe** — not wire |
| `analysis_depth` param | cap 3 vs 5 manifest | W3 | Product knob |

### 5.3 F2 vs F1 depth split (post-W3)

| Section | F2 basic | F1 deep |
|---------|----------|---------|
| `diagnosis`, `hook_analysis`, `niche_pattern`, `next_video` | synthesize | synthesize |
| `distribution`, `commerce`, `sound`, `persona`, `editing`, `metadata` | teaser/manifest | synthesize |
| `boost_attribution` | teaser only | synthesize when M3 fires |

### 5.4 Carousel path (deferred detail)

`CarouselAnalysis` shares HI-16 taxonomy — separate utilization rows when carousel diagnosis ships. Incremental W1–4 focus **video file** path; carousel save-rate hint in `FlopDiagnosisStrip` is forward-compatible only.

---

## 6. Channel diagnosis utilization backlog

As-built: **memo SSE** — `classify_trajectory`, `compute_score_card`, `build_channel_pattern`; **no** `build_signal_manifest`. Vision: `channel_findings[]` → `<<<CHANNEL FINDINGS>>>`.

### 6.1 Wired

| Data source | Output block | UI |
|-------------|--------------|-----|
| ED `fetch_user_posts` | trajectory, score_card | `ScoreCard`, trajectory badges |
| Corpus by handle | `channel_pattern`, competitive_landscape | Pattern section, peers |
| `niche_channel_benchmarks` | percentiles in score card | KPI grid |
| Gemini memo | `verdict`, `what_falling`, `what_worked`, `recommendations` | `SectionRenderer` |

### 6.2 Missing (§5.3 P0–P2)

| Finding id | V5 | Data | Wave |
|------------|-----|------|------|
| `channel_view_ceiling_300` | §2.1 proxy | views≤300 + ER | W4 |
| `channel_format_entropy_high` | §2.2 | format distribution | W4 |
| `channel_recent_vs_peak_er_drop` | §2.2 | recent vs peak windows | W4 |
| `channel_peer_format_saturation` | §2.3 | top 20 corpus 7d | W4 |
| `channel_compliance_aggregate` | §2.4 | roll-up video compliance signals | W4+ |
| `channel_boost_outlier_share` | §1.8 | `% suspect_medium` on handle | W4 |
| `channel_slang_staleness` | §2.5 | aggregate `persona_slang_dated` | W5 |

### 6.3 Credit & F8

- **Wave 0:** fix 3 vs 1 mismatch before scaling channel usage.
- **Wave 4:** channel peers must filter `reference_eligible` — `_run_peer_corpus_query` today does **not**; video ref pool already does (W0-5a).
- Channel memo must not cite ads-skew corpus rows as “viral mẫu” until W4-4 lands.

---

## 7. Decision gates (human approval)

| Gate | Decision | Blocks | Default recommendation |
|------|----------|--------|------------------------|
| **G1** Composer pills Cơ bản/Chuyên sâu | Ship in Wave 3? | W3-3 | Yes — vision §3.1.2; after W1 handoff |
| **G2** Hide follow-up turn 2+ | V1 or post-V1? | W5-1 | **Defer** until depth stable — Completeness 7/10 |
| **G3** Hero niche list (5–8 IDs) | Which niches get deep ingest | W2-3, §8.7 | Human picks from `creator_niches` with thin corpus report |
| **G4** Channel billing | 3× vs 1× | W0-1 | **3×** both sides per vision §10 — Completeness 10/10 |
| **G5** Depth billing | 1× basic / 2× deep | W3-3 | Sign-off before migration |
| **G6** `key_messages` trim | Post-ablation only | W5-2 | Wait for fire-rate metrics |

Format per project AskUserQuestion: Tech Lead presents options A/B/C with Completeness scores before Wave 3+ execution.

---

## 8. Doc maintenance checklist (per wave)

- [ ] Update [`feature-map.md`](../docs/feature-map.md) as-built rows for touched routes/endpoints
- [ ] Append [`changelog.md`](../docs/changelog.md) in same commit as code
- [ ] If FIELD wired: update [`data-utilization-map-v1.md`](../docs/data-utilization-map-v1.md) row + remove from §8 orphans
- [ ] If architectural: update [`system-design.md`](../docs/system-design.md) §9/§10
- [ ] QA baseline: `artifacts/qa-reports/<wave-id>-baseline.json`
- [ ] Do **not** edit canonical `feature-map-v1.md` without human amendment approval

---

## 9. Metrics & verification

| Metric | How | Target |
|--------|-----|--------|
| Signal fire-rate | Log per `signal.id` in `build_signal_manifest` | Ablation before trim; P0 signals >0% on flop+win sample |
| Claim tier humility | `corpus-health.sql` per hero niche | `reference_pool` ≥5 videos/30d before ref claims |
| Cron SLA | `pg_cron.job_run_details` + admin 4xx rule | Batch HTTP 2xx; class MV refresh after ingest |
| Utilization coverage | Count matrix rows with ≥1 non-`—` cell | 100% VideoAnalysis fields or §8 action |
| Channel finding quality | Manual memo review | P0 findings include counts; no “FYP=0%” |
| Depth cache correctness | Integration test | basic row ≠ deep payload when both exist |
| TD-7 parity | `pytest` extract contract | live SSE extract == batch ingest JSON schema |

**Scripts:** `artifacts/sql/corpus-health.sql`, GET `/admin/corpus-health`, `npm run test`, `cd cloud-run && pytest`.

---

## 10. NOT in incremental V1 (post-V1 / out of scope)

| Item | Why deferred |
|------|----------------|
| F3 Compare GTM / polish | Route **shipped** (`/app/compare`, `report_compare.py`) — hidden from V1 GTM per `feature-map.md`; no incremental polish unless product promotes |
| F6 full UX reshape / route rename `/app/xu-huong` | Handoff only in incremental path |
| Text chat intents ⑤⑥⑦ from composer | Post-V1 |
| `analysis_depth` in Wave 0–2 | Explicitly Wave 3+ |
| Douyin forecast product | Vision Wave 2+ — not incremental W2 scope |
| TikTok OAuth / Ads API boost proof | Out of scope |
| Admin dashboard beyond existing panels | Use Supabase + `/admin/*` |
| HI-13 batch API cutover | Optional cost — separate plan |
| English UI, native apps, subscriptions | Project rules |
| Wholesale rewrite to match every `feature-map-v1` § in one release | **This roadmap rejects** |

---

## 11. Mapping to vision §11 (reference only)

| Vision phase | Incremental waves |
|--------------|-------------------|
| Phase 0 (F8+billing+migration) | W0 + W1 (minus migration) |
| Phase 1a F2 Win | W1 |
| Phase 1b depth parity | W3 |
| Phase 1c F4 findings | W4 |
| Phase 2 F6 handoff | W1–2 |
| Phase 3 F7 | W2 |
| Phase 4 polish | W5 |

---

## 12. Launch gate alignment (§13B subset)

Incremental V1 **launch-ready** when:

- W0–W2 complete + **either** W3 depth **or** explicit human waiver deferring depth to post-launch mini-release
- W4 channel_findings P0 **or** waiver with documented risk: channel memo remains free-form → **F8 gap** on aggregate `analysis_json` / compliance roll-ups until C1 ships
- §13B items traced to wave IDs in QA report
- F8: no undocumented orphans; `key_messages` trim only after G6
- §13A `peer_percentile` — treat as **W1-3 complete**, not “shipped” until BE calls enrich + label

---

## 13. Top quick wins (post-audit priority)

1. **W0-1** — Channel credit FE=3 / BE=1 alignment.
2. **W1-3** — Wire `enrich_niche_meta_with_peer_tier` + `peer_percentile_label` (highest F8 Video impact on current path).
3. **W1-1** — Trends handoff query params + `AnswerScreen` parser.
4. **W0-3** — Cron SLA + `corpus-health` checklist.
5. **W1-4** — Scope/nav clarity across Home breakout vs Trends rails vs cross-niche lane (copy already done).

---

*Maintainer: Tech Lead. Next review after Wave 1 merge or taxonomy change.*
