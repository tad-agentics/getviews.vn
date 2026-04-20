# Phase D.0.i — Measurement dashboard read

**Date:** 2026-04-20
**Ship-gate:** Blocks all D.1+ deploys until green.
**Status:** **PENDING — awaiting 7-day production data**

---

## Purpose

Confirm every Phase B and Phase C measurement event fires with non-zero
counts over a 7-day production window **before** any D behavior change
ships. This is the C.8.7 gate Phase C deferred; D inherits it as the
first hard prerequisite.

If any event is missing or zero, file an issue and **block D.1+ deploys
until resolved.**

---

## Events under audit

### Phase B set (creator screens)

Wired via `src/lib/logUsage.ts` → `usage_events` table. Originating
sub-phase per `phase-b-closure.md`.

| Event | Origin | Expected surface |
|---|---|---|
| `video_screen_load` | B.1 | `/app/video` mount |
| `flop_cta_click` | B.1 | Flop-mode CTA on `/app/video` |
| `video_to_script` | B.1 / B.4.5 | "Tạo kịch bản từ video này" click |
| `kol_screen_load` | B.2 | `/app/kol` mount |
| `kol_pin` | B.2 | Toggle-pin `reference_channel_handles` |
| `script_screen_load` | B.4 | `/app/script` mount |
| `script_generate` | B.4 | `POST /script/generate` returns 200 |
| `channel_to_script` | B.4.5 | "Tạo kịch bản từ channel" click |

### Phase C set (answer research surface + history)

Per `phase-c-closure.md`.

| Event | Origin | Expected surface |
|---|---|---|
| `answer_session_create` | C.1 | `POST /answer/sessions` returns 200 |
| `answer_turn_append` | C.1 | `POST /answer/sessions/:id/turns` finalises |
| `templatize_click` | C.1 | `TemplatizeCard` Lưu button click |
| `answer_drawer_open` | C.1 | `SessionDrawer` open |
| `history_session_open` | C.6 | `/history` row click |
| `studio_composer_submit` | C.7 | Studio composer `onSubmit` |

Total: **14 events.**

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
    'answer_session_create', 'answer_turn_append', 'templatize_click',
    'answer_drawer_open', 'history_session_open', 'studio_composer_submit'
  ])
GROUP BY action
ORDER BY total_events DESC;
```

---

## Pass / fail contract

**Pass** — every event in the 14-row list above returns:

- `total_events > 0` (ideally ≥ 5 — means the event ran on real
  traffic, not a one-off smoke).
- `last_seen` within the last 24 hours (event is still firing).
- `unique_users ≥ 2` (not just a single test account).

**Fail modes and resolutions:**

| Symptom | Likely cause | Resolution |
|---|---|---|
| Missing row (action never seen) | Wiring bug — `logUsage(action, …)` call never reached the hook | Grep `src/**` for the event name; confirm call site exists + matches. Patch commit in D.0.6 closure. |
| `total_events = 0` | `usage_events.action` allow-list migration didn't apply; inserts silently dropped | Check `supabase/migrations/20260430000007_usage_events_c1_answer.sql` applied in prod |
| `total_events ≥ 1` but `last_seen > 24h ago` | Hook stopped firing (regression in the calling screen) | Traceback from the last-firing date to the release that broke it |
| `unique_users = 1` | Smoke-only — real traffic isn't exercising this path | Not a hard fail, but flag in notes; indicates the surface is broken for real users |
| Spurious `action` values | Typos in `logUsage` calls or old code shipping unintended events | Reconcile against the allow-list migration |

---

## 7-day measurement table (to be populated from production query)

Run this section's SQL, paste the result rows into the table below,
then commit the audit.

| # | Action | Total events | Unique users | First seen | Last seen | Pass / Fail | Notes |
|---|---|---|---|---|---|---|---|
| 1 | `video_screen_load` | — | — | — | — | ⏳ pending | |
| 2 | `flop_cta_click` | — | — | — | — | ⏳ pending | |
| 3 | `video_to_script` | — | — | — | — | ⏳ pending | |
| 4 | `kol_screen_load` | — | — | — | — | ⏳ pending | |
| 5 | `kol_pin` | — | — | — | — | ⏳ pending | |
| 6 | `script_screen_load` | — | — | — | — | ⏳ pending | |
| 7 | `script_generate` | — | — | — | — | ⏳ pending | |
| 8 | `channel_to_script` | — | — | — | — | ⏳ pending | |
| 9 | `answer_session_create` | — | — | — | — | ⏳ pending | |
| 10 | `answer_turn_append` | — | — | — | — | ⏳ pending | |
| 11 | `templatize_click` | — | — | — | — | ⏳ pending | |
| 12 | `answer_drawer_open` | — | — | — | — | ⏳ pending | |
| 13 | `history_session_open` | — | — | — | — | ⏳ pending | |
| 14 | `studio_composer_submit` | — | — | — | — | ⏳ pending | |

---

## Sign-off workflow

1. Pull the 7-day window via the SQL above (requires production
   Supabase access).
2. Populate the table. Mark every row Pass or Fail.
3. If any row fails:
   - File `artifacts/issues/d0i-<event>-missing.md` with the failure
     signature + suspected cause.
   - Open a fix commit under `fix(analytics): <event> not firing`.
   - **Do not** proceed to D.1 until all 14 rows pass.
4. If every row passes:
   - Append the sign-off block at the bottom of this file.
   - Close D.0.i in the D.0.6 spike close-out.
   - Unblock D.1+ deploys.

---

## Sign-off (to be filled after production data pull)

**Date:** —
**Signed by:** —
**Status:** —

All 14 events confirmed firing over the 7-day window ending —. No fail
rows. D.1+ deploys unblocked.

*(Template — fill in from the populated table above.)*
