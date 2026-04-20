# Phase D — Hardening, scale, and Phase B/C carryovers

Phase D adds **no new user-facing surfaces and no new features**. Every
milestone either closes a tech-debt item from Phase B (the C.8 carryovers
tracked in `artifacts/qa-reports/phase-c-closure.md` "Open follow-up"),
wires observability that Phase C deferred, or runs a systematic
end-to-end review across every shipped surface to verify the new UIUX
pivot actually holds up in production.

**Hard stop at Phase D.** No Phase E is currently scheduled. Commerce /
Ship Next / loop closure / long-form strategy, the three feature-shaped
creator intents (`comparison`, `series_audit`, `own_flop_no_url`), and
the layout revamps for the three still-legacy screens (`/app/trends`,
`/app/settings`, `/`) all stay deferred indefinitely — see
"Deliberately deferred (indefinite — no Phase E scheduled)" below. The
Phase D direction is **make everything already on main work well**;
anything that adds a new payload kind, new route, new intent handler
layout, or new report format is out of scope.

The canonical backlog reference is `artifacts/qa-reports/phase-c-closure.md`
(the "Open follow-up (C.8 carryovers — Phase D backlog)" table + the
"Outstanding Phase D items" list of 10 polish items, which mirror the
"Should-fix (Phase D)" sections of the six `phase-c-design-audit-*.md`
reports). Do not delete that file; this plan organises and timelines the
work it catalogued. The B-side carryover list in
`artifacts/qa-reports/phase-b-closure.md` "Open items carried into
Phase C" matches the C.8 scope 1:1 — D.1 closes both.

**Design source of truth**: same as Phase C —
`artifacts/uiux-reference/screens/{answer,thread-turns,channel,script}.jsx`,
`artifacts/uiux-reference/styles.css`. The only new primitives allowed
in D are the ones D.1 needs to close B carryovers: `PostingHeatmap`
(D.1.4), `ScriptSaveControls` + `ScriptShootScreen` (D.1.1). **No new
top-level routes. No new report payload kinds. No new intent handler
layouts.** The three tracked-but-unimplemented layout references
(`trends.jsx`, `SettingsScreen` block of `onboarding-settings.jsx`,
new-landing HTML files) are **not implemented** in D — their
corresponding live screens get a token-only swap in D.4 so the app-wide
`--gv-*` gate goes green, but JSX structure is frozen.

> **Non-negotiables that frame everything below** (carry forward from
> `phase-c-plan.md`):
> 1. The §J `ReportV1` data contract is the LLM-output contract. **No
>    breaking changes** to `answer_turns.payload` shape in D — additions
>    only (`Optional[...]` server-side, `field?:` client-side). UI is a
>    pure function of the payload; missing fields render humility state.
> 2. **TD-1 through TD-5** invariants stay intact (see `CLAUDE.md:85-95`):
>    TD-1 atomic credit deduction via `decrement_credit()`; TD-2 PayOS
>    webhook idempotency; TD-3 `profiles.is_processing` guard; TD-4 SSE
>    `stream_id`+`seq` 60s replay buffer (D.5.2 instruments drop-rate;
>    D.0.v decides Redis escalation); TD-5 credits granted upfront at
>    PAID webhook.
> 3. Every sub-phase closes only with a green design-audit report
>    (`artifacts/qa-reports/phase-d-design-audit-<subphase>.md`)
>    including the grep gate for raw hex / `--purple` / `--ink-soft` /
>    `--border-active` / `--gv-purple-*` / `Badge variant="purple"`.
> 4. Commits follow `AGENTS.md` — feature names: `feat(script-save): …`,
>    `feat(script-generate): …`, `feat(kol-match-persist): …`,
>    `feat(kol-growth): …`, `feat(channel-heatmap): …`,
>    `feat(token-purge): …`, `feat(observability): …`,
>    `feat(rls-audit): …`, `feat(answer-search): …`,
>    `feat(series-audit): …`, `feat(kol-compare): …`.
> 5. **Before any D behavior change ships to production, the D.0
>    measurement dashboard read (D.0.i) must be green** — Phase B + C
>    events emitting non-zero in production for 7 days. This is the
>    C.8.7 gate Phase C deferred; D inherits it as the ship-gate.

## Guiding principles

- **One sub-phase, one PR.** Atomic per milestone (aggregator +
  migration + tests + audit). Partial sub-phases don't ship.
- **Carryover, not redesign.** B-era specs in `phase-b-plan.md` §B.1–B.4
  are the source of truth for D.1.1–D.1.5 — D ships them, doesn't
  re-litigate.
- **Additions to §J only.** Pydantic `model_validator(mode="after")`
  keeps existing invariants (WhatStalled cap, `IdeasPayload.variant`
  enum, `GenericPayload.confidence.intent_confidence == "low"`).
- **Token gate non-negotiable.** Same grep as B and C audits. D.4
  closes the legacy namespace by phasing the purge across directories;
  until D.4.2 lands, **new code may not introduce legacy tokens**.
- **Phase E is named, not built.**

## Recommended order

| # | Sub-phase | Rationale |
|---|---|---|
| D.0 | Spike (5 sub-tasks) | Five hard prerequisites — measurement read, Gemini cost audit, token rebind map, PDF stack decision, SSE drop-rate eval. Single dedicated week. |
| D.1 | Phase B carryovers (parallel-safe) | Six atomic features, one per C.8 carryover. Original home: `phase-b-plan.md` §B.1–B.4. |
| D.2 | Phase C polish | Real RPC bodies for `pattern_wow_diff_7d` + `timing_top_window_streak`; missing events; `/history` pagination + cross-type search; budget guard + structured-output binding. |
| D.3 | **End-to-end review & closure** | Capstone QA pass. Seven streams: route coverage matrix, intent dispatch, report-format × edge cases, integration boundaries + TD invariants, copy + a11y, performance + bundle, fix-in-place. No new features. |
| D.4 | Token namespace deprecation + legacy-layout screen purge | Global `--gv-*` purge across **every** `src/**` file including the three legacy-layout surfaces (`/app/trends`, `/app/settings`, `/`) that never caught the Phase B/C pivot. Token-only for those three; the full layout revamps (`trends.jsx`, new `SettingsScreen`, new landing) are out of scope — deferred indefinitely with no Phase E scheduled. |
| D.5 | Observability + cost | Gemini cost dashboard, SSE drop instrumentation, RLS boundary audit, 90-day chat archival cron. |

Estimated **~8–9 weeks** with D.1 running parallel to D.2 and D.3. D.4
runs after D.1 to minimise merge churn against legacy-token consumers
D.1 doesn't otherwise touch. D.5 closes the phase.

**Hard stop at D.** No Phase E currently scheduled. Feature expansion
items previously marked "defer to Phase E" (new creator intents,
commerce, Ship Next, loop closure, long-form strategy, screen layout
revamps for trends/settings/landing) stay deferred indefinitely until
the roadmap explicitly opens a new phase. See "Deliberately deferred
(indefinite)" in Cross-cutting below.

---

## Pre-kickoff decisions (lock before D.0)

1. **C ship-gate is the D ship-gate** — D.0.i runs C.8.7 on day one.
2. **`ReportV1` additions only** — no field removals, no enum re-shapes,
   no `kind` discriminator changes.
3. **D.4 is sequential, not big-bang** — 38 legacy-token consumers as of
   2026-04-20; D.4.1 phases by directory, D.4.2 deletes defs last,
   D.4.3 adds the lint guard.
4. **Cost surface is the call site** — D.5.1 dashboard groups by
   `metadata.call_site`, not `model_name`.
5. **Hard stop at Phase D — no new features.** D.3 is an end-to-end
   review + fix-in-place pass, not a feature milestone. New creator
   intents (`series_audit`, `own_flop_no_url`, `comparison`), commerce,
   Ship Next, loop closure, long-form strategy, and the
   trends/settings/landing layout revamps all stay deferred
   indefinitely with no Phase E scheduled.
6. **D.4 legacy-layout purge is token-only.** `ExploreScreen.tsx`,
   `SettingsScreen.tsx`, `LandingPage.tsx` keep their existing JSX
   structure — only color tokens swap to `--gv-*`. Any commit that
   restructures these surfaces violates rule 5 and must revert.

---

## D.0 — Spike & pre-kickoff (1 week)

Resolve five hard prerequisites before D.1. Each sub-task ships a
written decision record under `artifacts/plans/`; D.0.6 locks the
decisions and unblocks downstream sub-phases.

### D.0.i — Measurement dashboard read (1d, gating)

Run the C.8.7 gate Phase C deferred. **This is the single ship-gate for
the entire phase.**

Confirm the following events are live in `usage_events` with non-zero
counts over a 3–7 day window:

- B set: `video_screen_load`, `flop_cta_click`, `video_to_script`,
  `kol_screen_load`, `kol_pin`, `script_screen_load`, `script_generate`,
  `channel_to_script`.
- C set: `answer_session_create`, `answer_turn_append`,
  `templatize_click`, `history_session_open`, `studio_composer_submit`.

If any event is missing or zero, file an issue and **block D.1+ deploys**
until resolved.

**Deliverable**: `artifacts/qa-reports/phase-d-d0-measurement-read.md`
with per-event 7-day counts + pass/fail + sign-off date.

### D.0.ii — Gemini cost audit (1.5d)

~4 Gemini call sites per paid `/answer` turn: `intent_classifier`
(`gemini.py:586`), `pattern_narrative` (`report_pattern.fill_pattern_
narrative`), `ideas_narrative` (deterministic today; opportunity per
`phase-c-design-audit-ideas.md` Should-fix #1), `generic_narrative`
(`report_generic_gemini.fill_generic_narrative`, falls open to
deterministic).

Spike work:
1. Sample 50 production `answer_turns` rows over 14d; pull matching
   Cloud Run logs; tally `[gemini-call] tokens_in/out` per call site.
2. Project monthly spend against the `CLAUDE.md` ~$70/mo Gemini ceiling.
3. Decide per call site whether to tighten via pydantic
   `response_format` binding (5-line change per site; `gemini.py`
   already uses `response_mime_type="application/json"` + manual
   `json.loads`).

**Deliverable**: `artifacts/plans/phase-d-gemini-cost-audit.md` —
per-call-site token spend + projected cost + tighten-or-leave decision.
Feeds D.2.5 and D.5.1.

### D.0.iii — Token dualism deprecation plan (1d, blocks D.4)

Inventory every consumer of the legacy token namespace. Run on
2026-04-20:

```
grep -rnE 'var\(--(purple|purple-light|ink-soft|border-active)\)|--gv-purple|variant="purple"' src/
```

→ **38 files.** Cluster by directory:

| Directory | File count | D.4.1 cluster |
|---|---|---|
| `src/components/ui/**` (Badge, Button, Card, Input) | 4 | D.4.1.a |
| `src/components/chat/**` | 9 | D.4.1.b |
| `src/components/explore/**` | 4 | D.4.1.c |
| `src/routes/_app/components/**` | 12 | D.4.1.d |
| `src/routes/_app/{checkout,pricing,settings,trends,history,learn-more,payment-success}/**` | 7 | D.4.1.e |
| `src/routes/_auth/**` | 2 | D.4.1.f |
| `src/app.css` (legacy defs) | 1 | D.4.2 |

Produce a **rebind map** in `artifacts/plans/phase-d-token-rebind-map.md`:

| Legacy | Replacement | Notes |
|---|---|---|
| `--purple` | `--gv-accent` | Verify per consumer; some are decorative not semantic |
| `--purple-light` | `--gv-accent-soft` | |
| `--ink-soft` | `--gv-ink-3` | C.6 audit confirmed 1:1 |
| `--border-active` | `--gv-rule` (or `--gv-ink` for emphasised) | Per-consumer judgment |
| `Badge variant="purple"` | `Badge variant="default"` after D.4.1.a | |

### D.0.iv — PDF rendering stack decision (0.5d, blocks D.1.1)

Decide WeasyPrint vs ReportLab vs server-side React.

| Option | Bloat | Notes |
|---|---|---|
| **A. WeasyPrint** | ~50MB Pango/Cairo | Best Vietnamese typography fidelity. C.8.1 default. |
| **B. ReportLab** | ~5MB pure Python | Vietnamese diacritics need explicit font registration. |
| **C. Server-side React** | needs Node sidecar | Rejected unless A and B fail. |

Default: **Option A (WeasyPrint).** Spike validates Cloud Run image
build + Vietnamese diacritic render. Fallback per C.8.1: if both A and
B fail, ship Copy-only and disable PDF with `title="Sắp có"`.

**Deliverable**: `artifacts/plans/phase-d-pdf-stack-decision.md` —
chosen stack + image-bloat measurement + sample render + dep entries
for `cloud-run/pyproject.toml` + `Dockerfile`.

### D.0.v — Cross-pod SSE replay evaluation (0.5d, conditional D.5.2 trigger)

`phase-c-plan.md` C.0.5 said "if measured drop-rate on `/answer/
sessions/:id/turns` exceeds 2% post-ship, promote to a Redis-backed
buffer in Phase D" — D.0.v is where that escalation decision gets made.

Spike work:
1. Read `[stream-resume]` log lines from `cloud-run/getviews_pipeline/
   session_store.py` for the last 14d; count cross-pod misses.
2. If miss-rate > 2%, draft the Upstash Redis promotion plan (cost +
   sizing). Implementation is **not** Phase D unless explicitly added
   as D.5.2.b.
3. If ≤ 2%, document the no-op decision; D.5.2 still ships the
   instrumentation.

**Deliverable**: `artifacts/plans/phase-d-sse-replay-decision.md`.

### D.0.6 — Spike close-out (1d)

Four deliverables shipped to `artifacts/plans/` + D.0.i measurement
read green + this doc updated. Three additional locks:

- **Migration sequencing** — D stamps bump from the latest on-main
  stamp; D.1.1 (`draft_scripts`), D.1.3 (`match_score`), D.2.3
  (`usage_events_d2`), D.2.4 (GIN index), D.5.1 (`gemini_calls`), D.5.4
  (`chat_archival_audit`) get sequential stamps assigned here.
- **Token additions in `src/app.css`**: none expected; D.4 only
  removes. If a `--gv-*` gap surfaces during D.4.1, add it in the
  matching cluster commit.
- **§J extension policy** restated in
  `artifacts/docs/answer-session-contract.md` — `Optional[...]` /
  `field?:` / humility render / pydantic invariants intact.

---

## D.1 — Phase B carryovers (~3 weeks; parallel-safe)

One milestone per C.8 carryover from `phase-c-closure.md`. Six atomic
commits, one per carryover (`feat(<feature>): …`). Can run in parallel
with D.2 and D.3 — only shared files are `src/lib/api-types.ts` and
`cloud-run/getviews_pipeline/report_types.py` (additions only).

### D.1.1 — `draft_scripts` + script save + Copy / PDF / Chế độ quay (1w)

Closes C.8.1. Spec per `phase-c-plan.md` C.8.1 verbatim — table shape,
RLS, endpoints (`POST /script/save`, `GET /script/drafts`, `GET
/script/drafts/:id`, `POST /script/drafts/:id/export`), frontend wiring
unchanged.

**D-era addition (from D.0.iv):** WeasyPrint dep lands in
`cloud-run/pyproject.toml` + `Dockerfile` system-package line in the
same PR as `POST /script/drafts/:id/export`. **New screen (< 200 LOC):**
`src/routes/_app/script/shoot/route.tsx` + `ShootScreen.tsx` — read-only
single-draft view, mobile-friendly, lazy-loaded.

**Measurement:** `script_save` (deferred B.4 event) goes live.
**Closure:** `phase-d-design-audit-script-save.md` + token gate +
`smoke-script-save.sh`. Commit: `feat(script-save): persistence + export controls`.

### D.1.2 — Gemini upgrade to `POST /script/generate` (3d)

Closes C.8.2 (originally B.4 deferred). HTTP contract **frozen**;
pytest re-uses `cloud-run/tests/test_script_generate.py` shape
assertions. Internal swap from deterministic scaffold to Gemini-bounded
scene generation inside `script_generate.py`.

D.0.ii cost audit may flag this as a `response_format` binding
candidate; if so, do the binding in the same PR.

`smoke-script-generate.sh` runs before/after — re-runs the B.4 smoke
pre/post Gemini swap per `phase-c-plan.md` C.8.2.

Commit: `feat(script-generate): Gemini upgrade with frozen contract`.

### D.1.3 — KOL `match_score` persistence (2d)

Closes C.8.3 (originally B.2 carryover). Spec per `phase-c-plan.md`
C.8.3 verbatim — add nullable `match_score INTEGER` +
`match_score_computed_at TIMESTAMPTZ` to `creator_velocity` (migration
scaffolded as `20260430000006_creator_velocity_match_score.sql` in C.0).
`kol_browse.py` reads cached score when fresh (< 7d), recomputes on
miss. Cache invalidates on `profiles.primary_niche` /
`profiles.reference_channel_handles` change via Postgres trigger.

Pytest extension: `test_kol_browse.py` adds 3 cases (cache hit, miss
recompute, trigger invalidation). `smoke-kol-match-persist.sh`: pin →
assert `match_score_computed_at IS NOT NULL` within 2s + identical
second-call score without recompute log.

Commit: `feat(kol-match-persist): cache match_score in creator_velocity`.

### D.1.4 — `PostingHeatmap` for `/channel` (3d)

Closes C.8.4 (originally B.3 deferred — specced in `phase-b-plan.md`
B.3 line 813). Reuses `TimingHeatmap` from C.4 with `cell.color`
swapped to single-hue ramp on `var(--gv-ink)` (no accent — distinguishes
from Timing format). Drops below `THỜI GIAN POST` KPI on `/channel`
with `marginTop: 24`.

**Backend:** `channel_analyze.py` adds `posting_heatmap[7][8]` from
`video_corpus.created_at` aggregation. Schema extension on
`ChannelAnalysisPayload` (additions only).

**Frontend primitive:** `src/components/v2/channel/PostingHeatmap.tsx`
— ~80 LOC, vitest covers cell tone classification.

`smoke-channel-heatmap.sh`: assert `posting_heatmap` is `7×8 number[][]`.

Commit: `feat(channel-heatmap): wire PostingHeatmap on /channel`.

### D.1.5 — Real 30d growth wiring (2d)

Closes C.8.5 (originally B.2 deferred). Switch `kol_browse.py` from the
`growth_percentile_from_avgs` proxy to the real
`creator_velocity.growth_30d_pct` column; backfill nulls with the
proxy; log per-row decisions in `[kol-growth]`.

Pytest extension: `test_kol_browse.py` adds 2 cases (real column read,
fallback-to-proxy with log assertion).

Commit: `feat(kol-growth): switch to real 30d growth from creator_velocity`.

### D.1.6 — Primitive render test backfill (3d)

Closes C.8.6. Five primitive render tests + two screen-level RTL tests
(~200 LOC) per `phase-c-plan.md` C.8.6 verbatim:

| Test | Surface |
|---|---|
| `ScriptPacingRibbon.test.tsx` | `src/components/v2/script/ScriptPacingRibbon.tsx` |
| `SceneIntelligencePanel.test.tsx` | `src/components/v2/script/SceneIntelligencePanel.tsx` |
| `MiniBarCompare.test.tsx` | `src/components/v2/script/MiniBarCompare.tsx` |
| `HookTimingMeter.test.tsx` | `src/components/v2/script/HookTimingMeter.tsx` |
| `DurationInsight.test.tsx` | `src/components/v2/script/DurationInsight.tsx` |
| `ChannelScreen.test.tsx` | `src/routes/_app/channel/ChannelScreen.tsx` |
| `ScriptScreen.test.tsx` | `src/routes/_app/script/ScriptScreen.tsx` |

Pure input renders + key DOM assertions. No mocking beyond TanStack
Query test wrappers.

Commit: `test(phase-b-backfill): primitive + screen-level render tests`.

### D.1 milestones (rolled up)

| # | Carryover | Estimate | Commit |
|---|---|---|---|
| D.1.1 | `draft_scripts` + script save + Copy/PDF/Chế độ quay | 1w | `feat(script-save): persistence + export controls` |
| D.1.2 | Gemini upgrade to `/script/generate` (frozen contract) | 3d | `feat(script-generate): Gemini upgrade with frozen contract` |
| D.1.3 | KOL `match_score` persistence | 2d | `feat(kol-match-persist): cache match_score` |
| D.1.4 | `PostingHeatmap` for `/channel` | 3d | `feat(channel-heatmap): wire PostingHeatmap on /channel` |
| D.1.5 | Real 30d growth wiring | 2d | `feat(kol-growth): switch to real 30d growth` |
| D.1.6 | Primitive render test backfill | 3d | `test(phase-b-backfill): primitive + screen-level render tests` |

---

## D.2 — Phase C polish (~2 weeks)

Closes the 10 items from `phase-c-closure.md` "Outstanding Phase D
items" and the matching Should-fix sections of the C audits.

### D.2.1 — Real `pattern_wow_diff_7d` RPC body (3d)

Closes Outstanding item #2 (RPC stub returns zero rows). Per
`phase-c-plan.md` §C.2 the RPC reads from a `video_patterns`
materialized view (or equivalent aggregator over `niche_intelligence`
+ historical `video_corpus`).

Body: pull current week top-10 pattern ranks per niche from
`niche_intelligence`; pull prior week from a 7-day-lagged snapshot;
diff into `new_entries[]` / `dropped[]` / `rank_changes[]` per the
`WoWDiff` shape in `api-types.ts`.

Pytest: `test_pattern_wow_diff_rpc.py`. Cases: NEW, DROPPED, rank
change (+/-), empty diff. Frontend unchanged — `WoWDiffBand` already
renders `wow_diff` when non-empty.

Commit: `feat(pattern-wow-diff): real RPC body`.

### D.2.2 — Real `timing_top_window_streak` RPC body (3d)

Closes Outstanding item #1 + `phase-c-design-audit-timing.md`
Should-fix #1 (stub returns 0; fatigue band never triggers).

Body: count consecutive weeks `(niche_id, day, hour_bucket)` has held
its rank position over the last 8 weeks of `video_corpus.created_at`.
Returns `{ weeks_at_top: int }`.

Pytest: `test_timing_top_window_streak_rpc.py`. Cases: zero-week,
multi-week, week-boundary edge. Frontend unchanged — `FatigueBand`
already renders when `weeks_at_top ≥ 4`.

Commit: `feat(timing-streak): real RPC body`.

### D.2.3 — Wire missing measurement events (2d)

Closes Outstanding items #3 + #4 + `phase-c-design-audit-chat-deletion.
md` Should-fix #1.

| Event | Wired at | metadata |
|---|---|---|
| `classifier_low_confidence` | `cloud-run/getviews_pipeline/answer_session.append_turn` | `{intent_id, confidence_score}` |
| `pattern_what_stalled_empty` | Same site, fires when `payload.what_stalled.length === 0 && confidence.what_stalled_reason !== null` | `{niche_id, reason}` |

Migration: `<stamp>_usage_events_d2_events.sql` extends the allow-list
(same pattern as `20260430000007_usage_events_c1_answer.sql`). Pytest:
`test_classifier_budget.py` adds 2 cases.

Commit: `feat(observability): classifier + what-stalled events`.

### D.2.4 — `/history` IntersectionObserver pagination + cross-type search (4d)

Closes Outstanding items #5 + #6 + `phase-c-design-audit-history.md`
Should-fix #1 + #2.

**Pagination (D.2.4.a, 2d):** `useHistoryUnion` → `useInfiniteQuery`
with the existing `p_cursor` keyset. `HistoryScreen.tsx` mounts
`IntersectionObserver` on the last row; trigger `fetchNextPage()` when
intersecting + `hasNextPage`. Page size stays 50; no RPC changes.

**Cross-type search (D.2.4.b, 2d):** new migration adds GIN index on
`answer_sessions.title` + `answer_sessions.initial_q` (or `tsvector` if
`useSearchSessions` precedent uses one). Search OR's over
`chat_messages.content ILIKE` + `answer_sessions.title ILIKE` +
`answer_sessions.initial_q ILIKE`, RLS-bounded. Filter ribbon stays
disabled during search.

Vitest: `HistoryScreen.test.tsx` (D.1.6 ships the shell; D.2.4 extends
with pagination + search assertions).

Commit: `feat(answer-search): /history pagination + cross-type search`.

### D.2.5 — `ClassifierDailyBudgetExceeded` guard around Generic Gemini + `response_format` binding on Pattern (3d)

Closes Outstanding items #8 + #10 + `phase-c-design-audit-generic.md`
Should-fix #1.

**D.2.5.a — Generic budget guard (1d):** wrap
`report_generic_gemini.fill_generic_narrative`'s `gemini_text_only`
call in `try/except ClassifierDailyBudgetExceeded`, fall open to
deterministic with `[generic-budget]` log line. Same pattern as
`[classifier-budget]` from C.0.1.

**D.2.5.b — Pattern `response_format` binding (2d):** swap manual
`json.loads` in `report_pattern.fill_pattern_narrative` for pydantic
`response_format` binding (5-line change per `gemini.py` precedent).
Validates against existing pytest cases. If D.0.ii flagged Ideas /
Generic for binding too, ship those changes here.

Commit: `feat(observability): Generic budget guard + Pattern structured output`.

### D.2 milestones (rolled up)

| # | Item | Estimate | Commit |
|---|---|---|---|
| D.2.1 | `pattern_wow_diff_7d` real RPC body | 3d | `feat(pattern-wow-diff): real RPC body` |
| D.2.2 | `timing_top_window_streak` real RPC body | 3d | `feat(timing-streak): real RPC body` |
| D.2.3 | `classifier_low_confidence` + `pattern_what_stalled_empty` events | 2d | `feat(observability): classifier + what-stalled events` |
| D.2.4 | `/history` IntersectionObserver + cross-type search | 4d | `feat(answer-search): /history pagination + cross-type search` |
| D.2.5 | Generic budget guard + Pattern `response_format` | 3d | `feat(observability): Generic budget guard + Pattern structured output` |

---

## D.3 — End-to-end review & closure (~2 weeks)

**No new features.** This is the capstone QA pass that exercises every
user-facing surface, every classified intent, every integration
boundary, and the five documented invariants (TD-1 through TD-5). Any
drift between the plan and what actually works gets fixed in place
before Phase D closes.

Replaces the previously-planned "new creator intents" milestone (intent
#7 `comparison`, intent #8 `series_audit`, intent #9 `own_flop_no_url`
— all three reclassified as feature work and deferred indefinitely with
the Phase D hard stop; see "Deliberately deferred (indefinite)" below).

Seven parallel streams, each with its own evidence artifact. Phase D
does not close until every stream is green.

### D.3.1 — Route coverage matrix (2d)

Every `/app/*` route × four states (empty / loading / error / success)
hand-tested at 360 / 720 / 1100 / 1280 px. Covers:

- `/app` (Studio home), `/app/answer`, `/app/history`, `/app/history/
  chat/:sessionId` (legacy transcript viewer).
- `/app/video`, `/app/channel`, `/app/kol`, `/app/script` (four Phase B
  creator screens).
- `/app/settings`, `/app/trends`, `/app/onboarding` (post-C.7 legacy
  surfaces — see D.4 for token purge).
- `/app/learn-more`, `/app/pricing`, `/app/checkout`,
  `/app/payment-success`.
- `/login`, `/signup`, `/auth/callback` (auth flow).
- `/` (landing, pre-rendered).

**Deliverable:** `artifacts/qa-reports/phase-d-route-coverage.md` with
pass/fail per `(route, state, breakpoint)` cell. Any fail → must-fix
task under D.3.7.

### D.3.2 — Intent dispatch coverage (2d)

All 20 intents from `phase-c-plan.md` §A exercised end-to-end. Each
intent gets a Playwright or manual trace: Studio composer →
`detectIntent` (client) → `resolveDestination` → correct destination
screen OR `/answer` with the correct report `format`. Special
attention to the 11 intents newly classified in C.0.1 (plus the
three feature-deferred intents — `series_audit` / `own_flop_no_url`
/ `comparison` — all today fall through to nearest existing
destination per the Phase C audit; verify the fallback is not a
crash).

Regression pytest under `cloud-run/tests/test_intent_dispatch_e2e.py`
adds one case per intent that currently lacks coverage. `intent-router.
test.ts` extended to cover any misrouting surfaced.

**Deliverable:** `artifacts/qa-reports/phase-d-intent-coverage.md` —
20-row table with dispatch outcome + expected outcome + notes.

### D.3.3 — Report format × edge cases (2d)

Each of Pattern / Ideas / Timing / Generic tested against real Gemini
responses (not fixtures) across:

- Full corpus (sample_size ≥ per-format floor).
- Thin corpus (sample_size < floor) — confirms HumilityBanner + thin
  shapes render as specified.
- SSE mid-turn reconnect (TD-4) — kill the connection at `seq=3`,
  reconnect with `?resume_from_seq=3`, confirm replay.
- Credit=0 pre-check — confirms 402 fires before the stream opens and
  no `answer_turns` row is written.
- §J schema invariant violations (simulated malformed Gemini output) —
  confirms the pydantic boundary rejects them rather than persists.

**Deliverable:** `artifacts/qa-reports/phase-d-format-edge-cases.md`.

### D.3.4 — Integration boundaries + TD invariants (2d)

Each TD from `CLAUDE.md` exercised against a real data path:

- **TD-1 (atomic credit deduction):** double-click same "send" button
  → confirm only one `decrement_credit` call fires (RPC `WHERE credits
  > 0` guard); insufficient credits → 402.
- **TD-2 (PayOS webhook idempotency):** replay a `PAID` webhook with
  the same `event_id` → `processed_webhook_events` UNIQUE rejects the
  second write; no duplicate credit grant.
- **TD-3 (`is_processing` concurrent request guard):** confirm
  `cron-reset-processing` clears flags older than 5 min; manually set
  one, wait 6 min, verify cron clears.
- **TD-4 (SSE replay):** cross-pod reconnect (scale Cloud Run to 2
  instances, force connection to a different pod) — confirm graceful
  failure per C.0.5 acceptable-degradation note; single-pod reconnect
  replays.
- **TD-5 (credits granted upfront at PAID):** pay a test PayOS order;
  confirm credits land in `profiles.credits` before the webhook
  returns 200.

**RLS boundary audit:** read-access check for `answer_sessions`,
`answer_turns`, `chat_sessions`, `chat_messages`, `video_corpus` —
authenticated user cannot see another user's rows; service-role
writes work as expected; `video_corpus` INSERT is blocked by RLS for
client writes (batch-only path per CLAUDE.md).

**Deliverable:** `artifacts/qa-reports/phase-d-integration-boundaries.
md` + `phase-d-rls-audit.md`.

### D.3.5 — Copy + a11y pass (1d)

- Grep every `.tsx` under `src/` against `.cursor/rules/copy-rules.mdc`
  forbidden openers (`Chào bạn`, `Tuyệt vời`, etc.) and forbidden
  words (`bí mật`, `công thức vàng`, etc.). Expected hits: 0.
- Keyboard-nav every interactive surface (tab order, focus
  indicators, modal focus trap).
- `aria-label` on every icon-only button. Every `<img>` has `alt`.
- JetBrains Mono on all numerical data (credits, multipliers,
  corpus sizes).
- Heading hierarchy (`h1` → `h2` → `h3`) correct per screen.
- Touch-target check: every interactive element ≥ 44×44 px.

**Deliverable:** `artifacts/qa-reports/phase-d-copy-a11y.md`.

### D.3.6 — Performance + bundle (1d)

- `npm run build` size delta vs pre-C main; confirm `vite.config.ts`
  `manualChunks` still splits `react-vendor`, `react-router`,
  `@tanstack`, `@supabase`, `@radix-ui`, `lucide-react`, `motion`.
- Lighthouse on `/`, `/app`, `/app/answer?session=<id>` — LCP, CLS,
  TTI targets per CLAUDE.md mobile-first baseline.
- React Query `staleTime` audit across all `use*` hooks in
  `src/hooks/` — no accidental `0` that refetches per render.
- Bundle-size regression budget: > 10% delta on any single chunk →
  flag as must-fix.

**Deliverable:** `artifacts/qa-reports/phase-d-perf-bundle.md` with
Lighthouse scores + bundle sizes + regression deltas.

### D.3.7 — Fix-in-place (open-ended, ≤ 1w)

Every must-fix surfaced by D.3.1–D.3.6 gets a `fix(qa): d3-ISSUE-NNN`
commit with a regression test. Should-fix items get filed in
`artifacts/issues/` but don't block Phase D closure.

**Sign-off rule for D.3:** 0 must-fix items remaining across all six
streams. Any must-fix reclassification requires an explicit note in
`phase-d-end-to-end-review.md`.

### D.3 milestones (rolled up)

| # | Stream | Estimate | Deliverable |
|---|---|---|---|
| D.3.1 | Route coverage matrix | 2d | `phase-d-route-coverage.md` |
| D.3.2 | Intent dispatch coverage | 2d | `phase-d-intent-coverage.md` |
| D.3.3 | Report format × edge cases | 2d | `phase-d-format-edge-cases.md` |
| D.3.4 | Integration boundaries + TD invariants | 2d | `phase-d-integration-boundaries.md` + `phase-d-rls-audit.md` |
| D.3.5 | Copy + a11y | 1d | `phase-d-copy-a11y.md` |
| D.3.6 | Performance + bundle | 1d | `phase-d-perf-bundle.md` |
| D.3.7 | Fix-in-place (open-ended) | ≤ 1w | `fix(qa): d3-ISSUE-NNN` commits |

**Aggregate deliverable:** `artifacts/qa-reports/phase-d-end-to-end-review.md`
summarising all seven streams with a scored "app health" matrix.

---

## D.4 — Token namespace deprecation + legacy-layout screen purge (~1 week)

Closes `phase-c-plan.md` "Token namespace dualism" risk. Phased by
directory per D.0.iii (38 files as of 2026-04-20). Order matters
because `src/components/ui/Badge.tsx` is the lowest-level primitive;
updating it first stops route consumers inheriting `variant="purple"`
on contact.

**Three legacy-layout screens never caught the Phase B/C pivot** and
retain the pre-pivot design + legacy-token namespace. Phase D closes
them with a **token-only swap** (preserve existing layout, rebind
colors to `--gv-*`). The full layout revamps to match the tracked
UIUX references are feature work and stay deferred indefinitely (see
"Deliberately deferred (indefinite)" below).

| Legacy surface | Route | Current impl | Legacy-token hits (2026-04-20) | Tracked new layout ref |
|---|---|---|---|---|
| **Trends** (Phase A-era ExploreScreen) | `/app/trends` | `src/routes/_app/trends/ExploreScreen.tsx` | 17 | `artifacts/uiux-reference/screens/trends.jsx` |
| **Settings** (legacy design) | `/app/settings` | `src/routes/_app/settings/SettingsScreen.tsx` | 23 | `artifacts/uiux-reference/screens/onboarding-settings.jsx` (SettingsScreen block, lines 121-226) |
| **Landing** (pre-pivot HTML) | `/` (pre-rendered) | `src/routes/_index/LandingPage.tsx` | 34 | `artifacts/uiux-reference/Landing Page.html` + `Landing Page v1.html` |

**Total legacy-token hits across the three screens: 74**, accounting
for the bulk of the 38-file D.0.iii rebind-map inventory.

### D.4.1 — Phased consumer purge (4d, seven commits)

Per the cluster table in D.0.iii. Each cluster:

1. Apply the rebind map.
2. Run grep on the cluster directory; assert 0 hits.
3. Snapshot visual diff (Playwright `quick-actions` project) — no
   regression beyond intentional purple → accent re-tint.
4. Commit per cluster:
   - `feat(token-purge): src/components/ui` (Badge + primitives)
   - `feat(token-purge): src/components/chat` + `src/components/explore`
   - `feat(token-purge): src/routes/_app/components`
   - `feat(token-purge): src/routes/_app/{checkout,pricing,…}`
   - `feat(token-purge): src/routes/_auth`
   - **`feat(token-purge): legacy-layout screens`** — the three
     layout-frozen surfaces (`ExploreScreen.tsx`, `SettingsScreen.tsx`,
     `LandingPage.tsx`). Strictly token swap; **no JSX structure
     changes**. Rationale documented in the commit: the full layout
     revamps are feature work per the hard stop at Phase D.
   - **`feat(token-purge): onboarding (safety)`** — even though
     `OnboardingScreen` is dropped per CLAUDE.md, its route file
     (`src/routes/_app/onboarding/route.tsx`) may carry stray tokens.
     Zero-out or confirm route is unmounted.

`Badge.tsx` D.4.1.a alters `variant="purple"` to a dev-only
deprecation shim that emits `console.warn` + maps to `variant="default"`.

**Explicit scope boundary (D.4.1):** The rebind script edits `className`
/ `style` property values only. Any attempt to restructure layout,
add new primitives, or wire new behaviour inside the three
legacy-layout screens is **out of scope** — the commits must match
`git diff --stat` with 0 JSX element additions or removals.

### D.4.2 — Delete legacy defs from `src/app.css` (0.5d)

Run the workspace-wide grep:

```
grep -rnE 'var\(--(purple|purple-light|ink-soft|border-active)\)|--gv-purple|variant="purple"' src/ --exclude=src/app.css
```

If hits == 0, delete `--purple`, `--purple-light`, `--ink-soft`,
`--border-active` definitions from `src/app.css` (~18 lines per the
2026-04-20 grep). If > 0, file an issue and block D.4.2.

Commit: `feat(token-purge): remove legacy tokens from app.css`.

### D.4.3 — CI lint rule (1d)

Workspace-level lint rule fails on any `src/**/*.{ts,tsx,css}` containing
`--purple`, `--purple-light`, `--ink-soft`, `--border-active`, or
`Badge variant="purple"`. Implementation: `scripts/check-tokens.mjs`
invoked from `npm run typecheck` (or new `npm run lint:tokens`), wired
into the CI job that runs `npm run build` on PRs.

Acceptance: a deliberate test PR introducing `var(--purple)` fails CI;
removing the line passes.

Commit: `chore(ci): legacy token reintroduction guard`.

### D.4 risks

- **Visual regression on landing / login / checkout** (highest
  legacy-purple density). Per-cluster commits + Playwright snapshots
  per cluster make reverts surgical.
- **Designer asks for purple back.** Don't reintroduce `--purple`.
  Propose a documented `--gv-*` token (e.g. `--gv-billing-accent`) and
  gate through the rebind map.

---

## D.5 — Observability + cost (~1.5 weeks)

### D.5.1 — Gemini cost dashboard (3d)

Daily token spend by call site. New `gemini_calls` table:

```sql
CREATE TABLE gemini_calls (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  call_site   TEXT NOT NULL,             -- 'pattern_narrative', 'intent_classifier', …
  model_name  TEXT NOT NULL,
  tokens_in   INTEGER NOT NULL,
  tokens_out  INTEGER NOT NULL,
  cost_usd    NUMERIC(10, 6) NOT NULL,
  duration_ms INTEGER NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX gemini_calls_call_site_recent_idx
  ON gemini_calls (call_site, created_at DESC);

ALTER TABLE gemini_calls ENABLE ROW LEVEL SECURITY;
-- service-role insert only; admin-only select via service_role
```

**Backend wiring:** central helper in `cloud-run/getviews_pipeline/
gemini.py` wraps every `genai.generate_content`, extracts
`usage_metadata.{prompt_token_count, candidates_token_count}`, computes
cost from a constants table, async-inserts into `gemini_calls`. Every
existing call site gets the wrapper with an explicit `call_site` string.

**Measurement event:** `gemini_call` with
`metadata.{call_site, cost_usd, tokens_in, tokens_out, model_name}` —
the `gemini_calls` row insert summarised into `usage_events` for
dashboard joins.

**Dashboard:** lives in the existing analytics dashboard. Three panels:
daily spend by call site (stacked bar), top-10 spendiest sessions
(table), token-cost ratio per call site (line, trend over time).

Pytest: `test_gemini_helper.py` covers wrapper output + `call_site`
propagation + cost computation.

Commit: `feat(observability): Gemini cost dashboard`.

### D.5.2 — SSE drop-rate instrumentation on `/answer/sessions/:id/turns` (2d)

Closes the D.0.v output. Wire the drop-rate metric into `usage_events`:

| Event | Fires | metadata |
|---|---|---|
| `sse_drop` | Client-side SSE `onerror` | `{endpoint, session_id, last_seq, reason: "network"\|"abort"\|"server"}` |
| `sse_resume_attempt` | Reconnect issued with `?resume_from_seq=<n>` | `{endpoint, session_id, attempted_seq, cross_pod_likely}` |
| `sse_resume_success` | Payload received within 5s of resume | `{endpoint, session_id}` |

`useSessionStream` extends to log all three. Migration extends the
`usage_events` allow-list. **D.5.2.b (optional, +2d):** if D.0.v
escalated to Redis (cross-pod miss > 2%), the Upstash Redis promotion
ships here.

Commit: `feat(observability): SSE drop-rate instrumentation`.

### D.5.3 — RLS boundary audit (`answer_sessions` + `answer_turns` + `chat_sessions`) (2d)

Audit the `service_role` vs `authenticated` split. C.0.5 stipulates
"service-role inserts only" on `answer_turns`; verify in production:

1. Pull every Cloud Run write to the three tables over 14d via Supabase
   audit logs.
2. Assert every write was `service_role`-keyed; no `authenticated` writes
   to `answer_turns`.
3. Re-test RLS via Supabase MCP `execute_sql` with explicit `auth.uid()`
   swaps.
4. Gaps surface as `fix(qa): rls-d53-…` per `AGENTS.md`.

Deliverable: `artifacts/qa-reports/phase-d-rls-audit.md` with 14-day
write-key distribution + policy re-verification + remediation log.

Commit: `feat(rls-audit): answer_* + chat_* boundary audit`.

### D.5.4 — 90-day `chat_sessions` + `chat_messages` archival cron (1.5d)

Closes Outstanding item #7 + `phase-c-design-audit-chat-deletion.md`
Should-fix #3.

**Edge Function:** `supabase/functions/cron-chat-archival/index.ts` —
runs nightly (`0 3 * * *` UTC). For each `chat_sessions` row with
`updated_at < now() - INTERVAL '90 days'`:

1. Insert audit row into `chat_archival_audit`
   (`{session_id, message_count, archived_at}`).
2. Hard-delete the `chat_sessions` row (cascade deletes
   `chat_messages` per existing FK).

`phase-c-plan.md` §C.7 Data model pre-decided this — **no soft-delete
column re-add; cascade hard-delete is the contract.**

Migration: `<stamp>_chat_archival_audit.sql` (audit table only —
RLS service-role only). Pytest: `test_cron_chat_archival.py` covers
90-day boundary + audit-row shape + cascade.

Commit: `feat(observability): 90-day chat archival cron`.

### D.5 milestones (rolled up)

| # | Item | Estimate | Commit |
|---|---|---|---|
| D.5.1 | Gemini cost dashboard | 3d | `feat(observability): Gemini cost dashboard` |
| D.5.2 | SSE drop-rate instrumentation (+2d if Redis per D.0.v) | 2d | `feat(observability): SSE drop-rate instrumentation` |
| D.5.3 | RLS boundary audit | 2d | `feat(rls-audit): answer_* + chat_* boundary audit` |
| D.5.4 | 90-day chat archival cron | 1.5d | `feat(observability): 90-day chat archival cron` |

---

## Cross-cutting

### Things retired when Phase D lands

- **Legacy token namespace** — `--purple` / `--purple-light` /
  `--ink-soft` / `--border-active` defs removed from `src/app.css`
  (D.4.2); `Badge variant="purple"` removed (D.4.1.a + D.4.2); CI lint
  rule prevents reintroduction (D.4.3).
- **Stub RPC bodies** — `pattern_wow_diff_7d` (D.2.1) and
  `timing_top_window_streak` (D.2.2) ship real bodies.
- **Manual `json.loads` on Pattern Gemini narrative** — replaced by
  pydantic `response_format` binding (D.2.5.b).
- **Single-page `/history`** — `useHistoryUnion` → `useInfiniteQuery`
  (D.2.4.a).
- **Pre-existing test failures from C close** — `HomeScreen.test.tsx` /
  `test_session_context.py` cleanup picked up during D.1.6 backfill.
- **`chat_sessions` rows > 90d old** — hard-deleted by D.5.4 cron;
  metadata preserved in `chat_archival_audit`.
- **TD-4 cross-pod caveat** — either escalated to Upstash Redis
  (D.5.2.b) or formally accepted per D.0.v decision record.

### Deliberately deferred (indefinite — no Phase E scheduled)

The Phase D direction is **hard stop** — once D.0–D.5 close, no
follow-up phase is currently planned. Everything below stays deferred
until the roadmap explicitly opens a new phase. Call out here so
nobody mistakes the list for "Phase E backlog":

**Feature expansion (previously "Phase E" candidates):**

- **Commerce / TikTok Shop signals** — `phase-c-plan.md` §A.3 stub.
  Requires net-new TikTok Shop ingest.
- **Personalized Ship Next** — 3-card morning ritual; needs creator-
  channel ingest + personalization model.
- **Loop closure measurement** — `script_save → live post → views`
  instrumentation. Requires creator-channel ingest.
- **Long-form channel strategy report** — needs a new `kind:
  "strategy"` ReportV1 variant (first net-new payload kind since C).

**Creator intents that would have been D.3 (now end-to-end review):**

- **Intent #7 `comparison`** — KOL A vs B side-by-side on `/app/kol?
  mode=compare`. Classification + routing shipped in C.0.1; destination
  handler is a stub. Needs a `KolCompareView.tsx` primitive + new route
  param wiring.
- **Intent #8 `series_audit`** — multi-URL Pattern with `per_video[]`
  extension. Classification shipped; needs `PerVideoBreakdown.tsx` +
  `report_pattern.py` accepting `video_ids[]`.
- **Intent #9 `own_flop_no_url`** — graceful-degrade URL prompt on the
  `QueryComposer`. Classification shipped; needs composer prompt UX.

**Layout revamps for legacy-layout screens (D.4 ships token-only
swap; layout remains pre-pivot):**

- **`/app/trends`** revamp per `artifacts/uiux-reference/screens/
  trends.jsx`.
- **`/app/settings`** revamp per
  `artifacts/uiux-reference/screens/onboarding-settings.jsx`
  (SettingsScreen block).
- **`/` landing** revamp per `artifacts/uiux-reference/Landing Page.
  html` + `Landing Page v1.html`.

**Already dropped (not a gap):**

- **`OnboardingScreen`** — dropped per `CLAUDE.md` ("niche set inline
  on first ChatScreen session"). Route file may be removed in D.4.1
  onboarding-safety commit.

### Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| D.4 token purge regresses landing / checkout / pricing / trends / settings visuals (highest legacy-purple density — 74 hits across the three legacy-layout screens alone) | High | D.0.iii rebind map per consumer; D.4.1 phases by directory (seven atomic commits) for surgical reverts; Playwright snapshot per cluster; legacy-layout commit is token-only (0 JSX element additions/removals asserted against `git diff --stat`). |
| D.4 legacy-layout purge tempts someone to "just revamp while we're here" | Medium | Pre-kickoff rule 6 is the hard stop: any JSX structure change in `ExploreScreen.tsx` / `SettingsScreen.tsx` / `LandingPage.tsx` fails the Phase D sign-off. Layout revamps stay deferred indefinitely. |
| D.5.1 Gemini cost surprises (spend > `$70/mo` ceiling) | Medium | D.0.ii pre-sizes the surface; D.2.5.b binding tightens worst offenders before D.5.1 dashboard ships; existing `ClassifierDailyBudgetExceeded` throttles classifier path. |
| D.5.3 RLS audit surfaces `service_role` misuse on `chat_sessions` / `answer_turns` | Medium | Audit deliverable is the remediation log. Gaps → `fix(qa): rls-d53-…`. |
| D.1.1 PDF dep installation bloat (~50MB image growth) | Medium | D.0.iv spike validates pre-merge; ReportLab fallback if > 50MB; Copy-only fallback if both fail. |
| D.0.i measurement read fails | Medium | Gating — blocks D deploys until analytics fixed. **Do not bypass.** |
| D.3.1 `per_video[]` extension breaks `PatternPayload` consumers | Low | §J `Optional[...]` + `field?:`; existing renders no-op when absent; pydantic validators keep WhatStalled cap intact. |
| D.2.4 cross-type search GIN index locks the table | Low | `CREATE INDEX CONCURRENTLY`. RLS unchanged. |
| D.2.5.b binding rejects pre-D Pattern responses | Low | `test_report_pattern.py` locks the shape; binding falls open with `[pattern-narrative-bind-fail]` (same precedent as Generic). |
| D.5.4 archival cron deletes a chat user wanted to recover | Low | 90-day cliff is the Phase C contract; audit table preserves metadata for support recovery. |

### Measurement

New events ship across D sub-phases (via `src/lib/logUsage.ts` →
`usage_events`):

| Event | Sub-phase | Fires when |
|---|---|---|
| `script_save` | D.1.1 | `POST /script/save` returns 200; `metadata.{draft_id, source_session_id?}` |
| `classifier_low_confidence` | D.2.3 | Cloud Run classifier returns Generic fallback; `metadata.{intent_id, confidence_score}` |
| `pattern_what_stalled_empty` | D.2.3 | Pattern ships with `what_stalled = []` + reason; `metadata.{niche_id, reason}` |
| `gemini_call` | D.5.1 | Every wrapped Gemini call; `metadata.{call_site, cost_usd, tokens_in, tokens_out, model_name}` |
| `sse_drop` | D.5.2 | Client SSE `onerror`; `metadata.{endpoint, session_id, last_seq, reason}` |
| `sse_resume_attempt` | D.5.2 | Reconnect issued; `metadata.{endpoint, attempted_seq, cross_pod_likely}` |
| `sse_resume_success` | D.5.2 | Payload received within 5s of resume; `metadata.{endpoint, session_id}` |

Existing live events (per `phase-c-closure.md`) continue: B set +
`answer_session_create`, `answer_turn_append`, `templatize_click`,
`answer_drawer_open`, `history_session_open`, `studio_composer_submit`.

D.0.i confirms the existing set is non-zero in production for 7 days
**before** any D behavior change ships.

### Testing strategy

**Backend (`cloud-run/tests/`)** — ≥ 80% branch coverage on new D.1
aggregators (Phase C bar):

- `test_draft_scripts.py` (D.1.1) — save/list/get/export shape, PDF +
  Copy paths, RLS.
- `test_script_generate.py` extended (D.1.2) — shape assertions +
  Gemini binding fallback.
- `test_kol_browse.py` extended (D.1.3/D.1.5) — cache hit/miss, trigger
  invalidation, real 30d, proxy fallback.
- `test_channel_analyze.py` extended (D.1.4) — `posting_heatmap` 7×8.
- `test_pattern_wow_diff_rpc.py` (D.2.1) — NEW/DROPPED/rank-change/empty.
- `test_timing_top_window_streak_rpc.py` (D.2.2) — week-boundary streaks.
- `test_classifier_budget.py` extended (D.2.3) — event emission.
- `test_history_union.py` extended (D.2.4) — pagination cursor +
  cross-type search ranking.
- `test_report_pattern.py` extended (D.2.5) — binding fallback.
- `test_report_generic.py` extended (D.2.5) — budget guard.
- `test_intent_dispatch_e2e.py` (D.3.2) — one case per §A intent.
- `test_gemini_helper.py` (D.5.1) — wrapper, `call_site` propagation,
  cost computation.
- `test_cron_chat_archival.py` (D.5.4) — 90-day boundary, cascade,
  audit row.

**Frontend (vitest)**:

- `PostingHeatmap.test.tsx` (D.1.4); `ScriptShootScreen.test.tsx` +
  `ScriptSaveControls.test.tsx` (D.1.1); 5 v2/script primitives +
  `ChannelScreen.test.tsx` + `ScriptScreen.test.tsx` (D.1.6 backfill).
- `HistoryScreen.test.tsx` extended (D.2.4); `useSessionStream.test.tsx`
  extended (D.5.2); `intent-router.test.ts` extended (D.3.2 — one
  case per §A intent); `Badge.test.tsx` (D.4.1.a shim warning).

**Shell smokes** (`artifacts/qa-reports/`):
`smoke-script-save.sh` (D.1.1), `smoke-script-generate.sh` (D.1.2 —
re-runs B.4 pre/post Gemini swap), `smoke-kol-match-persist.sh`
(D.1.3), `smoke-channel-heatmap.sh` (D.1.4).

**D.3 end-to-end review deliverables** (replace what used to be D.3
feature smokes): `phase-d-route-coverage.md`, `phase-d-intent-coverage.md`,
`phase-d-format-edge-cases.md`, `phase-d-integration-boundaries.md`,
`phase-d-rls-audit.md`, `phase-d-copy-a11y.md`, `phase-d-perf-bundle.md`,
`phase-d-end-to-end-review.md` (aggregate).

**Mandatory design audit per sub-phase**: same gate as Phase C — token
grep hits **0 in new files**. After D.4.2 the gate extends to **0 in
`src/app.css`** for the legacy defs.

### Vietnamese copy / kicker discipline

Same rules as B and C. Agent-authored fixed strings introduced in D:

| Surface | String |
|---|---|
| `ScriptSaveControls` Lưu / Copy / PDF | `Lưu vào lịch quay` / `Sao chép kịch bản` / `Tải PDF` (`Sắp có` if PDF disabled) |
| `ScriptShootScreen` H1 | `Chế độ quay` |
| `PostingHeatmap` kicker | `LỊCH ĐĂNG GẦN ĐÂY` |

(The three strings previously planned for `KolCompareView`,
`PerVideoBreakdown`, and the `own_flop_no_url` composer prompt are
dropped — those surfaces stay deferred indefinitely per the hard stop.)

### Responsive breakpoints

Same as Phase C (1100 / 900 / 720 / 640 / 560). D ships no new screens;
new primitives drop into existing screen layouts and inherit parent
breakpoint behaviour. Manual QA at all five widths against the
reference JSX. Any layout break is a `must-fix` in the matching audit.

### Timeline

| Sub-phase | Estimate | Reason |
|---|---|---|
| D.0 spike | **1w** | 5 sub-tasks |
| D.1 Phase B carryovers | **3w (parallel-safe)** | 6 atomic commits; D.1.1 anchors with WeasyPrint dep + new `/app/script/shoot`; others ≤ 3d |
| D.2 Phase C polish | **2w** | 5 milestones; D.2.4 (`/history` infinite + cross-type) is largest at 4d |
| D.3 End-to-end review & closure | **2w** | 6 coverage streams (≤ 2d each) + ≤ 1w fix-in-place buffer. Open-ended tail bounded by "0 must-fix" sign-off rule. Replaces the previously-planned D.3 new-creator-intents work. |
| D.4 Token namespace deprecation + legacy-layout screen purge | **1w** | 7 cluster commits (up from 6) + lint rule; phased to minimise visual blast radius. Legacy-layout purge (trends / settings / landing) is strictly token-only. |
| D.5 Observability + cost | **1.5w** | 4 milestones; D.5.1 cost dashboard is largest at 3d (+ optional D.5.2.b Redis = 2d) |
| Design-audit buffer | **1w** | Audit round-trips per sub-phase |
| **Total** | **~8–9w** (D.1 in parallel with D.2 saves ~1.5w; D.3 runs sequentially after D.2 because it audits what D.1 + D.2 shipped) | Six atomic D.1 commits, one per carryover |

D.0.i is gating, not coding; consumes 0 dev time but must be green
before any D behavior change ships.

---

## Sign-off rules

A sub-phase is "shipped" when **all** hold (rules 1–7 carried over from
`phase-c-plan.md`; rule 8 is D-specific):

1. Code merged to `main` via per-milestone PRs.
2. Backend pytest passing (≥ 80% branch coverage on new aggregators).
3. Frontend vitest passing on new primitives.
4. Shell smoke green.
5. Design-audit report green (token grep gate at 0 in new files; after
   D.4.2 the gate extends to `src/app.css`).
6. Measurement event(s) confirmed live in production within 24h
   post-merge — emit a smoke event (test user, dummy session) and
   verify `usage_events`. Production smoke is the contract; no
   separate staging analytics surface.
7. Documentation updated (this plan, `api-types.ts`, audit reports,
   `artifacts/docs/answer-session-contract.md` for any §J extension,
   `phase-d-token-rebind-map.md` for any D.4 cluster).
8. **Before any D behavior change ships to production, the D.0
   measurement dashboard read (D.0.i) must be green.** Ship-gate is
   Phase B + C events emitting non-zero in production for 7 days. This
   is the C.8.7 gate Phase C deferred — D inherits it.

**A sub-phase is not "shipped" until every line above is true.** Phase
D is closure-complete when D.0 → D.5 are all signed off, the legacy
token namespace is fully removed from `src/app.css`, the CI lint rule
is in place, the Gemini cost dashboard is reading non-zero call sites,
and the SSE drop-rate metric has 7d of production data.

---

**Recommended next step:** kick off D.0 with the five spike sub-tasks
running in parallel. D.0.i (measurement read) and D.0.iii (token rebind
map) are the two hard prerequisites — D.0.i unblocks every D.1+
behavior change, D.0.iii unblocks D.4. D.0.ii / D.0.iv / D.0.v can
resolve in any order during the same week. After D.0 closes, D.1 / D.2
/ D.3 run in parallel; D.4 follows D.1 to minimise merge churn against
the legacy-token consumers D.1 doesn't otherwise touch; D.5 closes
the phase.
