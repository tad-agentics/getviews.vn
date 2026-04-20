# Phase C.2.5 — Design audit: Pattern body (`/app/answer`)

**Date:** 2026-04-20  
**Refs:** `phase-c-plan.md` §C.2 exact design spec, `artifacts/uiux-reference/screens/answer.jsx` (sections), shipped `src/components/v2/answer/pattern/**`.

## Token gate (same rule as C.1.5)

**Method:** ripgrep on `src/components/v2/answer/pattern/**`:

| Check | Result |
|-------|--------|
| Hex `#[0-9a-fA-F]{3,8}` in TSX | **No hits** |
| Banned vars `--ink-soft`, `--purple`, `--border-active`, `--gv-purple-*` | **No hits** |
| Raw `rgba(` / `rgb(` in pattern TSX | **No hits** |
| Forecast primary row | **`--gv-forecast-primary-bg`** in `src/app.css`; used in `PatternActionCards.tsx` |

**Status:** **GREEN** — colors resolve through `var(--gv-*)` (including scrim/forecast tokens where applicable).

---

## Plan spot-checks (§C.2.3 layout)

| Spec | Shipped | Notes |
|------|---------|--------|
| **ConfidenceStrip** — mono band, `N=…`, freshness, optional **MẪU MỎNG** chip | `ConfidenceStrip.tsx` | `mt-[22px]`, `gv-canvas-2`, chip toggles humility visibility in parent. |
| **HumilityBanner** thin sample | `HumilityBanner.tsx` | Shown when `sample_size < 30` and chip-expanded. |
| **WoWDiffBand** optional | `WoWDiffBand.tsx` | Renders when `wow_diff` buckets non-empty. |
| **TL;DR** — TÓM TẮT, title, thesis 22px, SumStat grid, ink borders | `PatternBody.tsx` | `border-y` on callout row. |
| **Hook findings ×3** — grid, lifecycle / contrast / prereq rows | `HookFindingCard.tsx` | 40px / `1fr` / auto grid; mono lifecycle; prereq chips `gv-canvas-2`. |
| **WhatStalled** — danger rail, grey rank, ▼ delta, kicker `ĐÃ THỬ NHƯNG RƠI` | `WhatStalledCard.tsx`, `WhatStalledRow.tsx` | `border-l-[3px] border-[color:var(--gv-danger)]`; empty state uses `WhatStalledRow`. |
| **Evidence** — 3/2/1 cols @ 1100/720 | `EvidenceGrid.tsx` | `min-[1100px]:grid-cols-3`, `min-[720px]:grid-cols-2`. |
| **Pattern cells** 2×2 + border | `PatternCellGrid.tsx` | `gap-px` + `bg-[gv-ink]` hairlines; 60px chart slot. |
| **Action cards** + forecast row | `PatternActionCards.tsx` | Primary: `--gv-forecast-primary-bg`; mono forecast line. |

---

## Tier list

### Must-fix

- **None** at audit time — WhatStalled danger border, forecast token, and token grep are satisfied.

### Should-fix

1. **Chart slots** — **Done:** `PatternMiniChart` reads `chart_kind` + `chart_data` (`bars`, `primary_pct`, `marker`); `build_pattern_cells` + fixture emit data; dashed fallback if empty.
2. **Action card CTAs** — **Done:** `route` on payload (`/app/script`, `/app/channel`, `/app/trends`) + `useNavigate` + title-based fallback.

### Consider

1. **Uppercase Vietnamese kickers** — **Done:** section labels moved to sentence/title case (`Tóm tắt`, `Video mẫu`, …) with `tracking-wide` (no all-caps rail).
2. **Evidence thumbnails** — **Done:** optional `thumbnail_url` on `EvidenceCardPayload`; corpus select + `pick_evidence_videos`; `EvidenceGrid` uses `<img>` with error fallback to color tile.

---

## WhatStalled acceptance (C.2 non-negotiable)

- **Backend:** `PatternPayload` pydantic invariant + `tests/test_report_pattern.py` (`test_c22_what_stalled_acceptance_invariant`, empty+reason tests).
- **CI:** `smoke-answer-pattern.sh` runs pytest on `test_report_pattern.py`.

---

## Verdict

**C.2.5 audit: PASS** — Pattern body matches plan structure and token rules; **should-fix / consider** follow-ups from this audit are implemented in code (see Tier list above).
