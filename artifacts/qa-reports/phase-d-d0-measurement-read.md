# Phase D.0.i — Measurement dashboard read

**Date:** 2026-04-20
**Ship-gate:** Blocks all D.1+ deploys until green.
**Status:** **FAIL — 7-day production pull completed 2026-04-20; 11/14 events have zero rows.** D.1+ remains blocked until all rows pass the contract below.

**Production snapshot:** Supabase project **Getviews.vn** (`lzhiqnxfveqttsujebiv`, `ap-southeast-2`). Query executed via service-role SQL (7-day window = `created_at >= NOW() - INTERVAL '7 days'` at query time). A 30-day roll-up shows the same three `action` values only — no hidden traffic under alternate windows for the missing names.

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

To list **all 14 expected actions including zeros** (easier for the table below):

```sql
WITH expected AS (
  SELECT unnest(ARRAY[
    'video_screen_load', 'flop_cta_click', 'video_to_script',
    'kol_screen_load', 'kol_pin',
    'script_screen_load', 'script_generate', 'channel_to_script',
    'answer_session_create', 'answer_turn_append', 'templatize_click',
    'answer_drawer_open', 'history_session_open', 'studio_composer_submit'
  ]) AS action
)
SELECT e.action,
  COALESCE(COUNT(u.*), 0)::bigint AS total_events,
  COALESCE(COUNT(DISTINCT u.user_id), 0)::bigint AS unique_users,
  MIN(u.created_at) AS first_seen,
  MAX(u.created_at) AS last_seen
FROM expected e
LEFT JOIN usage_events u ON u.action = e.action
  AND u.created_at >= NOW() - INTERVAL '7 days'
GROUP BY e.action
ORDER BY total_events DESC, e.action;
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

## 7-day measurement table (production pull 2026-04-20)

| # | Action | Total events | Unique users | First seen (UTC) | Last seen (UTC) | Pass / Fail | Notes |
|---|---|---:|---:|---|---|---|---|
| 1 | `video_screen_load` | 0 | 0 | — | — | **Fail** | No rows in 7d (none in 30d either). |
| 2 | `flop_cta_click` | 0 | 0 | — | — | **Fail** | No rows in 7d. |
| 3 | `video_to_script` | 0 | 0 | — | — | **Fail** | No rows in 7d. |
| 4 | `kol_screen_load` | 38 | 3 | 2026-04-19 06:03:25 | 2026-04-20 09:14:39 | **Pass** | Meets volume; `last_seen` within 24h of pull; `unique_users ≥ 2`. |
| 5 | `kol_pin` | 0 | 0 | — | — | **Fail** | No rows in 7d. |
| 6 | `script_screen_load` | 35 | 4 | 2026-04-19 09:51:58 | 2026-04-20 09:13:19 | **Pass** | Meets volume; `last_seen` within 24h of pull. |
| 7 | `script_generate` | 0 | 0 | — | — | **Fail** | No rows in 7d. |
| 8 | `channel_to_script` | 0 | 0 | — | — | **Fail** | No rows in 7d. |
| 9 | `answer_session_create` | 0 | 0 | — | — | **Fail** | No rows in 7d. |
| 10 | `answer_turn_append` | 0 | 0 | — | — | **Fail** | No rows in 7d. |
| 11 | `templatize_click` | 0 | 0 | — | — | **Fail** | No rows in 7d. |
| 12 | `answer_drawer_open` | 0 | 0 | — | — | **Fail** | No rows in 7d. |
| 13 | `history_session_open` | 0 | 0 | — | — | **Fail** | No rows in 7d. |
| 14 | `studio_composer_submit` | 4 | 1 | 2026-04-20 08:45:53 | 2026-04-20 09:08:36 | **Fail** | `unique_users = 1` — contract asks ≥ 2; treat as **smoke-only** per fail-mode table. |

**Summary:** **2 / 14** rows meet the full contract (`kol_screen_load`, `script_screen_load`). `studio_composer_submit` has non-zero volume but **`unique_users = 1`** (fails). The other **11** actions have **zero** rows in the 7-day window. **Gate is not green.** Next steps: trace missing events (`logUsage` + allow-list / RLS on insert), then re-pull after fixes.

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

**Date:** 2026-04-20 (pull only — not a green sign-off)
**Signed by:** —
**Status:** **Not eligible — 11 fail rows + `studio_composer_submit` unique-user fail.**

Re-run this section after a subsequent pull when all 14 rows pass. Until then,
**D.1+ deploys remain blocked** per ship-gate.

*(Green template when eligible:)*

**Date:** —
**Signed by:** —
**Status:** **Green**

All 14 events confirmed firing over the 7-day window ending —. No fail
rows. D.1+ deploys unblocked.
