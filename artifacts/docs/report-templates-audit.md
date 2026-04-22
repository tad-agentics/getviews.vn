# Report Templates Audit — 2026-04-22

> **Question from the product lead:** *"I'm creating new report template formats with Claude Chat for the intents that are missing a template. Currently we only have 4 report templates — verify if it is correct."*

**Short answer:** Yes, 4 is correct. Verified at four layers of the stack. And the gap you're intuiting is real: **9 of the 13 answer-bound intents are force-fit into `pattern`**, which is the architectural root cause of the "every follow-up looks the same" bug.

---

## Decisions (2026-04-22, product lead)

After reviewing the first draft of this doc + the 6 reference designs from Claude Chat:

1. **The 6 reference designs are inspiration, not specs** — use them to shape new templates for intents that currently lack one. Do NOT rebuild the 4 existing templates to match the reference (they have production data shapes with real payload fields that the designs drop).
2. **Dropped intents:** `series_audit` and `comparison` are removed from the supported intent set.
3. **Dedicated screens, not Answer templates:** `video_diagnosis`, `metadata_only` → `/app/video`; `competitor_profile`, `own_channel` → `/app/channel`; `creator_search` → `/app/kol`; `shot_list` → `/app/script`. The reference designs for VideoDiagnosis and Channel can inspire UI polish on those dedicated screens but are **not** Answer-session templates.
4. **Merge into existing template:** `content_calendar` folds into `timing` (expanded TimingPayload gets calendar slots).
5. **New Answer templates needed:** 2 — `lifecycle` (serves `format_lifecycle_optimize` + `fatigue` + `subniche_breakdown`) and `diagnostic` (serves `own_flop_no_url`).

**Final count after this work:**
- 4 existing templates unchanged (pattern, ideas, generic) or expanded (timing gets calendar slots)
- 2 new Answer templates (lifecycle, diagnostic)
- = **6 Answer templates total**

The 4 dedicated screens (`/app/video`, `/app/channel`, `/app/kol`, `/app/script`) remain separate surfaces — not counted in the template total.

---

## The 4 templates — verified

Confirmed at every layer of the stack (a genuine contract, not drift).

| Layer | Artifact | Values |
|---|---|---|
| DB CHECK constraint | `supabase/migrations/20260430000000_answer_sessions.sql:11` | `format IN ('pattern', 'ideas', 'timing', 'generic')` |
| Pydantic envelope | `cloud-run/getviews_pipeline/report_types.py:183` | `ReportV1.kind: Literal["pattern", "ideas", "timing", "generic"]` |
| Backend payload models | `report_types.py:99 / 149 / 161 / 174` | `PatternPayload`, `IdeasPayload`, `TimingPayload`, `GenericPayload` |
| Frontend renderers | `src/components/v2/answer/{pattern,ideas,timing,generic}/` | `PatternBody`, `IdeasBody`, `TimingBody`, `GenericBody` |
| Frontend switch | `src/components/v2/answer/ContinuationTurn.tsx:26` | `switch (payload.kind)` — 4 cases |

The 4 templates are:

| Template | Payload shape (key fields) | What it visualises |
|---|---|---|
| **`pattern`** | `findings[]` (ranked hooks), `evidence_videos[]`, `patterns[]` (duration / hook_timing / sound_mix / cta_bars cells), `wow_diff`, `what_stalled[]` | Niche-level hook leaderboard + WoW shifts |
| **`ideas`** | `ideas[]` (IdeaBlock = hook + 6 slides + metric), `style_cards[]`, `stop_doing[]` | 5 shootable scripts with slide-by-slide |
| **`timing`** | `top_window`, `top_3_windows`, 7×8 `grid`, `variance_note`, `fatigue_band` | Heatmap of best posting windows |
| **`generic`** | `paragraphs[]`, `evidence_videos[]`, `off_taxonomy_suggestions[]` | Hedge narrative for off-taxonomy queries |

---

## The 19 intents — where each one lands

Source of truth: `src/routes/_app/intent-router.ts:51-71` (frontend) and `cloud-run/getviews_pipeline/gemini.py:585-605` (backend classifier). These lists should match but don't quite (see drift below).

### Routes AWAY from answer sessions (6 intents → dedicated surfaces, no template needed)

| Intent | Destination | Screen |
|---|---|---|
| `video_diagnosis` | `video` | `/app/video` |
| `metadata_only` | `video` | `/app/video` |
| `competitor_profile` | `channel` | `/app/channel` |
| `own_channel` | `channel` | `/app/channel` |
| `creator_search` | `kol` | `/app/kol` |
| `comparison` | `kol` | `/app/kol` |
| `shot_list` | `script` | `/app/script` |

(7 items in the table — `comparison` is the 7th; the 6-count is intents *unique* to dedicated surfaces.)

### Routes INTO answer sessions (13 intents, 4 templates)

| Intent | Destination | Current template | Good fit? |
|---|---|---|---|
| `trend_spike` | `answer:pattern` | **pattern** | ✅ |
| `content_directions` | `answer:pattern` | **pattern** | ✅ |
| `hook_variants` | `answer:ideas` | **ideas** (variant mode) | ✅ |
| `brief_generation` | `answer:ideas` | **ideas** | ✅ |
| `timing` | `answer:timing` | **timing** | ✅ |
| `follow_up_unclassifiable` | `answer:generic` | **generic** | ✅ |
| `subniche_breakdown` | `answer:pattern` | **pattern** (forced) | ❌ — needs segment/cluster shape |
| `format_lifecycle_optimize` | `answer:pattern` | **pattern** (forced) | ❌ — needs lifecycle curve (rising / peak / declining) |
| `fatigue` | `answer:pattern` | **pattern** (forced) | ❌ — needs hook-level fatigue signal, not niche hook ranking |
| `content_calendar` | `answer:pattern` | **pattern** (forced) | ❌ — needs calendar/timeline layout |
| `series_audit` | `answer:pattern` | **pattern** (forced) | ❌ — needs per-video progression, not niche ranking |
| `own_flop_no_url` | `answer:pattern` | **pattern** (forced) | ❌ — needs diagnostic shape, closer to `/app/video` flop mode |
| **`follow_up` / `follow_up_classifiable`** | dynamic | pattern / ideas / timing | see drift note |

**6 of 13 answer-bound intents are force-fit into `pattern`.** This is the root cause of "every follow-up looks the same" — the 6 intents all call `build_pattern_report()`, which aggregates ranked hooks for the niche regardless of the specific question.

### Drift between backend and frontend intent lists

Backend (`gemini.py:585-605`) has 19 labels; frontend (`intent-router.ts:51-71`) has 19 fixed ids but **the two lists don't perfectly overlap**.

| Label | Frontend | Backend | Notes |
|---|---|---|---|
| `find_creators` | — | ✓ | Frontend uses `creator_search`; backend uses `find_creators` — aliased? |
| `creator_search` | ✓ | — | — |
| `follow_up` | — | ✓ | Backend omnibus label |
| `follow_up_unclassifiable` | ✓ | — | Frontend's ambiguous-query label |

Pick one canonical name per concept. If `find_creators` and `creator_search` are the same thing, drop one; if different, document the split.

---

## What each missing template should probably be

If you're spec'ing new templates in Claude Chat, these are the semantics of the 5 intents currently mis-fit. For each I'll describe what the page needs to *show*, not the API shape — the Pydantic model falls out of that.

### 1. `format_lifecycle_optimize` — "is this format still working?"

**User asks:** *"Hook testimonial còn chạy được nữa không?" / "Format listicle có đang già không?"*

**Needs:**
- Lifecycle curve (x = weeks, y = avg views for the format) with phase labels (rising / peak / declining / dormant).
- Current position marker on the curve.
- A "refresh moves" list — how creators who stayed with the format past peak kept it working (twist / audio change / pacing change).
- Optional: comparable formats that succeeded the declining one.

**Why `pattern` doesn't fit:** PatternPayload has no time-series structure, and its `findings[]` ranks current winners — not "how is this one hook ageing."

### 2. `fatigue` — "is this hook burned out?"

**User asks:** *"Hook 'mình vừa test' còn hiệu quả không?"*

**Needs:**
- Single-hook focus (not a leaderboard).
- A burn-in signal: weeks at top, saturation % (how many active creators using it), view-per-instance decay.
- Alternatives: adjacent hooks that haven't peaked yet.

**Why `pattern` doesn't fit:** PatternPayload ranks hooks against each other. Fatigue is orthogonal — a hook can be #1 AND fatigued (that's the whole point).

**Note:** `TimingPayload` has a `fatigue_band` field but it's window-level (Thứ 7 18h is tired), not hook-level. Could be unified under a `FatigueSignal` component reused by both.

### 3. `content_calendar` — "give me a posting plan for next week"

**User asks:** *"Lên giúp lịch post 7 ngày tới cho kênh mình."*

**Needs:**
- A 7×N grid (day × post-slot) with idea chips assigned to each cell.
- Slot-level hooks + reasoning (why this hook on Wednesday vs Friday).
- Optional: a "gap analysis" showing which themes aren't yet in the plan.

**Why `pattern` doesn't fit:** it has no temporal layout. `timing` has a heatmap but it's engagement-only — no slot assignments or content attachment.

### 4. `series_audit` — "look at my last N videos and tell me what's drifting"

**User asks:** *"Xem 10 video gần nhất của mình, có đang lạc tone không?"*

**Needs:**
- Per-video cards ordered by time (not by performance) with consistency scores (tone / hook family / visual style / caption length).
- Drift detection: highlight the video where the style broke.
- Recommendation: re-anchor to which winning pattern.

**Why `pattern` doesn't fit:** PatternPayload is niche-wide, not creator-specific. It has no sequence axis.

### 5. `subniche_breakdown` — "break my niche into segments"

**User asks:** *"Trong skincare, có những ngách con nào đang nổi?"*

**Needs:**
- Cluster cards (acne / anti-aging / hydration / teen-skin / …) with per-cluster size, growth rate, top hook.
- Overlap map (Venn-style: which clusters share creators?).
- Entry recommendation: which cluster fits the user's channel best.

**Why `pattern` doesn't fit:** it treats the niche as one pool. You'd need a clustering pass that PatternPayload doesn't expose.

### 6. `own_flop_no_url` — "my last video flopped, diagnose blind"

**User asks:** *"Video tuần trước mình flop nhưng không còn link, nói chung mình làm sai gì?"*

**Needs:**
- Closest to `/app/video` flop-mode diagnosis, but without the corpus row.
- Common-failure checklist (weak hook / generic CTA / off-niche audio / wrong duration / …) scored on what the user described.
- "To diagnose properly, paste the link" CTA.

**Why `pattern` doesn't fit:** pattern shows winning hooks, not failure checklists. This intent is closer to `GenericPayload` (free-form hedge) than to any current template.

---

## Finalised scope (replaces the earlier recommendation)

Per the decisions at the top of this doc, the implementation plan is:

### New Answer templates to build

| # | Template | Serves intents | Reference design | Why new (not fold into existing) |
|---|---|---|---|---|
| 1 | **`lifecycle`** | `format_lifecycle_optimize`, `fatigue`, `subniche_breakdown` | Claude Chat's "Report 6: FORMAT" | Decay / cluster visualisation — no time-axis in `pattern`, no grouping in any existing template. |
| 2 | **`diagnostic`** | `own_flop_no_url` | Claude Chat's "Report 4: VIDEO DIAGNOSIS" (scoped — no URL input) | 5-part score + fix prescription shape doesn't fit any existing template; reusing `generic` would flatten it to paragraphs. |

### Expand an existing template

| Template | Change | Serves intents |
|---|---|---|
| `timing` | Add `calendar_slots[]` (7-day post plan) below the heatmap | `timing`, `content_calendar` |

### Intents dropped entirely

- `series_audit` — removed from supported intent set. Update `intent-router.ts` and `GEMINI_CLASSIFIER_PRIMARY_LABELS` simultaneously.
- `comparison` — removed. Already routed to `/app/kol`; now explicitly unsupported.

### Intents on dedicated screens (not Answer templates)

Reference designs can inspire UI polish on these screens but are out of scope for the Answer-templates work:

| Intent | Screen |
|---|---|
| `video_diagnosis`, `metadata_only`, `own_flop_no_url` (partial — when URL is known) | `/app/video` |
| `competitor_profile`, `own_channel` | `/app/channel` |
| `creator_search` | `/app/kol` |
| `shot_list` | `/app/script` |

### Existing 4 templates — untouched in this phase

`pattern`, `ideas`, `timing` (core), `generic` keep their production payload shapes. The reference designs have some nice UI details (lifecycle pills on pattern findings, per-idea metric badges) that can come in via incremental UI work, but the backend shapes stay stable so migration surface is bounded.

### Final count

**6 Answer templates** (4 existing + 2 new) + 4 dedicated screens = the full intent coverage.

---

## Update checklist when you add a new template

Adding a template touches 5 layers — missing any one of them causes the "payload kind unknown" diagnostic banner (`ContinuationTurn.tsx:60-86 UnknownPayloadSurface`). In order:

1. **Migration** — extend the CHECK constraint on `answer_sessions.format` to include the new literal. No existing rows to migrate — the enum only gates new sessions.
2. **`cloud-run/getviews_pipeline/report_types.py`** — add a new `XxxPayload(BaseModel)`, add its literal to `ReportV1.kind`, add the branch to `validate_and_store_report`.
3. **Backend builder** — new module `report_xxx.py` with `build_xxx_report(niche_id, query, …)`, plus `report_xxx_gemini.py` for the query-aware narrative (see pattern set by `report_timing_gemini.py` + `report_ideas_gemini.py` in batch-3).
4. **Dispatcher** — add the new format to `cloud-run/getviews_pipeline/answer_session.py:select_builder_for_turn` + the dispatch `if` chain in `append_turn`.
5. **Frontend** — new `src/components/v2/answer/xxx/XxxBody.tsx`, add a case to `ContinuationTurn.tsx` switch, add the literal to `AnswerSessionFormat` in `src/routes/_app/intent-router.ts`, and update `INTENT_DESTINATIONS` for any intents that now route here.

The dispatcher at step 4 is where we got burned last week (`select_builder_for_turn` was added but the `noqa: ARG001` on the builders meant the query was still dropped). Pin the "query must be used" invariant with a regression test per builder.

---

## TL;DR for the meeting

1. "4 templates" is correct and verified at 5 layers of the stack.
2. After the 2026-04-22 scope call: **ship 2 new Answer templates + 1 expansion**.
   - NEW `lifecycle` — serves `format_lifecycle_optimize` + `fatigue` + `subniche_breakdown`. PRD: [`report-template-prd-lifecycle.md`](./report-template-prd-lifecycle.md).
   - NEW `diagnostic` — serves `own_flop_no_url` (URL-less video diagnosis). PRD: [`report-template-prd-diagnostic.md`](./report-template-prd-diagnostic.md).
   - EXPAND `timing` — add `calendar_slots[]` to absorb `content_calendar`. PRD: [`report-template-prd-timing-calendar.md`](./report-template-prd-timing-calendar.md).
3. **Drop** `series_audit` and `comparison` from the supported intent set.
4. Claude Chat's 6 reference designs are inspiration. The Pattern / Ideas / Timing / Generic payload shapes stay stable so the backend contract is unchanged; new templates follow the designs only where no existing shape fits.
5. Backend/frontend intent-list drift still needs a cleanup pass: `find_creators` vs `creator_search`, `follow_up` vs `follow_up_unclassifiable`. Handle before adding the new literals so we don't amplify it.

## Recommended build order

1. **Timing + calendar expansion** — smallest scope, no migration, reuses existing narrative module, good warm-up.
2. **Intent-list drift cleanup** — canonicalise `creator_search`/`find_creators` and `follow_up_unclassifiable`/`follow_up`, drop `series_audit` + `comparison`. Frontend + backend lists align. One small PR, must land before step 3 so new literals don't inherit the drift.
3. **Lifecycle template** — bigger scope (3 modes, new Gemini module, new frontend components). Needs the CHECK migration.
4. **Diagnostic template** — smallest of the new templates (single intent, no mode discriminator). Stack on lifecycle migration so the CHECK constraint alters only once.
