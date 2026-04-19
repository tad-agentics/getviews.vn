# Phase B · B.3 — supplementary design parity (`/app/channel`)

**Date:** 2026-04-19
**Parent audits:** `phase-b-design-audit-channel.md` (B.3.5), `phase-b-b3-full-audit.md` (B.3 closure), `phase-b-b33-channel-audit.md` (B.3.3 compliance), `phase-b-b31-channel-analyze-audit.md` (B.3.1 API).
**Scope:** Second-pass drift check against `artifacts/uiux-reference/screens/channel.jsx` + `CHANNEL_DETAIL` fixture in `data.js`, after the primary audit + pixel-parity pass (`82d64c2`) landed on `main`.

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

## Remaining drifts vs `channel.jsx` (after primary audit)

### must-fix

| ID | Item | Reference (`channel.jsx`) | Shipped (`ChannelScreen.tsx`) | Fix |
|----|------|---------------------------|-------------------------------|------|
| M-1 | Full-width CTA missing **script icon** | `<Icon name="script" size={13} /> Tạo kịch bản theo công thức này` (line 118) | `<Btn variant="accent" ... disabled title="Sắp có">Tạo kịch bản theo công thức này</Btn>` — **no icon** (line 365-367) | Import `FileText` (or the project's script glyph) and prefix the button children with `<FileText className="mr-1.5 h-3.5 w-3.5" strokeWidth={1.7} aria-hidden />`. Keep disabled state until B.4 route lands. |

### should-fix

| ID | Item | Note |
|----|------|------|
| S-1 | Bio quote style — design uses **straight ASCII** `"..."` (`channel.jsx:35`); shipped wraps in curly `&ldquo;&rdquo;` at `ChannelScreen.tsx:266`. Cosmetic, but design spec is literal. | Either revert to straight quotes or document curly as a deliberate Vietnamese-typography upgrade. Low urgency — reviewer preference. |
| S-2 | `" · cache"` suffix on the `computed_at` footer (`ChannelScreen.tsx:374`) exposes cache-hit state to end users. Design shows no such affordance. | Gate behind `import.meta.env.DEV`, or move to an `aria-hidden` mono tick, or drop entirely — the 7d cache is an implementation detail. |
| S-3 | Top-video caption `line-clamp-2` (`ChannelScreen.tsx:330`) is a shipped enhancement not in the reference. Keeps as-is; reference titles are short by design, real TikTok titles are not. | Keep. Document as intentional for real data. |

### consider

| ID | Item | Note |
|----|------|------|
| C-1 | `drop-shadow-md` on video-tile view overlay (`ChannelScreen.tsx:326`) not in reference — safe legibility upgrade for pastel swatch backgrounds. | Keep. |
| C-2 | `TopBar` + live pulse + KOL button + `"Kênh khác"` form — reference has only a **ghost back button** `Về Studio` at the top, then the hero card. Primary audit already parks this as "product choice; keep for parity with `/app/video`". | Parked. Re-verify when `/app/script` (B.4) lands whether all four creator screens share the same shell chrome. |
| C-3 | `TOP_VIDEO_TILE_COLORS` backend palette is four pastels; reference `VIDEOS` uses darker saturated hexes (`#3D2F4A`, `#7C2A4A`, etc.). Visually softer than reference but consistent across real tiles (whose `thumbnail_url` usually renders on top). | Parked. If the design team wants the dark-pastel mood, move the palette into a `channel_tile_palette` token catalog and share with `/app/video` hero tiles. |
| C-4 | Lesson empty-state copy — `"Cần ≥10 video trong ngách để tổng hợp bài học."` / `"Chưa có bài học từ mô hình."` (`ChannelScreen.tsx:343-344`) — reference has no empty state (lessons are hardcoded), so this is strictly additive for thin-corpus real data. | Keep. |
| C-5 | Initial-avatar generalization — reference hardcodes `"S"`; shipped uses `channelInitial(data.name, data.handle)`. Necessary for real creators. | Keep. |

---

## Explicitly deferred / aligned-with-plan

- **`PostingHeatmap`** — intentionally absent (plan §B.3 defers). Shipped surfaces cadence + time as a chip, plus the `THỜI GIAN POST` KPI cell — sufficient signal density for the hero strip.
- **`Tạo kịch bản theo công thức này` CTA** — disabled (`title="Sắp có"`) until B.4 `/app/script` lands. Confirmed by reference: the design's CTA also has no `onClick`; parity is visual, not behavioral.
- **`force_refresh=1` querystring escape hatch** — shipped only, not a design concern. Correctly scoped to URL-level (not a visible control).

---

## Test coverage (B.3 backend)

`cloud-run/tests/test_channel_analyze.py` covers:

| Test | Guarantees |
|------|-----------|
| `test_normalize_formula_pcts_targets_hundred` | `_normalize_formula_pcts` rescales 4 steps to sum = 100, each ≥ 4. |
| `test_top_hook_from_types_mode` | Plurality hook + usage % for KPI `HOOK CHỦ ĐẠO`. |
| `test_optimal_length_band_from_duration_seconds` | `ĐỘ DÀI TỐI ƯU` band from `analysis_json.duration_seconds`. |
| `test_median_middle_value` | Helper coverage for duration band + ER aggregates. |
| `test_views_mom_delta_with_synthetic_windows` | `↑ N% MoM` string driven by 30d vs prior-30d averages. |
| `test_run_channel_analyze_thin_corpus_no_credit` | **Gate**: `total < CORPUS_GATE_MIN (=10)` → `formula_gate="thin_corpus"`, `formula=None`, `decrement_credit` not called. Asserts `CORPUS_GATE_MIN == 10`. |

Frontend tests: no dedicated `ChannelScreen.test.tsx` shipped. `FormulaBar` has no unit test either. Recommended follow-up (not a must-fix for closure): a lightweight render test asserting (a) 4 weighted segments when `steps` provided, (b) empty-state copy branches on `formulaGate`.

---

## Verdict

**Green** for the primary B.3 ship, with one pixel-level must-fix carried forward (M-1, missing script icon on the CTA) and two low-urgency should-fix items (S-1 bio quotes, S-2 cache suffix). Primary audit already closed the structural drift (hero padding, 36px rhythm, 901px breakpoint, KPI `channel` variant, video-tile chrome, formula copy, lessons `mb-0.5`). Token gate clean. Backend gate + cache semantics covered by `test_channel_analyze.py`.

Next: fold M-1 + S-2 into the next `/app/channel` polish commit, then hand off to **B.4 `/app/script`** (unblocks the currently-disabled "Tạo kịch bản theo công thức này" CTA).

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
