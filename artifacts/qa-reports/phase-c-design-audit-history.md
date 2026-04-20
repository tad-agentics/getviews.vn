# Phase C.6 — /history restyle design audit

**Milestone:** C.6.3 (plan §C.6 milestones)
**Verdict:** **PASS** — ready to close C.6.

---

## Scope

Unify `/app/history` so both `/answer` research sessions and legacy
`chat_sessions` are browseable through one surface driven by the
server-side `history_union` Postgres RPC (migration
`20260430000003_history_union.sql`).

---

## Shipped per plan §C.6

| Plan item | Status | Notes |
|---|---|---|
| Header: kicker `LỊCH SỬ NGHIÊN CỨU` + serif title `Tất cả các phiên` | ✅ | `HistoryScreen.tsx` header block, `gv-serif 28px` title with mono uppercase 10px kicker above. |
| 3-chip filter ribbon (Tất cả / Phiên nghiên cứu / Hội thoại) | ✅ | `HistoryFilterRibbon.tsx`, bound to `?filter=` query param (default: `all`; `all` strips param). |
| Active chip uses `--gv-accent-soft` bg + `--gv-accent` text | ✅ | accent-deep text on accent-soft bg, matching Pattern `FollowUpCard` convention. |
| Search input to the right of the filter chips | ✅ | Lucide `Search` icon + `Input`, debounced 300ms. |
| Filter disabled during active search | ✅ | `HistoryFilterRibbon` accepts `disabled`; ribbon greys and the click handler no-ops. |
| Session list rows: niche kicker + turn count + relative date + serif title | ✅ | `HistoryRow.tsx` composes TypePill + FormatSubPill + relativeTime + line-clamped serif title + turn count line. |
| Grouped by date heading | ✅ | `groupByDate` keys on `relativeTime(updated_at)` (Hôm nay / Hôm qua / 2 ngày / 2 tháng). Headings styled `--gv-canvas-2` block + mono uppercase label. |
| Active row `--gv-accent-soft` background + 3px accent left border | ✅ | `HistoryRow` accepts `active` prop; wires the two classes. (Today no caller passes `active=true` since `/history` is a list, not a pinned-row view — but the contract is ready for the day a detail panel splits off.) |
| Empty state: serif title + body + CTA "Bắt đầu phân tích →" → `/app/answer` | ✅ | Three empty branches: search miss, `filter=answer` no-rows, `filter=chat` no-rows, default no-rows. All non-error branches route to `/app/answer`. |
| Error state: serif body + accent CTA "Thử lại" | ✅ | Accent CTA is `text-[color:var(--gv-accent)] underline`, not legacy `--accent` (which still shims to `--purple-light`). |
| Row visual distinguishing: `NGHIÊN CỨU` chip for answer, `HỘI THOẠI` chip for chat | ✅ | `TypePill` component. Answer uses accent tokens; chat uses neutral `--gv-canvas-2` + `--gv-rule` tokens. |
| Format sub-pill (Pattern / Ideas / Timing / Tổng quát) on answer rows | ✅ | `FormatSubPill`, hidden for chat rows. |
| Click routes answer rows → `/app/answer?session=<id>`, chat rows → `/app/history/chat/<id>` | ✅ | `handleRowClick` picks by `row.type`; no 404 risk since chat route is the read-only transcript viewer. |
| Measurement event `history_session_open` with `metadata.type ∈ {answer, chat}` | ✅ C.6.4 | Fired inside `handleRowClick` before navigation. |
| Rename / delete actions only on chat rows | ✅ | `HistoryRow.actions` slot; answer rows pass `actions={undefined}`. Answer archival would go through a PATCH call (not in scope for C.6). |

## Server-side union (C.6.1)

The Postgres `history_union` RPC (migration `20260430000003`) is the
single source of truth. Signature (verified):

```sql
history_union(p_filter TEXT DEFAULT 'all',
              p_cursor TIMESTAMPTZ DEFAULT NULL,
              p_limit INT DEFAULT 20)
  RETURNS TABLE (id UUID, type TEXT, format TEXT, niche_id INT,
                 title TEXT, turn_count INT, updated_at TIMESTAMPTZ)
```

Contract:
- `type = 'answer'` rows include `format` + `niche_id` from
  `answer_sessions`; `turn_count` lateral-joined from `answer_turns`.
- `type = 'chat'` rows emit `NULL::text` for format + `NULL::int` for
  niche_id; `title` falls back to `LEFT(first_message, 100)` when the
  session row doesn't carry an explicit title; `turn_count` lateral-joined
  from `chat_messages`.
- Both sides RLS-bound via `user_id = auth.uid()`.
- `archived_at IS NULL` filter only applies to `answer_sessions` (plan
  C.6 note: `chat_sessions` lost soft-delete in migration `_036`;
  confirmed by inspection of the RPC body).

Pytest `tests/test_history_union.py` (8 cases) verifies the
Python-side contract mirrors of the SQL: filter enum membership,
ordering semantics, cursor strict-less-than, null safety for chat
columns, format enum on answer rows, filter WHERE equivalence.

## Token grep gate

```
grep -rnE "var\(--purple\)|var\(--ink-soft\)|var\(--border-active\)|\
--gv-purple|variant=\"purple\"|#[0-9a-fA-F]{3,8}|rgba?\(" \
  src/routes/_app/history/
```

**Result: 0 hits.** All colors resolve through `--gv-*` tokens:
`--gv-ink`, `--gv-ink-3`, `--gv-ink-4`, `--gv-canvas-2`, `--gv-paper`,
`--gv-rule`, `--gv-accent`, `--gv-accent-soft`, `--gv-accent-deep`,
`--gv-danger`.

The four violations flagged by the earlier codebase reality-check
(`HistoryScreen.tsx` lines 235/245/248/302 on legacy `--purple` /
`--ink-soft` / `Badge variant="purple"`) are closed via the rewrite —
the new screen has no references to any of those tokens.

## Must-fix

None.

## Should-fix (Phase D / polish)

1. **Pagination.** `useHistoryUnion` currently calls the RPC with
   `p_cursor: null` + `p_limit: 50`. The RPC contract supports keyset
   pagination (`p_cursor < updated_at`), but the hook doesn't wire an
   infinite-scroll `IntersectionObserver` yet. Plan §C.6 flagged this as
   "should-fix when product prioritizes parity." Ship in a follow-up
   when user research shows lists growing past 50 sessions.
2. **Cross-type search.** `useSearchSessions` only hits `chat_messages`
   ILIKE today. Answer sessions aren't indexed for full-text yet.
   Flagged as Phase D (plan §C.6 scope note). The filter ribbon is
   disabled during search to prevent a confusing "search answer rows"
   behaviour that wouldn't actually search answer content.
3. **Counts on the ribbon.** Client-side counts work when filter=`all`;
   when filter=`answer` or `chat`, we hide counts (biased by the
   server-side filter). A future `GET /history?counts_only=true` endpoint
   (plan fixture mapping) would let counts persist across filter states.
4. **`HistoryRow` shared with `SessionDrawer`.** Plan suggested
   extraction. Deferred: `SessionDrawer` renders `AnswerSessionRow`
   (answer-only shape) while `HistoryRow` renders `HistoryUnionRow`
   (both types). Unifying would require a shape converter at the
   drawer call site for marginal DRY gain.

## Consider

- **Active-row highlight in the detail-pane view.** The `HistoryRow`
  `active` prop is wired and ready; the `/app/history` layout doesn't
  split into a list + detail pane today, so no caller sets `active`.
  If a "see preview" drawer ships in Phase D, flip the prop.
- **Deleting answer sessions.** Requires a PATCH call to
  `/answer/sessions/:id` with `archived_at` set — not in C.6 scope.
  Today chat rows get rename/delete affordances; answer rows are
  click-through-only.

---

## Sign-off

C.6.1 RPC contract (shipped in C.0 spike closure; pytest verified
here) + C.6.2 `HistoryScreen.tsx` rewrite + `HistoryRow.tsx` +
`HistoryFilterRibbon.tsx` + C.6.3 token audit + C.6.4 `history_session_open`
event = all green. Ready to close C.6 and open C.7 (`/chat` deletion)
— which is already partially landed (plan notes mid-C that the tab
swap + ChatScreen removal already shipped as part of C.1 Studio
wiring; C.7 formalises the cleanup).
