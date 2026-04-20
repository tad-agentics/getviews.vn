# Phase C.3 — Ideas report design audit

**Milestone:** C.3.5 (plan §C.3 milestones, p.1252–1264)
**Verdict:** **PASS** — ready to close C.3.

---

## Render order (plan §C.3 design spec)

`src/components/v2/answer/ideas/IdeasBody.tsx` composes the six sections in
the locked order:

1. `ConfidenceStrip` (reused from Pattern — same `N=… · window_days · niche_scope · freshness_hours` shape).
2. `HumilityBanner` (thin-sample only, `confidence.sample_size < 60`).
3. `LeadParagraph` — kicker `BRIEF` + title + 2–3 sentence serif body.
4. `IdeaBlock × N` — 5 on full corpus, 3 on thin corpus, 5 hook variants in
   variant mode. Layout: `60px | 1fr | 220px` grid with serif rank, title +
   tag/confidence row, angle, why_works (w/ citation sup), hook callout,
   slides accordion (6 rows collapsed behind chevron), prerequisites chips,
   metric block, style chip, evidence thumbs (up to 2).
5. `StyleCardGrid × 5` — 5-col desktop, 2-col ≤1100, 1-col ≤720.
6. `StopDoingList × 5` — 3-col grid (rank / bad+why / fix). Fix cell uses
   `--gv-accent-soft` + `--gv-accent-deep`. Suppressed in variant mode AND
   thin-corpus mode (empty array upstream; body hides on `length === 0`).
7. `IdeasActionCards × 2` — primary "Mở Xưởng Viết với ý #1" + secondary
   "Lưu cả 5 ý tưởng". Forecast row above CTA matches Pattern's contract.

Responsive parity with Pattern: grids collapse at 1100 / 900 / 720 stops; the
`IdeaBlock` 3-col grid drops to single-col on `<900`.

---

## Token grep gate

```
grep -rnE "var\(--purple\)|var\(--ink-soft\)|var\(--border-active\)|\
--gv-purple|variant=\"purple\"|#[0-9a-fA-F]{3,8}|rgba?\(" \
  src/components/v2/answer/ideas/
```

**Result: 0 hits.** All colors resolve through `--gv-*` tokens:
`--gv-ink`, `--gv-ink-2`, `--gv-ink-3`, `--gv-ink-4`, `--gv-canvas`,
`--gv-canvas-2`, `--gv-paper`, `--gv-rule`, `--gv-rule-2`, `--gv-accent`,
`--gv-accent-soft`, `--gv-accent-deep`, `--gv-forecast-primary-bg`.

Evidence thumbnails ship as neutral `--gv-canvas-2` placeholders — no
hardcoded hex tile colors. Users tap the tile to load the real thumbnail on
`/app/video?video_id=…`.

---

## §J data contract coverage

| Schema field | IdeasBody consumer | Status |
|---|---|---|
| `IdeasPayload.confidence` | `ConfidenceStrip` | ✅ |
| `IdeasPayload.lead` | `LeadParagraph.body` | ✅ |
| `IdeasPayload.ideas[]` (5) | `IdeaBlock` × 5 | ✅ |
| `IdeasPayload.style_cards[]` (5) | `StyleCardGrid` | ✅ |
| `IdeasPayload.stop_doing[]` (0 or 5) | `StopDoingList` | ✅ |
| `IdeasPayload.actions[]` (2) | `IdeasActionCards` | ✅ |
| `IdeasPayload.sources[]` | right-rail (`AnswerSourcesCard` via `ContinuationTurn`) | ✅ |
| `IdeasPayload.related_questions[]` | right-rail (`RelatedQs`) | ✅ |
| `IdeasPayload.variant` ∈ {`standard`, `hook_variants`} | `LeadParagraph` title swap + upstream suppression of `stop_doing` | ✅ |
| `IdeaBlockPayload.{id, title, tag, angle, why_works, hook, slides, metric, prerequisites, confidence, style, evidence_video_ids}` | `IdeaBlock` | ✅ all 12 rendered |

---

## Backend invariants

- `IdeasPayload.variant` enum is enforced at the pydantic schema boundary
  (`report_types.py:158`). Negative test
  `test_envelope_rejects_unknown_variant_at_schema_boundary` proves it.
- Empty-state contract: `sample_size < 60` → 3 ideas + no `stop_doing`
  (`build_thin_corpus_ideas_report`). Covered by `test_thin_corpus_reduces_to_three_ideas`.
- Variant suppression: `hook_variants` → `stop_doing = []` and 2–3 slide
  bullets per idea (`build_hook_variants_report`). Covered by
  `test_hook_variants_sets_variant_and_suppresses_stop_doing`.
- Live pipeline path (`build_ideas_report`): thin niche routes to
  thin-corpus fixture; full corpus returns 5 ideas with evidence ids joined
  from corpus. Covered by `test_build_ideas_report_thin_niche_routes_to_thin_fixture`
  + `test_build_ideas_report_full_corpus_returns_5_ideas`.

---

## Must-fix

None.

## Should-fix (Phase D / polish)

1. **Real Gemini copy for `angle` / `why_works` / `slides` bodies.** Current
   `compute_ideas_blocks` emits deterministic Vietnamese templates per hook
   family. The §J schema allows richer Gemini-bounded narrative (plan
   §C.3.2 "Gemini bounded per-field; cached"); mirror Pattern's
   `fill_pattern_narrative` helper when corpus volume warrants the cost.
2. **Evidence thumbnails — bg fallback.** `--gv-canvas-2` is a neutral
   placeholder. If Phase D adds `IdeaBlockPayload.bg_colors` or
   `evidence_thumbnails[]` with real TikTok thumbnail URLs, wire the tile
   background to load the real image.
3. **Slides accordion keyboard accessibility.** Button has `aria-expanded`
   but no `<details>` fallback. Consider `react-aria` accordion if the
   slides list grows to > 6 items per idea.

## Consider

- **`StyleCardGrid` 5-col at narrow desktop.** At 1100–1280 viewports the
  5-col grid squeezes card desc text. Could drop to 3-col in the 1100–1280
  band; acceptable today because 1280 is the platform canonical width
  (C.0.4 decision).
- **`IdeaBlock` rank color.** Plan §C.3 used `var(--ink-3)` for the serif
  rank; shipped uses `--gv-ink-3`. Same intent, different namespace
  (Phase B `--gv-*` convention). No action.

---

## Sign-off

C.3.1 aggregator (backend) + C.3.2 compute helpers + C.3.3 frontend body +
C.3.4 token audit + C.3.5 smoke = all green. Ready to close C.3 and open
C.4 (Timing).
