# Phase C — closure

**Date:** 2026-04-20
**Plan:** `artifacts/plans/phase-c-plan.md` (§C.0–C.7)
**Verdict:** **GREEN** — Phase C core (C.0–C.7) is closure-complete. Studio composer + `/answer` research surface + 4 report formats + `/history` restyle + `/chat` deletion all shipped; §J data contract enforced at the schema boundary; token gate clean across every Phase C surface. C.8 (Phase B carryovers) is an explicit Phase D backlog — tracked but out of Phase C scope.

---

## Milestone matrix

| Sub-phase | Deliverable | Status | Design audit |
|-----------|-------------|--------|--------------|
| **C.0** Spike | Intent classifier v2, idea-directions decision, sample gates, width decision, `answer_sessions` + `answer_turns` migration, `--gv-danger` token | **Shipped** | n/a (spike close-out) |
| **C.1** `/answer` shell | `AnswerShell` + `QueryHeader` + `SessionDrawer` + `FollowUpComposer` + `TimelineRail` + `TemplatizeCard`; `useSessionStream` extracted; `QueryComposer` lifted from `home.jsx:211-260`; 5 Cloud Run endpoints; fixture aggregator | **Shipped** | `phase-c-design-audit-answer-shell.md` |
| **C.2** Pattern | `WhatStalled` non-negotiable (schema + compute + test + smoke); `ConfidenceStrip` / `WoWDiffBand` / `HookFindingCard` / `WhatStalledCard` / `HumilityBanner` / `PatternActionCards` / `PatternCellGrid` / `PatternMiniChart`; `pattern_wow_diff_7d` RPC; `fill_pattern_narrative` Gemini | **Shipped** | `phase-c-design-audit-pattern.md` |
| **C.3** Ideas | 5 primitives (`LeadParagraph` / `IdeaBlock` / `StyleCardGrid` / `StopDoingList` / `IdeasActionCards`); `IdeasBody` composer; `build_ideas_report` + thin + `hook_variants` paths; `niche_taxonomy.style_distribution` column | **Shipped** | `phase-c-design-audit-ideas.md` |
| **C.4** Timing | `TimingHeatmap` + `TimingHeadline` + `VarianceNote` + `FatigueBand` + `TimingActionCards`; `TimingBody` composer; `build_heatmap_grid` + `compute_top_windows` + `classify_variance`; `timing_top_window_streak` RPC (stub body, signature frozen) | **Shipped** | `phase-c-design-audit-timing.md` |
| **C.5** Generic + multi-intent | `OffTaxonomyBanner` + `NarrativeAnswer` + `GenericEvidenceGrid` + `GenericBody`; `cap_paragraphs` 2×320-char enforcement; `detect_pattern_subreports` + `PatternSubreports` wrapper for §A.4 Report+timing merge | **Shipped** | `phase-c-design-audit-generic.md` |
| **C.6** `/history` restyle | `HistoryFilterRibbon` (3-chip) + `HistoryRow` (unified TypePill) + full rewrite of `HistoryScreen`; `history_union` RPC drives all three filter states; `history_session_open` event per row | **Shipped** | `phase-c-design-audit-history.md` |
| **C.7** `/chat` deletion | `/app/chat` route unmounted; `ChatScreen.tsx` deleted; `BottomTabBar` swapped to Sparkles → `/app/answer`; `Destination` union excludes `"chat"`; `follow_up_unclassifiable` routes to `answer:generic`; `studio_composer_submit` event | **Shipped** | `phase-c-design-audit-chat-deletion.md` |

**C.8** (Phase B carryovers, ~3w per plan) — **not in Phase C scope**; tracked as Phase D backlog. See "Open follow-up (C.8)" below.

---

## §J data contract enforcement

The plan's "non-negotiable: UI is a pure function of the payload; missing fields render humility state, never silent holes" is enforced at the pydantic schema boundary in `cloud-run/getviews_pipeline/report_types.py`:

| Invariant | Site | Test |
|---|---|---|
| `PatternPayload` WhatStalled: `len(what_stalled) ∈ [2,3]` OR (`== 0` AND `confidence.what_stalled_reason != null`) | `report_types.py @model_validator(mode="after")` | `test_report_pattern.test_empty_stalled_without_reason_raises`, `test_what_stalled_cap_at_three`, `test_validate_and_store_rejects_invariant_violation`, `test_c22_what_stalled_acceptance_invariant` |
| `PatternPayload.what_stalled` capped at 3 entries | same validator | `test_what_stalled_cap_at_three` |
| `IdeasPayload.variant ∈ {standard, hook_variants}` | `Literal` type in pydantic | `test_report_ideas.test_envelope_rejects_unknown_variant_at_schema_boundary` |
| `TimingPayload.grid` is `list[list[float]]` 7×8 | pydantic shape + smoke assertion | `test_report_timing.test_fixture_timing_validates`, `smoke-answer-timing.sh` jq check |
| `TimingPayload.variance_note.kind ∈ {strong, weak, sparse}` | smoke script jq gate + `classify_variance` helper | `test_classify_variance_thresholds` + `smoke-answer-timing.sh` |
| `GenericPayload.narrative.paragraphs` ≤ 2 × 320 chars | server-side `cap_paragraphs` truncation + `[generic-truncated]` log | `test_report_generic.test_cap_paragraphs_enforces_2_entries`, `_truncates_on_sentence_boundary`, `_handles_unpunctuated_input` |
| `GenericPayload.confidence.intent_confidence == "low"` always | builder pins value regardless of caller | `test_report_generic.test_build_generic_report_threads_window_days_on_fallback` asserts, `_never_sets_niche_scope` |
| `HookFinding.contrast_against.why_this_won` ≤ 200 chars | `Field(max_length=200)` | pydantic-enforced |
| `HookFinding.insight` ≤ 200 chars | `Field(max_length=200)` | pydantic-enforced |
| `PatternPayload.subreports.timing` merge (§A.4) falls open on builder error | `_build_pattern_subreports` try/except → `subreports=None` | `test_multi_intent_merge.test_build_pattern_report_timing_subreport_failure_does_not_abort_primary` |

**Every §J payload either validates or fails the stream** — no silently-corrupt rows persist to `answer_turns.payload`.

---

## Test coverage

### Backend — `cloud-run/tests/` (37 test files, 411 cases)

New for Phase C:

| File | Tests | Covers |
|------|-------|--------|
| `test_answer_session_c12.py` | 5 | Session create + get + patch + idempotency-key + permission boundary (C.1.2) |
| `test_answer_session_list.py` | 3 | Drawer list + scope (30d / all) + keyset cursor (C.1) |
| `test_answer_turn_stream.py` | 4 | SSE streaming + resume_from_seq replay + TD-4 buffer + cross-pod degradation (C.0 close-gap) |
| `test_classifier_budget.py` | 3 | `ClassifierDailyBudgetExceeded` guard + deterministic fallback + `[classifier-budget]` log (C.0.1) |
| `test_adaptive_window.py` | 5 | 7d → 14d → 30d adaptive widening + per-format floors + `confidence.window_days` reporting (C.0.3) |
| `test_intent_layered_merge.py` | 7 | Client-side `detectIntent` + server-side `classify_intent_gemini` merge + 0.3 disagreement rule (C.0.1) |
| `test_report_pattern.py` | 13 | Fixture / thin / WoW merge / WhatStalled invariant / build path (C.2.1–C.2.2) |
| `test_report_ideas.py` | 16 | Fixture / thin / variant / hook_variants / window threading / ranking / compute helpers / schema boundary (C.3) |
| `test_report_timing.py` | 16 | Fixture / thin / fatigued / variance thresholds / bucket coverage / heatmap normalisation / single-sample drop / streak fail-open (C.4) |
| `test_report_generic.py` | 15 | Fixture / cap_paragraphs / off_taxonomy / pick_broad_evidence / build paths / always-low / always-free (C.5) |
| `test_multi_intent_merge.py` | 17 | `detect_pattern_subreports` keyword matching + 4 §A.4 merge cases (C.5.3) |
| `test_history_union.py` | 8 | Filter enum + ordering + cursor semantics + null safety + WHERE mirror (C.6.1) |

### Frontend — `src/**/*.test.{ts,tsx}` (17 files, 114 cases)

| File | Tests | Covers |
|------|-------|--------|
| `useSessionStream.test.ts` | 7 | SSE line buffer + payload delivery + onFinal callback + 402/429 gates + error tokens (C.1.0) |
| `QueryComposer.test.tsx` | 6 | Enter submits + Shift+Enter newline + empty blocks + URL chip + disabled (C.1.0) |
| `intent-router.test.ts` | 29 | `detectIntent` across all 18 fixed intents + `resolveDestination` + `planAnswerEntry` session-vs-redirect (C.0.1 + C.7) |
| (pre-existing) | 72 | Regression — unchanged by Phase C |

### Smoke scripts

| Script | Scope |
|---|---|
| `smoke-answer-shell.sh` | C.1 shell — session create/append/get; payload validates |
| `smoke-answer-pattern.sh` | C.2 — WhatStalled invariant + live SSE |
| `smoke-answer-ideas.sh` | C.3 — variant enum + 5/5/5 on full + 3/0 on thin |
| `smoke-answer-timing.sh` | C.4 — grid 7×8 + variance enum + lift↔kind consistency + fatigue_band shape |
| `smoke-answer-generic.sh` | C.5 + C.5.3 — generic invariants + Pattern+timing subreport merge |

---

## Token + design gate

Grep run across every Phase C surface:

```
grep -rnE 'var\(--purple\)|var\(--ink-soft\)|var\(--border-active\)|--gv-purple|variant="purple"|#[0-9a-fA-F]{3,8}|rgba?\(' \
  src/components/v2/answer/ src/routes/_app/answer/ src/routes/_app/history/ \
  src/components/v2/QueryComposer.tsx src/components/BottomTabBar.tsx
```

**Result: 0 hits.** Every color reference resolves through `--gv-*` tokens.

New design tokens introduced in Phase C:

- `--gv-danger: #B91C1C` (`src/app.css:326`) — Phase C.0.6 close-out; consumed by `WhatStalledCard` left border, `FatigueBand` note, history delete-icon color, GenericBody fallback pill.
- `--gv-forecast-primary-bg` — primary ActionCard forecast-row tint.
- `--gv-scrim` — modal scrim used by `SessionDrawer`.

---

## Measurement events live

Wired via `src/lib/logUsage.ts` → `usage_events` table (migration `20260430000007_usage_events_c1_answer.sql` allow-list extension):

| Event | Fires | Wired at |
|---|---|---|
| `answer_session_create` | `POST /answer/sessions` returns 200 | `AnswerScreen.tsx:139` |
| `answer_turn_append` | `POST /answer/sessions/:id/turns` finalises; `metadata.kind`, `metadata.format` | `AnswerScreen.tsx:158, 198` |
| `templatize_click` | TemplatizeCard Lưu button click | `TemplatizeCard.tsx:18` |
| `answer_drawer_open` | SessionDrawer open event | (wired in AnswerScreen container) |
| `history_session_open` | `/history` row click; `metadata.type ∈ {answer, chat}` | `HistoryScreen.tsx:167` |
| `studio_composer_submit` | Studio composer `onSubmit` | `HomeScreen.tsx:72` |

**Not yet wired** (Phase D — see "Open follow-up" below):

- `classifier_low_confidence` — emit when Gemini classifier drops to Generic fallback (plan §C.7.4).
- `pattern_what_stalled_empty` — emit when Pattern ships with `what_stalled = []` + `what_stalled_reason` set (plan §C.2.5). Low priority — schema invariant + humility UI already cover the user-facing risk; event is for corpus-coverage telemetry only.

---

## Retired / removed

- **`/app/chat` route + `ChatScreen.tsx` + `src/routes/_app/chat/`** — fully removed (C.1 + C.7).
- **`useChatStream` hook + test** — moved into `useSessionStream` during C.0 close-gap; `useChatStream.ts` + `useChatStream.test.ts` deleted from `src/hooks/`.
- **`SaveCard` component** — renamed to `TemplatizeCard` in C.1 (same visuals, new intent; wires to C.8.1 script_save when that carryover ships).
- **Quick-action grid entries for report intents** (`trend_spike` / `content_directions` / `brief_generation` / `hook_variants` / `timing` / `fatigue`) — pruned from home; replaced by the Studio composer as single entry point.
- **Measurement events `chat_classified_redirect` + `chat_legacy_override`** — never shipped (plan tier-2 revision dropped them alongside the chat-deletion hard cliff).

---

## Open follow-up (C.8 carryovers — Phase D backlog)

Plan §C.8 specifies 7 items. None are required for Phase C closure; each is a Phase B tech-debt item that can ship independently.

| # | Carryover | Plan estimate | Status | Notes |
|---|---|---|---|---|
| C.8.1 | `draft_scripts` + `script_save` + Copy/PDF/Chế độ quay | 1w | ⏸ Pending | Migration `20260430000005_draft_scripts.sql` landed in C.0 spike; endpoints + UI not wired. WeasyPrint vs ReportLab dep decision still open. |
| C.8.2 | Gemini upgrade to `POST /script/generate` | 3d | ⏸ Pending | HTTP contract frozen; swap internal deterministic scaffold for real Gemini call. |
| C.8.3 | KOL `match_score` persistence | 2d | ⏸ Pending | Migration `20260430000006_creator_velocity_match_score.sql` landed; wiring not complete. |
| C.8.4 | `PostingHeatmap` component for `/channel` | 3d | ⏸ Pending | Reuse `TimingHeatmap` with single-hue ramp + new RPC on `video_corpus.created_at`. |
| C.8.5 | Real 30d growth wiring | 2d | ⏸ Pending | Switch `kol_browse.py` from proxy to real `creator_velocity.growth_30d_pct`. |
| C.8.6 | Primitive render test backfill | 3d | ⏸ Pending | 5 primitives + 2 screen-level RTL per Phase B closure doc. |
| C.8.7 | 3–7 day measurement dashboard read | gating | ⏸ Open | Confirms existing Phase B events fire non-zero in production before any C-era behavior change ships. Run before C.8.1–C.8.5 endpoints light up. |

**Recommendation:** kick off C.8.6 (primitive render test backfill) and C.8.7 (measurement read) first — they're cheapest and de-risk the bigger items. Schedule C.8.1 (script_save) once the WeasyPrint/ReportLab spike lands.

---

## Outstanding Phase D items (not in plan §C.8)

Minor polish identified during C.2–C.6 audits, tracked here so they don't get lost:

1. **`timing_top_window_streak` RPC body is a stub** (returns 0). Fatigue band contract shipped; lights up when the real body lands.
2. **`pattern_wow_diff_7d` RPC body is a stub** (returns zero rows). `WoWDiffBand` hides cleanly on empty data.
3. **`classifier_low_confidence` event** — wire when needed (Phase D).
4. **`pattern_what_stalled_empty` event** — wire when needed (Phase D).
5. **`/history` IntersectionObserver pagination** — RPC supports keyset cursor; hook currently fetches 50-row pages without infinite scroll. Ship when a user's session count materially exceeds 50.
6. **Cross-type search on `/history`** — search is chat-only today; answer sessions aren't full-text indexed yet.
7. **90-day `chat_sessions` archival cron** — plan §C.7 note; hard-delete policy deferred.
8. **Generic Gemini budget guard** — `report_generic_gemini.fill_generic_narrative` falls through to deterministic copy on any error but doesn't explicitly reuse `ClassifierDailyBudgetExceeded`. Wire if Generic volume grows.
9. **Real Gemini copy for Ideas `angle` / `why_works` / `slides`** — deterministic templates ship today; Gemini upgrade is a Phase D polish pass.
10. **Gemini structured output for Pattern narrative** — prompts cap token counts and validate JSON manually; pydantic `response_format` binding could tighten later.

---

## Audit artifact inventory

| Screen / surface | Audit file |
|---|---|
| `/answer` shell | `phase-c-design-audit-answer-shell.md` |
| Pattern report | `phase-c-design-audit-pattern.md` |
| Ideas report | `phase-c-design-audit-ideas.md` |
| Timing report | `phase-c-design-audit-timing.md` |
| Generic + multi-intent | `phase-c-design-audit-generic.md` |
| `/history` restyle | `phase-c-design-audit-history.md` |
| `/chat` deletion | `phase-c-design-audit-chat-deletion.md` |
| **Phase C closure (this doc)** | `phase-c-closure.md` |

---

## Sign-off

Phase C is **closure-complete** for the research surface. The Studio composer + `/answer` surface with four typed report payloads + `/history` restyle + `/chat` deletion all shipped. §J data contract is enforced at the pydantic schema boundary; UI is a pure function of validated payloads. Token gate green across every Phase C surface. Backend: 411/411 pytest. Frontend: 114/114 vitest. No must-fix issues.

**Recommended next step:** run the C.8.7 measurement dashboard read against the live B events (7-day window) before opening any C.8 behavior changes. In parallel, pick up C.8.6 primitive render test backfill to bank cheap insurance.
