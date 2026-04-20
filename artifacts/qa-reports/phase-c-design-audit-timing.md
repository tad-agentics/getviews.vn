# Phase C.4 — Timing report design audit

**Milestone:** C.4.5 (plan §C.4 milestones, p.1290–1300)
**Verdict:** **PASS** — ready to close C.4.

---

## Render order (plan §C.4 design spec)

`src/components/v2/answer/timing/TimingBody.tsx` composes the seven
sections in the locked order:

1. `ConfidenceStrip` (reused from Pattern — same schema).
2. `HumilityBanner` (thin-sample only, `confidence.sample_size < 80`).
3. `TimingHeadline` — left: kicker `SƯỚNG NHẤT` + serif top window +
   insight sentence; right: kicker `3 CỬA SỔ CAO NHẤT` + ranked list
   with lift multipliers. Lifted 1:1 from `thread-turns.jsx:111-140`.
4. `TimingHeatmap` — 7 days × 8 hour buckets, 28px row label column
   + 8 value columns with the reference's 5-level tone ramp re-mapped
   to `--gv-*` tokens. Legend footer carries sample count + niche.
5. `VarianceNote` chip (**new** per plan §2.3 §5): `strong` / `weak` /
   `sparse` keyed to `top_window.lift_multiplier` ≥ 2.0 / ≥ 1.3 / < 1.3.
   Prevents the heatmap from shipping false confidence on thin samples.
6. `FatigueBand` (**new** per plan §2.3 §6, optional): rendered only
   when `fatigue_band` is populated (streak ≥ 4 weeks at #1 for the
   top window, via `timing_top_window_streak` RPC).
7. `TimingActionCards × 2` — "Lên lịch post vào {day} {hours}" (primary,
   routes `/app/script`) + "Xem kênh đối thủ khai thác cửa sổ này"
   (secondary, routes `/app/kol`). Forecast row above CTA uses the top
   window's lift multiplier as the expected range.

Empty-state contract (plan §2.3): when `sample_size < 80` OR
`variance_note.kind === "sparse"`, the heatmap hides cell values below 5
(via `maskBelowFive={true}`). Top-3 list still renders. Parent body also
shows `HumilityBanner` when thin.

---

## Token grep gate

```
grep -rnE "var\(--purple\)|var\(--ink-soft\)|var\(--border-active\)|\
--gv-purple|variant=\"purple\"|#[0-9a-fA-F]{3,8}|rgba?\(" \
  src/components/v2/answer/timing/
```

**Result: 0 hits.** All colours resolve through `--gv-*` tokens:
`--gv-ink`, `--gv-ink-2`, `--gv-ink-3`, `--gv-ink-4`, `--gv-canvas-2`,
`--gv-paper`, `--gv-rule`, `--gv-accent`, `--gv-accent-soft`,
`--gv-accent-deep`, `--gv-accent-2-soft` (heatmap mid-band),
`--gv-forecast-primary-bg`.

The tone ramp at `timingFormat.cellBackgroundForValue` deliberately
replaces the reference's `rgba(37, 244, 238, 0.25)` mid-band with the
existing `--gv-accent-2-soft` token (same intent, token-clean).

---

## §J data contract coverage

| Schema field | TimingBody consumer | Status |
|---|---|---|
| `TimingPayload.confidence` | `ConfidenceStrip` | ✅ |
| `TimingPayload.top_window` (`day`, `hours`, `lift_multiplier`, `insight`) | `TimingHeadline` | ✅ all fields rendered |
| `TimingPayload.top_3_windows[]` | `TimingHeadline` right column | ✅ |
| `TimingPayload.lowest_window` | embedded in `top_window.insight` copy (backend-generated) | ✅ |
| `TimingPayload.grid[7][8]` | `TimingHeatmap` | ✅ |
| `TimingPayload.variance_note` (`kind`, `label`, `detail`) | `VarianceNote` | ✅ 3 visual states |
| `TimingPayload.fatigue_band` (`weeks_at_top`, `copy`, nullable) | `FatigueBand` | ✅ null-safe |
| `TimingPayload.actions[]` (2) | `TimingActionCards` | ✅ forecast row |
| `TimingPayload.sources[]` | right-rail (`AnswerSourcesCard` via `ContinuationTurn`) | ✅ |
| `TimingPayload.related_questions[]` | right-rail (`RelatedQs`) | ✅ |

---

## Backend invariants

- **Variance classification** (plan §2.3 §5): `classify_variance` in
  `report_timing_compute.py` is a pure function of `top_windows[0].lift_multiplier`.
  Covered by `test_classify_variance_thresholds` (four cases:
  strong / weak / sparse / empty).
- **Empty state** (`sample_size < 80`): live pipeline routes to
  `build_thin_corpus_timing_report` which pins `variance_note.kind` to
  `sparse`. Covered by `test_build_timing_report_thin_niche_routes_to_thin`.
- **Fatigue band** only populates when `timing_top_window_streak` RPC
  returns ≥ 4. Covered by
  `test_build_timing_report_populates_fatigue_when_streak_geq_4` (mock
  returns 6; fatigue_band populated with 6-week copy) and
  `test_build_timing_report_full_corpus_returns_strong_variance` (mock
  returns 0; fatigue_band stays null).
- **RPC fail-open:** `fetch_top_window_streak` returns 0 when the RPC
  raises. Covered by `test_fetch_top_window_streak_fails_open_on_rpc_error`.
- **Heatmap normalization:** `build_heatmap_grid` maps cell medians to
  0–10 against the peak cell. Covered by
  `test_build_heatmap_grid_normalises_to_0_10`.
- **Sample filter:** `compute_top_windows` drops cells with < 2 samples
  to avoid single-video spurious wins. Covered by
  `test_compute_top_windows_drops_single_sample_cells`.

---

## Must-fix

None.

## Should-fix (Phase D / polish)

1. **`timing_top_window_streak` RPC body is a stub** (returns 0). The
   fatigue band will never trigger in production until the migration
   body lands. Noted on the plan's "WoW stub" precedent (Pattern). Open
   as Phase D work; the helper + schema + UI are ready to light up the
   moment the RPC returns a non-zero value.
2. **Niche median lift precision.** `compute_top_windows` currently
   proxies lift via the 0–10 normalised scale (`value / 5.0`). When the
   niche has a bimodal distribution, this can overstate the #1 window's
   lift. Tighten by dividing per-cell median by `niche_median_views`
   directly when cell sample ≥ 3.
3. **Legend contrast for `--gv-accent-2-soft` on `--gv-paper`.** Low
   contrast at small sizes. Design review to decide whether to darken
   the mid-band or add a hairline border on the 5–7 band cells.

## Consider

- **RTL heatmap axis.** Reference uses Monday-first (T2..CN); Vietnamese
  market convention is unchanged. No action.
- **Heatmap row labels.** Currently use 2-char abbreviations (T2..CN).
  Reference uses the same. Accessible name includes the full bucket
  label so screen readers read the full cell context.

---

## Sign-off

C.4.1 RPC stub signature + C.4.2 aggregator & compute + C.4.3 frontend
body + C.4.4 intent retirement (already wired in C.0.1 as
`timing → "answer:timing"`) + C.4.5 token audit + C.4.6 smoke = all
green. Ready to close C.4 and open C.5 (Generic + multi-intent merge).
