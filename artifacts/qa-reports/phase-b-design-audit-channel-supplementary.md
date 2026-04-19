# Phase B · B.3 — supplementary design parity (`/app/channel`)

**Date:** 2026-04-19 (original); **closure update:** 2026-04-19  
**Parent audits:** `phase-b-design-audit-channel.md` (B.3.5), `phase-b-b3-full-audit.md` (B.3 closure), `phase-b-b33-channel-audit.md` (B.3.3 compliance), `phase-b-b31-channel-analyze-audit.md` (B.3.1 API).  
**Scope:** Second-pass drift check against `artifacts/uiux-reference/screens/channel.jsx` + `CHANNEL_DETAIL` fixture in `data.js`, after the primary audit + pixel-parity pass (`82d64c2`) landed on `main`.

---

## Status (post-implementation)

All **must-fix** and **should-fix** items from the drift table below are **closed in code** (see **Resolution** column). **S-3** and **C-*** rows remain intentional / parked per original notes. **`FormulaBar` unit tests** were added per the doc’s recommended follow-up.

---

## Token & banned-pattern sweep (re-verified)

`grep -nE '#[0-9a-fA-F]{3,6}\b|var\(--purple|var\(--border\b|var\(--ink-soft|var\(--faint|var\(--border-active'`

| File | Hits |
|---|---|
| `src/routes/_app/channel/**/*.tsx` | **0** |
| `src/components/v2/FormulaBar.tsx` | **0** |
| `src/components/v2/KpiGrid.tsx` | **0** |

All surfaces resolve through `--gv-*` tokens. The only literal hex in the B.3 surface is backend-side `TOP_VIDEO_TILE_COLORS = ("#D9EB9A", "#E8E4DC", "#C5F0E8", "#F5E6C8")` in `cloud-run/getviews_pipeline/channel_analyze.py:30-35`, served as API payload `top_videos[].bg_color` and rendered via inline `style={{ backgroundColor: v.bg_color }}` — payload data, not author-chosen hex in JSX. Consistent with the reference (`v.bg` in `VIDEOS` fixture is also raw hex).

---

## Drift table vs `channel.jsx` (historical) → resolution

### must-fix

| ID | Item | Resolution |
|----|------|--------------|
| M-1 | CTA missing script icon vs `channel.jsx:118` | **Done:** `FileText` on “Tạo kịch bản…”. **Update (B.4.5):** CTA enabled — navigates to `/app/script` with formula prefill + `channel_to_script` analytics. |

### should-fix

| ID | Item | Resolution |
|----|------|--------------|
| S-1 | Bio curly vs straight `"..."` | **Done:** bio rendered with straight ASCII U+0022 quotes via a template literal in `ChannelScreen.tsx`. Commit **`9a4b42f`**. |
| S-2 | `· cache` in footer | **Done:** `import.meta.env.DEV && data.cache_hit === true` only. Commit **`377c162`**. |
| S-3 | `line-clamp-2` on video titles | **Unchanged by design** — intentional for long TikTok titles (see original note). |

### consider

| ID | Item | Note |
|----|------|------|
| C-1 | `drop-shadow-md` on view overlay | Keep — legibility. |
| C-2 | TopBar + pulse + KOL + “Kênh khác” | Parked until B.4 shell review. |
| C-3 | Backend tile palette vs reference `VIDEOS` | Parked — design / token catalog optional. |
| C-4 | Lesson empty-state copy | Keep — thin-corpus UX. |
| C-5 | Dynamic avatar initial | Keep — real data. |

---

## Explicitly deferred / aligned-with-plan

- **`PostingHeatmap`** — intentionally absent (plan §B.3 defers). Shipped surfaces cadence + time as a chip, plus the `THỜI GIAN POST` KPI cell — sufficient signal density for the hero strip.
- **`Tạo kịch bản theo công thức này` CTA** — **shipped (B.4.5):** opens Xưởng Viết with `scriptPrefillFromChannel` (niche, topic, top hook). Historical note: the static `channel.jsx` reference had no `onClick`; product chose behavioural routing for production.
- **`force_refresh=1` querystring escape hatch** — shipped only, not a design concern. Correctly scoped to URL-level (not a visible control).

---

## Test coverage (B.3 backend)

`cloud-run/tests/test_channel_analyze.py` covers:

| Test | Guarantees |
|------|------------|
| `test_normalize_formula_pcts_targets_hundred` | `_normalize_formula_pcts` rescales 4 steps to sum = 100, each ≥ 4. |
| `test_top_hook_from_types_mode` | Plurality hook + usage % for KPI `HOOK CHỦ ĐẠO`. |
| `test_optimal_length_band_from_duration_seconds` | `ĐỘ DÀI TỐI ƯU` band from `analysis_json.duration_seconds`. |
| `test_median_middle_value` | Helper coverage for duration band + ER aggregates. |
| `test_views_mom_delta_with_synthetic_windows` | `↑ N% MoM` string driven by 30d vs prior-30d averages. |
| `test_run_channel_analyze_thin_corpus_no_credit` | **Gate**: `total < CORPUS_GATE_MIN (=10)` → `formula_gate="thin_corpus"`, `formula=None`, `decrement_credit` not called. Asserts `CORPUS_GATE_MIN == 10`. |

### Frontend (supplementary follow-up)

**`src/components/v2/FormulaBar.test.tsx`** — Vitest + Testing Library:

| Case | Asserts |
|------|---------|
| Steps provided | Segment labels (`Hook · 22%`, …) and detail lines render. |
| `formula_gate === "thin_corpus"` + no steps | Empty copy **“Chưa đủ video để dựng công thức”**. |
| Empty steps + `gate === null` | **“Chưa có công thức”**. |

`ChannelScreen.test.tsx` not added (heavier setup); optional later.

---

## Verdict

**Green / closed:** supplementary drifts **M-1**, **S-1**, **S-2** are implemented on `main`; token sweep unchanged; **FormulaBar** covered by lightweight unit tests. Hand off to **B.4 `/app/script`** when ready (enables the script CTA behavior).

---

## Traceability

| B.3 milestone | Commit |
|---------------|--------|
| B.3.1 migration + gate + `GET /channel/analyze` | `8901522` |
| B.3.2 posting cadence + MoM + reach KPIs | `15db5d6` |
| B.3.3 `/app/channel` + `FormulaBar` + hook | `e8a98dc` |
| B.3.3 audit + must-fix UI / B.3.4 routing | `8c9d43a` |
| B.3.5 design audit + reference parity | `b7eb6a7` |
| B.3 pixel parity (KpiGrid, rhythm, 901 breakpoint) | `82d64c2` |
| Supplementary doc (initial) | `ce826c2` |
| Supplementary fixes M-1, S-2 | `377c162` |
| Supplementary fix S-1 (ASCII bio quotes) | `9a4b42f` |
| `FormulaBar` Vitest coverage + supplementary audit doc closure | `d9acc72` |
