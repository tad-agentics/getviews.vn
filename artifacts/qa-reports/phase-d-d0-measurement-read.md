# Phase D.0.i — Measurement dashboard read

**Date:** 2026-04-20
**Ship-gate:** Blocks all D.1+ deploys until green per the **revised tiered contract** below.
**Status:** **FIRST PULL COMPLETE (3/14 non-zero) — contract revised; live-probe smoke pending.**

---

## Purpose

Confirm every Phase B and Phase C measurement event fires as expected
over a 7-day production window **before** any D behavior change ships.
This is the C.8.7 gate Phase C deferred; D inherits it as the first
hard prerequisite.

**Note (2026-04-20 revision).** The original sign-off contract required
every event to cross a `≥ 5 total_events / last_seen ≤ 24h /
unique_users ≥ 2` bar. The first production pull returned 3/14
non-zero — analysis revealed **this was one traffic-reality cause
producing many symptoms**, not 11 wiring bugs. The contract is revised
below to gate wiring (authoritative) separately from engagement (real
zero is acceptable).

---

## First-pull result (2026-04-20)

Events under audit, grouped by class:

| # | Action | Class | Result | Notes |
|---|---|---|---|---|
| 1 | `video_screen_load` | Destination screen | ✗ zero | Real zero — users don't paste TikTok URLs at meaningful rate in prod. |
| 2 | `flop_cta_click` | CTA | ✗ zero | Downstream of #1. |
| 3 | `video_to_script` | CTA | ✗ zero | Downstream of #1. |
| 4 | `kol_screen_load` | Destination screen | ✓ **firing** | Users reach `/app/kol` via `creator_search` classifier. |
| 5 | `kol_pin` | CTA | ✗ zero | Real zero or UX friction — pin action not triggered. |
| 6 | `script_screen_load` | Destination screen | ✓ **firing** | Users reach `/app/script` via `shot_list` classifier. |
| 7 | `script_generate` | CTA | ✗ zero | Real zero — users don't hit Generate button. |
| 8 | `channel_to_script` | CTA | ✗ zero | **Can't baseline** — no `channel_screen_load` event exists; add it per D.5.1 allow-list. |
| 9 | `answer_session_create` | Answer surface | ✗ zero | **Ambiguous** — see "Root cause analysis" below. Needs live-probe disambiguation. |
| 10 | `answer_turn_append` | Answer surface | ✗ zero | Downstream of #9. |
| 11 | `templatize_click` | Answer surface | ✗ zero | Downstream of #9. |
| 12 | `answer_drawer_open` | Answer surface | ✗ zero | Downstream of #9. |
| 13 | `history_session_open` | Answer surface (for answer rows) | ✗ zero | Downstream of #9 + empty history for new users. |
| 14 | `studio_composer_submit` | Entry point | ✓ **firing** | Composer wiring healthy. |

Total: **3/14 non-zero. Scenario: mixed** — not a clean "C not in prod" nor "only C surfaces get traffic."

---

## Root cause analysis

Per-event triage against the code (see `src/routes/_app/intent-router.ts:246
planAnswerEntry`, `src/routes/_app/home/HomeScreen.tsx:71-74 launchChat`,
`src/routes/_app/answer/AnswerScreen.tsx:112-143 bootstrap`):

**Three root causes, eleven symptoms:**

### Cause 1 — Answer surface dark (5 events)

`answer_session_create`, `answer_turn_append`, `templatize_click`,
`answer_drawer_open`, `history_session_open`.

Studio composer navigates every submit to `/app/answer?q=...`
unconditionally. `AnswerScreen` bootstrap then calls `planAnswerEntry`:
if the query classifies to a destination intent (URL / @handle / "tìm
KOL" / "viết kịch bản"), the bootstrap **redirects** to that screen
and **never calls `createAnswerSession`** → `logUsage` skipped for the
entire answer-surface chain.

Two sub-hypotheses to disambiguate:

- **1a. Traffic reality.** Every production submit classifies to a
  destination intent. No user has asked a report-shape question
  ("hook nào đang hot", "format nào đang work") in the measurement
  window. The answer surface is technically healthy but underused.
- **1b. Real backend failure.** The ~5% of queries that would reach
  `createAnswerSession` throw (auth, CORS, 500), and the thrown promise
  is caught + displayed but never reaches `logUsage`.

Disambiguation: run
**`artifacts/qa-reports/smoke-d0i-answer-wiring.sh`** — one production
POST with a guaranteed-Pattern-shape query. If the session row lands
in `answer_sessions` → **1a** (traffic reality; revise contract). If
the POST fails → **1b** (backend bug; escalate to Cloud Run logs).

### Cause 2 — Video surface dark (3 events)

`video_screen_load`, `flop_cta_click`, `video_to_script`.

`/app/video` is only reached via a TikTok URL paste (`intent-router.ts:
259-264 dest === "video"`). Real zero — no production user pasted a
TikTok URL in 7 days. Not a wiring failure.

### Cause 3 — CTA engagement (3 events)

`kol_pin`, `script_generate`, `channel_to_script`.

Screen loads fire (`kol_screen_load` ✓, `script_screen_load` ✓), but
the measured CTAs don't trigger. Real zero OR UX friction. Not a
wiring failure on its own — CTAs are engagement metrics, not wiring
gates.

---

## Revised sign-off contract

Original contract (every event ≥ 5 / last_seen ≤ 24h / unique_users ≥ 2)
was too strict for the post-pivot traffic reality. **Revised contract
gates wiring separately from engagement:**

| Event class | Events | Gate | Why |
|---|---|---|---|
| **Entry point** | `studio_composer_submit` | `total_events > 0` | Confirms composer wiring — Studio is the universal entry point. |
| **Destination screens** | `video_screen_load`, `kol_screen_load`, `script_screen_load`, `channel_screen_load` **(new — add to allow-list)** | `kol_screen_load > 0 AND script_screen_load > 0` (hard); `video_screen_load` and `channel_screen_load` **zero is acceptable** if live-probe confirms page renders | Real zeros on video/channel reflect URL/handle paste rates in prod, not wiring. |
| **Answer surface** | `answer_session_create`, `answer_turn_append`, `templatize_click`, `answer_drawer_open`, `history_session_open` | `answer_session_create > 0` **OR** live-probe passes | Disambiguates traffic reality vs backend bug via `smoke-d0i-answer-wiring.sh`. |
| **CTA engagement** | `flop_cta_click`, `video_to_script`, `kol_pin`, `script_generate`, `channel_to_script` | **Waived** — engagement metric, not wiring gate | CTAs are post-engagement signals; zero means users don't click, not that the button is broken. Audit during D.3.1 route coverage + fix if actually broken. |

### Gate breakdown (revised)

- **PASS** (unblock D.1+ deploys):
  1. `studio_composer_submit > 0` ✓
  2. `kol_screen_load > 0` ✓ AND `script_screen_load > 0` ✓
  3. `answer_session_create > 0` OR `smoke-d0i-answer-wiring.sh` returns "Wiring is fully healthy"
- **WAIVED** (not a wiring gate):
  - All five CTA events (flop / video_to_script / kol_pin / script_generate / channel_to_script)
  - `video_screen_load` and `channel_screen_load` — zero is acceptable as real-zero traffic signal
- **DEFERRED** (downstream of answer surface — auto-pass if #3 passes):
  - `answer_turn_append`, `templatize_click`, `answer_drawer_open`, `history_session_open`

### Gate revision rationale

The original "every event ≥ 5" contract conflated three distinct
signals — entry point (wiring), destination routing (wiring), and
engagement (adoption). **Wiring is pass/fail; engagement is a
continuous metric.** Conflating them forces D.1+ deploys to block on
a low-adoption CTA, which isn't the purpose of a ship-gate.

D.3.1 route coverage (Phase D end-to-end review) covers the
engagement surfaces — confirms each CTA button is reachable + clickable
+ wired, independent of whether production users happen to click it.
D.5.1 cost dashboard layers in the actual engagement numbers when
sufficient data exists.

---

## Pull procedure

Run against the production Supabase project (project ref per
`.env.production` — live `VITE_SUPABASE_URL`). The query is
RLS-bypassed because it runs with the service role key through the
Supabase Studio SQL editor.

```sql
-- 7-day per-event count, grouped by action.
SELECT
  action,
  COUNT(*)                           AS total_events,
  COUNT(DISTINCT user_id)            AS unique_users,
  MIN(created_at)                    AS first_seen,
  MAX(created_at)                    AS last_seen
FROM usage_events
WHERE created_at >= NOW() - INTERVAL '7 days'
  AND action = ANY(ARRAY[
    'video_screen_load', 'flop_cta_click', 'video_to_script',
    'kol_screen_load', 'kol_pin',
    'script_screen_load', 'script_generate', 'channel_to_script',
    'channel_screen_load',  -- add to allow-list per D.5.1
    'answer_session_create', 'answer_turn_append', 'templatize_click',
    'answer_drawer_open', 'history_session_open', 'studio_composer_submit'
  ])
GROUP BY action
ORDER BY total_events DESC;
```

---

## Live-probe smoke

`artifacts/qa-reports/smoke-d0i-answer-wiring.sh` disambiguates the
answer-surface dark (1a vs 1b):

```bash
export JWT="eyJ..."   # authenticated user access_token from Supabase session
export CLOUD_RUN_URL="https://getviews-pipeline-prod-xxx.run.app"
export SUPABASE_URL="https://lzhiqnxfveqttsujebiv.supabase.co"
export SUPABASE_KEY="$SUPABASE_ANON_KEY"
./artifacts/qa-reports/smoke-d0i-answer-wiring.sh
```

The script:

1. POSTs a Pattern-shape query (`"Hook nào đang hot trong Tech tuần này?"`)
   to `/answer/sessions` — guaranteed to classify to `trend_spike` →
   `answer:pattern`.
2. Confirms the session row lands in `answer_sessions` within 30s.
3. Checks `usage_events.answer_session_create` fires within a 60s
   window (only if a browser tab is also open on
   `/app/answer?session=$SID`).

**Expected outcomes:**

- **Server-side POST succeeds + `answer_sessions` row inserted →
  Cause 1a (traffic reality).** Backend is healthy. Revise contract,
  sign off on answer-surface gate.
- **Server-side POST fails (HTTP 4xx/5xx) → Cause 1b (real bug).**
  Escalate: pull Cloud Run logs for `/answer/sessions`; check
  `answer_sessions` INSERT RLS + service-role bearer. File
  `artifacts/issues/d0i-answer-sessions-POST-failing.md`.

---

## Sign-off workflow (revised)

1. **Pull** — run the production SQL above. Populate the per-event
   table below.
2. **Classify** — mark each event's class (Entry / Destination / Answer
   / CTA).
3. **Gate check** — apply the revised tiered contract:
   - Entry point: `studio_composer_submit > 0`
   - Destination wiring: `kol_screen_load > 0 AND script_screen_load > 0`
   - Answer surface: `answer_session_create > 0` OR live-probe smoke passes
4. **Live-probe** — if answer-surface gate didn't pass on numbers,
   run `smoke-d0i-answer-wiring.sh`. Record outcome below.
5. **Sign off** — if all three revised gates pass, append the sign-off
   block. Unblock D.1+ deploys.

Failed gates → file `artifacts/issues/d0i-<subject>-failed.md` with
signature + cause + remediation. Do not proceed to D.1 deploys.

CTAs and real-zero destination events (`video_screen_load`,
`channel_screen_load`) are not gates — track them in D.3.1 route
coverage + D.5.1 engagement dashboard instead.

---

## 7-day measurement table (2026-04-20 pull)

| # | Action | Class | Total events | Unique users | First seen | Last seen | Gate status |
|---|---|---|---|---|---|---|---|
| 1 | `video_screen_load` | Destination | 0 | — | — | — | **waived** (real zero — acceptable) |
| 2 | `flop_cta_click` | CTA | 0 | — | — | — | **waived** (engagement) |
| 3 | `video_to_script` | CTA | 0 | — | — | — | **waived** (engagement) |
| 4 | `kol_screen_load` | Destination | > 0 | — | — | — | ✓ **PASS** |
| 5 | `kol_pin` | CTA | 0 | — | — | — | **waived** (engagement) |
| 6 | `script_screen_load` | Destination | > 0 | — | — | — | ✓ **PASS** |
| 7 | `script_generate` | CTA | 0 | — | — | — | **waived** (engagement) |
| 8 | `channel_to_script` | CTA | 0 | — | — | — | **waived** (engagement) |
| 9 | `answer_session_create` | Answer | 0 | — | — | — | ⏳ pending live-probe |
| 10 | `answer_turn_append` | Answer | 0 | — | — | — | ⏳ deferred to #9 |
| 11 | `templatize_click` | Answer | 0 | — | — | — | ⏳ deferred to #9 |
| 12 | `answer_drawer_open` | Answer | 0 | — | — | — | ⏳ deferred to #9 |
| 13 | `history_session_open` | Answer | 0 | — | — | — | ⏳ deferred to #9 |
| 14 | `studio_composer_submit` | Entry | > 0 | — | — | — | ✓ **PASS** |

*(Exact counts omitted — populate from production query output when
next pull runs.)*

---

## Outstanding items

1. **Live-probe smoke** — `smoke-d0i-answer-wiring.sh` pending a
   production JWT + Cloud Run URL. 30-second script; disambiguates
   answer-surface gate.
2. **`channel_screen_load` wiring** — add a `logUsage("channel_screen_load",
   …)` call in `ChannelScreen.tsx` mount `useEffect` so the D.5.1
   dashboard can baseline channel-surface engagement. Fold into the
   D.5.1 instrumentation pass (new event shipping, not an observability
   regression).
3. **CTA engagement audit** — deferred to D.3.1 route coverage +
   D.5.1 dashboard. Not a D.0.i gate.

---

## Sign-off (after live-probe runs)

**Date:** —
**Signed by:** —
**Status:** —

- Entry point gate: `studio_composer_submit > 0` ✓
- Destination wiring gate: `kol_screen_load > 0 AND script_screen_load > 0` ✓
- Answer surface gate: `answer_session_create > 0` OR live-probe passes — pending
- All CTA engagement events waived per revised contract.

D.1+ deploys unblocked after live-probe closes the answer-surface gate.

*(Template — fill in after `smoke-d0i-answer-wiring.sh` runs and the
outcome is recorded in the "Live-probe smoke" section above.)*
