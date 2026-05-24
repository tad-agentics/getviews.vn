# Incremental V1 Roadmap — GetViews.vn

**Version:** 1.1  
**Date:** 2026-05-22  
**Branch baseline:** `main` @ `680c803` (Wave 5 ship; Wave 4 @ `9b97207`; Wave 3 @ `9cd0957`)  
**Status:** SSOT for incremental path to V1 vision — **not** a wholesale `feature-map-v1.md` implementation plan  
**Changelog v1.1:** As-built audit — fix ref-pool vs channel-peer gaps, `peer_percentile` wiring, W1-4 done scope, handoff inventory, Compare GTM note, F8 DoD.  
**Wave 0 (2026-05-22):** ✅ Complete — see §4 Wave 0 status.  
**Wave 1 (2026-05-22):** ✅ Complete — `feat(wave1): handoffs + peer_percentile + win signals` @ `e3b5d01`.  
**Wave 3 (2026-05-22):** ✅ Complete @ `9cd0957` + W3-5 upsell UI (§4.11.3).  
**Wave 4 (2026-05-23):** ✅ Complete @ `9b97207` — channel findings + deep utilization.  
**Wave 5 (2026-05-23):** ✅ Complete @ `680c803` — intent CTA rail, format parity, key_messages trim, Trends channel peek, §13B sweep.

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
- Taxonomy prod **16×82**; `data-utilization-map-v1.md` **v1.1 resynced 2026-05-22** (`8ad7ab0` baseline) — class MV rows, pivot §9, as-built `🔨` markers for vision-only fields.
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
| Channel credit FE≠BE | ✅ W0-1 — `CHANNEL_DIAGNOSE_CREDIT_COST=3`; FE/BE aligned @ `8ad7ab0` | — |
| Trends→Answer handoff | ✅ W1-1/W1-2 — `answerHandoff.ts`; query `depth`/`mode`/`from` → `video_mode` on `/answer/turns` @ `e3b5d01` | — |
| No `analysis_depth` | ✅ W3 — whitelist + cache `(video_id, analysis_depth)` + billing 1×/2× @ `9cd0957` | — |
| Home vs Trends breakout scope | ✅ W1-4 copy — Tier III vs TrendsRail 7d/viral vs CrossNiche; nav dedup UX residual → W2 if needed | **Wave 2** (optional) |
| Answer follow-up turn 2+ | ✅ W5-1 @ `f3054f5` — `IntentCtaRail` + `intentCtaSuggestions.ts`; ẩn `FollowUpComposer` free text; deep upgrade CTA in rail (not sticky body) | — |
| `channel_findings[]` P0 | ✅ W4-1 — `channel_findings.py` + `<<<CHANNEL FINDINGS>>>` @ `9b97207` | — |
| `peer_percentile` | ✅ W1-3 — `finalize_niche_meta_peer_tier` + label when `content_class_tier` axis @ `e3b5d01` | — |
| Ref pool `reference_eligible` | ✅ Batch ingest + `fetch_corpus_reference_pool` filter (`corpus_context.py`) | **Done** — verify only |
| Channel peer ads-skew | ✅ W4-4 — `_run_peer_corpus_query(..., reference_eligible_only=True)` + fallback @ `9b97207` | — |
| Utilization map stale | ✅ W1-5 — v1.1 resync @ `88a86e5`; orphans + BAT column as-built | — |

### 3.1 Handoff inventory (vision §4.10)

| Entry surface | Target (V1) | As-built @ `e3b5d01` | Wave |
|---------------|-------------|----------------------|------|
| Kho video / Explore card | `/app/answer?q={url}&depth=basic&mode=win&from=trends` | ✅ query URL via `answerHandoff` / inline equivalent | ✅ W1-1 |
| `TrendsRail` row click | same + `from=trends` | ✅ `trendsVideoHandoffPath` | ✅ W1-1 |
| `PatternModal` / evidence tile | `?q=` + inherit depth/mode | ✅ `from=pattern`; evidence tiles inherit via `inheritHandoffFromSearch` | ✅ W1-2 |
| `GenericEvidenceGrid` | same | ✅ `inheritHandoffFromSearch` (`from=evidence`) | ✅ W1-2 |
| `SceneIntelligencePanel` | same | ✅ `inheritHandoffFromSearch` (`from=script`) | ✅ W1-2 |
| `IdeaBlock` | same | ✅ `from=ideas` (raw aweme_id) | ✅ W1-2 |
| Home composer / Studio | pill + depth picker (post-W3) | ✅ Cơ bản/Chuyên sâu pills + `?depth=` @ W3 | ✅ W3 |
| Compare single-side fallback | `/app/answer` + `prefillUrl` | ✅ state `prefillUrl` → query migrate (legacy) | — |

**Note:** ✅ W1-1 — `mode=win` via `?mode=` → `video_mode` on `/answer/turns` → `build_video_report(mode=…)`. `analysis_depth` logged only until Wave 3.

---

## 4. Waves 0–5 (ease / risk ordered)

### Wave 0 — Trust, docs, cron SLA (no schema epic) ✅ *Shipped 2026-05-22*

| Item | Status | Notes |
|------|--------|-------|
| W0-1 Channel billing 3× | ✅ | `CHANNEL_DIAGNOSE_CREDIT_COST=3`; pre-check ≥3 before RPC; FE comment sync |
| W0-2 Doc hygiene | ✅ | utilization map header + feature-map cross-links |
| W0-3 Cron SLA checklist | ✅ | [`wave0-cron-sla-checklist.md`](../docs/wave0-cron-sla-checklist.md) |
| W0-4 TD-7 pytest gate | ✅ | `test_hi9_extraction_models`, `test_corpus_boost_w0`, channel credit + endpoint tests; `test_cohort_assignment_parity` stale (settings monkeypatch — pre-existing) |
| W0-5a Ref pool verify | ✅ | `test_corpus_boost_w0.py` + existing instructiveness tests |
| W0-5b M1 columns verify | ✅ | migrations `20260520000000`, `20260730000000`; boost classify tests |

<details>
<summary>Wave 0 task table (reference)</summary>

| Item | Effort | Risk | F8 utilization impact | Video diag | Channel diag | Acceptance criteria | Files touched |
|------|--------|------|----------------------|------------|--------------|---------------------|---------------|
| **W0-1** Align channel billing FE↔BE (3× both or 1× both per §10 sign-off) | S | Low | Trust — không block utilization | — | Billing honest | User charged = UI label; RPC count matches product | `ChannelScreen.tsx`, `channel_diagnose.py`, `routers/video.py`, `feature-map.md` |
| **W0-2** Doc hygiene: note utilization map pre-implement; link pivot §9 | S | Low | Maintainer gate | — | — | Roadmap + `data-utilization-map-v1.md` header warns stale; `feature-map.md` cross-link | `artifacts/docs/*.md` |
| **W0-3** Cron SLA checklist + `corpus-health` admin pass | S | Low | F8 BAT visibility | — | — | Nightly jobs in `pg_cron` return 2xx; admin panel shows hero niche tiers | `artifacts/sql/corpus-health.sql`, `admin.py`, runbook in ACTIVE_CONTEXT |
| **W0-4** TD-7 spot audit (live vs batch prompt hash / test) | S | Low | Parity invariant | Both | Both | Existing `test_*` parity green; no drift in `prompts.py` extract block | `cloud-run/tests/`, `corpus_ingest.py`, `extraction.py` |
| **W0-5a** Ref pool `reference_eligible` — **verify done** (ingest + `corpus_context.py`) | S | Low | F8 P0 video refs | Ref tiles organic | — | `fetch_corpus_reference_pool` skips `suspect_medium` when ≥5 refs; pytest green | `corpus_context.py`, `corpus_ingest.py` |
| **W0-5b** M1 `boost_attribution` columns — verify ingest + promoted cols live | S | Low | F8 BAT | Batch refs | Corpus rollup | Cols populated on nightly ingest sample | migrations, `corpus_boost_suspect.py` |

**Wave 0 exit:** billing aligned; corpus-health runnable; ref pool verified; **no** migration `analysis_depth`.

</details>

---

### Wave 1 — Handoffs, dedup UX, small wiring ✅ *Shipped 2026-05-22 @ `e3b5d01`*

| Item | Status | Notes |
|------|--------|-------|
| W1-1 Trends → Answer query params | ✅ | `answerHandoff.ts`; BE `video_mode` on `/answer/turns` |
| W1-2 §3.1 handoff sites | ✅ | PatternModal, evidence, SceneIntel, IdeaBlock + `feature-map.md` |
| W1-3 peer_percentile pipeline | ✅ | `finalize_niche_meta_peer_tier` + label; `creator_tier` on tier MV |
| W1-4 Home vs Trends dedup copy | ✅ | Tier III / TrendsRail / CrossNiche CTAs |
| W1-5 Utilization map resync | ✅ | `data-utilization-map-v1.md` v1.1 @ `88a86e5` |
| W1-6 Win W0 signals (2) | ✅ | `signals/win.py`; `test_signals_win.py` |

<details>
<summary>Wave 1 task table (reference)</summary>

| Item | Effort | Risk | F8 utilization impact | Video diag | Channel diag | Acceptance criteria | Files touched |
|------|--------|------|----------------------|------------|--------------|---------------------|---------------|
| **W1-1** Trends Explore + TrendsRail → Answer query params `depth=basic&mode=win&from=trends` | S | Low | F2 Win path entry | Corpus-hit basic demo | — | 1 tap lands Answer with params; `AnswerScreen` parses `depth`/`mode`/`from` and passes BE | `ExploreScreen.tsx`, `AnswerScreen.tsx`, `TrendsRail.tsx`, `intent-router.ts` |
| **W1-2** Align §3.1 handoff sites (PatternModal, evidence, SceneIntel, IdeaBlock) | S | Low | Consistent depth inherit | Handoff | — | All 6 navigate sites in §3.1 documented in `feature-map.md` | `PatternModal.tsx`, `GenericEvidenceGrid.tsx`, `SceneIntelligencePanel.tsx`, `IdeaBlock.tsx` |
| **W1-3** `peer_percentile` pipeline: call `enrich_niche_meta_with_peer_tier` + format `peer_percentile_label` | M | Med | F8 S1 — class×tier MV in diagnosis | FlopDiagnosisStrip shows percentile | — | Payload has numeric + label; empty → existing humility copy | `video_analyze.py`, `video_niche_benchmark.py`, `report_types.py`, `FlopDiagnosisStrip.tsx` |
| **W1-4** Home vs Trends **scope/nav** (copy ✅ `da76f96`): clarify 3 surfaces | S | Low | STU/F6 dedup UX | — | — | Tier III → within-niche; TrendsRail → 7d/viral rails; CrossNiche → cross-class; CTAs distinct | `HomeSuggestionsToday.tsx`, `TrendsRail.tsx`, `CrossNicheBreakoutLane.tsx` |
| **W1-5** Resync `data-utilization-map-v1.md` — 16×82, class MV rows, pivot §9 | M | Low | F8 gate accurate | Matrix | Matrix | Orphan count ≤5; BAT column matches cron; as-built `🔨` markers | `data-utilization-map-v1.md` |
| **W1-6** Win path W0 — **P0 subset (2)** of vision §4.8.3: `win_er_above_niche_p75`, `win_hook_aligns_niche_top` | M | Med | F2 utilizes extract on hit tier | §4.8 W0 | — | New `signals/win.py`; `tier_gate=hit`; unit tests; fire-rate logged | `signals/win.py`, `signals/registry.py`, tests |

**Wave 1 exit:** ✅ §3.1 handoffs spec-compliant; utilization map resynced; W0 P0 win signals tested; peer tier label on tier-MV path. **`analysis_depth` enforcement deferred Wave 3.**

</details>

---

### Wave 2 — Script → Answer (narrative-first) + F6/data plane

**Product decisions (2026-05-22 — human sign-off):**

| # | Decision | Choice |
|---|----------|--------|
| 1 | Shoot mode | **Migrate vào Answer** — không giữ `/app/script/shoot` route riêng lâu dài |
| 2 | Drafts | **Cả hai:** `answer_turns.payload` = source of truth session; `draft_scripts` + `source_session_id` (đã có FK) cho export/shoot/edit lưu lại |
| 3 | Schema | **Reuse `narrative_vi`** — `_schema_version: "script_v1"`; sections `hook_analysis`, `script_structure`, `next_video`; `shots[]` = structured appendix (không fork type riêng) |
| 4 | Credits | **OK:** primary script turn **3×**; regenerate/edit shot = follow-up turn **1×** (same as other answer follow-ups) |
| 5 | Composer + intent-router | **Giữ nguyên** — entry turn 1: Studio pill · handoff/deeplink **prefill `?q=`** (URL, @handle, script brief) → `planAnswerEntry()` / `detectIntent()` — **không** text tự do trên Studio. Feature mới = thêm row `INTENT_DESTINATIONS` + CTA matrix §4.10.2 |
| 6 | Intent scope | **Giữ toàn bộ intent** trong router — **không** cắt row |
| 7 | Follow-up UX | **CTA intent pill** — không composer chat tự do; mỗi `AnswerSessionFormat` gợi ý 2–4 CTA khác nhau (§4.10.2); `intent_type` explicit trên tap |

**Architecture invariant (Wave 2+):**

```text
Turn 1: User input (Studio pill | handoff prefill ?q=)
  → intent-router.ts (detectIntent → planAnswerEntry)
  → /app/answer?session=…  OR  redirect /app/channel | /app/compare
  → POST /answer/turns (format + intent_type from router)

Turn 2+: Intent CTA pill (explicit intent_type + payload)
  → append_turn same session OR redirect compare/channel
  → NO free-text FollowUpComposer / NO follow_up_unclassifiable from chat
```

- **Composer** (`QueryComposer`) = **entry Studio only** — 4 pill + depth; không follow-up chat slot.
- **IntentCtaRail** = follow-up trong Answer — matrix per format §4.10.2.
- **Giữ toàn bộ** `INTENT_DESTINATIONS` — truy cập qua CTA + entry, không xóa intent.
- Deprecate chỉ `/app/script` **route + editor shell** — không deprecate router.
- Handoffs (`answerHandoff.ts`) chỉ set query params / `?q=` — router vẫn là SSOT cho `format=script` vs `video` vs …

**Sequencing:** W2-1a → W2-1b → W2-1c (route + narrative + shoot/drafts); W2-2–W2-4 song song sau W2-1b.

| Item | Effort | Risk | F8 utilization impact | Video diag | Channel diag | Acceptance criteria | Files touched |
|------|--------|------|----------------------|------------|--------------|---------------------|---------------|
| **W2-1a** Deprecate `/app/script` route — entries prefill Answer composer | M | Low | F7 single surface | — | — | No user-facing `/app/script` (redirect); CTAs → `answerHandoff` / `?q=` prefill; **`planAnswerEntry` unchanged**; deeplink `topic`/`hook`/`duration` → composed `?q=` text, not bypass router | `ScriptScreen.tsx`, `routes.ts`, CTAs, `answerHandoff.ts`, `intent-router.ts` |
| **W2-1b** Narrative-first script report | L | Med | F7 synthesis | — | — | `build_script_report` → `synthesize_script_narrative_vi()`; payload has `narrative_vi` + `shots[]`; `ScriptBody` headline → sections → shot rail (mirror `VideoBody`) | `report_script.py`, `ScriptBody.tsx`, `api-types.ts`, `gemini.py` |
| **W2-1c** Drafts + shoot in Answer shell | M | Med | F7 persist | — | — | Save draft sets `draft_scripts.source_session_id`; shoot panel at `?session=&shoot=` or in-session mode; export via existing `/script/drafts/*/export` | `AnswerScreen.tsx`, `useScriptSave.ts`, migration if index needed |
| **W2-2** `ConfidenceStrip` consistent on F6 pattern + kho | S | Low | F8 claim tiers | — | — | Thin corpus → humility on all F6 cards | `TrendsPatternGrid.tsx`, `ExploreScreen.tsx`, `claim_tiers.py` |
| **W2-3** Hero niche list doc + `BATCH_PRIORITY_NICHE_IDS` align | S | Low | F8 §8.7 ingest depth | Better refs | Better peers | 5–8 niches documented; batch config matches | `feature-map-v1.md` §8.7, env docs, `corpus_ingest.py` |
| **W2-4** `subject_matter` / proximity ranking promote (audit §8) | M | Med | Ref pool quality | Proximity tiles | — | Proximity picks use promoted field; ablation logged | `video_analyze.py`, `corpus_ingest.py` |

<details>
<summary>Wave 2 — superseded W2-1 (reference)</summary>

| Item | Notes |
|------|-------|
| ~~W2-1 ritual → Script ≤2 tap~~ | **Done in practice** — prefill → `/app/answer?q=…`; replaced by W2-1a/b/c epic |

</details>

**Wave 2 exit:** Mọi script flow trong `/app/answer` narrative-first; **composer + intent-router** vẫn là entry SSOT; shoot + draft linked session; F6 claim-tier aware; hero niche batch aligned.

**Wave 2 complete @ `b169673`** (2026-05-22): `cc6384a` narrative-first + `8d4759a` housekeeping + W2-4 batch closure; docs resynced.

| Item | Status | Notes |
|------|--------|-------|
| W2-1a Deprecate `/app/script` route | ✅ | Redirect + `scriptPrefillFromDeeplink`; CTAs → `/app/answer?q=` |
| W2-1b Narrative-first script report | ✅ | `synthesize_script_narrative_vi()`; `ScriptBody` sections → shot rail |
| W2-1c Drafts + shoot in Answer | ✅ | `ScriptActionsBar` + `?shoot=` panel; `source_session_id` on save |
| W2-2 ConfidenceStrip on F6 | ✅ | `TrendsPatternGrid` + Explore kho when corpus thin |
| W2-3 Hero niche list + batch IDs | ✅ | `feature-map-v1.md` §8.7; default `1,2,3,4,5,8,9,11` |
| W2-4 subject_matter proximity | ✅ | Live + batch ref pool; ablation log; batch `subject_matter_inserted` metric |

**Schema contract (W2-1b — Tech Lead default):**

```text
ScriptReportPayload {
  narrative_vi: { headline_vi, ket_luan_nhanh, diagnosis_vi: { sections[] } }  // script_v1 sections
  topic, hook, duration, tone, niche_label
  shots[]           // 6-shot scaffold + references (appendix)
  sources[], related_questions[]
}
```

Reuse FE: `DiagnosisSectionRenderer` / section ids where overlap; script-only UI for shot carousel below narrative block.

---

### Wave 3 — Depth epic (F2 basic / F1 deep) ✅ *Shipped 2026-05-22 @ `9cd0957`*

**UI (2026-05-22, pre-W3 BE):** `QueryComposer` thay **Dán link video** / **Dán @handle** → pill **Cơ bản** / **Chuyên sâu** (`QueryComposer.tsx`, `HomeScreen`, `AnswerScreen` initial composer). Handoff `?depth=basic|deep` qua `buildAnswerHandoffPath`; Trends vẫn force `depth=basic`.

| Item | Effort | Risk | F8 utilization impact | Video diag | Channel diag | Acceptance criteria | Files touched |
|------|--------|------|----------------------|------------|--------------|---------------------|---------------|
| **W3-1** Migration `video_diagnostics.analysis_depth` + PK `(video_id, analysis_depth)` | L | High | F8 cache partition | basic/deep cache | — | §4.12.3 applied; backfill `deep`; no serve wrong depth | `supabase/migrations/`, `database.types.ts` |
| **W3-2** BE `append_turn` / `build_video_report` accept `analysis_depth` | L | High | F2/F1 split | Section whitelist | — | basic ⊆ deep sections; manifest cap 3 vs 5 | `answer_session.py`, `diagnose_sections.py`, `salience.py`, `gemini.py` |
| **W3-3** FE depth pills + billing 1×/2× | M | High | Product billing | — | — | Pills ✅; BE deduct 2× on `deep` primary video | `QueryComposer.tsx`, `HomeScreen`, `AnswerScreen`, `answer_session.py` |
| **W3-4** Cache upsert always sets `analysis_depth` | M | Med | No wasted re-extract | Both depths | — | Lookup `.eq(analysis_depth)`; on-demand URL cache partitioned | `video_analyze.py`, `report_video.py` |

**Wave 3 exit:** §13B depth items; follow-up UX → ✅ W5-1 CTA pills shipped @ `f3054f5` (§4.10.2).

| Item | Status | Notes |
|------|--------|-------|
| W3-0 Depth pills (composer UI) | ✅ | Thay Dán link/@handle; handoff `?depth=` |
| W3-1 Migration `analysis_depth` | ✅ | `20260827000000_video_diagnostics_analysis_depth.sql` |
| W3-2 BE whitelist + manifest cap | ✅ | `BASIC_SECTION_ALLOWLIST`; cap 3/5 |
| W3-3 Billing 1×/2× | ✅ | `append_turn` deduct ×2 on video deep |
| W3-4 Cache partition | ✅ | PK `(video_id, analysis_depth)`; on-demand URL keyed |
| W3-5 §4.11.3 post–Cơ bản upsell UI | ✅ | Teaser pills + `locked_sections` in body; deep upgrade CTA moved to `IntentCtaRail` @ W5-1 (not sticky body button) |

---

### Wave 4 — Channel findings & video deep utilization ✅ *Shipped 2026-05-23 @ `9b97207`*

| Item | Effort | Risk | F8 utilization impact | Video diag | Channel diag | Acceptance criteria | Files touched |
|------|--------|------|----------------------|------------|--------------|---------------------|---------------|
| **W4-1** `build_channel_findings()` P0 (4 findings) + prompt inject | L | Med | F4 salience layer | — | Memo uses findings | `<<<CHANNEL FINDINGS>>>` when ≥1; no FYP% claims | `channel_diagnose.py`, new `channel_findings.py` |
| **W4-2** §4.7 M3 live `boost_attribution` on user video (ingest-only today) | M | Med | F1 deep only | Section emits | — | Heuristic in new module (e.g. `signals/distribution.py`); “có dấu hiệu” copy; **no** `signals/boost.py` yet | `signals/distribution.py`, `diagnose_sections.py` |
| **W4-3** §4.8 P0 signal backlog + remaining W0 win signals (3) | L | Med | Manifest density | More sections | — | Fire-rate logged; tests per signal id | `signals/win.py`, `signals/*.py`, tests |
| **W4-4** Channel peer sort `.eq("reference_eligible", True)` on corpus queries | M | Med | F8 M2 on channel | — | Peers not ads-skew | `_run_peer_corpus_query` + fallback chain filter §4.7.5 | `channel_diagnose.py` |

**Wave 4 exit:** §5.3 C1 + §4.7 P1 partial; channel memo evidence-backed. **Utilization gate:** [`data-utilization-map-v1.md`](../docs/data-utilization-map-v1.md) §10 — cross-check W4-1…W4-4 ↔ FIELD matrix trước merge.

| Item | Status | Notes |
|------|--------|-------|
| W4-0 Utilization map Wave 4 gate | ✅ | §10 cross-check @ map v1.2 (`9cd0957` baseline) |
| W4-1 `channel_findings` | ✅ | P0×4 + `<<<CHANNEL FINDINGS>>>` prompt inject |
| W4-2 Live M3 boost | ✅ | `boost_attribution` section F1 deep; `signals/distribution.py` |
| W4-3 Signal backlog + Win W0 remainder | ✅ | 5 Win W0 + P0 flop signals + tests |
| W4-4 Channel `reference_eligible` peers | ✅ | Eligible-first + &lt;4 handle fallback |

---

### Wave 5 — Polish & gated cuts ✅ *Shipped 2026-05-23 @ `680c803`*

| Item | Effort | Risk | F8 utilization impact | Video diag | Channel diag | Acceptance criteria | Files touched |
|------|--------|------|----------------------|------------|--------------|---------------------|---------------|
| **W5-1** | Intent CTA pill follow-up — matrix per `AnswerSessionFormat`; ẩn `FollowUpComposer` free text | M | Med | Guided multi-intent session | Turn 2+ without chat | — | Video → ≥3 CTAs (script, compare, deep, …); explicit `intent_type`; `source_entry=intent_cta`; TimelineRail kept | `IntentCtaRail.tsx`, `intentCtaSuggestions.ts`, `AnswerScreen.tsx`, `answer_session.py` |
| **W5-2** | Intent output format round — align bodies + `narrative_vi` | L | Med | UX consistency | All formats | — | Pattern / timing / ideas / … narrative parity | `report_*.py`, `*Body.tsx`, `gemini.py` |
| **W5-3** `key_messages` trim post-ablation | S | Low | Cost ~1–3% | — | — | Diff v6 on sample; map §8 updated | `models.py`, `prompts.py` |
| **W5-4** F5 channel quick peek on Trends card | M | Med | 1–2 P0 findings | — | Teaser | Card shows ceiling OR format entropy | Trends channel card FE + API |
| **W5-5** GTM copy + launch gate §13B sweep | M | Low | — | — | — | All §13B checkboxes evidence-linked | docs + QA baselines |

**Wave 5 exit:** §13B sweep evidence in `artifacts/qa-reports/wave5-baseline.json`; incremental W0–W5 complete.

| Item | Status | Notes |
|------|--------|-------|
| W5-1 Intent CTA rail | ✅ | `IntentCtaRail`, `intentCtaSuggestions.ts`; hide `FollowUpComposer` free text; BE `intent_type` + `source_entry=intent_cta`; deep upgrade CTA in rail @ `f3054f5` |
| W5-2 `narrative_vi` headline parity | ✅ | `report_types.py`, `ReportNarrativeHeadline.tsx`, format bodies @ `d9e4628` |
| W5-3 `key_messages[]` trim | ✅ | Extraction schema trim @ `65e4145` — **G6 caveat:** trim applied without formal ablation metrics |
| W5-4 F5 channel quick peek | ✅ | `channel_quick_peek.py`, `ChannelQuickPeekTeaser.tsx` on Trends @ `98814cb` |
| W5-5 §13B sweep + QA baseline | ✅ | Launch gate evidence + changelog @ `680c803` |

---

## 5. Video diagnosis utilization backlog

Map: extract field → signal (`signals/registry.py`) → `section_id` → UI (`VideoBody`, `DiagnosisSectionRenderer`).

### 5.1 Wired (as-built — maintain)

Baseline extract → signal → UI map. **Depth:** F2 vs F1 rules in **§5.3** (commerce, distribution strips, boost, carousel deep-only). **Graduated from backlog:** `stats_history`, `hook_timeline`, boost FE block → **§5.2** ✅.

| Extract / promote | Signal / path | Section | UI | Status |
|-------------------|---------------|---------|-----|--------|
| `hook_*`, `hook_phrase` | `hook_*` | `hook_analysis`, `diagnosis` | `HookPhaseGrid`, `HookTimelineStrip` (§5.2), copy from `meta.hook_phrase` | ✅ maintain |
| `commerce_intent.*` | `commerce_*` | `commerce` | `DiagnosisSectionRenderer` — **F1 deep only**; F2 → locked upsell (§5.3) | ✅ maintain |
| `target_audience`, `pain_points`, `style_tags`, `promotion_type`, `tone` | persona / enrichment | sidebar context | `ContextStrip` via `report.enrichment` + `videoToneVi` | ✅ maintain |
| `scenes[]` (video extract) | editing signals | `editing` | BE segments + v6 `editing` prose when **F1 deep** | ✅ maintain |
| `scene_intelligence` (F7 corpus) | nightly batch | F7 script | `SceneIntelligencePanel` — **unwired**; see **feature-map F7 partial** (not §5.1 video path) | ⏸ F7 backlog |
| `performance_tier` + corpus stats | performance signals | `diagnosis` | `PerformanceTierChip`, `FlopDiagnosisStrip`, `KpiGrid` | ✅ maintain |
| `reference_videos` + proximity | `niche_reference_anchor` | `niche_pattern` | `VideoTileRow` / `EvidenceVideoEmbed` / `FormatCardsGrid`; `reference_eligible` pool filter | ✅ maintain |
| `douyin_*` (on-demand) | `douyin_origin_*` | `douyin_origin` | v6 section when `douyin_match` populates extract — **F1 deep only** (not Douyin browse `KHO_*` flag) | ✅ maintain |
| Batch `boost_attribution` + `reference_eligible` | ingest + ref pool; live M3 ✅ W4-2 | `boost_attribution` (F1) | `BoostAttributionBlock` + ref tiles — **§5.2** FE; **§5.3** basic = upsell `teaser_vi` only | ✅ maintain |

### 5.2 Missing / weak (incremental priority)

| Extract | Target signal/section | Wave | Notes |
|---------|----------------------|------|-------|
| `stats_history` M4 | `distribution_spike_then_flat` | ✅ Launch 2b + §5 FE | `StatsHistoryStrip` — **F1 deep only** (§5.3 @ `d864f065`) |
| `hook_analysis.hook_timeline[]` | pacing signals (P1) | ✅ Launch 2a + §5 FE | BE `hook_timeline_pacing_sparse`; `hook_timeline` on analyze response + `HookTimelineStrip` in `VideoBody` |
| `transitions_per_second` | `editing_cut_pace_*` | ✅ Launch 2a | Signal in synthesis `editing` section — no dedicated strip (F1 audit path) |
| `persona_consistency_signals` | channel rollup | ✅ Launch 2a | `channel_persona_drift` on channel path — not video `VideoBody` |
| `key_messages[]` | — | ✅ W5-3 @ `65e4145` | **Trimmed** from extraction schema — G6: trim without formal ablation metrics |
| Dedicated FE `boost_attribution` UI block | — | ✅ §5 FE | `BoostAttributionBlock` — F1 deep; meta fallback deep-only (§5.3 @ `d864f065`) |
| §4.11.3 post-basic upsell UI | teaser + “Phân tích chuyên sâu” CTA | W3-5 | ✅ Shipped — `VideoDeepUpsell` + `locked_sections` metadata |

### 5.4 Carousel path

| Extract | Target | Status | UI |
|---------|--------|--------|-----|
| `CarouselAnalysis.slides[]` + ME-19 fields | swipe psychology / slide intel | ✅ §5 FE | `CarouselIntelStrip` — **F1 deep only** (§5.3 @ `d864f065`) |
| `content_arc`, `swipe_trigger_type`, pacing | synthesis `hook_analysis` / distribution | ✅ BE | Carousel meta chips in strip; save-rate hint in `FlopDiagnosisStrip` |

### 5.3 F2 vs F1 depth split (post-W3) — ✅ complete

| Section | F2 basic | F1 deep | Status |
|---------|----------|---------|--------|
| `diagnosis`, `hook_analysis`, `niche_pattern`, `next_video` | synthesize | synthesize | ✅ `BASIC_SECTION_ALLOWLIST` + synthesis |
| `distribution`, `commerce`, `sound`, `persona`, `editing`, `metadata` | teaser/manifest | synthesize | ✅ BE whitelist + `locked_sections` with `signal_count`; FE upsell pills; `StatsHistoryStrip` deep-only |
| `boost_attribution` | teaser only | synthesize when M3 fires | ✅ deep-only synthesis @ W4-2; basic `teaser_vi` in upsell; no meta fallback on basic |
| §5.4 carousel slide intel | locked upsell | full strip | ✅ `CarouselIntelStrip` deep-only |

---

## 6. Channel diagnosis utilization backlog

As-built: **memo SSE** — `classify_trajectory`, `compute_score_card`, `build_channel_pattern`, **`build_channel_findings()`** (W4-1). Vision: `channel_findings[]` → `<<<CHANNEL FINDINGS>>>` — **✅ shipped @ `9b97207`**.

### 6.1 Wired — ✅ complete

| Data source | Output block | UI | Status |
|-------------|--------------|-----|--------|
| ED `fetch_user_posts` | trajectory, score_card | `ScoreCard`, trajectory badges | ✅ @ `78999fa` — `fetch_channel_videos_live` → SSE `score_card`; FE `ChannelDiagnosisBody` |
| Corpus by handle | `channel_pattern`, competitive_landscape | Pattern prompt blocks + peers | ✅ @ `78999fa` + `9b97207` — `build_channel_pattern`; corpus peers (`reference_eligible`); `competitive_landscape` → `CreatorTileRow` |
| `niche_channel_benchmarks` | percentiles in score card | KPI grid (`ScoreCard`) | ✅ @ `78999fa` — `compute_score_card` → `~Pn` + cadence/peak rows |
| **`channel_findings.py`** (W4-1) | P0×4 findings → `<<<CHANNEL FINDINGS>>>` prompt inject | Evidence-backed memo sections | ✅ @ `9b97207` — `build_channel_findings` → `format_findings_for_prompt` |
| Quick-peek `channel_summary` + `niche_benchmarks` | Percentile bars on Studio | `ChannelBenchmarkStrip` @ §6 | ✅ @ `37831b05` (BE quick-peek fields @ `98814cbf`) — Nhanh on `/app` |
| Gemini memo | `verdict`, `what_falling`, `what_worked`, `recommendations` | `SectionRenderer` | ✅ @ `78999fa` — Sâu SSE on Studio @ `37831b05` |

**Note:** Channel memo has no separate `channel_pattern` section_id (unlike video F1) — pattern stats feed prompt blocks (`<<<FORMAT PERFORMANCE>>>`) and findings, not a standalone heading.

### 6.2 Findings backlog (§5.3 P0–P2)

| Finding id | V5 | Data | Wave |
|------------|-----|------|------|
| `channel_view_ceiling_300` | §2.1 proxy | views≤300 + ER | ✅ W4-1 |
| `channel_format_entropy_high` | §2.2 | format distribution | ✅ W4-1 |
| `channel_recent_vs_peak_er_drop` | §2.2 | recent vs peak windows | ✅ W4-1 |
| `channel_peer_format_saturation` | §2.3 | top 20 corpus 7d | ✅ W4-1 |
| `channel_compliance_aggregate` | §2.4 | roll-up video compliance signals | ✅ Launch 2a |
| `channel_boost_outlier_share` | §1.8 | `% suspect_medium` on handle | ✅ Launch 2a |
| `channel_slang_staleness` | §2.5 | aggregate `persona_slang_dated` | ✅ Launch 2c |

**Studio UX (§6 ship):** ✅ @ `37831b05` — Channel analysis embedded on `/app` via `HomeMyChannelSection` + `ChannelStudioPanel`. Tab **Khám kênh** removed; `/app/channel` redirects to `/app?handle=…`. Cloud Run user pod post quick-peek deploy required for Nhanh benchmark strip.

### 6.3 Credit & F8

- **Wave 0:** ✅ fix 3 vs 1 mismatch before scaling channel usage.
- **Wave 4:** ✅ channel peers filter `reference_eligible` — `_run_peer_corpus_query(..., reference_eligible_only=True)` + &lt;4 handle fallback @ `9b97207`; video ref pool already did (W0-5a).
- Channel memo must not cite ads-skew corpus rows as “viral mẫu” — **✅ W4-4 shipped**.

---

## 7. Decision gates (human approval) — ✅ all resolved

| Gate | Decision | Blocks | Default recommendation | Status |
|------|----------|--------|------------------------|--------|
| **G1** Composer pills Cơ bản/Chuyên sâu | Ship in Wave 3? | W3-3 | Yes — vision §3.1.2; after W1 handoff | ✅ **Yes @ W3** (`9cd0957`) — `QueryComposer` pills + `?depth=` handoff |
| **G2** Hide follow-up turn 2+ | Free-text follow-up vs CTA rail | — | Replace chat with guided CTAs | ✅ **Resolved @ W5-1** (`f3054f5`) — `IntentCtaRail` thay `FollowUpComposer`; §4.10.2 |
| **G3** Hero niche list (5–8 IDs) | Which niches get deep ingest | W2-3, §8.7 | Human picks from `creator_niches` with thin corpus report | ✅ **Confirmed** — 8 IDs `[1,2,3,4,5,8,9,11]` @ `feature-map-v1.md` §8.7; evidence `launch-phase0-g3-hero.json` |
| **G4** Channel billing | 3× vs 1× | W0-1 | **3×** both sides per vision §10 — Completeness 10/10 | ✅ **3× @ W0-1** (`8ad7ab0`) — `CHANNEL_DIAGNOSE_CREDIT_COST=3` BE + FE |
| **G5** Depth billing | 1× basic / 2× deep | W3-3 | Sign-off before migration | ✅ **Resolved @ W3** (`9cd0957`) — `decrement_credit(p_amount)` 1/2; migration `analysis_depth` PK |
| **G6** `key_messages` trim | Post-ablation only | — | Trim only after ablation metrics | ✅ **Trim @ W5-3** (`65e4145`) — **caveat:** no formal ablation metrics logged |

Format per project AskUserQuestion: Tech Lead presents options A/B/C with Completeness scores before Wave 3+ execution. **Historical — all gates closed; no open human blocks for launch.**

---

## 8. Doc maintenance checklist (per wave)

- [ ] Update [`feature-map.md`](../docs/feature-map.md) as-built rows for touched routes/endpoints
- [ ] Append [`changelog.md`](../docs/changelog.md) in same commit as code
- [ ] If FIELD wired: update [`data-utilization-map-v1.md`](../docs/data-utilization-map-v1.md) row + remove from §8 orphans
- [ ] If architectural: update [`system-design.md`](../docs/system-design.md) §9/§10
- [x] QA baseline: `artifacts/qa-reports/<wave-id>-baseline.json` (Wave 5: `wave5-baseline.json` @ `680c803`)
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
| Text chat intents ⑤⑥⑦ from composer | **Không** free composer chat — chỉ CTA pill hoặc entry pill; `/api/chat` legacy rows |
| ~~Intent CTA follow-up matrix~~ | ✅ W5-1 @ `f3054f5` — shipped |
| ~~Intent output format parity~~ | ✅ W5-2 @ `d9e4628` — shipped |
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

- ✅ **W0–W5 complete** @ `680c803` — baseline `a271b1e` → `680c803`
- ✅ **W3 depth** @ `9cd0957` + W3-5 upsell teasers; deep CTA in `IntentCtaRail` @ W5-1 (`f3054f5`)
- ✅ **W4 channel_findings P0** @ `9b97207` — memo evidence-backed via `channel_findings.py` + peer `reference_eligible` filter
- ✅ **W5 polish** — CTA rail, `narrative_vi` parity, `key_messages` trim (G6 caveat), Trends channel quick peek, §13B sweep
- §13B evidence: `artifacts/qa-reports/wave5-baseline.json`
- F8: no undocumented orphans; `key_messages` ✅ trimmed @ W5-3 (formal ablation metrics deferred)
- §13A `peer_percentile` — ✅ **W1-3 shipped** @ `e3b5d01` (`finalize_niche_meta_peer_tier` + `peer_percentile_label` on `content_class_tier` axis)

---

## 13. Post-W5 next steps (remaining §13B / post-V1)

Wave 5 tasks complete — **Launch phase (full pre-launch):** Phases 0 → 1 → 2a → 2b → 2c must complete before Phase 3 ship gates. Human decision: do all utilization + §13B before GTM (see plan `post-w5_v1_launch`).

1. ~~**Phase 0**~~ ✅ — Hero niche depth (G3), corpus-health, BAT crons, humility copy, demo URL (`launch-phase0-baseline.json`)
2. ~~**Phase 1**~~ ✅ — Channel depth picker (F5 full + F4 Sâu billing D2) (`launch-phase1-baseline.json`)
3. ~~**Phase 2a**~~ ✅ — Core channel findings + video P1 signals + `channel_persona_drift` + G6 ablation (`launch-phase2a-baseline.json`)
4. ~~**Phase 2b**~~ ✅ — `stats_history` M4 cron + `distribution_spike_then_flat`; migrations `20260827000002`/`000003` applied; batch `00132-4sg` (`launch-phase2b-baseline.json`)
5. ~~**Phase 2c**~~ ✅ — Remaining §5.3.3 + §4.8.3 P1/P2 backlog + SSE Layer B (`launch-phase2c-baseline.json`)
6. ~~**Phase 3 infra**~~ ✅ — `db push`, types regen `b479f64`, Cloud Run deploy, cron/vault verify (`launch-phase3-baseline.json`, `post-w5-uncommitted-audit.md`)
7. **Phase 3 GTM** — `/visual-audit`, `/dogfood`, `/pre-handoff`, `/deploy` (Vercel SPA) — **deferred** (human gates)
8. ~~**§5 video FE utilization**~~ ✅ — `StatsHistoryStrip` + `HookTimelineStrip` + `BoostAttributionBlock` + `CarouselIntelStrip` in `VideoBody`

*W0–W5 complete @ `680c803`; **Launch Phases 0–2c + infra complete** @ `b479f64`; §5 video FE wired 2026-05-23; GTM deferred.*

---

*Maintainer: Tech Lead. Next review after post-W5 §13B items or taxonomy change.*
