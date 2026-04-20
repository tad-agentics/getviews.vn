# Phase C — `/answer` research surface + report formats + Phase B carryovers

The single research surface that the four Phase B screens point into. Every
unclassified or report-shaped intent now lands on `/app/answer?session_id=…`
as one of four typed payloads (Pattern, Ideas, Timing, Generic). The UI is a
**pure function** of the payload — fields missing → humility state, never a
silent hole. `/app/chat` retreats to a generic free-text fallback for
unclassifiable follow-ups only.

This plan supersedes `artifacts/plans/phase-c-report-formats.md`. The intent
map (§A) and data contract (§J) below replace that document inline; the
report-formats file stays in tree as a reference pointer at the top. Keep
this single document as the source of truth.

**Design source of truth**: `artifacts/uiux-reference/screens/answer.jsx`,
`artifacts/uiux-reference/screens/thread-turns.jsx`. Tokens live in
`artifacts/uiux-reference/styles.css`. Where new sections are required
(`ConfidenceStrip`, `WhatStalled`, `OffTaxonomyBanner`, `WoWDiffBand`,
`HumilityBanner`, `VarianceNote`, `FatigueBand`, lifecycle row, prerequisites
row, forecast row on `ActionCard`, `TemplatizeCard` upgrade, idea blocks),
those are flagged for Claude Design and gated by **C.0**.

> **Non-negotiables that frame everything below:**
> 1. The §J data contract is the LLM-output contract. UI is a pure function
>    of the payload; missing fields render humility state, never silent holes.
> 2. **`WhatStalled` ships in C.2 or C.2 does not close.** Full stop — see §C.2.
> 3. Every sub-phase closes only with a green design-audit report (same rule
>    as B.1.6 / B.2.x / B.3.x / B.4.6) including the grep gate for raw hex /
>    `--purple` / `--ink-soft` / `--border-active` / `--gv-purple*`.
> 4. Commits follow `AGENTS.md` — phase gates `feat(answer): backend
>    complete`, `feat(answer): screens complete`, `test(answer): qa pass`;
>    carryovers use their own feature name (`feat(script-save): …`,
>    `feat(history): …`, `feat(channel-heatmap): …`).

## Guiding principles

- **One sub-phase, one PR.** Each milestone lands an atomic PR with backend
  aggregator + migration + tests + docs. Partial sub-phases don't ship.
- **The contract is the wire.** §J pydantic schemas are authored before any
  frontend route work. No UI primitive renders a field that isn't in the
  payload type.
- **Humility over hedging caption.** Thin corpus → fewer cards (driven by
  sample-size gates §C.0.3), not a 42%-disclaimer footer. `HumilityBanner`
  appears once at the top, not interleaved.
- **Slots beat prompts.** If a number is computable from corpus or
  `niche_intelligence`, compute it. Gemini stays for `thesis`, `insight`,
  `why_works`, `why_stalled`, `tip`, narrative paragraphs, and bounded
  metric copy. Numbers — never.
- **Retire chat fallbacks as each format ships.** `/app/chat` loses its
  corresponding quick-action CTA the moment Pattern / Ideas / Timing /
  Generic lands.
- **Token gate is non-negotiable.** Same grep as Phase B audits. `/history`
  restyle (§C.6) closes the four known violations as part of its audit.
- **`src/lib/api-types.ts` is extended on day 1 of C.1** — `AnswerSession`,
  `AnswerTurn`, `ReportV1` discriminated union, all four payload types
  defined before any route work begins.

## Recommended order

| # | Sub-phase | Rationale |
|---|---|---|
| C.0 | Spike (intent classifier + sample gates + width + answer-session model + idea-directions ref) | Five hard blockers — none of the formats can ship until they resolve. Single dedicated week. |
| C.1 | `/answer` shell foundation | Route, shell, `QueryHeader`, `SessionDrawer`, `FollowUpComposer`, `ContinuationTurn` dispatch, right rail, session CRUD. No format rendering yet — pure scaffold. |
| C.2 | **Pattern format (with `WhatStalled`)** | Highest-value report format; `WhatStalled` is the §C.2 non-negotiable that turns the product from "prettier Trends" into "auditable research tool". |
| C.3 | Ideas format | Reference coverage is highest (~85%) — second-easiest to ship after C.2. Variant mode for hook variants comes here. |
| C.4 | Timing format | Heatmap reuses `thread-turns.jsx` `TimingTurn`. New: `VarianceNote`, optional `FatigueBand`. |
| C.5 | Generic fallback + multi-intent merge | Humility format. Closes the multi-intent merge rules from §A.4. |
| C.6 | `/history` restyle | Closes 4 token violations. Aligns card shape to `SessionDrawer`. Adds "Phiên nghiên cứu" filter. |
| C.7 | `/chat` retirement | `intent-router.ts` redirects all classifiable intents into `/app/answer`. Chat stays for unclassifiable `follow_up` only. |
| C.8 | Phase B carryovers | One milestone each: `draft_scripts` table + script_save, Gemini upgrade to `/script/generate`, KOL `match_score` persistence, `PostingHeatmap` for `/channel`, real 30d growth wiring, primitive render test backfill, 3–7 day measurement dashboard read **before** any C behavior change. |

Estimated **10–13 weeks** including 1 spike week + 1 buffer week for
design-audit round-trips and measurement-read gating.

---

## Pre-kickoff decisions (lock before C.0 starts)

These are the decisions that the C.0 spike resolves, captured here so the
spike doesn't re-litigate them mid-week.

1. **Single source of truth for intent classification.** The Cloud Run
   classifier is the source. `intent-router.ts` is a thin pre-flight that
   only handles structural signals (URL → `/video`, `@handle` →
   `/channel`); everything else is shipped to Cloud Run for classification
   and a destination decision is round-tripped back. C.0.1 freezes this.
2. **`/answer` is a session, not a one-shot route.** Every render is
   gated by an `answer_sessions.id` UUID in the URL. Sessions persist in
   Postgres with RLS; turns append rather than overwrite. C.0.5 lays the
   tables.
3. **Pattern is the canonical format.** Ideas, Timing, Generic share the
   shell, the right rail, the `FollowUpComposer`, the timeline rail, and
   the `ConfidenceStrip` / `HumilityBanner` cross-cutting primitives. Only
   the body changes. Build Pattern first; the others reuse 70% of the
   shell.
4. **`WhatStalled` blocks Pattern close.** §C.2 cannot ship without it.
   Period. Backend must populate `Pattern.what_stalled[]`; frontend must
   render the negative `HookFinding` variant. If Gemini can't produce 2–3
   stalled patterns for a niche, the field is `[]` with a `reason` string
   ("ngách quá thưa, chưa đủ video lùi 14 ngày") and the UI renders an
   empty-state row — but the **section never disappears silently**.
5. **B.4 width decision applies everywhere.** Whatever C.0.4 picks (1280
   vs 1380), `/video`, `/kol`, `/channel`, `/script`, `/answer`,
   `/history` all conform. No per-route override. The script `1280` cap
   that B.4 carried (B.4 M-1 in `phase-b-closure.md`) gets resolved by
   this single C.0 decision.

---

## C.0 — Spike & pre-kickoff (1 week)

Resolve five hard blockers before writing a line of C.1 code.

### C.0.1 — Intent classifier v2 (1.5d)

Map all 20 creator intents from §A.1–A.2 to `(destination | report_format)`
and freeze the classifier behaviour. **This is an extension of the live
classifier, not a new build** — see "Existing infrastructure" below.

**Existing infrastructure (confirmed live on main as of 2026-04-20):**

- **Client deterministic layer:** `src/routes/_app/intent-router.ts`
  `detectIntent()` classifies 7 intents today (`video_diagnosis`,
  `competitor_profile`, `own_channel`, `shot_list`, `creator_search`,
  `trend_spike`, `content_directions`, `follow_up`). **Missing 11 of
  the plan's 20 intents:** `subniche_breakdown`,
  `format_lifecycle_optimize`, `fatigue`, `brief_generation`,
  `hook_variants`, `timing`, `content_calendar`, `comparison`,
  `series_audit`, `metadata_only`, `own_flop_no_url`. C.0.1 owns
  closing that gap — either by extending `detectIntent()` with 11 new
  keyword branches (preferred; cheap; no LLM call) or by punting all
  11 to `follow_up` on the client and letting the Cloud Run classifier
  carry the whole load (simpler but costs ~11× more classifier calls).
  **Default: extend `detectIntent()` for all 11** so the client
  pre-qualifies with `confidence: "medium"` and Cloud Run only
  disambiguates on tie-break.
- **Server deterministic layer:** `cloud-run/getviews_pipeline/intents.py`
  `classify_intent()` + `QueryIntent` enum. Currently 11 enum members;
  extend to match the §A 20-intent taxonomy in the same PR as
  `detectIntent()` so client and server stay synced.
- **Server LLM layer:** `cloud-run/getviews_pipeline/gemini.py:586`
  `classify_intent_gemini()` already runs with a 21-intent vocabulary
  in its system prompt (line 552+). Endpoint wrapper lives at
  `cloud-run/main.py:371 classify_intent_endpoint`. **C.0.1 adds the
  `destination_or_format` return field + the `Destination` union; the
  Gemini call itself is not net-new.**
- **Budget guard:** `EnsembleDailyBudgetExceeded` is a bare
  `ValueError` subclass at `ensemble.py:46`. Shape is reusable; wire
  a sibling `ClassifierDailyBudgetExceeded` at the same pattern with
  its own daily counter. The plan's earlier reference to
  `ed_budget.py` is actually `ensemble.py` — corrected here.

Decisions to land:

1. **Gemini vs deterministic.** Two classifiers in layered order (not
   parallel): **client-side deterministic** (`detectIntent()`) runs
   first and returns `{intent, confidence}`. If
   `confidence === "high"` (URL/handle/keyword match), skip LLM. On
   `"medium" | "low"`, the query + deterministic guess ship to Cloud
   Run's existing `classify_intent_endpoint`, which runs
   `classify_intent()` (deterministic) → `classify_intent_gemini()`
   (LLM confirm). Gemini return shape extended to include
   `destination_or_format`, `niche_filter`, `format_emphasis`.
2. **Confidence thresholds.**
   - `high` → route immediately, no LLM call.
   - `medium` → Gemini classifier confirms; if it disagrees by ≥ 0.3, the
     LLM wins.
   - `low` → Gemini decides outright. If Gemini also returns `low`, the
     intent is `follow_up` and renders **Generic** with the
     `intent_confidence: "low"` flag set on `ConfidenceStrip`.
3. **Destination dispatch matrix.** Codified in `intent-router.ts` as
   `INTENT_DESTINATIONS: Record<FixedIntentId, Destination>` (see C.7
   for the full type). Source of truth. Mirrored server-side in a
   new `cloud-run/getviews_pipeline/intent_router.py` that imports the
   enum from `intents.py` and adds the destination map. **C.7 wires
   this map into the final routing decision.**
4. **Budget.** Gemini classifier call costs ≤ 1 unit / classification.
   Deterministic pass costs 0. Daily budget guard reuses the
   `EnsembleDailyBudgetExceeded` shape from
   `cloud-run/getviews_pipeline/ensemble.py:46` (not `ed_budget.py` —
   that module handles corpus ingest budgets, not classifier budgets).
   Implement as `ClassifierDailyBudgetExceeded` at the same pattern;
   when exceeded, fall back to deterministic-only and log
   `[classifier-budget]`.

**Deliverable**: `artifacts/plans/intent-classifier-v2.md` decision record
+ `cloud-run/getviews_pipeline/intent_router.py` module (imports
`QueryIntent` from `intents.py`, owns the destination map) + extended
`intent-router.ts` `detectIntent()` covering the 11 missing intents +
matching pytest + vitest stubs. **No Gemini wiring changes yet** —
`classify_intent_gemini()` already runs; C.7 adds the
`destination_or_format` field to its return shape.

### C.0.2 — `idea-directions.jsx` design ref (0.5d, blocking)

`phase-c-report-formats.md` §2.2 references `idea-directions.jsx` as the
reference for `IdeaBlock`, `StyleCard`, `StopRow`. **The file does not
exist in `artifacts/uiux-reference/screens/`.** Three options:

1. **Locate it.** Search Claude Design's earlier handoff for the file. If
   present in stash/branch, lift into `artifacts/uiux-reference/screens/`.
2. **Commission.** Brief Claude Design with §C.3 spec + `answer.jsx`
   primitives; ask for an `idea-directions.jsx` reference matching the
   `answer.jsx` token vocabulary. Adds 1 week to C.3 timeline if taken.
3. **Re-scope from `answer.jsx`.** Build `IdeaBlock` and friends as
   compositions of `AnswerBlock` + `HookFinding`-shape + custom slot rows.
   Lower fidelity but no design dependency. Default unless option 1 lands.

**Hard cutoff: end of C.0 week (Fri 2026-04-24, 17:00 ICT).** If by then
neither option 1 nor option 2 has produced a checked-in
`artifacts/uiux-reference/screens/idea-directions.jsx`, option 3
(re-scope from `answer.jsx`) takes effect automatically and C.3
proceeds on the 1.5w base estimate. No further escalation; C.3 cannot
sit waiting on a design ref past this date.

**Deliverable**: line-item in `artifacts/plans/idea-directions-decision.md`
recording option chosen + impact on C.3 estimate. Filed by 2026-04-24.

### C.0.3 — Sample-size gates (1d)

Confirm corpus density per niche supports the §J empty-state thresholds.

Bars per format:

| Format | `sample_size` floor | Behaviour below floor |
|---|---|---|
| Pattern | 30 | `HumilityBanner`; skip `HookFindings[2..3]`; skip `WhatStalled`; render TL;DR + 3 `EvidenceVideos` only |
| Ideas | 60 | `HumilityBanner`; reduce to 3 `IdeaBlocks`; skip `StopDoing` |
| Timing | 80 | `HumilityBanner`; hide heatmap cells with `value < 5`; show top-3 windows list only |
| Generic | n/a | Always renders `OffTaxonomyBanner`; degrades narrative length only |

Spike work:

1. Query `niche_intelligence` (materialized view) + `video_corpus` per
   niche over 7d / 14d / 30d windows; produce a per-niche table of
   `(window, sample_size)` for each of the 21 active niches.
2. **Reuse `corpus_hashtag_yields_14d()` RPC** (landed 2026-04-29 in
   `20260429180000_corpus_hashtag_yields_rpc.sql`) to validate
   hashtag-level coverage within each niche — an adaptive yield table
   already models this exact problem for corpus ingest; the spike
   piggy-backs on it rather than re-running aggregations.
3. For every niche where 7d sample is below the Pattern floor, decide:
   - widen window to 14d automatically (preferred), or
   - degrade to 14d Generic (acceptable fallback), or
   - exclude the niche from `/answer` until corpus depth catches up.
4. Pattern + Ideas use **adaptive windows**: backend reports the actual
   window in `confidence.window_days` so the strip is honest.

**Deliverable**: `artifacts/docs/answer-sample-coverage.md` — table of
21 niches × 4 formats × actual coverage at default window, plus the
adaptive-window policy.

### C.0.4 — Width decision: 1280 vs 1380 platform-wide (0.5d)

Phase B closed with `/script` capped at 1280 (B.4 M-1 in
`phase-b-closure.md`) while the `script.jsx` reference targets 1380.
`answer.jsx` references `maxWidth: 1320`. Pick a single canonical max:

- **Option A — 1280 platform-wide.** `/answer` clamps to 1280, matches
  shipped `/video` `/kol` `/channel` `/script`. Lowest risk; Phase B
  carry resolves trivially.
- **Option B — 1380 platform-wide.** Promote all four B routes + new
  `/answer` to 1380. Extra QA pass on B routes; mid risk.
- **Option C — 1320 (`answer.jsx` literal).** Compromise; bumps B routes
  by 40px. Low risk.

Recommended default: **Option A** unless C.0 design audit shows `/answer`
hero blocks crowd at 1280 (specifically the 3-col patterns grid and the
right rail at 320 + 40 gap). Decision logged in
`artifacts/plans/phase-c-width-decision.md`.

Whatever wins, this single value lands in `src/app.css`
`gv-route-main--canonical` (or whatever the chosen var is) and **all six
routes consume it**. No per-route overrides survive C.0.

### C.0.5 — Answer-session data model (1.5d)

Two new tables. Both RLS-gated to `auth.uid()`. Service role writes the
report payload during stream completion.

```sql
-- supabase/migrations/2026XXXXXXXXXX_answer_sessions.sql

CREATE TABLE answer_sessions (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  niche_id     INTEGER REFERENCES niche_taxonomy(id),
  title        TEXT NOT NULL,                -- LLM-generated short title
  initial_q    TEXT NOT NULL,                -- the seed query
  intent_type  TEXT NOT NULL,                -- §A intent id (e.g. 'trend_spike')
  format       TEXT NOT NULL,                -- 'pattern'|'ideas'|'timing'|'generic'
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  archived_at  TIMESTAMPTZ
);

CREATE INDEX answer_sessions_user_recent_idx
  ON answer_sessions (user_id, updated_at DESC) WHERE archived_at IS NULL;

ALTER TABLE answer_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "answer_sessions_select_own" ON answer_sessions
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "answer_sessions_insert_own" ON answer_sessions
  FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "answer_sessions_update_own" ON answer_sessions
  FOR UPDATE USING (auth.uid() = user_id);

CREATE TABLE answer_turns (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id   UUID NOT NULL REFERENCES answer_sessions(id) ON DELETE CASCADE,
  turn_index   INTEGER NOT NULL,             -- 0 = primary, 1.. = follow-ups
  kind         TEXT NOT NULL,                -- 'primary'|'timing'|'creators'|'script'|'generic'
  query        TEXT NOT NULL,
  payload      JSONB NOT NULL,               -- §J ReportV1 (turn 0) or smaller turn shape
  classifier_confidence TEXT NOT NULL,       -- 'high'|'medium'|'low'
  intent_confidence TEXT NOT NULL,           -- mirrors confidence_strip
  cloud_run_run_id TEXT,                     -- correlation w/ Cloud Run logs
  credits_used INTEGER NOT NULL DEFAULT 0,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (session_id, turn_index)
);

CREATE INDEX answer_turns_session_order_idx
  ON answer_turns (session_id, turn_index);

ALTER TABLE answer_turns ENABLE ROW LEVEL SECURITY;
CREATE POLICY "answer_turns_select_own" ON answer_turns
  FOR SELECT USING (
    auth.uid() = (SELECT user_id FROM answer_sessions WHERE id = session_id)
  );
-- service-role inserts only; no insert policy for authenticated users
```

Pre-decided:

- `payload` JSONB is **schema-validated server-side** by the matching §J
  pydantic model before insert. Bad payloads fail the stream rather than
  persist a broken session.
- **Credit accounting is integer-only** (matches the existing
  `profiles.credits INTEGER` + `decrement_credit()` RPC contract — no
  fractional accounting):
  - `kind === 'primary'` → **1 credit** (deducted via TD-1 RPC, see
    below).
  - `kind ∈ ('timing','creators','script')` → **0 credits** (free
    follow-ups; the primary turn already paid for the session).
  - `kind === 'generic'` → **0 credits** (humility fallback is always
    free — restated in §C.5).
- **TD-1 (atomic credit deduction) is non-negotiable.** Primary-turn
  credit deduction goes through the existing Supabase RPC
  `decrement_credit()` with its `WHERE credits > 0` guard. **Never** a
  client-side read-then-write. The deduction happens server-side in
  Cloud Run **before** the SSE stream begins; if it fails (insufficient
  credits), the endpoint returns `402 Payment Required` and no
  `answer_turns` row is written.
- **TD-4 (SSE reconnection) inherited.** `/answer/sessions/:id/turns`
  uses the same `stream_id` + `seq` per-token replay buffer pattern that
  Cloud Run already runs for video analysis — `put_stream_chunks` /
  `get_stream_chunks` in `cloud-run/getviews_pipeline/session_store.py`
  (not `runtime.py` — that module holds only `run_sync` + the analysis
  semaphore). Buffer TTL is **120s** (`_STREAM_REPLAY_TTL_SEC` in
  `session_store.py:41`). Mid-turn dropouts resume from `seq` rather
  than re-billing. Reconnect query: `?resume_from_seq=<n>`.
  **Best-effort caveat:** the buffer is per-instance; with Cloud Run
  `max-instances: 5` and `--concurrency 20`, a reconnect that hits a
  different pod gets a fresh stream rather than a replay. Acceptable
  for C.1 MVP (matches the precedent documented in
  `session_store.py:8-10`); if measured drop-rate on answer follow-ups
  exceeds 2% post-ship, promote to a Redis-backed buffer in Phase D.
  Document the full contract in
  `artifacts/docs/answer-session-contract.md`.
- **Idempotency on session creation.** `POST /answer/sessions` accepts
  an `Idempotency-Key` header (UUIDv4 generated client-side, cached
  120s server-side keyed on `(user_id, key)` — matches the replay-TTL
  for operational simplicity). Replays return the same `session_id`.
  Prevents double-clicks and page-reload races during the C.7.1
  chat-redirect pre-flight from creating duplicate sessions.
- Soft-delete via `archived_at`. UI hides archived; user can restore.

**Deliverable**: migration file checked in **but not pushed** to staging
until C.1.1. Contract docs in `artifacts/docs/answer-session-contract.md`
including the TD-4 resume protocol and idempotency-key cache TTL.

### C.0 milestones

1. **C.0.1** (1.5d) — intent classifier v2 decision record + skeleton
2. **C.0.2** (0.5d) — `idea-directions.jsx` decision record (default: re-scope from `answer.jsx`)
3. **C.0.3** (1d) — sample coverage table + adaptive-window policy
4. **C.0.4** (0.5d) — width decision (default: 1280 platform-wide)
5. **C.0.5** (1.5d) — `answer_sessions` + `answer_turns` migration + RLS + pydantic schemas drafted
6. **C.0.6** (1d) — **Spike close-out** review with three deliverables shipped to `artifacts/plans/` + this doc updated to lock the decisions. Required before C.1 starts. Three additional one-line locks land in this milestone:
   - **Token additions in `src/app.css`:** `--gv-danger` (seeded from the Phase B accent-red precedent — final hex pinned by design review). Consumed by `WhatStalledRow` (C.2) and the `chat_classified_redirect` toast variant if needed (C.7). No other danger-color literal allowed in C surfaces.
   - **Migration sequencing:** placeholder filenames `2026XXXXXXXXXX_*.sql` resolved to real `YYYYMMDDHHmmss_` stamps before any sub-phase opens its PR. **Floor: `20260430000000`** (latest on-main as of 2026-04-20 is `20260429180000_corpus_hashtag_yields_rpc.sql`); subsequent migrations bump from there. C.0.6 assigns sequential stamps across C.0.5 (`answer_sessions` + `answer_turns`), C.2.1 (`pattern_wow_diff_7d` RPC), C.4.1 (`timing_top_window_streak`), C.6.1 (`history_union` RPC), C.8.1 (`draft_scripts`), C.8.3 (`creator_velocity.match_score` add).
   - **TD-1 / TD-4 / idempotency contract** (per C.0.5 above) restated in `artifacts/docs/answer-session-contract.md` with worked example payloads.

---

## §A — Intent × destination map (folded in from `phase-c-report-formats.md` §1)

All 20 realistic creator intents. Source of truth for `INTENT_DESTINATIONS`
in C.0.1.

### §A.1 Dispatch to existing screen (no `/answer` report)

| # | Intent id | Trigger | Destination | Phase B status |
|---|---|---|---|---|
| 1 | `video_diagnosis` | TikTok video URL | `/app/video?video_id=…` | ✅ B.1 shipped |
| 2 | `competitor_profile` | `@handle` w/ competitor framing | `/app/channel?handle=…` | ✅ B.3 shipped |
| 3 | `own_channel` | `@handle` + self-reference ("mình/tôi") | `/app/channel?handle=…` | ✅ B.3 shipped |
| 4 | `creator_search` / `find_creators` | "tìm KOL/creator/KOC" | `/app/kol?filters=…` | ✅ B.2 shipped |
| 5 | `shot_list` | "viết kịch bản / shotlist / cách quay" | `/app/script?topic=…&hook=…` | ✅ B.4 shipped |
| 6 | `metadata_only` | URL + "stats / lượt view" only | `/app/video?video_id=…&mode=stats` | ✅ B.1 covers; mode flag minor (C.7) |
| 7 | `comparison` (A vs B) | 2+ `@handles` w/ compare framing | `/app/kol?pinned=a,b&mode=compare` | ⚠️ KOL has pinned tab; compare-mode is new (C.8) |
| 8 | `series_audit` | Multi-URL (2+ videos) | `/app/video?video_ids=…&mode=series` | ❌ **Phase D** |
| 9 | `own_flop_no_url` | "tại sao video tôi ít view" w/o URL | Prompt for URL → dispatch to `/app/video` | ❌ **Phase D** (graceful-degrade) |

### §A.2 Lands on `/answer` — needs report format

| # | Intent id | Trigger | Format | C sub-phase |
|---|---|---|---|---|
| 10 | `trend_spike` | "hook đang hot / tuần này / đang viral" | **Pattern** | C.2 |
| 11 | `content_directions` | "nên làm gì / format nào / hướng nội dung" | **Pattern** | C.2 |
| 12 | `subniche_breakdown` | "Beauty skincare / Tech AI tools" | **Pattern** (niche filter) | C.2 |
| 13 | `format_lifecycle_optimize` | "30s vs 60s / carousel vs video" | **Pattern** (format section emphasized) | C.2 |
| 14 | `fatigue` | "pattern nào đang chết / hết trend" | **Pattern** (lifecycle emphasized) | C.2 |
| 15 | `brief_generation` | "viết brief tuần tới / 5 ý tưởng video" | **Ideas** | C.3 |
| 16 | `hook_variants` | "biến thể của hook X / 5 cách viết hook này" | **Ideas** (variant mode) | C.3 |
| 17 | `timing` | "đăng giờ nào / thứ mấy tốt nhất" | **Timing** | C.4 |
| 18 | `content_calendar` | "tuần này post gì khi nào" | **Pattern + Timing** (merged §A.4) | C.5 multi-intent rules |
| 19 | `follow_up_classifiable` | Natural language, intent detected by §C.0.1 | Route to Pattern/Ideas/Timing by subject | C.7 |
| 20 | `follow_up_unclassifiable` | Natural language, no intent | **Generic** fallback | C.5 |

### §A.3 Phase D (explicitly stubbed; not shipped in C)

- **Commerce/seller** — "sản phẩm TikTok Shop bán chạy", "affiliate rate
  ngách X", "product angle finder"
- **Personalized `Ship Next`** — creator-channel ingest + 3 personalized
  angle cards
- **Loop closure** — measure tool-originated posts vs self-sourced
- **Long-form strategy** — "should I rebrand my channel?"
- **`series_audit` (intent #8)** + **`own_flop_no_url` (intent #9)** —
  defer because both need multi-input UX work that doesn't exist yet
  on `/video`.

### §A.4 Multi-intent merge rules (lifted from `phase-c-report-formats.md` §3, owned by C.5)

| Case | Rule | Example |
|---|---|---|
| Destination + report | Destination wins; report becomes `ActionCard` on destination | "Phân tích URL + 3 hook variants" → `/app/video` + action chip "hook variants" |
| Report + report (same family) | Merge in-shape | `trend_spike` + `content_directions` → single Pattern with both emphases |
| Report + action | Report + `ActionCard` with corpus-backed prefill | "Hook hot + viết kịch bản hook #1" → Pattern + prominent script ActionCard |
| Report + timing | Merge — Pattern + Timing section | "Post gì khi nào" → Pattern report with Timing section inserted |
| Everything else | Primary intent only; secondary signals → filters/params | "Hook Tech < 500K follower" → Pattern with `followers_lt: 500000` |

---

## C.1 — `/answer` shell foundation (~2 weeks)

> **Design source**: `artifacts/uiux-reference/screens/answer.jsx`
> + `artifacts/uiux-reference/screens/thread-turns.jsx`
> + `artifacts/uiux-reference/styles.css` (tokens)
>
> Every px / kicker / token must trace back to one of these files.

Ships the route, shell, drawer, composer, right rail, and continuation-turn
dispatch. **No format rendering** — Pattern body is a placeholder
`AnswerBlock` until C.2 lands. Validates the contract end-to-end with a
fixture-driven `Pattern` payload.

### Exact design spec (from `answer.jsx` and `thread-turns.jsx`)

**Layout** (`answer.jsx:60`): outer wrapper `background: var(--canvas)`,
`maxWidth: ${WIDTH_FROM_C0}` (default 1280 per C.0.4), `margin: 0 auto`,
`padding: 28px 28px 120px`. Two-column grid `gridTemplateColumns: 'minmax(0,
1fr) 320px'`, `gap: 40`, `marginTop: 36`, `alignItems: 'start'`. Responsive
at `@media (max-width: 1100px)` → single column, rail re-orders to top
(see §"Responsive breakpoints" below for the full rules from `answer.jsx`
lines 277–290).

**Crumb / drawer toggle row** (`answer.jsx:62-74`):
- `display: flex, alignItems: center, gap: 10, marginBottom: 18`,
  `fontSize: 12, color: var(--ink-4), flexWrap: wrap`.
- Studio chip (`Icon name="arrow-left" size={11}`) + drawer chip
  `Phiên nghiên cứu · {count}` + slash separator + niche kicker
  `NGHIÊN CỨU · {NICHE}` (mono uc 10px, letterSpacing 0.14em) +
  flex-spacer + `ProgressPill`.
- All three buttons use `className="chip"`.

**`QueryHeader`** (`answer.jsx:299-343`):
- Container `borderTop: 2px solid var(--ink), borderBottom: 1px solid
  var(--rule), padding: 24px 0 22px`.
- Top mono row (10px, letterSpacing 0.16em, ink-4): `CÂU HỎI` + 1px
  flex-rule + `{user_name} · {timestamp}`. `marginBottom: 12`.
- H1 `fontFamily: var(--serif)`, `fontSize: clamp(28px, 3.4vw, 42px)`,
  `lineHeight: 1.1`, `letterSpacing: -0.02em`, `fontWeight: 500`,
  `textWrap: balance`.
- Research narrative below: `display: flex, flexWrap: wrap, gap: 16,
  marginTop: 18, alignItems: center`. Renders 4 `ResearchStep` rows
  (`answer.jsx:345-369`) — quét → phân tích → tìm pattern → viết tóm tắt
  — animated dot per stage; final `chip-lime` HOÀN TẤT chip when
  `done && stage >= 4`.
- Pulse dot: 6px, `var(--accent)`, animation `pulseDot 1s infinite`
  (lines 363–366).

**Timeline rail** (`answer.jsx:88-95`):
- `position: absolute, left: -18, top: 20, bottom: 100, width: 1,
  background: var(--rule)`. Hidden ≤ 1100px (`.turn-rail { display: none
  }`). Only renders when `turns.length > 1`.
- Continuation `TurnDivider` nodes attach (`thread-turns.jsx:18-24`):
  9px circle, `var(--accent)` bg, `2px solid var(--canvas)` border, outer
  `boxShadow: 0 0 0 1px var(--ink)`, positioned `left: -22, top: 30`.

**`SessionDrawer`** (`thread-turns.jsx:407-472`):
- Backdrop `position: fixed, inset: 0, zIndex: 100, background:
  rgba(10,12,16,0.35)`. Click outside closes.
- Drawer `position: absolute, left: 0, top: 0, bottom: 0, width: 380,
  background: var(--canvas), borderRight: 1px solid var(--ink),
  display: flex, flexDirection: column, animation: slideIn 0.25s
  ease-out`.
- Header (`padding: 20px 22px 16px, borderBottom: 1px solid var(--rule)`):
  kicker `PHIÊN NGHIÊN CỨU` (mono uc 10px, letterSpacing 0.18em, ink-4) +
  serif title `Các phiên gần đây` (22px) + close chip.
- New-session CTA `btn btn-accent, margin: 16px 22px, padding: 12px 14px`
  with `[sparkle]` icon.
- Session list rows: `padding: 12px 14px`, active row
  `background: var(--accent-soft), borderLeft: 3px solid var(--accent)`.
  Each row: niche kicker (mono uc 9px, letterSpacing 0.14em) + turn count
  + relative date (mono) + serif title (14px, lineHeight 1.3,
  textWrap: pretty).
- Footer: `padding: 12px 22px, borderTop: 1px solid var(--rule)`, mono
  count + `Xem tất cả` chip.

**`FollowUpComposer`** (`answer.jsx:677-735`):
- Outer wrapper `marginTop: 48`, kicker `TIẾP TỤC NGHIÊN CỨU` (mono uc
  10px, letterSpacing 0.18em, ink-4, marginBottom 12).
- Card `background: var(--paper), border: 2px solid var(--ink),
  borderRadius: 16, boxShadow: 4px 4px 0 var(--ink), padding: 4`.
- Inner `padding: 14px 18px 6px` containing `<textarea rows={2}>` —
  `border: 0, outline: 0, resize: none, background: transparent,
  fontFamily: var(--sans), fontSize: 15, lineHeight: 1.45, color:
  var(--ink)`. Enter (no shift) submits.
- Footer `padding: 8px 10px, borderTop: 1px solid var(--rule)` —
  followup-suggestion chips on left + `Gửi` `btn btn-accent` on right
  (disabled state `opacity: 0.4`).

**Right rail** (`answer.jsx:266-272` → `Sources` `answer.jsx:741-765`,
`RelatedQs` `answer.jsx:787-820`, `SaveCard` `answer.jsx:822-846`):
- All three cards: `border: 1px solid var(--rule), background:
  var(--paper), padding: 18px`. Stacked with `marginTop: 18` between.
- `Sources` header: kicker `NGUỒN` left + accent count right (`var(--accent)`).
  Inner rows (`answer.jsx:767-785`): 28×28 icon tile (`background:
  var(--canvas-2), border: 1px solid var(--rule)`) + label + sub-mono +
  big mono count.
- `RelatedQs`: kicker `CÂU HỎI LIÊN QUAN`, list of buttons separated by
  `borderTop: 1px solid var(--rule)`, `padding: 12px 0`, hover `color:
  var(--accent) !important`.
- **`SaveCard` becomes `TemplatizeCard` in C.1** — same physical card
  (`background: var(--ink), color: var(--canvas), padding: 18px`), kicker
  swaps to `LƯU NGHIÊN CỨU` (kept) but the serif title becomes "Biến
  báo cáo này thành template cho các tuần sau." (already correct copy
  in `answer.jsx:830-832`). Buttons: `Lưu` (canvas bg, ink text), `Chia
  sẻ`, `PDF` (transparent bg, `border: 1px solid rgba(255,255,255,0.3)`).
  See §"Things retired".

**`ContinuationTurn` dispatch** (`thread-turns.jsx:70-83`):
- Maps `turn.kind` → `{timing: TimingTurn, creators: CreatorsTurn,
  script: ScriptTurn, generic: GenericTurn}` (default `GenericTurn`).
- `TurnDivider` per turn (`thread-turns.jsx:9-45`): kicker (mono uc 10px,
  letterSpacing 0.18em, accent, fontWeight 600) `{LABEL} · LƯỢT {NN}` +
  flex rule + relative time.
- H2 `fontFamily: var(--serif), fontSize: clamp(22px, 2.6vw, 30px),
  lineHeight: 1.15, letterSpacing: -0.02em, fontWeight: 500, textWrap:
  balance`.
- `MiniResearch` strip below (`thread-turns.jsx:47-67`): "Dùng lại 47
  nguồn" → "Trả lời" → check chip `2.1s · cùng phiên`.

### Data model (C.0.5 schemas — restated for C.1 wiring)

`answer_sessions` — see §C.0.5.
`answer_turns` — see §C.0.5.

C.1 ships **CRUD only**. Payloads in C.1 are read from a fixture
endpoint that returns hand-authored `Pattern` JSON conforming to §J. C.2
replaces the fixture with the live aggregator.

### Fixture mapping (design → backend, C.1 placeholders)

Source fixtures: `PAST_SESSIONS` (`answer.jsx:8-15`) drives the drawer;
fixture Pattern payload (to be authored in
`artifacts/uiux-reference/data.js` as `ANSWER_FIXTURE_PATTERN`) drives
the body until C.2.

| Design field (`answer.jsx` JSX literal) | Response field | Source |
|---|---|---|
| Drawer session list (`PAST_SESSIONS`) | `GET /answer/sessions` returns `[{id, title, niche_label, turns_count, updated_at}]` | `answer_sessions` joined to `niche_taxonomy` |
| Drawer active row (`s.active === true`) | client-side from `useParams().session_id` | router |
| `QueryHeader` `q` text | `session.initial_q` | `answer_sessions.initial_q` |
| `QueryHeader` niche kicker `NGHIÊN CỨU · {NICHE}` | `session.niche_label` | `niche_taxonomy.label` |
| `QueryHeader` user kicker `An · 2 phút trước` | `session.created_at` formatted client-side + `profile.display_name` | `auth.users` + `profiles` |
| `ProgressPill` count + duration | `session.last_turn.cloud_run_duration_ms` + `session.last_turn.payload.confidence.sources_total` | `answer_turns.payload` |
| `ResearchStep` labels (`answer.jsx:330-333`) | hard-coded for C.1; payload-driven in C.2 (`payload.research_steps[]`) | static for C.1 |
| `Sources` source rows (`answer.jsx:755-758`) | `payload.sources[]: {kind, label, count, sub}` | aggregated by Cloud Run |
| `RelatedQs` 4 chips | `payload.related_questions[4]` (LLM-generated, bounded) | Gemini call within `report_pattern.py` |
| `TemplatizeCard` Lưu / Chia sẻ / PDF | `POST /answer/sessions/:id/templatize` (creates a new `templates` row in C.8) | C.8.x table |
| Body — Pattern placeholder | `payload.report` discriminated union per §J | `answer_turns.payload` JSONB |

**Client-side only:**
- Relative time formatting (`Vừa xong`, `Hôm qua`, `2 ngày`, `Tuần
  trước`) — derived from `updated_at`.
- `ProgressPill` "Đang nghiên cứu… {n}/4" animation — driven by streaming
  status from Cloud Run, not from Postgres.
- `MiniResearch` 2-step strip — pure animation; uses local `useState`
  with the same `setTimeout` pattern as `answer.jsx:38-42`.

### New tables

- `answer_sessions`, `answer_turns` (C.0.5).
- `templates` (introduced by C.8.1 alongside `script_save`):
  ```sql
  CREATE TABLE templates (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_session_id UUID REFERENCES answer_sessions(id) ON DELETE SET NULL,
    title       TEXT NOT NULL,
    payload     JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
  );
  ```
  RLS `auth.uid() = user_id`. C.1 only references the table for the
  `TemplatizeCard` button stub — actual templating logic lives in C.8.

### New Cloud Run module: `answer_session.py`

- `create_session(user_id, niche_id, initial_q, intent_type, format) →
  AnswerSession` — service-role insert into `answer_sessions`, returns
  the row.
- `append_turn(session_id, turn_index, kind, query, payload, confidences,
  cloud_run_run_id, credits_used) → AnswerTurn` — schema-validates
  `payload` against the matching §J pydantic model before insert.
- `list_sessions(user_id, limit, archived) → list[AnswerSession]` — used
  by `GET /answer/sessions`.
- `get_session_turns(user_id, session_id) → list[AnswerTurn]` — used
  by `GET /answer/sessions/:id`.
- `archive_session(user_id, session_id)` and `restore_session(...)` —
  RLS-bounded soft delete.

### New Cloud Run endpoints

All `/answer/*` endpoints validate the user JWT via the same Supabase
JWKS path Cloud Run already uses for `/stream` (`main.py`), and inherit
the existing CORS handling.

- `POST /answer/sessions` — body `{initial_q, intent_type, niche_id,
  format}`. **Header `Idempotency-Key: <uuidv4>` required** (per
  C.0.5); replays within 120s return the same `session_id`. Inserts
  an empty session row; C.1 clients then call `POST /answer/sessions/
  :id/turns` to append the primary turn.
- `POST /answer/sessions/:id/turns` — body `{query, kind}`. Optional
  query `?resume_from_seq=<n>` for TD-4 SSE replay (inherits the
  120s per-instance `stream_id` + `seq` buffer Cloud Run uses for
  `/stream` — `session_store.py`). Cross-pod resume degrades to a
  fresh stream; see C.0.5.
  Auth-required. **Credit semantics (per C.0.5):**
  `kind === 'primary'` deducts 1 credit via the `decrement_credit()`
  RPC (TD-1) **before** the SSE stream opens; insufficient credits →
  `402 Payment Required` and no `answer_turns` write. All other `kind`s
  are free. On completion, payload is schema-validated against the
  matching §J pydantic model and the turn is inserted.
  C.1 ships the **fixture** aggregator (returns
  `ANSWER_FIXTURE_PATTERN`); C.2–C.5 replace it.
- `GET /answer/sessions` — keyset pagination `?cursor=<iso updated_at>
  &limit=20&scope=30d|all`. Default `scope=30d` matches the drawer's
  default; `scope=all` is used by `/history` for the unbounded view.
  Returns rows ordered by `updated_at DESC`, RLS-bounded to `auth.uid()`,
  excludes `archived_at IS NOT NULL` unless `?include_archived=true`.
- `GET /answer/sessions/:id` — full session + ordered turns. RLS-bounded.
- `PATCH /answer/sessions/:id` — body `{title?, archived_at?}`.

### Frontend: `/app/answer` route

- Route file: `src/routes/_app/answer/route.tsx` (TanStack Router).
- URL params: `?session=<uuid>&q=<seed_query>` (q optional once session
  exists).
- TanStack Query keys:
  - `['answer-sessions', user_id]` — drawer list, `staleTime: 60_000`.
  - `['answer-session', session_id]` — full session, `staleTime:
    30 * 60 * 1000` (sessions are append-only after primary turn
    completes, so stale-while-revalidate is safe).
- Streaming: reuses the existing chat SSE plumbing
  (`src/lib/streamingFetch.ts`); `runSend` analog calls `POST /answer/
  sessions/:id/turns` and pipes deltas into local turn state. Final
  delta carries the validated payload.
- New primitives needed (names match `### New design primitives`):
  - `AnswerShell` (page wrapper, owns the 2-col grid).
  - `QueryHeader` + `ResearchStep` + `ProgressPill` (composed).
  - `SessionDrawer` (modal aside w/ overlay + slide-in animation).
  - `FollowUpComposer` (textarea + suggestion chips + send button).
  - `TimelineRail` (`position: absolute` 1px column).
  - `TurnDivider` (kicker + serif H2 + `MiniResearch`).
  - `Sources` + `SourceRow`.
  - `RelatedQs`.
  - `TemplatizeCard` — the `SaveCard` rename, **kept identical to
    `answer.jsx:822-846` for C.1**; functionality wires up in C.8.
- Reuses from B: `Btn`, `Chip`, `Icon`, `Card` (where applicable),
  `KpiGrid` (Pattern uses 3-col `SumStat` grid in §C.2).

### New design primitives

New files under `src/components/v2/answer/` — build during C.0.5 / C.1.1
backend overlap so C.1.2 frontend work is never blocked.

| Component | Description | Source |
|---|---|---|
| `AnswerShell` | Outer wrapper: `background: var(--canvas)`, `maxWidth: <C.0.4>`, `padding: 28px 28px 120px`. Owns the 2-col grid + responsive collapse at 1100px. | `answer.jsx:56-86` |
| `QueryHeader` | `borderTop: 2px solid var(--ink), borderBottom: 1px solid var(--rule), padding: 24px 0 22px`. Mono kicker row + serif H1 + `ResearchStep` row. | `answer.jsx:299-343` |
| `ResearchStep` | 14×14 circle (border 1.5px, ink/rule/transparent by state) + mono label (11px). Uses `pulseDot` keyframe for active state. | `answer.jsx:345-369` |
| `ProgressPill` | `chip mono` 10px — "Đang nghiên cứu… {n}/4" while in progress; "{N}s · {sources} nguồn" when done. Right-aligned in crumb row. | `answer.jsx:371-384` |
| `AnswerBlock` | Editorial section wrapper: `marginTop: 44`, kicker (mono uc 10px, letterSpacing 0.18em, accent, fontWeight 600) + serif H2 (clamp 20–26px). Animation classes `answer-block` + `show`. | `answer.jsx:390-416` |
| `SumStat` | 3-col grid cell: kicker (mono uc 9px) + serif value (40px, lineHeight 1, fontWeight 500) + mono trend (11px) with optional ▲ + tone color (`rgb(0,159,250)` for `up`). | `answer.jsx:418-434` |
| `TimelineRail` | 1px-wide vertical rule, `position: absolute, left: -18, top: 20, bottom: 100, background: var(--rule)`. Hidden ≤ 1100px. | `answer.jsx:88-95` |
| `TurnDivider` | Kicker `{LABEL} · LƯỢT {NN}` + serif H2 + `MiniResearch` strip + 9px node attached to `TimelineRail`. | `thread-turns.jsx:9-45` |
| `MiniResearch` | 2-step research strip ("Dùng lại N nguồn" → "Trả lời") + completion chip. Pure animation; no API. | `thread-turns.jsx:47-67` |
| `SessionDrawer` | Modal aside, 380px wide, `slideIn` keyframe animation, list of `answer_sessions` rows w/ active accent. Header serif title + new-session btn-accent. Footer count + "Xem tất cả" chip → routes to `/app/history?filter=answer`. **Pagination:** server-side keyset on `updated_at DESC LIMIT 20`; loads more on scroll (`IntersectionObserver` on the last row). **Default scope:** sessions where `updated_at > now() - INTERVAL '30 days' AND archived_at IS NULL`. The "Xem tất cả" chip is the only path to older / archived sessions (handled by `/history`, not the drawer). | `thread-turns.jsx:407-472` |
| `FollowUpComposer` | `border: 2px solid var(--ink), borderRadius: 16, boxShadow: 4px 4px 0 var(--ink)`. Textarea + suggestion chips + accent send button. | `answer.jsx:677-735` |
| `Sources` + `SourceRow` | Right-rail card; rows are 28×28 icon tile + label + sub-mono + big mono count. | `answer.jsx:741-785` |
| `RelatedQs` | Right-rail card; click → `appendTurn(q)` calls the same composer flow. Hover color → accent. | `answer.jsx:787-820` |
| `TemplatizeCard` | Inverted card (`background: var(--ink), color: var(--canvas)`). Kicker `LƯU NGHIÊN CỨU` + serif title + 3 buttons (Lưu / Chia sẻ / PDF). C.1 ships UI; C.8.1 wires templating. | `answer.jsx:822-846` (renamed from `SaveCard`) |
| `EvidenceCard` | Existing 9/12 aspect tile w/ gradient overlay, `[idx]` accent badge, duration mono badge, creator mono + 2-line title, footer w/ views + retention. **Lifted from `answer.jsx:502-547`.** Reused by Pattern (C.2), Generic (C.5), Ideas evidence-row (C.3). | `answer.jsx:493-547` |
| `ContinuationTurn` | Dispatcher; chooses renderer by `turn.kind`. Used by C.4 (timing turn) and C.7 (intent-routed follow-ups). | `thread-turns.jsx:70-83` |

Reuses from Phase B: `Btn`, `Chip`, `Card`, `Icon`, `SectionMini`,
`KpiGrid` (channel variant for §C.2 evidence count strip).

### C.1 milestones

1. **C.1.1** (3d) — `answer_sessions` + `answer_turns` migration applied
   to staging + RLS verified + service-role write path. `src/lib/api-types.ts`
   gets `AnswerSession`, `AnswerTurn`, `ReportV1` discriminated union, and
   four payload types (`PatternPayload`, `IdeasPayload`, `TimingPayload`,
   `GenericPayload`) — see §J.
2. **C.1.2** (3d) — `answer_session.py` Cloud Run module + 5 endpoints
   (`POST /sessions`, `POST /sessions/:id/turns`, `GET /sessions`, `GET
   /sessions/:id`, `PATCH /sessions/:id`) + fixture aggregator returning
   `ANSWER_FIXTURE_PATTERN` + pytest covering the create/append/list flow.
3. **C.1.3** (4d) — `/app/answer` route + `AnswerShell` + `QueryHeader` +
   `SessionDrawer` + `FollowUpComposer` + right-rail (Sources / RelatedQs
   / TemplatizeCard) + timeline rail + `ContinuationTurn` dispatch
   (renderers stubbed). Body renders the fixture Pattern as a single
   `AnswerBlock` w/ a "C.2 incoming" placeholder.
4. **C.1.4** (1d) — measurement events `answer_session_create`,
   `answer_turn_append`, `templatize_click` wired via
   `src/lib/logUsage.ts`. Migration in
   `supabase/migrations/2026XXXXXXXXXX_usage_events_c1.sql` extends the
   allow-list.
5. **C.1.5** (1d) — **Design audit** — compare shipped `/app/answer`
   shell against `answer.jsx` + `thread-turns.jsx` section-by-section:
   primitives, tokens, kickers, spacing, copy, responsive behaviour
   (1100, 720 breakpoints). Produce
   `artifacts/qa-reports/phase-c-design-audit-answer-shell.md` with
   `must-fix / should-fix / consider` tiers. Ship all must-fix items
   before closing C.1.
   - **Token check**: zero raw hex codes in JSX; zero purple-era tokens
     (`--ink-soft`, `--purple`, `--border-active`, or any `--gv-purple-*`)
     in new screen files. Every color reference must resolve to a
     `var(--gv-*)` token. Grep new files for `#[0-9a-fA-F]{3,6}` and the
     banned token list as part of the audit — any hit is a `must-fix`.
   **Non-negotiable: C.1 cannot close without a green audit report.**
6. **C.1.6** (0.5d) — shell smoke `artifacts/qa-reports/smoke-answer-shell.sh`:
   curl `POST /answer/sessions`, then `POST /sessions/:id/turns` with
   `kind: "primary"`, then `GET /sessions/:id`, assert HTTP 200 and the
   payload validates against `PatternPayload`.

---

## C.2 — Pattern format (~2.5 weeks) — **`WhatStalled` is non-negotiable**

> **Design source**: `artifacts/uiux-reference/screens/answer.jsx` (sections
> TÓM TẮT / BẰNG CHỨNG · 3 HOOK / VIDEO MẪU / PATTERNS / BƯỚC TIẾP THEO)
> + new sections from `phase-c-report-formats.md` §2.1 §5 (folded inline
> into this milestone).
>
> Every px / kicker / token must trace back to one of these files.

Covers intents 10, 11, 12, 13, 14, plus 19 when classified as
pattern-family. Replaces the fixture aggregator from C.1 with the live
`report_pattern.py` pipeline.

### Exact design spec (from `answer.jsx` + new sections)

Render order — locked. Every section is a child of `AnswerBlock`.

1. **`ConfidenceStrip`** — band immediately under `QueryHeader`, before any
   `AnswerBlock`. **NEW.** `padding: 12px 16px, background:
   var(--canvas-2), border: 1px solid var(--rule), borderRadius: 8,
   marginTop: 22, display: flex, gap: 12, flexWrap: wrap, alignItems:
   center, fontFamily: var(--mono), fontSize: 12, color: var(--ink-3)`.
   Content: `N=47 · 7 ngày · Tech · cập nhật 3h trước` + optional `chip
   chip-amber` "MẪU MỎNG" when `sample_size < 30` (clicking opens the
   `HumilityBanner` body inline).
2. **`WoWDiffBand`** (optional) — **NEW.** Above TL;DR when `wow_diff`
   present. `padding: 10px 14px, background: var(--accent-soft), border:
   1px solid var(--accent), borderRadius: 6, marginTop: 16, fontSize:
   13, color: var(--accent-deep)`. Content: `🆕 NEW pattern vào #2 · hook
   X rớt từ #2 → #4`.
3. **TL;DR** — kicker `TÓM TẮT`, title "Điều bạn nên biết". Body: serif
   lead 22px (`answer.jsx:107-115`) + 3-col `SumStat` grid (`answer.jsx:
   117-124`, `borderTop: 1px solid var(--ink), borderBottom: 1px solid
   var(--ink)`, marginTop 24).
4. **`HookFindings × 3`** (positive) — kicker `BẰNG CHỨNG · 3 HOOK`,
   title "Pattern đang thắng, xếp theo retention" (`answer.jsx:128-163`).
   `display: flex, flexDirection: column, gap: 16`. Each `HookFinding`
   gains three new sub-rows below the existing `insight` paragraph
   (within the middle column of the 40px / 1fr / auto grid):
   - **Lifecycle row** — `marginTop: 10, display: flex, gap: 14, flexWrap:
     wrap, fontFamily: var(--mono), fontSize: 11, color: var(--ink-3)`.
     Content: `Xuất hiện {first_seen} · Đỉnh {peak} · {momentum_label}`
     where `momentum_label ∈ {"đang lên" (var(--accent)), "đứng yên"
     (var(--ink-3)), "đang giảm" (var(--ink-2))}`.
   - **Contrast row** — `marginTop: 8, fontSize: 12, color: var(--ink-2),
     lineHeight: 1.5`. Content: `Thắng vì: {why_this_won} · So với:
     "{contrast_against.pattern}"`.
   - **Prerequisites row** — `marginTop: 8, display: flex, gap: 6,
     flexWrap: wrap`. Each prereq: `chip mono, fontSize: 10, padding:
     2px 8px, background: var(--canvas-2), color: var(--ink-3)`.
5. **`WhatStalled × 2..3`** (negative) — **THE NON-NEGOTIABLE, see §5
   below.** Kicker `ĐÃ THỬ NHƯNG RƠI` (mono uc 10px, letterSpacing
   0.18em, `color: var(--gv-danger)`), title "Pattern không còn hiệu
   quả". Same layout as `HookFinding` but: `borderLeft: 3px solid
   var(--gv-danger)` (vs accent), rank serif greyed (`var(--ink-4)`
   instead of `var(--ink-3)`), `RETENTION` value w/o ▲ chip, `delta`
   shown as `▼ {delta}` in `var(--ink-2)`. Plus `why_stalled` paragraph
   in place of `insight` (same 13.5px serif, `var(--ink-2)`). Lifecycle
   row reads `{first_seen} · Đỉnh {peak} · đang giảm`. The
   `--gv-danger` token is added to `src/app.css` in **C.0.6** (see
   "Token additions" below) — value seeded from the Phase B accent-red
   precedent; final hex pinned in C.0.6 design review.
6. **`EvidenceVideos × 6`** — kicker `VIDEO MẪU`, title "6 video dùng
   pattern này đang bùng nổ" (`answer.jsx:166-180`). 3-col grid, gap 14;
   ≤ 1100 → 2-col, ≤ 720 → 1-col. Reuses `EvidenceCard`.
7. **`PatternCells` 2×2** — kicker `PATTERNS`, title "Điểm chung của 47
   video thắng" (`answer.jsx:183-222`). 2×2 grid wrapped in `border: 1px
   solid var(--ink)`. Cells: Thời lượng vàng / Thời điểm hook / Nhạc
   nền / CTA. Each `PatternCell` = kicker (mono uc 10px) + serif finding
   (28px) + chart slot (60px min) + detail text (13px ink-3).
8. **`ActionCards × 3` with forecast** — kicker `BƯỚC TIẾP THEO`, title
   "Biến insight thành video" (`answer.jsx:224-254`). `gridTemplateColumns:
   repeat(3, 1fr), gap: 12`. Each card gains a **forecast row** above the
   existing CTA strip: `marginTop: 10, padding: 8px 10px, background:
   {primary ? rgba(255,255,255,0.08) : var(--canvas-2)}, borderRadius: 4,
   fontSize: 11, fontFamily: var(--mono)`. Content: `Dự kiến: {forecast.
   expected_range} view (kênh trung bình {forecast.baseline})`.

**Empty state** (Pattern, sample_size < 30): render `ConfidenceStrip` with
"MẪU MỎNG" chip + `HumilityBanner` (`background: var(--canvas-2), border:
1px solid var(--rule), borderRadius: 8, padding: 16 18, fontSize: 14,
lineHeight: 1.55`). Skip `HookFindings[2..3]` and `WhatStalled` entirely.
Keep TL;DR + 3 `EvidenceVideos`. **Layout never collapses asymmetrically;
sections render their empty rows or hide cleanly with the rest of their
section.**

### Data model (all from §J `Pattern`)

`Pattern` payload, persisted in `answer_turns.payload` (turn 0). Source
tables / RPCs:

| Field | Source |
|---|---|
| `confidence.{sample_size, window_days, niche_scope, freshness_hours}` | `niche_intelligence` + `video_corpus` aggregations; `freshness_hours = now() - max(video_corpus.created_at)` for the niche |
| `wow_diff.{new_entries, dropped, rank_changes}` | new RPC `pattern_wow_diff_7d(niche_id INT)` — **reads from `video_patterns` table** (landed 2026-04-29 in `20260429120000_video_patterns_reconcile.sql`; carries hook-signature hashes + weekly instance counts + delta columns, exactly the shape `wow_diff` needs) rather than re-aggregating from `hook_effectiveness` row by row |
| `tldr.thesis` | Gemini bounded ≤ 280 chars, cached on `answer_turns.payload` |
| `tldr.callouts[3]` | aggregated from `hook_effectiveness` (count, retention, sample) |
| `findings[3]: HookFinding` | `hook_effectiveness` ranked by `avg_views * retention`, top 3, joined to `video_corpus` for evidence ids; `lifecycle.first_seen` from `min(video_corpus.created_at)` for that hook_type, `peak` from peak-week aggregation, `momentum` from 14-day slope |
| `findings[i].contrast_against` | runner-up hook in same niche; `why_this_won` Gemini bounded ≤ 200 chars |
| `findings[i].prerequisites[]` | static template per hook family (`shared/data/hook-prereq-templates.ts`); falls back to `[]` if unmapped |
| `findings[i].insight` | Gemini bounded ≤ 200 chars, grounded in `contrast_against` |
| `what_stalled[2..3]: HookFinding` | hooks where current 7d retention is in bottom quartile of niche **and** had top-3 rank in the prior 7-day window. If `< 2` qualify, `what_stalled = []` with `confidence.what_stalled_reason: "ngách quá thưa…"` instead |
| `what_stalled[i].why_stalled` | Gemini bounded ≤ 200 chars |
| `evidence_videos[6]: EvidenceCard` | top 6 `video_corpus` rows tagged with one of the 3 winning hook_types, sorted by views desc, deduped by creator |
| `patterns[4]: PatternCell` | duration band (mode), hook timing (median), sound mix (% original), CTA family (mode) — all from `niche_intelligence` and `video_corpus.analysis_json` |
| `actions[3]: ActionCard with forecast` | static templates (open Xưởng Viết / phân tích kênh / theo dõi trend) + `forecast.expected_range` derived from B.4 forecast formula (`hook_score × duration_band × niche median`) |
| `sources[]: SourceRow` | tally of distinct video_ids, creators, scanned channels — used in right rail |
| `related_questions[4]` | Gemini bounded list, cached |

### Fixture mapping (design → backend)

Source fixture: `EVIDENCE_VIDEOS` (`answer.jsx:493-500`) + inline literals.
**Fixtures are the contract; the backend serves them, not the other way
around.**

| Design field (JSX literal) | `Pattern.payload` field | Source |
|---|---|---|
| `EVIDENCE_VIDEOS[i].creator` | `evidence_videos[i].creator_handle` | `video_corpus.creator_handle` |
| `EVIDENCE_VIDEOS[i].title` | `evidence_videos[i].title` | `video_corpus.title` |
| `EVIDENCE_VIDEOS[i].views` ("412K") | `evidence_videos[i].views` (raw int, formatted client-side) | `video_corpus.views` |
| `EVIDENCE_VIDEOS[i].ret` ("78%") | `evidence_videos[i].retention` (numeric 0–1) | `video_diagnostics.retention_curve` last point |
| `EVIDENCE_VIDEOS[i].dur` ("0:28") | `evidence_videos[i].duration_sec` (int) | `analysis_json.duration_seconds` |
| `EVIDENCE_VIDEOS[i].bg` ("#1F2A3B") | `evidence_videos[i].bg_color` | seeded server-side from `NICHE_TILE_COLORS[niche_id][i % 6]` (precedent: `channel_analyze.py`) |
| `EVIDENCE_VIDEOS[i].hook` | `evidence_videos[i].hook_family` | `hook_effectiveness.hook_type` joined via `video_corpus.hook_type` |
| `HookFinding.pattern` ("Mình vừa test ___ và") | `findings[i].pattern` | `hook_effectiveness.hook_type` |
| `HookFinding.retention` ("74%") | `findings[i].retention.value` | `hook_effectiveness.avg_retention` |
| `HookFinding.delta` ("+312%") | `findings[i].delta.value` | computed: `(avg_views / niche_avg_views) - 1`, formatted with sign client-side |
| `HookFinding.uses` (214) | `findings[i].uses` | `hook_effectiveness.sample_size` |
| `HookFinding.insight` (paragraph) | `findings[i].insight` | Gemini bounded |
| `HookFinding.videos: [0,1]` (indices into `EVIDENCE_VIDEOS`) | `findings[i].evidence_video_ids[]` | `findings[i]` join to `evidence_videos[]` by `video_id` |
| New: lifecycle row `Xuất hiện {first_seen} · Đỉnh {peak} · {momentum}` | `findings[i].lifecycle: {first_seen, peak, momentum}` | aggregations described above |
| New: contrast row `Thắng vì: {why_this_won} · So với: "{pattern}"` | `findings[i].contrast_against: {pattern, why_this_won}` | aggregator + Gemini |
| New: prerequisites chips | `findings[i].prerequisites[]` | static template lookup |
| New: `WhatStalled` rows (same shape) | `what_stalled[]` | aggregator described above |
| `SumStat` 3 callouts (`answer.jsx:121-123`) | `tldr.callouts[3]: {label, value, trend, tone}` | aggregations |
| `lead` paragraph | `tldr.thesis` | Gemini |
| `PatternCell` 4 cells | `patterns[4]: {title, finding, detail, chart_kind}` | aggregator (chart_kind ∈ `{duration, hook_timing, sound_mix, cta_bars}` resolves client-side to the existing chart components in `answer.jsx:575-633`) |
| `ActionCard` (3) — title/sub/cta | `actions[3]: {icon, title, sub, cta, primary}` | static templates |
| New: `ActionCard` forecast row | `actions[i].forecast: {expected_range, baseline}` | B.4 forecast formula |
| `Sources` rows (`answer.jsx:755-758`) | `sources[]: {kind, label, count, sub}` | aggregator |
| `RelatedQs` 4 chips | `related_questions[4]` | Gemini |
| `ConfidenceStrip` "N=47 · 7 ngày · Tech · cập nhật 3h trước" | `confidence: {sample_size, window_days, niche_scope, freshness_hours}` | `niche_intelligence` + corpus |
| `WoWDiffBand` "🆕 NEW pattern vào #2" | `wow_diff: {new_entries[], dropped[], rank_changes[]}` | `pattern_wow_diff_7d` RPC |

**Client-side only (no backend field needed):**
- "M:SS" duration formatting from `duration_sec`.
- View "K"/"M" abbreviation from raw int.
- `momentum_label` Vietnamese copy from enum.
- `chart_kind` → component map: `{duration: <DurationChart/>,
  hook_timing: <HookTimingChart/>, sound_mix: <SoundMix/>, cta_bars:
  <CtaBars/>}` (all already in `answer.jsx:575-633`).
- "MẪU MỎNG" chip visibility from `confidence.sample_size < 30`.
- `ConfidenceStrip` freshness `cập nhật {n}h trước` formatted from
  `freshness_hours`.

### New tables / migrations

- `supabase/migrations/2026XXXXXXXXXX_pattern_wow_diff_rpc.sql`:

  ```sql
  -- Reads from video_patterns (20260429120000_video_patterns_reconcile.sql)
  -- which already stores per-hook-signature instance counts + weekly deltas.
  -- Avoid re-aggregating from hook_effectiveness here.
  CREATE OR REPLACE FUNCTION public.pattern_wow_diff_7d(p_niche_id INT)
  RETURNS TABLE (
    hook_type   TEXT,
    rank_now    INT,
    rank_prior  INT,
    rank_change INT,
    is_new      BOOLEAN,
    is_dropped  BOOLEAN
  )
  LANGUAGE sql STABLE SET search_path = public AS $$
    WITH now7 AS (
      SELECT hook_signature, instance_count_7d FROM video_patterns
      WHERE niche_id = p_niche_id AND week_end = date_trunc('week', now())
    ), prior7 AS (
      SELECT hook_signature, instance_count_7d FROM video_patterns
      WHERE niche_id = p_niche_id AND week_end = date_trunc('week', now()) - interval '7 days'
    ) SELECT ... ;
  $$;
  GRANT EXECUTE ON FUNCTION public.pattern_wow_diff_7d(INT) TO service_role;
  ```

  (Implementation deferred to C.2.1; signature frozen here so frontend
  type-gen runs in parallel.)

### New Cloud Run module: `report_pattern.py`

- `build_pattern_report(niche_id, query, intent_type, window_days) →
  PatternPayload` — top-level entry. Loads `niche_intelligence`,
  `hook_effectiveness`, `video_corpus`, `pattern_wow_diff_7d`. Returns a
  pydantic-validated `PatternPayload`.
- `_compute_findings(...)` → 3 positive `HookFinding` rows.
- `_compute_what_stalled(...)` → 2–3 negative `HookFinding` rows; returns
  `[]` + `reason` when corpus too thin.
- `_compute_lifecycle(hook_type, niche_id) → {first_seen, peak,
  momentum}` — pure SQL, deterministic.
- `_compute_contrast(hook_type, runner_up_hook_type) → {pattern,
  why_this_won}` — Gemini bounded.
- `_compute_forecast(action_id, niche_id, picks) → {expected_range,
  baseline}` — B.4 forecast formula.
- All Gemini calls cached on `answer_turns.payload` after the turn
  inserts; no re-roll on session re-open.

### New Cloud Run endpoints

- `POST /answer/sessions/:id/turns` — extended to dispatch to
  `report_pattern.build_pattern_report` when
  `format ∈ {pattern, wo_diff_pattern, lifecycle_pattern}`. Streams the
  same SSE shape as C.1 fixture; finalizes with the validated payload.

### Frontend: extends `/app/answer` route

- `src/components/v2/answer/pattern/` directory:
  - `ConfidenceStrip.tsx`
  - `WoWDiffBand.tsx`
  - `HookFinding.tsx` (extended from `answer.jsx:440-487` with the
    three new sub-rows)
  - `WhatStalledRow.tsx` (the negative variant — separate component to
    keep audit-grep clean)
  - `HumilityBanner.tsx`
  - `PatternBody.tsx` (composes the 8 sections in render order)
- TanStack Query: same `['answer-session', session_id]` key; payload type
  narrowed via `payload.report.kind === "pattern"` discriminant.

### New design primitives

| Component | Description | Source |
|---|---|---|
| `ConfidenceStrip` | Mono band under `QueryHeader`. `padding: 12px 16px, background: var(--canvas-2), border: 1px solid var(--rule), borderRadius: 8`. Includes optional thin-corpus chip. | NEW (per `phase-c-report-formats.md` §2.1) |
| `WoWDiffBand` | Optional accent band above TL;DR. `padding: 10px 14px, background: var(--accent-soft), border: 1px solid var(--accent), borderRadius: 6`. | NEW |
| `HumilityBanner` | Box `padding: 16 18, background: var(--canvas-2), border: 1px solid var(--rule), borderRadius: 8, fontSize: 14`. Always shown when `confidence.sample_size < threshold`. | NEW |
| `HookFinding` (extended) | Adds lifecycle row, contrast row, prerequisites row inside the existing 40px / 1fr / auto grid. | `answer.jsx:440-487` + new |
| `WhatStalledRow` | Negative variant: `borderLeft: 3px solid var(--gv-danger)`, rank in `var(--ink-4)`, `delta` shown as `▼` in `var(--ink-2)`, `why_stalled` paragraph. Consumes the `--gv-danger` token added in C.0.6. | NEW |
| `ActionCard` (extended) | Existing card (`answer.jsx:639-671`) + forecast row above CTA strip. | `answer.jsx:639-671` + new |
| `PatternCell` | Existing 2×2 grid cell. Composed unchanged. | `answer.jsx:553-573` |
| `PatternBody` | Composes the 8 sections in fixed render order. The site of the "render order is locked" rule. | NEW |

### C.2 milestones

1. **C.2.1** (3d) — `pattern_wow_diff_7d` RPC migration + `report_pattern.
   py` module skeleton + pydantic `PatternPayload` schema (mirrors §J) +
   pytest covering empty / thin-corpus / full / WhatStalled-empty cases.
2. **C.2.2** (4d) — `_compute_findings` + `_compute_what_stalled` +
   `_compute_lifecycle` + `_compute_contrast` + Gemini bounded prompts +
   credit deduction wiring. **Adds the `WhatStalled` non-negotiable
   acceptance test: payload must include either `what_stalled[2..3]` or
   `what_stalled = [] && confidence.what_stalled_reason ≠ null`.**
3. **C.2.3** (4d) — frontend Pattern body: `ConfidenceStrip`, `WoWDiffBand`,
   extended `HookFinding`, `WhatStalledRow`, extended `ActionCard`
   (forecast row), `HumilityBanner`, `PatternBody` composer. Replaces the
   C.1 placeholder `AnswerBlock`.
4. **C.2.4** (1d) — retire `trend_spike` + `content_directions` quick-action
   chat CTAs from `/app/chat` in favour of `/app/answer` redirect (chat
   continues to ingest typed `trend_spike` / `content_directions` queries
   for one release; emits `chat_pattern_redirect` event so we can measure
   migration). Updates `intent-router.ts` to add
   `INTENT_DESTINATIONS["trend_spike"] = "answer:pattern"` etc.
5. **C.2.5** (1d) — **Design audit** — compare shipped Pattern body
   against `answer.jsx` + new section specs. Specifically audits:
   `WhatStalled` red-accent border, lifecycle row mono spacing,
   prerequisites chip styling, forecast row contrast on primary
   `ActionCard`. Produce
   `artifacts/qa-reports/phase-c-design-audit-pattern.md`. Same token
   gate. **Non-negotiable: C.2 cannot close without (a) green audit and
   (b) the `WhatStalled` acceptance test passing in CI.**
6. **C.2.6** (0.5d) — shell smoke `artifacts/qa-reports/smoke-answer-pattern.sh`:
   curl `POST /answer/sessions/:id/turns` with intent `trend_spike`,
   assert HTTP 200, payload validates, `what_stalled` either has 2–3
   entries or has `confidence.what_stalled_reason`.

### C.2 checkpoint (measure for 2 weeks post-ship)

Gate metric: **≥ 25% of Pattern sessions issue at least one follow-up
turn within 10 minutes of the primary turn completing.** (Operational:
`answer_turn_append` count where `kind != "primary"` per session,
group by 10-min window after `kind === "primary"` create.)

If gate fails after 2 weeks: pause C.3, revisit whether the report's
density is too high or the `FollowUpComposer` placement is wrong.

---

## C.3 — Ideas format (~1.5 weeks; +1 week if `idea-directions.jsx` is
commissioned in C.0.2)

> **Design source**: `artifacts/uiux-reference/screens/answer.jsx`
> primitives reused as scaffolding (per C.0.2 default re-scope decision).
> If C.0.2 produces an `idea-directions.jsx` reference, the spec below
> picks up its px values 1:1 — same kicker / token / spacing patterns as
> Phase B screens.

Covers intents 15 (`brief_generation`), 16 (`hook_variants`), plus 19 when
classified as idea-family.

### Exact design spec (default — re-scoped from `answer.jsx`)

Render order — locked.

1. **`ConfidenceStrip`** — same as Pattern.
2. **`LeadParagraph`** — kicker `BRIEF`, title "5 ý tưởng video tuần này".
   Body: serif 18px, lineHeight 1.5, ink-2, max-width 720, copy bounded
   to 2–3 sentences ("Dựa trên N video thắng trong ngách X, đây là 5
   kịch bản có retention cao nhất. Mỗi kịch bản kèm slide-by-slide.").
3. **`IdeaBlocks × 5`** — kicker `Ý TƯỞNG · {NN} VIDEO`, no shared title.
   Each `IdeaBlock` (composed from `AnswerBlock` + `HookFinding`-shape
   + custom rows):
   - Outer: `border: 1px solid var(--rule), background: var(--paper),
     padding: 22 24, marginBottom: 16, display: grid,
     gridTemplateColumns: 60px 1fr 220px, gap: 20`.
   - Left col: serif rank `01..05` (40px, ink-3, lineHeight 0.9).
   - Middle col:
     - Title (serif 22px, fontWeight 500, lineHeight 1.25,
       letterSpacing -0.01em).
     - Mono kicker row: `tag` chip (`chip mono, fontSize: 10`) +
       `confidence` mono `N=N · K creator` (12px, ink-4).
     - `angle` paragraph (14px, ink-2, lineHeight 1.55, marginTop 8).
     - `why_works` paragraph (13px, ink-3, lineHeight 1.5, marginTop 8)
       with citation `sup` matching `HookFinding` (`answer.jsx:470-473`).
     - **Hook callout** (NEW): `marginTop 12, padding: 10 14, background:
       var(--ink), color: var(--canvas), borderRadius: 4, fontFamily:
       var(--mono), fontSize: 14, fontWeight: 500`. Content: the hook
       phrasing.
     - **Slides accordion** (collapsible, NEW): `marginTop 10, border:
       1px solid var(--rule), borderRadius: 6`. Header row (`padding:
       10 14, fontSize: 12, color: var(--ink-3), display: flex,
       justifyContent: space-between`) `Slide-by-slide (6 slide)` +
       chevron. Body when expanded: 6 numbered rows (`grid: 28px 1fr,
       gap: 12, padding: 10 14, borderTop: 1px solid var(--rule)`).
     - **Prerequisites row** (NEW): `marginTop 10`, same chip styling
       as Pattern.
   - Right col:
     - `metric` block: kicker (mono uc 9px) + serif value (28px) +
       sub-mono range (11px ink-4). Example: `RETENTION DỰ KIẾN /
       72% / 64–80%`.
     - `style` chip (`chip-accent`).
     - `evidence` (NEW): 2 mini `EvidenceCard` thumbnails stacked, each
       `aspect-ratio: 9/12, width: 100%` — clicking → `/video`.
4. **`StyleCards × 5`** — kicker `PHONG CÁCH`, title "5 hướng quay song
   song". 5-col flex (≤ 1100 → 2-col, ≤ 720 → 1-col). Each card:
   `border: 1px solid var(--rule), padding: 14, fontSize: 13, ink-2`.
   Header: `name` (serif 16px, fontWeight 500). Body: `desc` (12px ink-3).
   Footer: `paired_ideas[]` mono (10px ink-4) → `Cho ý tưởng #1, #3`.
5. **`StopDoing × 5`** — kicker `BỎ NGAY`, title "5 thói quen rớt view".
   Each row: `display: grid, gridTemplateColumns: 80px 1fr 1fr,
   borderBottom: 1px solid var(--rule), padding: 14 16`. Cols: rank serif
   (28px ink-4) / `bad → why` (13px ink-2) / `fix` (13px accent-deep
   bg `var(--accent-soft)`).
6. **`ActionCards × 2`** — same shape as Pattern, with forecast row.
   Defaults: "Mở Xưởng Viết với ý tưởng #1" (primary, routes to
   `/script?topic=…&hook=…`) + "Lưu cả 5 ý tưởng" (secondary, calls
   `POST /answer/sessions/:id/templatize`).

**Variant mode (intent 16, `hook_variants`):** Suppresses `StopDoing`.
`IdeaBlocks` collapse to hook variants only — the hook callout dominates
(`fontSize: 18`), `slides[6]` becomes `bullets[2..3]`, `style` and
`evidence` cards stay. `LeadParagraph` copy switches to "5 cách viết hook
'{seed}'".

**Empty state** (Ideas, `sample_size < 60`): `HumilityBanner` + reduce to
`IdeaBlocks × 3` + skip `StopDoing`.

### Data model (all from §J `Ideas`)

| Field | Source |
|---|---|
| `confidence.*` | same as Pattern |
| `lead` | Gemini bounded |
| `ideas[5]: IdeaBlock` | aggregator joins top 5 winning angles per niche from `video_corpus` × `hook_effectiveness`; Gemini fills `angle`, `why_works`, `hook`, `slides[6]` per idea |
| `ideas[i].evidence_video_ids[2]` | top-2 sample videos for the angle |
| `ideas[i].metric: {label, value, range}` | derived from `niche_intelligence` retention quartiles for the angle's hook family |
| `ideas[i].prerequisites[]` | same template lookup as Pattern findings |
| `ideas[i].confidence: {sample_size, creators}` | aggregator counts |
| `style_cards[5]: StyleCard` | 5 visual styles from `niche_intelligence.style_distribution` (new field — see C.3.1 migration) |
| `stop_doing[5]: StopRow` | bottom 5 hook patterns by retention in last 14d, w/ Gemini-generated `why` + `fix` |
| `actions[2]` | static templates + forecast |

### Fixture mapping (design → backend)

For every `IdeaBlock` field, the backend serves it; the frontend renders
without inferring. Same fixture-as-contract rule as Pattern.

| Design field | Response field | Source |
|---|---|---|
| `IdeaBlock.title` (serif 22px) | `ideas[i].title` | Gemini bounded ≤ 80 chars |
| `IdeaBlock.tag` chip | `ideas[i].tag` | enum (`tutorial / reaction / listicle / story / explainer`) |
| `IdeaBlock.angle` paragraph | `ideas[i].angle` | Gemini bounded ≤ 240 chars |
| `IdeaBlock.why_works` w/ citations | `ideas[i].why_works` (text) + `ideas[i].evidence_video_ids[]` | Gemini + corpus |
| `IdeaBlock.hook` callout text | `ideas[i].hook` | Gemini bounded ≤ 100 chars |
| `IdeaBlock.slides[6]` accordion | `ideas[i].slides[6]: {step, body}` | Gemini bounded |
| `IdeaBlock.metric` ("RETENTION 72%, 64–80%") | `ideas[i].metric: {label, value, range}` | aggregator |
| `IdeaBlock.prerequisites` chips | `ideas[i].prerequisites[]` | static template |
| `IdeaBlock.confidence` ("N=12 · 5 creator") | `ideas[i].confidence: {sample_size, creators}` | aggregator |
| `IdeaBlock.style` chip ("Quay handheld") | `ideas[i].style` | derived from `style_cards` mapping |
| `IdeaBlock.evidence` 2 thumbs | `ideas[i].evidence_video_ids[2]` | corpus join |
| `StyleCard.name`, `desc`, `paired_ideas[]` | `style_cards[i]` | aggregator + Gemini for `desc` |
| `StopRow.bad`, `why`, `fix` | `stop_doing[i]` | aggregator + Gemini |
| `ActionCard` | same as Pattern | static |

### New tables / migrations

- `supabase/migrations/2026XXXXXXXXXX_niche_intelligence_styles.sql` —
  adds `style_distribution JSONB DEFAULT '[]'` column to
  `niche_intelligence`, populated by the existing nightly batch
  refresher.

### New Cloud Run module: `report_ideas.py`

- `build_ideas_report(niche_id, query, intent_type, window_days, variant
  ∈ {standard, hook_variants}) → IdeasPayload`.
- `_compute_ideas(...)` → 5 `IdeaBlock` rows.
- `_compute_style_cards(...)` → 5 `StyleCard` rows.
- `_compute_stop_doing(...)` → 5 `StopRow` rows.
- Gemini bounded per-field; cached.

### New Cloud Run endpoints

- `POST /answer/sessions/:id/turns` extended for
  `format ∈ {ideas, ideas_variant}` — dispatches to
  `report_ideas.build_ideas_report`.

### Frontend: extends `/app/answer` route

- `src/components/v2/answer/ideas/`:
  - `IdeaBlock.tsx`
  - `StyleCard.tsx`
  - `StopRow.tsx`
  - `IdeasBody.tsx`

### New design primitives

| Component | Description | Source |
|---|---|---|
| `IdeaBlock` | Composed: 60px / 1fr / 220px grid; serif rank; title + kicker + angle + why_works (w/ citation) + hook callout + slides accordion + prereqs; right col metric + style chip + 2 evidence thumbs. | NEW (default re-scope from `answer.jsx`) |
| `StyleCard` | Border card; serif name + desc + paired_ideas mono row. | NEW |
| `StopRow` | 3-col grid (rank / bad+why / fix). FIX cell `background: var(--accent-soft), color: var(--accent-deep)`. | NEW |
| `IdeasBody` | Composes the 6 sections in fixed render order. | NEW |

### C.3 milestones

1. **C.3.1** (1d) — `style_distribution` migration + nightly batch refresh
   wiring + pytest covering style aggregation.
2. **C.3.2** (3d) — `report_ideas.py` aggregator + Gemini bounded prompts
   + pydantic `IdeasPayload` schema + pytest covering full / thin-corpus
   (`< 60`) / variant-mode cases.
3. **C.3.3** (4d) — frontend Ideas body: `IdeaBlock`, `StyleCard`,
   `StopRow`, `IdeasBody`. Variant mode toggled by `payload.variant`.
4. **C.3.4** (1d) — retire `brief_generation` quick-action chat CTA;
   redirect to `/app/answer`. Updates `intent-router.ts`.
5. **C.3.5** (1d) — **Design audit** — produce
   `artifacts/qa-reports/phase-c-design-audit-ideas.md`. Token gate
   non-negotiable. Closure rule same as C.2.5.
6. **C.3.6** (0.5d) — shell smoke `smoke-answer-ideas.sh`.

---

## C.4 — Timing format (~1 week)

> **Design source**: `artifacts/uiux-reference/screens/thread-turns.jsx`
> `TimingTurn` (lines 88–192). Covers Heatmap, top-3 windows, headline
> insight. New: `VarianceNote` chip, optional `FatigueBand`.

Covers intent 17 (`timing`); merged with Pattern for intent 18 in C.5.

### Exact design spec (from `thread-turns.jsx:88-192` + new sections)

Render order — locked.

1. **`ConfidenceStrip`** — same shape, but pinned `sample_size` floor 80
   (see §C.0.3).
2. **Headline + insight block** — exactly `thread-turns.jsx:111-140`:
   - Container `display: grid, gridTemplateColumns: 1fr 280px, gap: 24,
     padding: 18 22, border: 1px solid var(--ink), background:
     var(--paper)`.
   - Left: kicker `SƯỚNG NHẤT` (mono uc 10px, letterSpacing 0.16em) +
     serif window (32px, fontWeight 500) + insight paragraph (14px ink-3)
     w/ inline `<strong>` lift multiplier and inline `<span class="mono">`
     for low-window callout.
   - Right: kicker `3 CỬA SỔ CAO NHẤT` + 3 rows (`display: flex,
     alignItems: center, gap: 8, fontSize: 12`): rank mono accent +
     `{day} · {hours}` + `▲ {lift}×` mono blue.
3. **Heatmap** — exactly `thread-turns.jsx:142-183`:
   - Kicker `HEATMAP · 7 NGÀY × 8 KHUNG GIỜ` (mono uc 10px,
     letterSpacing 0.16em, accent, fontWeight 600).
   - Grid `gridTemplateColumns: 28px repeat(8, 1fr), gap: 3, padding: 10,
     background: var(--paper), border: 1px solid var(--rule)`. Cells use
     `tone(v)` map (5 levels).
   - Legend: low → high swatches, source caption right-aligned.
4. **`VarianceNote` chip** — **NEW.** Below heatmap, before any action row.
   `display: inline-flex, padding: 6 12, borderRadius: 999, fontFamily:
   var(--mono), fontSize: 11, fontWeight: 500`.
   - When `top_window.lift_multiplier ≥ 2.0`: `chip chip-lime` "Heatmap
     CÓ ý nghĩa" with check icon.
   - When `1.3 ≤ lift < 2.0`: `chip` (default) "Heatmap đáng cân nhắc".
   - When `lift < 1.3`: `chip chip-amber` "Heatmap CHƯA ổn định — mẫu
     thưa".
5. **`FatigueBand`** (optional) — **NEW.** Renders only when
   `fatigue_band` present (i.e. `top_window` has been `#1` for ≥ 4
   weeks). Shape: same as `WoWDiffBand` from Pattern but in `var(--ink-3)`
   text on `var(--canvas-2)` bg. Copy: "Cửa sổ này đã là #1 trong N
   tuần — có thể đang bão hòa."
6. **`ActionCards × 2`** with forecast — "Lên lịch post vào {top_window}"
   (primary, routes to `/script` if user has script in flight, else copies
   the window) + "Xem kênh đối thủ đang khai thác cửa sổ này" (secondary,
   routes to `/channel?handle=<top_competitor>`).

**Empty state** (`sample_size < 80`): `HumilityBanner` + hide cells with
`value < 5` + show top-3 windows list only.

### Data model (all from §J `Timing`)

| Field | Source |
|---|---|
| `confidence.*` | same as Pattern; `sample_size` is video count in window |
| `top_window: {day, hours, lift_multiplier}` | aggregation: `sum(views) per (day_of_week, hour_bucket)` over `video_corpus` for niche; pick max |
| `top_3_windows[3]` | top 3 from same aggregation |
| `lowest_window: {day, hours}` | same aggregation, min |
| `grid[7][8]: int 0–10` | min-max scaled cell values from the aggregation |
| `variance_note.kind` ∈ `{strong, weak, sparse}` | derived from `top_window.lift_multiplier` thresholds |
| `fatigue_band.weeks_at_top` | nullable; new RPC `timing_top_window_streak(niche_id, top_window) → int` |
| `actions[2]` | static templates + forecast |

### Fixture mapping (design → backend)

| Design field (`thread-turns.jsx:88-192`) | Response field | Source |
|---|---|---|
| `Thứ 7, 18:00 – 22:00` headline | `top_window: {day, hours}` formatted client-side | aggregation |
| `2.8×` strong tag | `top_window.lift_multiplier` | aggregation |
| `3–6h sáng T2` low window | `lowest_window: {day, hours}` | aggregation |
| 3 windows list (right col) | `top_3_windows[3]: {day, hours, lift_multiplier}` | aggregation |
| Heatmap grid 7×8 | `grid[7][8]` | aggregation |
| `tone(v)` color map | client-side from `grid` values | client |
| Source caption "Dữ liệu từ 47 video mẫu · niche Tech" | `confidence.sample_size` + `confidence.niche_scope` | aggregation |
| `VarianceNote` chip | `variance_note: {kind, label}` (label localized server-side) | derived |
| `FatigueBand` text | `fatigue_band: {weeks_at_top, copy}` | RPC + Gemini for copy |
| `ActionCards` | `actions[2]: {icon, title, sub, cta, primary, forecast}` | static |

### New tables / migrations

- `supabase/migrations/2026XXXXXXXXXX_timing_top_window_streak_rpc.sql`:

  ```sql
  CREATE OR REPLACE FUNCTION public.timing_top_window_streak(
    p_niche_id INT, p_day INT, p_hour_bucket INT
  ) RETURNS INTEGER LANGUAGE sql STABLE SET search_path = public AS $$
    -- consecutive ISO weeks where (day, hour_bucket) was the niche top window
  $$;
  GRANT EXECUTE ON FUNCTION public.timing_top_window_streak(INT, INT, INT) TO service_role;
  ```

### New Cloud Run module: `report_timing.py`

- `build_timing_report(niche_id, query, window_days) → TimingPayload`.
- `_aggregate_grid(...)` → 7×8 grid + top/lowest windows.
- `_classify_variance(top_lift) → {kind, label}`.
- `_check_fatigue(niche_id, top_window) → {weeks_at_top, copy} | None`.

### New Cloud Run endpoints

- `POST /answer/sessions/:id/turns` extended for `format == "timing"`.

### Frontend: extends `/app/answer` route

- `src/components/v2/answer/timing/`:
  - `TimingHeadline.tsx`
  - `TimingHeatmap.tsx` (lifted from `thread-turns.jsx:142-183`)
  - `VarianceNote.tsx`
  - `FatigueBand.tsx`
  - `TimingBody.tsx`

### New design primitives

| Component | Description | Source |
|---|---|---|
| `TimingHeatmap` | 7×8 grid, 28px row label col + 8 value cols, `tone(v)` 5-level color map. | `thread-turns.jsx:142-183` |
| `TimingHeadline` | 1fr / 280px split: kicker + serif window + insight paragraph (left); kicker + 3-row top windows list (right). | `thread-turns.jsx:111-140` |
| `VarianceNote` | Single chip; 3 visual states keyed by `kind`. | NEW |
| `FatigueBand` | Optional banner; ink-3 text on canvas-2 bg. | NEW |
| `TimingBody` | Composes the 6 sections in fixed render order. | NEW |

### C.4 milestones

1. **C.4.1** (1d) — `timing_top_window_streak` RPC migration + pytest.
2. **C.4.2** (2d) — `report_timing.py` aggregator + pydantic
   `TimingPayload` schema + pytest covering full / thin-corpus / fatigued
   cases.
3. **C.4.3** (2d) — frontend Timing body: `TimingHeatmap` (lifted),
   `TimingHeadline`, `VarianceNote`, `FatigueBand`, `TimingBody`.
4. **C.4.4** (0.5d) — retire `timing` quick-action chat CTA; route to
   `/app/answer`.
5. **C.4.5** (1d) — **Design audit** —
   `artifacts/qa-reports/phase-c-design-audit-timing.md`. Token gate.
   Closure rule same as C.2.5.
6. **C.4.6** (0.5d) — shell smoke `smoke-answer-timing.sh`.

---

## C.5 — Generic fallback + multi-intent merge (~1 week)

> **Design source**: `artifacts/uiux-reference/screens/thread-turns.jsx`
> `GenericTurn` (lines 364–388). New: `OffTaxonomyBanner`,
> `ConfidenceStrip` `FALLBACK` mode.

Covers intent 20 (`follow_up_unclassifiable`); also lands the multi-intent
merge rules from §A.4.

### Exact design spec (from `thread-turns.jsx:364-388` + new sections)

Render order — locked.

1. **`ConfidenceStrip` (FALLBACK mode)** — `chip chip-amber` "FALLBACK ·
   intent thấp" pinned at the start of the strip; rest of the strip
   shows `sample_size` and `window_days` only (no niche scope, since
   classifier didn't decide).
2. **`OffTaxonomyBanner`** — **NEW.** `padding: 14 18, background:
   var(--canvas-2), border: 1px dashed var(--ink-4), borderRadius: 8,
   fontSize: 14, lineHeight: 1.55, color: var(--ink-2)`. Copy: "Câu hỏi
   này ngoài taxonomy — gợi ý: dùng Soi Kênh / Xưởng Viết / Tìm KOL thay
   vì đào sâu ở đây." Below: 3 chip buttons (each `chip` with relevant
   icon) routing to `/channel`, `/script`, `/kol`.
3. **`NarrativeAnswer`** — kicker `TRẢ LỜI`, body 1–2 serif paragraphs
   (`thread-turns.jsx:367-375`); LLM is instructed to hedge explicitly
   via system prompt.
4. **`EvidenceVideos × 3`** — same `EvidenceCard` 3-col grid as Pattern
   has, but only 3 cards. (`thread-turns.jsx:377-381`).
5. **No `ActionCards`** — Generic deliberately omits CTAs; the
   `OffTaxonomyBanner` already routes.

### Multi-intent merge rules implementation

§A.4 cases live in `intent_router.py` (server-side) + `INTENT_DESTINATIONS`
matrix (client-side). C.5 ships:

- **Destination + report case** — when classifier returns `{destination:
  "/video", secondary: "ideas"}`, the destination route receives a
  `?action=ideas` query param. `/app/video` reads it, renders an
  inline `ActionCard` "5 hook variants cho video này" routing to
  `/app/answer?session_id=…&format=ideas`.
- **Report + report (same family)** — classifier merges into one Pattern
  payload with `format_emphasis: "trend_spike+content_directions"`;
  `report_pattern.py` reads emphasis to bias `findings[]` weighting (e.g.,
  prioritize most recent 7d windows when `trend_spike` is in the mix).
- **Report + timing** — classifier returns `format: "pattern"` with
  `subreports: ["timing"]`. `report_pattern.py` calls
  `report_timing.build_timing_report` and inserts the result as a
  `PatternSubreport` (new field on `PatternPayload` per §J extension).
  Pattern body renders the timing block between `PatternCells` and
  `ActionCards`.
- **Everything else** — secondary signals become filter params on the
  primary report; classifier returns `filters: {followers_lt: 500_000}`
  which the aggregator threads into corpus queries.

### Data model (all from §J `Generic`)

| Field | Source |
|---|---|
| `confidence.*` w/ `intent_confidence: "low"` | classifier output |
| `off_taxonomy: {suggestions[3]: {label, route, icon}}` | static template |
| `narrative.paragraphs[]` | Gemini bounded ≤ 2 paragraphs, hedging system prompt |
| `evidence_videos[3]` | top 3 from corpus matching the broadest interpretation of the query |

### Fixture mapping (design → backend)

| Design field (`thread-turns.jsx:364-388`) | Response field | Source |
|---|---|---|
| `TRẢ LỜI` kicker | static client-side | client |
| Narrative paragraph (serif 20px) w/ `<strong>` accent-soft inline | `narrative.paragraphs[]` | Gemini |
| `EvidenceCard × 3` (`EVIDENCE_VIDEOS.slice(0,3)`) | `evidence_videos[3]` | corpus |
| `OffTaxonomyBanner` 3 chips | `off_taxonomy.suggestions[3]` | static |

### New Cloud Run module: `report_generic.py`

- `build_generic_report(query, niche_id?, intent_confidence) →
  GenericPayload`.
- Gemini bounded with hedging system prompt.
- **Length cap (per §J):** `narrative.paragraphs[]` max 2 entries, each
  ≤ 320 chars. Enforced server-side; over-cap responses are truncated
  at the last sentence boundary and logged `[generic-truncated]`.
  `test_report_generic.py` asserts both bounds.

### New endpoint behaviour

- `POST /answer/sessions/:id/turns` extended for `format == "generic"`.
- **Generic is always free** (per C.0.5): credit deduction is skipped
  regardless of `intent_confidence`. The point of the humility format
  is "we couldn't confidently answer this" — charging for that would
  be backwards. Restated here so the C.5 implementation matches the
  C.0.5 contract.

### Frontend: extends `/app/answer` route

- `src/components/v2/answer/generic/`:
  - `OffTaxonomyBanner.tsx`
  - `NarrativeAnswer.tsx`
  - `GenericBody.tsx`
- `src/components/v2/answer/multi/`:
  - `PatternSubreport.tsx` — wraps a `TimingBody` inside a Pattern.

### New design primitives

| Component | Description | Source |
|---|---|---|
| `OffTaxonomyBanner` | Dashed-border canvas-2 box + 3 routing chips. | NEW |
| `NarrativeAnswer` | Serif 20px paragraph block, inline accent-soft `<strong>`. | `thread-turns.jsx:367-375` |
| `GenericBody` | Composes the 4 sections in fixed render order. | NEW |
| `PatternSubreport` | Wraps any other format body inside a Pattern; renders a sub-kicker + reduced spacing. | NEW |

### C.5 milestones

1. **C.5.1** (1d) — `report_generic.py` + pydantic `GenericPayload` +
   Gemini hedging prompt + pytest.
2. **C.5.2** (2d) — frontend Generic body + `OffTaxonomyBanner` +
   `NarrativeAnswer` + `GenericBody`.
3. **C.5.3** (2d) — multi-intent merge implementation: classifier
   subreports field + `report_pattern.py` reads `subreports` and calls
   the right aggregator + `PatternSubreport` frontend wrapper. Pytest
   covers all four merge cases from §A.4.
4. **C.5.4** (1d) — **Design audit** —
   `artifacts/qa-reports/phase-c-design-audit-generic.md`. Token gate.
5. **C.5.5** (0.5d) — shell smoke `smoke-answer-generic.sh`.

---

## C.6 — `/history` restyle (~1 week)

Closes the four token violations and aligns the screen to the
`SessionDrawer` card vocabulary so `/answer` sessions and legacy chat
sessions live consistently. Adds a "Phiên nghiên cứu" filter to surface
`/answer` sessions distinct from `/chat`.

### Exact design spec (lifted from `SessionDrawer`)

- Header: kicker `LỊCH SỬ NGHIÊN CỨU` (mono uc 10px, letterSpacing
  0.18em, ink-4) + serif title `Tất cả các phiên` (28px, fontWeight 500).
- Filter ribbon (`marginTop: 14`): 3 chips — `Tất cả` / `Phiên nghiên
  cứu` (filters `answer_sessions`) / `Hội thoại` (filters
  `chat_sessions`). Active chip `chip-accent`.
- Search input (existing) sits to the right of the filter chips.
- Session list rows: same shape as `SessionDrawer` rows (niche kicker +
  turn count + relative date + serif title), but full-width and grouped
  by date heading (existing pattern). Active row `background:
  var(--accent-soft), borderLeft: 3px solid var(--accent)`.
- Empty state: serif title (24px) + body (15px ink-3) + primary CTA "Bắt
  đầu phân tích →" routing to `/app/answer` (not `/app/chat`).
- Error state: serif body + accent CTA "Thử lại". **Replaces the
  current `text-[var(--purple)]` underline.**

### Token violations to close (the four flagged in
`HistoryScreen.tsx`)

| Line | Violation | Replacement |
|---|---|---|
| 235 | `text-[var(--purple)] underline` | `text-[var(--gv-accent)] underline` (on the `Thử lại` button) |
| 245 | `text-[var(--ink-soft)]` | `text-[var(--gv-ink-3)]` |
| 248 | `text-[var(--ink-soft)] mb-4` | `text-[var(--gv-ink-3)] mb-4` |
| 302 | `<Badge variant="purple">` | `<Badge variant="accent">` — **new variant added to `src/components/ui/badge.tsx` that uses `var(--gv-accent)` + `var(--gv-accent-soft)`**. Do **not** target the legacy `--accent` token; per `src/app.css:100` it still aliases to `--purple-light`, so the swap would keep the color purple. |

The audit grep run as part of C.6.5 must show **0 hits** for `--purple` /
`--ink-soft` / `--border-active` / `--gv-purple-*` in
`src/routes/_app/history/**`.

### Data model

No schema changes. Union happens **server-side via a new Postgres RPC**
(not a client-side merge). Client-side merge would need two separate
TanStack queries with manual interleave on `updated_at`, fragile when
either side paginates. The RPC keeps ordering and pagination authoritative.

```sql
-- supabase/migrations/2026XXXXXXXXXX_history_union_rpc.sql
CREATE OR REPLACE FUNCTION public.history_union(
  p_filter TEXT DEFAULT 'all',  -- 'all' | 'answer' | 'chat'
  p_cursor TIMESTAMPTZ DEFAULT NULL,
  p_limit  INT DEFAULT 20
)
RETURNS TABLE (
  id          UUID,
  type        TEXT,        -- 'answer' | 'chat'
  format      TEXT,        -- 'pattern'|'ideas'|'timing'|'generic' | NULL
  niche_id    INT,
  title       TEXT,
  turn_count  INT,
  updated_at  TIMESTAMPTZ
)
LANGUAGE sql STABLE SET search_path = public AS $$
  -- RLS-bounded by auth.uid(); union of answer_sessions + chat_sessions.
  -- answer_sessions filter: archived_at IS NULL (has the column per C.0.5).
  -- chat_sessions filter: no deleted_at / archived_at filter — migration _036
  -- removed soft-delete on chat_sessions (see CLAUDE.md + _034/_035/_036).
  -- ORDER BY updated_at DESC LIMIT p_limit;
  -- p_cursor is the previous page's tail updated_at for keyset pagination.
$$;
GRANT EXECUTE ON FUNCTION public.history_union(TEXT, TIMESTAMPTZ, INT) TO authenticated;
```

Client renders the row, and on click routes to the matching screen:
`type === 'answer'` → `/app/answer?session=<id>`,
`type === 'chat'` → `/app/chat?session=<id>` (the override-only chat
route per C.7).

Rows visually distinguish by a small mono pill on the right: `NGHIÊN CỨU`
(`chip chip-accent`) for answer rows, `HỘI THOẠI` (`chip` neutral) for
chat rows. No icon, no color beyond the chip — keeps the row scannable.

### Fixture mapping (design → backend)

| Design field | Response field | Source |
|---|---|---|
| Filter chip count badges | `GET /history?counts_only=true` returns `{answer: N, chat: N}` | `count(answer_sessions) + count(chat_sessions)` |
| Row type pill (`NGHIÊN CỨU` / `HỘI THOẠI`) | `type ∈ {answer, chat}` | `history_union` RPC |
| Format sub-pill (Pattern / Ideas / …) | `format` | `history_union` RPC |
| Active row underline | from `useParams().session_id` | router |

### New Cloud Run endpoints

- Extend existing `GET /history` to call the new `history_union` RPC.
  Query params: `?filter=all|answer|chat&cursor=<iso>&limit=20`. Pure
  pass-through to the RPC; no aggregation in the endpoint.

### Frontend

- `src/routes/_app/history/HistoryScreen.tsx` rewrite (not new file).
- New primitive: none — reuses `SessionDrawer` row JSX as a `HistoryRow`
  component (extracted to `src/components/v2/answer/HistoryRow.tsx`,
  shared with the drawer).

### C.6 milestones

1. **C.6.1** (1d) — `history_union` RPC migration + extend `GET /history`
   to call it. Pytest covers union ordering by `updated_at`, keyset
   pagination via `p_cursor`, and the three filter values.
2. **C.6.2** (2d) — `HistoryScreen.tsx` rewrite with filter ribbon, new
   row shape, fixed token violations. Extract `HistoryRow` shared with
   `SessionDrawer`.
3. **C.6.3** (1d) — **Design audit** —
   `artifacts/qa-reports/phase-c-design-audit-history.md`. **Audit
   grep gate must hit 0 across the entire `/history` route.**
4. **C.6.4** (0.5d) — measurement event `history_session_open` with
   `metadata.type ∈ {answer, chat}`.

---

## C.7 — `/chat` retirement (~1 week)

Routes all classifiable intents into `/app/answer` via `intent-router.ts`.
`/app/chat` stays alive for unclassifiable `follow_up` queries only — a
thin Gemini conversational fallback. Quick-action CTAs for report
intents are removed.

### Behaviour change

Updated `intent-router.ts` (and the `INTENT_DESTINATIONS` matrix from
§C.0.1):

```ts
// src/routes/_app/intent-router.ts (final shape, post-C.7)
type Destination =
  | "video" | "channel" | "kol" | "script"
  | "answer:pattern" | "answer:ideas" | "answer:timing" | "answer:generic"
  | "chat";

// The static map handles the 13 fixed intents. follow_up_classifiable
// is dispatched separately by resolveDestination() because it depends
// on the classifier's `subject` field (resolved at call time, not at
// matrix definition time). Keeping the matrix purely string-typed lets
// vitest snapshot it cleanly and lets C.7.5 audit grep it for orphans.
const INTENT_DESTINATIONS: Record<FixedIntentId, Destination> = {
  // ... destination intents unchanged (1-7 per §A.1)
  trend_spike:                  "answer:pattern",
  content_directions:           "answer:pattern",
  subniche_breakdown:           "answer:pattern",
  format_lifecycle_optimize:    "answer:pattern",
  fatigue:                      "answer:pattern",
  brief_generation:             "answer:ideas",
  hook_variants:                "answer:ideas",
  timing:                       "answer:timing",
  content_calendar:             "answer:pattern", // multi-intent merges timing
  follow_up_unclassifiable:     "chat",           // <- the only chat survivor
};

export function resolveDestination(
  intent: ClassifiedIntent,
): Destination {
  if (intent.id === "follow_up_classifiable") {
    return `answer:${intent.subject}` as Destination;
  }
  return INTENT_DESTINATIONS[intent.id];
}
```

`ChatScreen.tsx` `runSend` (the lines 433–537 area) gains a pre-flight
that, when `resolveDestination(intent) !== "chat"`:

1. Creates an `answer_sessions` row server-side via `POST /answer/
   sessions` (with `Idempotency-Key` header per C.0.5).
2. Navigates to `/app/answer?session=<uuid>&q=<seed>` with `replace:
   true`.
3. Returns early; no `insertUser` / `stream` against the chat backend.

**In-flight stream guard.** Pre-flight runs only on the **initial**
`runSend` call. If a chat stream is already in progress, the redirect
is skipped and the existing stream completes; this prevents the C.7
behavior cliff from interrupting active chat sessions. Vitest covers
the "stream already started → no redirect" branch.

The existing `competitor_profile` / `own_channel` short-circuit at
`ChatScreen.tsx:455-478` is the precedent — extend to all report intents.

### Staged rollout (escape hatch)

C.7.1 ships behind a single query-string flag matching the B.4
`channel_to_script` rollout precedent:

- **Default** — all classifiable intents redirect to `/app/answer`.
- **Override** — `?legacy=chat` on any URL bypasses the matrix and
  routes the query through the legacy chat pipeline. Honored for **one
  release** (one full deploy cycle, ~7 days), then removed in C.7.6
  cleanup.
- **Telemetry** — `chat_legacy_override` event fires whenever the
  override is used so we can see if anyone is actually depending on it
  before removal.

The override is a paste-in-URL escape hatch for support, not a
user-facing toggle. No UI exposes it. If the gate metric (`>= 25%
follow-up rate from §C.2 checkpoint`) regresses sharply post-rollout,
support can hand the override URL to affected users while we
investigate.

### `BottomTabBar` impact

`src/components/BottomTabBar.tsx` currently has 5 tabs including
**Chat**. After C.7 the chat tab survives but its **icon + label
swap to "Phiên nghiên cứu"** and routes to `/app/answer` (most-recent
session if one exists, else `/app/answer/new`). The literal `/app/chat`
route stays mounted as a fallback for the override flag and for the
unclassifiable `follow_up` redirect target — no user-discoverable nav
points to it.

C.7.2 ships the swap; the `/app/chat` route stays in `routes.ts`
unchanged (no removal).

### `/app/chat` quick-action retirements

The home / chat empty-state quick-action grid loses these cards:

- "Trend tuần này" (`trend_spike`)
- "Hướng nội dung" (`content_directions`)
- "Brief tuần tới" (`brief_generation`)
- "Hook variants" (`hook_variants`)
- "Đăng giờ nào" (`timing`)
- "Pattern hết trend" (`fatigue`)

Replaced by a single "Mở phiên nghiên cứu mới" card routing to
`/app/answer` with no seed query.

### Data model

No schema. Extends the C.0.1 classifier matrix only.

### C.7 milestones

1. **C.7.1** (2d) — `intent-router.ts` matrix update + `resolveDestination()`
   helper + `ChatScreen.tsx` `runSend` pre-flight redirect for all
   classifiable intents + `?legacy=chat` override + in-flight stream
   guard. Vitest covers the routing matrix snapshot, the override
   bypass, and the "stream already started → no redirect" branch.
2. **C.7.2** (1d) — home / chat empty-state quick-action grid pruning;
   adds single "Mở phiên nghiên cứu mới" card. **Plus the
   `BottomTabBar.tsx` Chat tab swap** (icon + label → "Phiên nghiên
   cứu", route → `/app/answer`); literal `/app/chat` route stays in
   `routes.ts` unchanged for the override + unclassifiable fallback.
3. **C.7.3** (2d) — Cloud Run server-side `intent_router.py` Gemini
   wiring (the C.0.1 medium/low confidence path that defers to LLM).
   Pytest covers high/medium/low confidence flows + budget guard
   (`[classifier-budget]` log + deterministic fallback when daily quota
   exceeded).
4. **C.7.4** (1d) — measurement events `chat_classified_redirect`
   (fires when chat would have handled but redirected to `/answer`),
   `classifier_low_confidence` (fires on Generic fallback),
   `chat_legacy_override` (fires on `?legacy=chat` use). All via
   `logUsage`.
5. **C.7.5** (1d) — **Design audit** —
   `artifacts/qa-reports/phase-c-design-audit-chat-retirement.md`
   confirming the retired CTAs are gone, the new tab + card are
   present, and the classifier matrix is the single source of truth
   (no orphaned routing code paths).
6. **C.7.6** (0.5d, **+1 release after C.7.1**) — remove the
   `?legacy=chat` override + the `chat_legacy_override` event after
   the one-release window closes, contingent on `chat_legacy_override`
   row count being ≤ 5 in the prior 7 days. If higher, escalate before
   removing.

---

## C.8 — Phase B carryovers (~3 weeks; can run in parallel with C.6/C.7)

One milestone per carryover from `phase-b-closure.md` "Open items
carried into Phase C" + "Recommended test backfill" + "Explicitly
deferred". Each carryover is its own atomic feature commit
(`feat(<feature>): …` per `AGENTS.md`).

### C.8.1 — `draft_scripts` table + `script_save` + Copy / PDF / Chế độ quay (1w)

Closes B.4 carryover #1 ("`script_save` persistence") + the three buttons
that ship `title="Sắp có"` today.

**Migration** `supabase/migrations/2026XXXXXXXXXX_draft_scripts.sql`:

```sql
CREATE TABLE draft_scripts (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  niche_id    INTEGER REFERENCES niche_taxonomy(id),
  topic       TEXT NOT NULL,
  hook        TEXT NOT NULL,
  hook_delay_ms INTEGER NOT NULL,
  duration_sec INTEGER NOT NULL,
  tone        TEXT NOT NULL,
  shots       JSONB NOT NULL DEFAULT '[]',  -- ScriptShot[]
  source_session_id UUID REFERENCES answer_sessions(id) ON DELETE SET NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX draft_scripts_user_recent_idx
  ON draft_scripts (user_id, updated_at DESC);

ALTER TABLE draft_scripts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "draft_scripts_select_own" ON draft_scripts
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "draft_scripts_modify_own" ON draft_scripts
  FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
```

**Endpoints**:

- `POST /script/save` — body `{topic, hook, hook_delay_ms, duration,
  tone, shots[], source_session_id?}`. Inserts; returns `{draft_id}`.
- `GET /script/drafts` — list user's drafts.
- `GET /script/drafts/:id` — single draft for restoration.
- `POST /script/drafts/:id/export` — body `{format: "pdf" | "copy"}`.
  Copy: returns text payload formatted for Zalo clipboard paste — no
  formatting characters, mono dur prefixes per shot (matches B.4
  `script_data.py` formatter). No server-state mutation.
  PDF: server-rendered. **Dep decision (C.8.1.0 half-day spike, before
  any code lands):** evaluate WeasyPrint vs ReportLab; default to
  WeasyPrint if its system-package surface (Pango/Cairo) fits the
  Cloud Run container without > 50MB image bloat. Whichever wins is
  added to `cloud-run/pyproject.toml` as a real dep entry **in the
  same PR** as the export endpoint — no "we'll add it later" hedging.
  Fallback: if both fail, ship the Copy path only and disable the PDF
  button with `title="Sắp có"`; record the deferral in C.8 milestones.

**`cloud-run/pyproject.toml` change (C.8.1.0):**

```toml
dependencies = [
  # ... existing ...
  "weasyprint>=63.0",  # or "reportlab>=4.0" per spike outcome
]
```

Plus the matching system-package install line in `cloud-run/Dockerfile`
(WeasyPrint requires `libpango-1.0-0 libcairo2 libpangoft2-1.0-0`). Ship
in the same PR; CI image build proves it works.

**Frontend**:

- `src/routes/_app/script/ScriptScreen.tsx` enables the three buttons.
- "Lưu vào lịch quay" button calls `POST /script/save`, navigates to
  `/app/history?type=script`.
- "Copy" button calls `POST /script/drafts/:id/export?format=copy`,
  copies to clipboard via `navigator.clipboard.writeText`.
- "PDF" button calls `POST /script/drafts/:id/export?format=pdf`,
  triggers download.
- "Chế độ quay" button → routes to `/app/script/shoot/:id` (a new
  read-only view scoped down to mobile-friendly text-only beats — minimal
  new screen, `<200 LOC`).

**Measurement**: `script_save` event — **the deferred B.4 event from
`phase-b-closure.md`** — goes live here.

**Closure**: design audit
`artifacts/qa-reports/phase-c-design-audit-script-save.md` + token
gate + smoke `smoke-script-save.sh`.

### C.8.2 — Gemini upgrade to `POST /script/generate` (3d)

Closes B.4 carryover ("Gemini upgrade to `/script/generate`"). HTTP
contract **frozen** — request and response shapes unchanged. Internal
swap from deterministic scaffold to Gemini-bounded scene generation
inside `cloud-run/getviews_pipeline/script_generate.py`.

Pytest must lock the response shape (re-uses
`cloud-run/tests/test_script_generate.py` shape assertions). Behavioral
change is shot text quality only — frontend is unaffected. Smoke
`smoke-script-generate.sh` runs before/after to confirm shape stability.

Commit: `feat(script-generate): Gemini upgrade with frozen contract`.

### C.8.3 — KOL `match_score` persistence (2d)

Closes B.2 carryover ("KOL `match_score` persistence"). Add nullable
`match_score INTEGER` + `match_score_computed_at TIMESTAMPTZ` to
`creator_velocity` (new migration). `kol_browse.py` reads cached score
when fresh (< 7d), recomputes on miss. Cache invalidates on `profiles.
primary_niche` or `profiles.reference_channel_handles` change via a new
trigger.

Commit: `feat(kol-match-persist): cache match_score in creator_velocity`.

### C.8.4 — `PostingHeatmap` component for `/channel` (3d)

Closes B.3 carryover ("`PostingHeatmap` component for `/channel`").
Implements the deferred primitive `PostingHeatmap` (specced in
`phase-b-plan.md` B.3 New design primitives table). Reuses
`TimingHeatmap` from C.4 with `cell.color` swapped to a single-hue
ramp on `var(--ink)` (no accent — distinguishes from Timing format's
accent ramp). Drops in below the existing `THỜI GIAN POST` KPI on
`/channel` with `marginTop: 24`.

Backend: `channel_analyze.py` adds `posting_heatmap[7][8]` to its
response by aggregating `video_corpus.created_at` for the handle.

Commit: `feat(channel-heatmap): wire PostingHeatmap on /channel`.

### C.8.5 — Real 30d growth wiring (2d)

Closes B.2 deferred item ("KOL growth term — real 30d when
`creator_velocity` lands"). The data pipeline emitted `growth_30d_pct`
during Phase A; `kol_browse.py` currently uses the
`growth_percentile_from_avgs` proxy. Switch to the real column,
backfill any nulls with the proxy, log per-row decisions in the
`[kol-growth]` tag.

Commit: `feat(kol-growth): switch to real 30d growth from creator_velocity`.

### C.8.6 — Primitive render test backfill (3d)

Closes B closure "Recommended test backfill". Five primitive render
tests + two screen-level RTL tests (~200 LOC total per closure §):

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
Query test wrappers. Commit: `test(phase-b-backfill): primitive +
screen-level render tests`.

### C.8.7 — 3–7 day measurement dashboard read (gating, not coding)

Closes B closure "Measurement sanity check". Before any C behavior
change ships to production, the following events must be confirmed live
in the analytics dashboard with non-zero counts over a 3–7 day window:

- `video_screen_load`, `flop_cta_click`, `video_to_script` (B.1 + B.4.5)
- `kol_screen_load`, `kol_pin` (B.2.5)
- `script_screen_load`, `script_generate`, `channel_to_script` (B.4)

If any event is missing or unexpectedly zero, file an issue and pause
the C deploy until resolved. Captured as a gate in C.0.6 spike
close-out and re-checked before C.2.4 (the first behavior-changing
chat redirect).

### C.8 milestones (rolled up)

| # | Carryover | Estimate | Commit |
|---|---|---|---|
| C.8.1 | `draft_scripts` + script save + Copy/PDF/Chế độ quay | 1w | `feat(script-save): persistence + export controls` |
| C.8.2 | Gemini upgrade to `/script/generate` (frozen contract) | 3d | `feat(script-generate): Gemini upgrade with frozen contract` |
| C.8.3 | KOL `match_score` persistence | 2d | `feat(kol-match-persist): cache match_score in creator_velocity` |
| C.8.4 | `PostingHeatmap` for `/channel` | 3d | `feat(channel-heatmap): wire PostingHeatmap on /channel` |
| C.8.5 | Real 30d growth wiring | 2d | `feat(kol-growth): switch to real 30d growth` |
| C.8.6 | Primitive render test backfill | 3d | `test(phase-b-backfill): primitive + screen-level render tests` |
| C.8.7 | 3–7 day measurement dashboard read | gating | n/a (analytics confirmation) |

---

## §J — Data contract (ReportV1 — folded in from `phase-c-report-formats.md` §6)

The §J payload type lands as the discriminated union `ReportV1` in
`src/lib/api-types.ts` and the matching pydantic models in
`cloud-run/getviews_pipeline/report_types.py`. Server validates before
inserting into `answer_turns.payload`. Frontend treats this as the wire.

```ts
// src/lib/api-types.ts (excerpt)

export type ReportV1 =
  | { kind: "pattern"; report: PatternPayload }
  | { kind: "ideas";   report: IdeasPayload }
  | { kind: "timing";  report: TimingPayload }
  | { kind: "generic"; report: GenericPayload };

export type ConfidenceStrip = {
  sample_size: number;
  window_days: number;
  niche_scope: string | null;       // "Tech" | "Beauty/Skincare" | …
  freshness_hours: number;
  intent_confidence: "high" | "medium" | "low";
  what_stalled_reason?: string | null;  // populated when what_stalled = []
};

export type Metric = {
  value: string;     // "74%" — pre-formatted for inline display
  numeric: number;   // 0.74 — for chart math
  definition: string; // "viewers past 15s"
};

export type Lifecycle = {
  first_seen: string;  // ISO date
  peak: string;        // ISO date
  momentum: "rising" | "plateau" | "declining";
};

export type ContrastAgainst = {
  pattern: string;
  why_this_won: string; // ≤ 200 chars
};

export type HookFinding = {
  rank: number;
  pattern: string;
  retention: Metric;
  delta: Metric;
  uses: number;
  lifecycle: Lifecycle;
  contrast_against: ContrastAgainst;
  prerequisites: string[];
  insight: string;             // ≤ 200 chars; for WhatStalled this is why_stalled
  evidence_video_ids: string[];
};

export type SumStat = {
  label: string;
  value: string;
  trend: string;
  tone: "up" | "down" | "neutral";
};

export type EvidenceCardPayload = {
  video_id: string;
  creator_handle: string;
  title: string;
  views: number;
  retention: number;            // 0–1
  duration_sec: number;
  bg_color: string;             // server-seeded hex
  hook_family: string;
};

export type PatternCellPayload = {
  title: string;
  finding: string;
  detail: string;
  chart_kind: "duration" | "hook_timing" | "sound_mix" | "cta_bars";
  chart_data: unknown;          // chart-kind-specific shape; client narrows
};

export type ActionCardPayload = {
  icon: string;
  title: string;
  sub: string;
  cta: string;
  primary?: boolean;
  route?: string;
  forecast: { expected_range: string; baseline: string };
};

export type SourceRow = {
  kind: "video" | "channel" | "creator" | "datapoint";
  label: string;
  count: number;
  sub: string;
};

export type WoWDiff = {
  new_entries: { rank: number; pattern: string }[];
  dropped:     { rank_prior: number; pattern: string }[];
  rank_changes:{ pattern: string; from: number; to: number }[];
};

export type PatternPayload = {
  confidence: ConfidenceStrip;
  wow_diff: WoWDiff | null;
  tldr: { thesis: string; callouts: SumStat[]; /* len 3 */ };
  findings: HookFinding[];     // len 3 — positive
  what_stalled: HookFinding[]; // len 0..3 — negative; if 0, confidence.what_stalled_reason !== null
  evidence_videos: EvidenceCardPayload[];  // len 6
  patterns: PatternCellPayload[];          // len 4
  actions: ActionCardPayload[];            // len 3
  sources: SourceRow[];
  related_questions: string[]; // len 4
  subreports?: { timing?: TimingPayload };  // multi-intent merge slot
};

export type IdeaBlockPayload = {
  id: string;
  title: string;
  tag: string;
  angle: string;
  why_works: string;
  evidence_video_ids: string[];   // len 2
  hook: string;
  slides: { step: number; body: string }[];  // len 6 (2-3 in variant mode)
  metric: { label: string; value: string; range: string };
  prerequisites: string[];
  confidence: { sample_size: number; creators: number };
  style: string;
};

export type IdeasPayload = {
  confidence: ConfidenceStrip;
  lead: string;
  ideas: IdeaBlockPayload[];     // len 5 (or 3 if sample_size < 60)
  style_cards: { id: string; name: string; desc: string; paired_ideas: string[] }[]; // len 5
  stop_doing: { bad: string; why: string; fix: string }[];  // len 5; empty if sample_size < 60
  actions: ActionCardPayload[];  // len 2
  sources: SourceRow[];
  related_questions: string[];
  variant: "standard" | "hook_variants";
};

export type TimingPayload = {
  confidence: ConfidenceStrip;
  top_window: { day: string; hours: string; lift_multiplier: number };
  top_3_windows: { rank: number; day: string; hours: string; lift_multiplier: number }[];
  lowest_window: { day: string; hours: string };
  grid: number[][]; // 7×8
  variance_note: { kind: "strong" | "weak" | "sparse"; label: string };
  fatigue_band: { weeks_at_top: number; copy: string } | null;
  actions: ActionCardPayload[];  // len 2
  sources: SourceRow[];
  related_questions: string[];
};

export type GenericPayload = {
  confidence: ConfidenceStrip;   // intent_confidence === "low"
  off_taxonomy: { suggestions: { label: string; route: string; icon: string }[] };  // len 3
  narrative: { paragraphs: string[] };  // len 1..2
  evidence_videos: EvidenceCardPayload[];  // len 3
  sources: SourceRow[];
  related_questions: string[];
};

export type AnswerSession = {
  id: string;
  user_id: string;
  niche_id: number | null;
  title: string;
  initial_q: string;
  intent_type: string;
  format: "pattern" | "ideas" | "timing" | "generic";
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type AnswerTurn = {
  id: string;
  session_id: string;
  turn_index: number;
  kind: "primary" | "timing" | "creators" | "script" | "generic";
  query: string;
  payload: ReportV1;             // discriminated union
  classifier_confidence: "high" | "medium" | "low";
  intent_confidence: "high" | "medium" | "low";
  cloud_run_run_id: string | null;
  credits_used: number;
  created_at: string;
};
```

This is the LLM-output contract. The UI is a pure function of the
payload. **Missing fields render the matching humility / empty state —
never silent holes.**

---

## Cross-cutting

### Things retired when Phase C lands

- `/app/chat` quick-action CTAs for: `trend_spike`, `content_directions`,
  `brief_generation`, `hook_variants`, `timing`, `fatigue`,
  `format_lifecycle_optimize`, `subniche_breakdown`. Replaced by single
  "Mở phiên nghiên cứu mới" card (C.7.2).
- `SaveCard` component → renamed `TemplatizeCard` (C.1.3). Same visuals,
  new copy + new intent (Lưu / Chia sẻ / PDF wire to template flow in
  C.8.1). The old name is grep-removed.
- Purple-era tokens in `/history` (`var(--purple)`, `var(--ink-soft)`,
  `Badge variant="purple"`) — closed in C.6.

### Deliberately deferred to Phase D

- Everything in `phase-c-report-formats.md` §1.3 (carried forward in
  §A.3 above): commerce/seller, personalized Ship Next, loop closure,
  long-form strategy.
- Intent **#8 `series_audit`** — multi-URL `/video?video_ids=…&mode=
  series`. Needs new `/video` UI work that doesn't exist yet.
- Intent **#9 `own_flop_no_url`** — graceful-degrade flow when user asks
  "tại sao video tôi ít view" without a URL. Needs URL-prompt UX
  scaffolding on `/chat` or `/answer` that we don't want to ship in C.
- KOL **compare mode** (intent #7 `comparison`) — pin tab works, but
  `mode=compare` is new layout work; kept on the carry list (C.8 could
  pick it up if scope opens, but default-deferred).

### Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Low classifier confidence inflates Gemini cost | Medium | C.0.1 budget guard reuses `EnsembleDailyBudgetExceeded` pattern; deterministic fallback when daily quota exceeded; `[classifier-budget]` log tracks consumption |
| Sample-size sparsity per niche (Pattern < 30, Ideas < 60, Timing < 80) | High | C.0.3 adaptive-window policy widens 7d → 14d; below 14d → degrade to Generic; `HumilityBanner` always visible |
| `WhatStalled` corpus coverage too thin to surface 2–3 negatives | Medium | Pydantic schema allows `what_stalled: []` only when `confidence.what_stalled_reason` is set; UI renders an explicit empty row, never a missing section |
| Follow-up turn credit semantics surprise users | Low | C.0.5 sets a simple integer-only policy: **1 credit per primary, 0 per follow-up, 0 for Generic.** `ConfidenceStrip` shows the deduction inline at primary-turn open; pricing copy + chat / answer entry-point copy updated concurrent with C.1 ship |
| In-flight chat stream interrupted by C.7 redirect | Medium | C.7.1 redirect fires only on initial `runSend` pre-flight; in-flight streams continue uninterrupted. Vitest covers the "stream already started" branch that bypasses redirect. Behind a `?legacy=chat` escape hatch for one release per the B.4 precedent |
| Purple-token leakage across `/history` regressing | Low | C.6.3 grep gate; CI lint adds `--purple` / `--ink-soft` / `--border-active` / `--gv-purple-*` to the Phase B token-scan job |
| Token namespace dualism (`--purple` vs `--gv-*`) surfacing on mixed surfaces | Medium | `src/app.css` still defines both the legacy Make tokens (`--purple`, `--ink-soft`, `--accent → --purple-light`) and the `--gv-*` family. New Phase C code uses `--gv-*` exclusively; **composing a legacy Make primitive inside a `/answer` screen would pull in purple shims.** C.1 frontend audit grep must scan the component tree for mixed-namespace consumers, not just files in `src/routes/_app/answer/**`. Full deprecation of `--purple` is a Phase D task, not C. |
| `/answer` session schema change after launch | Low | RLS + service-role-only payload writes; payload validated server-side against pydantic before insert; bad payloads fail the stream rather than persist |
| `script_save` PDF rendering brittle (weasyprint deps) | Medium | C.8.1 spike-day evaluates weasyprint vs lighter alt; export endpoint returns 503 with clear copy if PDF stack fails; "Copy" path always works |
| Multi-intent merge confuses classifier | Medium | C.5.3 pytest covers all four §A.4 cases; observability tag `[multi-intent]` logs every classifier decision that includes a `subreports` field |
| Measurement gate (C.8.7) blocks C deploy | Low | Gate is read-only; if it fails, fix the analytics first (it's already 2 weeks post-B-ship); does not block coding work, only behavior changes |

### Measurement

Product events via `src/lib/logUsage.ts`. New events ship across C
sub-phases:

| Event | Sub-phase | Fires when |
|---|---|---|
| `answer_session_create` | C.1.4 | `POST /answer/sessions` returns 200 |
| `answer_turn_append` | C.1.4 | `POST /answer/sessions/:id/turns` finalizes; `metadata.kind`, `metadata.format` |
| `answer_format_rendered` | C.2.5 / C.3.5 / C.4.5 / C.5.5 | client renders the body section root; `metadata.kind ∈ {pattern, ideas, timing, generic}` |
| `templatize_click` | C.1.4 | `TemplatizeCard` Lưu button click (C.1 placeholder; wires to real templating in C.8.1) |
| `history_session_open` | C.6.4 | `/history` row click; `metadata.type ∈ {answer, chat}` |
| `chat_classified_redirect` | C.7.4 | `ChatScreen.runSend` redirects to `/answer`; `metadata.intent` |
| `classifier_low_confidence` | C.7.4 | classifier returns Generic fallback; `metadata.intent_id` |
| `script_save` | C.8.1 (the deferred B.4 event) | `POST /script/save` returns 200 |
| `pattern_what_stalled_empty` | C.2.5 | Pattern payload ships with `what_stalled = []`; `metadata.reason` |

Existing live B events (per `phase-b-closure.md`) continue:
`video_screen_load`, `flop_cta_click`, `video_to_script`,
`kol_screen_load`, `kol_pin`, `script_screen_load`, `script_generate`,
`channel_to_script`.

C.8.7 gates production C deploy on a 3–7 day dashboard read of the live
B events before any behavior change in C ships.

### Testing strategy

**Backend (`cloud-run/tests/`):**

| File | Covers |
|---|---|
| `test_intent_router.py` | C.0.1 deterministic classifier matrix, all 20 intents → destination/format mapping, confidence thresholds, budget guard fallback |
| `test_answer_session.py` | C.1 create/append/list/archive lifecycle, RLS, payload schema validation rejection on bad JSON |
| `test_report_pattern.py` | `_compute_findings`, `_compute_what_stalled` (incl. empty-with-reason case), `_compute_lifecycle`, `_compute_contrast`; **acceptance: payload always has `what_stalled[2..3]` OR `what_stalled = [] && confidence.what_stalled_reason ≠ null`** |
| `test_report_ideas.py` | `_compute_ideas`, variant-mode collapse, `< 60` thin-corpus fallback, `style_distribution` aggregation |
| `test_report_timing.py` | `_aggregate_grid`, `_classify_variance` thresholds, `_check_fatigue` streak RPC, `< 80` thin-corpus fallback |
| `test_report_generic.py` | hedging prompt bounded output, `OffTaxonomyBanner` suggestion routing |
| `test_multi_intent_merge.py` | All four §A.4 cases including `Pattern.subreports.timing` shape |
| `test_pattern_wow_diff_rpc.py` | RPC NEW / DROPPED / rank-change correctness |
| `test_timing_top_window_streak_rpc.py` | RPC streak counting across week boundaries |
| `test_draft_scripts.py` | C.8.1 save / list / get / export shape |

**Frontend (vitest):**

| File | Covers |
|---|---|
| `AnswerShell.test.tsx` | C.1 shell renders + responsive collapse |
| `ConfidenceStrip.test.tsx` | C.2 thin-corpus chip toggle, freshness formatting |
| `HookFinding.test.tsx` | C.2 lifecycle / contrast / prerequisites rows render |
| `WhatStalledRow.test.tsx` | C.2 negative variant tokens + ▼ delta |
| `IdeaBlock.test.tsx` | C.3 variant mode collapse to bullets |
| `TimingHeatmap.test.tsx` | C.4 cell tone classification |
| `VarianceNote.test.tsx` | C.4 three states by lift threshold |
| `OffTaxonomyBanner.test.tsx` | C.5 chip routing |
| `HistoryScreen.test.tsx` | C.6 filter chip toggling, row type pill, zero-purple-token render |
| `intent-router.test.ts` | C.7 matrix snapshot |

**Shell smokes** (`artifacts/qa-reports/`):

- `smoke-answer-shell.sh` (C.1.6)
- `smoke-answer-pattern.sh` (C.2.6) — **asserts `WhatStalled` invariant**
- `smoke-answer-ideas.sh` (C.3.6)
- `smoke-answer-timing.sh` (C.4.6)
- `smoke-answer-generic.sh` (C.5.5)
- `smoke-script-save.sh` (C.8.1)
- `smoke-script-generate.sh` (C.8.2 — re-runs B.4 smoke pre/post Gemini swap)

**Mandatory design audit per sub-phase**: same gate as Phase B.
Every audit closes with the grep gate (`#[0-9a-fA-F]{3,8}`,
`--ink-soft`, `--purple`, `--border-active`, `--gv-purple-*`,
`Badge variant="purple"`) hitting **0 in new files**.

### Responsive breakpoints (all C surfaces, non-negotiable)

Lifted from `answer.jsx:277-290`. Every new screen must respect these
before the design audit closes:

| Breakpoint | Behaviour | Reference |
|---|---|---|
| ≤ 1100px | `.answer-grid` collapses to 1 column, rail re-orders to top (`.answer-rail { order: -1 }`); `.video-evidence-grid` 3-col → 2-col; `.patterns-grid` 2x2 → 1-col; `.action-grid` 3-col → 1-col; `.turn-rail` hidden; KOL `.hide-narrow` rules continue per Phase B | `answer.jsx:277-284` |
| ≤ 900px | `thread-turns.jsx` `.creator-row` collapses to 2-col, hides cols 3 / 4 / button (`thread-turns.jsx:262-266`); `.script-meta` 4-col → 2-col; `.script-beat` 4-col → 2-col w/ tag in col 2 | `thread-turns.jsx:351-356` |
| ≤ 720px | `.video-evidence-grid` 2-col → 1-col; `.generic-grid` 3-col → 1-col | `answer.jsx:285-287`, `thread-turns.jsx:384` |
| ≤ 640px | H1 `font-size` shrinks per `styles.css` rule (Phase B precedent) | `styles.css` |
| ≤ 560px | Big-number `.bignum` font-size shrinks per `styles.css` rule | `styles.css` |

Manual QA at all five widths against the reference JSX. Any layout
break is a `must-fix` in the audit.

### Vietnamese copy / kicker discipline

Same rules as Phase B. Every kicker is `mono uc 9–10px, letterSpacing
0.14–0.18em, color: var(--ink-4)` unless the section is accent-led
(C.2 `BƯỚC TIẾP THEO` style: `color: var(--accent), fontWeight: 600`).
Vietnamese copy must be authored by the agent (not Gemini) for all
fixed labels and CTAs; only `thesis`, `insight`, `why_works`,
`why_stalled`, `tip`, `narrative.paragraphs` come from Gemini, all
schema-bounded per §J. Same `clamp(...)` typography ladders (28→42px
H1, 22→26px H2, 18→22px serif body) carry over from `answer.jsx`.

### Revised timeline

| Sub-phase | Estimate | Reason |
|---|---|---|
| C.0 spike | **1w** | 5 hard blockers — classifier + idea-directions + sample gates + width + answer-session model |
| C.1 `/answer` shell | **2w** | Migration + 5 endpoints + shell + 3 audits + smoke |
| C.2 Pattern (incl. `WhatStalled`) | **2.5w** | Highest-value report + non-negotiable + design-audit |
| C.3 Ideas | **1.5w** | (+1w if `idea-directions.jsx` commissioned in C.0.2) |
| C.4 Timing | **1w** | Heatmap reuses; only 2 new sections |
| C.5 Generic + multi-intent merge | **1w** | Lightweight format + classifier rules |
| C.6 `/history` restyle | **1w** | Token-violation closure + filter ribbon |
| C.7 `/chat` retirement | **1w** | Classifier matrix + chat redirect + grid pruning |
| C.8 Phase B carryovers | **3w (parallel)** | One milestone per carryover; can run alongside C.6/C.7 |
| Design-audit buffer | **1w** | Audit round-trips per sub-phase |
| **Total** | **~12–13w** (C.8 in parallel saves ~1.5w) | |

C.8.7 (measurement dashboard read) is a gating activity, not a coding
sub-phase; it consumes 0 new dev time but must be green before C.2.4
ships any behavior change.

---

## Sign-off rules

A sub-phase is "shipped" when **all** of the following hold:

1. Code merged to `main` via per-milestone PRs.
2. Backend pytest passing (≥ 80% branch coverage on new aggregators).
3. Frontend vitest passing on new primitives.
4. Shell smoke green.
5. Design-audit report green (token grep gate at 0).
6. Measurement event(s) confirmed live in production within 24h
   post-merge — emit a smoke event (test user account, dummy session)
   and verify the row lands in `usage_events` via the analytics
   dashboard. There is no separate staging analytics surface;
   production smoke is the contract.
7. Documentation updated (this plan, `api-types.ts`, audit reports).
8. For C.2 specifically: `WhatStalled` non-negotiable acceptance test
   green in CI.

**A sub-phase is not "shipped" until every line above is true.** Phase C
is closure-complete when C.0 → C.7 are all signed off and C.8.7
measurement read confirms no funnel regression vs Phase B baseline.

---

**Recommended next step:** kick off C.0 with the five spike sub-tasks
running in parallel. C.0.1 (intent classifier) and C.0.5 (answer-session
data model) are the two hard prerequisites for C.1; C.0.2 / C.0.3 / C.0.4
can resolve in any order during the same week.
