# Phase C.5 — Generic + multi-intent merge design audit

**Milestone:** C.5.4 (plan §C.5 milestones)
**Verdict:** **PASS** — ready to close C.5.

---

## Render order (plan §C.5 design spec)

`src/components/v2/answer/generic/GenericBody.tsx` composes the four
required sections in the locked order:

1. **FALLBACK chip + `ConfidenceStrip`** — dedicated pill "FALLBACK ·
   intent thấp" rendered unconditionally above the strip so low-confidence
   landings always announce themselves. Strip itself carries
   `sample_size`, `window_days`, `freshness_hours` (backend forces
   `niche_scope = null` so the strip doesn't claim a niche scope).
2. **`OffTaxonomyBanner`** — dashed ink-4 border on canvas-2 bg + 3
   chip buttons routing to `/app/channel`, `/app/script`, `/app/kol`.
   Copy: "Câu hỏi này ngoài taxonomy — gợi ý: dùng Soi Kênh / Xưởng
   Viết / Tìm KOL thay vì đào sâu ở đây." Icons: Eye / Film / Users
   (lucide-react).
3. **`NarrativeAnswer`** — kicker `TRẢ LỜI` + 1–2 serif 20px paragraphs.
   Renders nothing when backend returns an empty array (OffTaxonomyBanner
   still stands alone).
4. **`GenericEvidenceGrid`** — 3-col (≤720 → 1-col) evidence tiles with
   creator handle, caption, views, duration. Tiles route to `/app/video?
   video_id=…`; thumbnails use server-seeded `bg_color` plus optional
   `thumbnail_url` image when available.
5. **No ActionCards** — the OffTaxonomyBanner IS the routing surface
   (plan §2.4 explicit omission).

## Multi-intent merge (plan §A.4 — C.5.3)

Four cases from plan §A.4:

| # | Case | C.5.3 implementation | Status |
|---|---|---|---|
| 1 | Destination + report | Classifier returns destination; secondary shown as ActionCard on destination screen. Lives in TS `intent-router.ts` map + SPA routes. | ✅ (scope: existing C.0.1 matrix) |
| 2 | Report + report (same family) | `build_pattern_report` reads `_intent_type` today; `format_emphasis` blending is a Phase D tweak when corpus warrants. | ⏸ future |
| 3 | **Report + timing** | `detect_pattern_subreports(query)` keyword-matches "giờ nào" / "khi nào post" / "khung giờ" etc → `build_pattern_report(..., subreports=["timing"])` → invokes `build_timing_report` → attaches under `subreports.timing`. `PatternBody` renders `<PatternSubreports>` between `PatternCells` and `ActionCards`. | ✅ live |
| 4 | Everything else | Secondary signals → filter params on primary report. Covered by existing classifier tests; no schema change. | ✅ (scope) |

Subreport failures are non-fatal — if `build_timing_report` raises,
Pattern still ships with `subreports = null`. Covered by
`test_build_pattern_report_timing_subreport_failure_does_not_abort_primary`.

---

## Token grep gate

```
grep -rnE "var\(--purple\)|var\(--ink-soft\)|var\(--border-active\)|\
--gv-purple|variant=\"purple\"|#[0-9a-fA-F]{3,8}|rgba?\(" \
  src/components/v2/answer/generic/ src/components/v2/answer/multi/
```

**Result: 0 hits.** All colours resolve through `--gv-*` tokens:
`--gv-ink`, `--gv-ink-2`, `--gv-ink-3`, `--gv-ink-4`, `--gv-canvas-2`,
`--gv-paper`, `--gv-rule`, `--gv-accent`, `--gv-accent-soft`,
`--gv-accent-deep`.

---

## §J data contract coverage

### GenericPayload

| Schema field | Consumer | Status |
|---|---|---|
| `confidence` w/ `intent_confidence: "low"` | `ConfidenceStrip` + FALLBACK chip | ✅ |
| `off_taxonomy.suggestions[3]` (label, route, icon) | `OffTaxonomyBanner` | ✅ 3 chips |
| `narrative.paragraphs[]` (1–2 entries, ≤ 320 chars each) | `NarrativeAnswer` | ✅ length cap enforced server-side |
| `evidence_videos[3]` | `GenericEvidenceGrid` | ✅ |
| `sources[]`, `related_questions[]` | right-rail | ✅ |

### PatternPayload subreports (§A.4 case 3)

| Schema field | Consumer | Status |
|---|---|---|
| `subreports?.timing` (`TimingPayload`) | `PatternSubreports` → `TimingBody` | ✅ |

---

## Backend invariants

- **Narrative length cap.** `cap_paragraphs` enforces 2 entries × 320
  chars, truncating at the last sentence boundary. Over-cap input logs
  `[generic-truncated]`. Covered by `test_cap_paragraphs_*` (4 tests).
- **Always low confidence.** `build_generic_report` pins
  `intent_confidence = "low"` and `niche_scope = None` regardless of the
  caller's `niche_id`. Covered by `test_build_generic_report_never_sets_niche_scope`.
- **Always free.** Per C.0.5 credit rule, `answer_session.append_turn`
  skips `decrement_credit` for `kind == "generic"`; C.5 doesn't change
  that path. Confirmed against `answer_session.py:100-104`.
- **OffTaxonomy suggestions are immutable returns.** `build_off_taxonomy_payload()`
  returns a deep copy; mutating the returned dict doesn't poison the
  static constant. Covered by
  `test_off_taxonomy_suggestions_are_copies_not_references`.
- **Multi-intent merge failure isolation.** Timing subreport failure
  drops to `subreports = null`; primary Pattern payload still ships.
  Covered by `test_build_pattern_report_timing_subreport_failure_does_not_abort_primary`.

---

## Must-fix

None.

## Should-fix (Phase D / polish)

1. **Gemini narrative is opportunistic.** `report_generic_gemini.
   fill_generic_narrative` falls back to deterministic hedging copy on
   any error. In production, wire the `gemini_text_only` call to the
   same budget guard Pattern uses (`ClassifierDailyBudgetExceeded`) so
   the Generic turn has an explicit free-tier path.
2. **`format_emphasis` for §A.4 case 2.** Deferred per plan footnote
   ("Pattern builder reads `_intent_type` today"). Would require
   classifier returning `format_emphasis` field + Pattern builder
   reading it to bias `findings[]` weighting.
3. **Stronger destination + report coupling (§A.4 case 1).** Today the
   destination screen shows its standard ActionCards; a "5 hook
   variants cho video này" card keyed on `?action=ideas` query param
   would tighten the merge UX. Scoped to Phase D.

## Consider

- **OffTaxonomyBanner chip hover state.** Currently borders ink on
  hover. Could promote to accent to match Pattern/Ideas conventions if
  dogfood prefers a stronger affordance.
- **Evidence tile count.** 3 matches reference; if corpus sparse, we
  could degrade to 1–2 tiles with a "mở rộng thời gian" hint. Acceptable
  today because the backend always pads to 3 via the fixture.

---

## Sign-off

C.5.1 `report_generic.py` real aggregator + `report_generic_compute.py`
helpers + `report_generic_gemini.py` hedging prompt + C.5.2 frontend
body (4 primitives) + C.5.3 multi-intent merge (detection + builder +
PatternSubreports wrapper) + C.5.4 token audit + C.5.5 smoke = all
green. Ready to close C.5 and open C.6 (/history restyle).
