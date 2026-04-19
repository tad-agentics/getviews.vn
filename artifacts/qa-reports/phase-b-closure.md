# Phase B — closure (`/video` · `/kol` · `/channel` · `/script`)

**Date:** 2026-04-19
**Plan:** `artifacts/plans/phase-b-plan.md` (§B.1–B.4)
**Verdict:** **GREEN** — four creator screens shipped, primary + supplementary audits closed in code, token gate clean across all routes. Two intentional deferrals (`PostingHeatmap`, `script_save`) and one parked deviation (`/app/script` 1280 vs 1380 width) carry into Phase C.

---

## Milestone matrix

| Sub-phase | Deliverable | Status | Evidence |
|-----------|-------------|--------|----------|
| **B.1** `/video` | Deep-dive (pacing ribbon, hook phases, forecast, CTA) | **Shipped + polished** | `src/routes/_app/video/VideoScreen.tsx`; v2 primitives (`RetentionCurve`, `Timeline`, `HookPhaseCard`, `IssueCard`, `KpiGrid`); audits `phase-b-design-audit-video.md` + `phase-b-design-audit-video-supplementary.md`. |
| **B.2** `/kol` | Kênh Tham Chiếu (table, filters, sticky detail, mutation) | **Shipped + polished** | `src/routes/_app/kol/KolScreen.tsx`; `src/hooks/useKolBrowse.ts`; v2 `SortableCreatorsTable`, `MatchScoreBar`, `KolStickyDetailCard`, `FilterChipRow`; backend `kol_browse.py` + `toggle_reference_channel` RPC; audits `phase-b-design-audit-kol.md` + supplementary (M-1/M-2/M-3 + S-1..S-4 closed); checkpoint `phase-b-b2-checkpoint.md`; measurement `phase-b-b25-measurement.md`. |
| **B.3** `/channel` | Phân Tích Kênh (hero, formula bar, top videos, lessons, CTA) | **Shipped + polished** | `src/routes/_app/channel/ChannelScreen.tsx`; v2 `FormulaBar`, `KpiGrid` (channel variant); backend `channel_analyze.py` + `channel_formulas` migration + `channel_corpus_stats` RPC; audits `phase-b-design-audit-channel.md` + `phase-b-b3-full-audit.md` + `phase-b-b33-channel-audit.md` + supplementary (M-1/S-1/S-2 closed, FormulaBar Vitest added). |
| **B.4** `/script` | Xưởng Viết (pacing ribbon, shot rows, scene intelligence, forecast, generate) | **Shipped + polished** | `src/routes/_app/script/ScriptScreen.tsx`; v2 `ScriptPacingRibbon`, `ScriptShotRow`, `SceneIntelligencePanel`, `ScriptForecastBar`, `MiniBarCompare`, `HookTimingMeter`, `DurationInsight`, `CardInput`, `CitationTag`; backend `script_generate.py` + `script_data.py` + `scene_intelligence_refresh.py` + `scene_intelligence` migration; audits `phase-b-design-audit-script.md` + `phase-b-b4-implementation-audit.md` + supplementary (M-2/S-1/S-2/S-3 closed, M-1 parked). |

---

## Token & banned-pattern gate — all four routes

`grep -nE '#[0-9a-fA-F]{3,8}\b|--ink-soft|--purple|--border-active|--gv-purple|text-white|bg-black|rgba\(|rgb\('`

| Scope | Hits |
|---|---|
| `src/routes/_app/{video,kol,channel,script}/**/*.tsx` | **0** |
| `src/components/v2/*.tsx` (Phase B primitives) | **0** |

All surfaces resolve through `--gv-*` tokens. The only literal hex in the Phase B surface is server-side payload data: `TOP_VIDEO_TILE_COLORS` in `channel_analyze.py:30-35` (pastel tile swatches) — served as `top_videos[].bg_color` and rendered via inline `style`. Consistent with B.3 precedent.

---

## Test coverage

**Backend (`cloud-run/tests/`):**

| File | Tests | Covers |
|------|-------|--------|
| `test_kol_browse.py` | 11 | Browse + toggle-pin + search filters + match-score computation (B.2). |
| `test_channel_analyze.py` | 6 | `_normalize_formula_pcts`, `_top_hook_from_types`, `_optimal_length_band`, `_median`, `_compute_views_mom_delta`, **gate (≥10 corpus) → no credit** (B.3). |
| `test_script_generate.py` | 2 | `_segment_lengths` rescale + `build_script_shots` shape & topic interpolation (B.4). |
| `test_script_data.py` | 3 | `_fmt_delta_pct`, `_pattern_label`, `latest_hook_effectiveness_rows` dedupe (B.4). |
| `test_scene_intelligence.py` | 4 | Event parsing + threshold (MIN_VIDEOS=30) + emit + **overlay-sample cap across events** (B.4.1). |

**Frontend:**

| File | Tests | Covers |
|------|-------|--------|
| `MatchScoreBar.test.tsx` | 3 | Clamp / round cases (B.2 supplementary). |
| `FormulaBar.test.tsx` | 3 | Segments + thin-corpus copy + null-gate copy (B.3 supplementary). |
| `scriptPrefill.test.ts` | 3 | Ritual / channel / video prefill → URL query; 500-char topic truncation (B.4.4 / B.4.5). |
| `scriptEditorMerge.test.ts` | 2 | `ScriptShot` → editor mapping; `scene_intelligence` row merge (B.4.3). |

**Not shipped (non-blocking follow-up):** `ChannelScreen.test.tsx`, `ScriptScreen.test.tsx`, render tests for `ScriptPacingRibbon` / `SceneIntelligencePanel` / `MiniBarCompare` / `HookTimingMeter` / `DurationInsight`. All are cheap pure-input renders; recommended for Phase C baseline hardening.

---

## Measurement instrumentation (`src/lib/logUsage.ts`)

| Event | Status |
|-------|--------|
| `video_screen_load`, `flop_cta_click`, `video_to_script` | **Live** (B.1 + B.4.5) |
| `kol_screen_load`, `kol_pin` | **Live** (B.2.5) |
| `script_screen_load`, `script_generate`, `channel_to_script` | **Live** (B.4) |
| `script_save` | **Deferred** — disabled until persistence ships (Phase C) |

All live events should be validated in the product analytics dashboard over a **3–7 day measurement window** before Phase C kickoff.

---

## Explicitly deferred (aligned with plan)

| Item | Status | Home |
|------|--------|------|
| `PostingHeatmap` component (B.3) | Intentionally absent — cadence/time + `THỜI GIAN POST` KPI cover signal density | Phase C or later |
| `script_save` persistence + "Lưu vào lịch quay" / Copy / PDF / Chế độ quay (B.4) | Disabled with `title="Sắp có"` | Phase C |
| Gemini-rich `POST /script/generate` | v1 deterministic scaffold; HTTP contract frozen | Phase C enhancement |
| KOL `match_score` persistence | Recomputed per request; acceptable v1 | Phase C if DB load warrants |
| KOL growth term | `growth_percentile_from_avgs` proxy; real 30d when `creator_velocity` lands | Data pipeline, not Phase B |

---

## Open items carried into Phase C

1. **B.4 M-1 — content width 1280 vs design 1380.** Outer `<main className="gv-route-main gv-route-main--1280">` in `ScriptScreen.tsx:295` still caps at 1280px (`src/app.css:519-521`); inner `max-w-[1380px]` wrappers are ineffective. Supplementary polish landed M-2/S-1/S-2/S-3 but left the width cap — appears to be a deliberate call for platform consistency with `/video`, `/channel`, `/kol`. Decision needed in Phase C: promote all four routes to 1380, keep 1280 platform-wide, or add per-route override.
2. **Phase C scope brief.** No `artifacts/plans/phase-c-plan.md` yet. Needs to capture: `script_save` persistence, Gemini upgrade to `/script/generate`, KOL match persistence, `PostingHeatmap`, real 30d growth wiring.
3. **Measurement sanity check.** 3–7 day dashboard read on all live `logUsage` events to confirm funnel integrity (home → video → script, channel → script, kol → pin) before any Phase C behavior changes.
4. **Recommended test backfill.** Five primitives + two screen-level render tests (~200 lines total); cheap insurance before Phase C expands the surface.

---

## Audit artifacts inventory

| Screen | Primary | Supplementary | Other |
|--------|---------|---------------|-------|
| B.1 `/video` | `phase-b-design-audit-video.md` | `phase-b-design-audit-video-supplementary.md` | — |
| B.2 `/kol` | `phase-b-design-audit-kol.md` | `phase-b-design-audit-kol-supplementary.md` | `phase-b-b22-audit.md`, `phase-b-b23-audit.md`, `phase-b-b2-checkpoint.md`, `phase-b-b25-measurement.md` |
| B.3 `/channel` | `phase-b-design-audit-channel.md` | `phase-b-design-audit-channel-supplementary.md` | `phase-b-b3-full-audit.md`, `phase-b-b31-channel-analyze-audit.md`, `phase-b-b33-channel-audit.md` |
| B.4 `/script` | `phase-b-design-audit-script.md` | `phase-b-design-audit-script-supplementary.md` | `phase-b-b4-implementation-audit.md` |

---

## Sign-off

Phase B is **closure-complete** for the creator surfaces. Four screens live on `main`, primary + supplementary design drift closed where actionable, token gate green, backend gates + credit semantics covered by unit tests, entry-point analytics instrumented. Carry items are scoped and docketed — no silent debt.

**Recommended next step:** spend one week on measurement + Phase C plan drafting; land the B.4 M-1 width decision as part of that plan.
