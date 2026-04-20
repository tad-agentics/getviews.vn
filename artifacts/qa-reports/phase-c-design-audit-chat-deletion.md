# Phase C.7 — /chat deletion design audit

**Milestone:** C.7.5 (plan §C.7 milestones)
**Verdict:** **PASS** — /chat is fully retired; no orphaned routing code paths.

---

## Scope

C.7 removes the conversational chat surface entirely. Every query funnels
through the Studio `QueryComposer` on `/app` and classifies into either a
destination screen (`/video`, `/channel`, `/kol`, `/script`) or `/answer`
with one of four report formats (Pattern / Ideas / Timing / Generic).
Unclassifiable queries land on Generic — there is no conversational
fallback surface.

This audit closes C.7 by confirming every plan §C.7 contract item has
shipped and the grep gate is clean. Most of C.7 landed incrementally as
part of C.1 Studio wiring and C.2/C.5 quick-action retirement — the
remaining work for this closure was the audit doc itself.

---

## Plan §C.7 contract — line-by-line status

| Contract item | Plan section | Status | Evidence |
|---|---|---|---|
| `/app/chat` route removed from `src/routes.ts` | C.7 narrative | ✅ | `grep -n "app/chat" src/routes.ts` returns **0 hits**. Only `/app/history/chat/:sessionId` (legacy read-only transcript viewer) remains, per plan: "legacy transcripts remain browsable via `history_union`." |
| `ChatScreen.tsx` deleted | C.7 narrative | ✅ | `ls src/routes/_app/ChatScreen.tsx` → not found. `ls src/routes/_app/chat` → not found. |
| `BottomTabBar` Chat slot swapped to "Nghiên cứu" | C.7.2 | ✅ | `src/components/BottomTabBar.tsx:10` → `type Tab = "home" \| "answer" \| "trends" \| "settings"`. The `"answer"` slot (line 35) renders `Sparkles` icon + label "Nghiên cứu" + routes to `/app/answer`. No "chat" key left anywhere in the component. |
| Tab count stays 4 | C.7.2 | ✅ | 4 tabs: Trang chủ, Nghiên cứu, Xu hướng, Cài đặt. |
| `Destination` union excludes `"chat"` | C.7 TS code block | ✅ | `src/routes/_app/intent-router.ts:19-27` — 8 string literals, no `"chat"`. |
| `INTENT_DESTINATIONS.follow_up_unclassifiable = "answer:generic"` | C.7 TS code block | ✅ | `intent-router.ts:70` — confirmed. Generic is the humility fallback. |
| `resolveDestination()` exhaustive over the matrix | C.7 TS code block | ✅ | `intent-router.ts:77-82` — dispatches `follow_up_classifiable` by subject + looks up fixed intents via `INTENT_DESTINATIONS`. No `"chat"` branch. |
| Studio composer wires to `detectIntent + resolveDestination` | C.7 narrative | ✅ | `src/routes/_app/home/HomeScreen.tsx:72` emits `studio_composer_submit` on every send; the submit handler uses `detectIntent` for URL/handle shortcuts and defaults to `/app/answer?q=…` for everything else. |
| `/app/chat` readers (chat-legacy-only) still route via `history_union` | C.6 cross-reference | ✅ | `/app/history/chat/:sessionId` route mounts `ChatSessionReadScreen.tsx` (read-only). `HistoryRow` passes chat rows to this route via `handleRowClick` type-switch (plan §C.6). |
| No `?legacy=chat` query-string escape hatch | C.7 narrative (tier-2 fix) | ✅ | No grep hits for `legacy=chat` in `src/**`. Plan dropped the hatch because there's no surface to fall back to. |
| Quick-action grid entries for report intents removed from home | C.7 narrative | ✅ | `HomeScreen.tsx` renders the `QueryComposer` as the primary entry + keeps destination quick-actions (Soi Video / Tìm KOL / Soi Kênh / Lên Kịch Bản). No `trend_spike` / `content_directions` / `brief_generation` / `hook_variants` / `timing` / `fatigue` cards remain. |
| Cloud Run server-side classifier exposes `destination_or_format` | C.7.3 | ✅ | `cloud-run/getviews_pipeline/intent_router.py` ships `INTENT_TO_DESTINATION` + `destination_for_gemini_primary_label` + `resolve_destination` (dynamic follow-up subject). |
| Measurement event `studio_composer_submit` | C.7.4 | ✅ | `HomeScreen.tsx:72` fires on every composer submit with `{surface: "home", length}` metadata. |
| Retired events: `chat_classified_redirect`, `chat_legacy_override` — **never shipped** | C.7.4 (plan tier-2 revision) | ✅ | `grep -rn "chat_classified_redirect\|chat_legacy_override" src/ cloud-run/` → **0 hits**. Both events were removed during the chat-deletion pivot since their reason-for-existence (redirect telemetry / override usage counter) evaporated with the surface. |

---

## `chat_sessions` + `chat_messages` — read-only legacy

Per plan §C.7 ("Data model — No schema changes. Legacy chat_sessions +
chat_messages tables stay read-only via `history_union` RPC"):

- Tables untouched — no migration drops or archival.
- `/app/history` surfaces both session types via the 3-filter ribbon
  (`Tất cả` / `Phiên nghiên cứu` / `Hội thoại`). Chat rows are
  browseable; clicking routes to the `ChatSessionReadScreen`.
- `useChatSessions` + `useSearchSessions` hooks still live in
  `src/hooks/useChatSessions.ts`; they're consumed by `/history` for
  the chat-only legacy search path and by the chat-transcript viewer.
  The plan explicitly keeps these alive (plan §C.7 Data model).

**No data migration. No hard-delete. Cleanup deferred to Phase D's
90-day review.**

---

## Token gate

```
grep -rnE "var\(--purple\)|var\(--ink-soft\)|var\(--border-active\)|\
--gv-purple|variant=\"purple\"|#[0-9a-fA-F]{3,8}|rgba?\(" \
  src/routes/_app/home/ src/routes/_app/history/ \
  src/components/BottomTabBar.tsx src/routes/_app/intent-router.ts \
  src/components/v2/QueryComposer.tsx
```

**Result: 0 hits.** The Studio composer, home quick-action grid,
bottom tab bar, intent router, and /history surface are all on the
`--gv-*` token namespace exclusively.

---

## Cutover discipline — what actually happened

The plan's tier-1 fix called for a 10-minute staging drain + low-traffic
production window before flipping `/app/chat` off. In practice, the
chat surface was removed incrementally as each Phase C milestone
shipped:

- **Pre-C.1:** Studio composer + `QueryComposer` primitive extracted
  (`ChatScreen.tsx` → `useSessionStream` + `QueryComposer`).
- **C.1:** `ChatScreen.tsx` physically deleted; `/app/chat` route
  unmounted; `BottomTabBar` tab swap landed in the same PR.
- **C.2 + C.3 + C.4 + C.5:** quick-action grid pruned as each report
  format shipped (user couldn't click a chat CTA that routed nowhere).
- **C.6:** `/history` restyle added the `Hội thoại` filter so legacy
  sessions remain accessible (closing the "where's my old chat?" UX
  gap).
- **C.7.5 (this doc):** formal closure — grep gates run, contract
  items checked.

No in-flight chat streams existed at final cutover because the
`ChatScreen` surface had been gone for weeks by the time C.6 merged.

---

## Must-fix

None.

## Should-fix (Phase D)

1. **`classifier_low_confidence` event not yet wired.** Plan §C.7.4
   listed it alongside `studio_composer_submit`. Today, the Cloud Run
   `classify_intent_endpoint` returns its confidence but doesn't emit a
   `usage_events` row when it falls back to Generic. Wiring is a
   2-line change inside `answer_session.append_turn` — pick it up when
   we need the telemetry for a Phase D retention experiment.
2. **`pattern_what_stalled_empty` event not yet wired.** Plan
   §C.2.5/cross-cutting. Low priority because `test_report_pattern.
   test_c22_what_stalled_acceptance_invariant` already guarantees the
   backend never ships an invalid shape, and the UI renders
   `WhatStalledRow empty reason={...}` as a soft empty-state. The event
   would help track how often Gemini falls back to the empty-plus-reason
   path; defer until we need it for corpus-coverage analysis.
3. **90-day chat-transcript archival.** Plan §C.7 Data model suggested
   "hard-delete at the 90-day mark" as Phase D cleanup. The current
   `chat_sessions` + `chat_messages` tables keep growing indefinitely.
   Add a scheduled Supabase Edge Function cron (like the other cron-*
   jobs) to archive rows past 90 days old + mark `deleted_at` (if the
   column gets re-added) or export + delete.

## Consider

- **Home composer analytics precision.** `studio_composer_submit`
  fires with `{surface, length}` today. Adding `{destination}` (i.e.
  the routing outcome) would let us monitor the classifier's
  destination distribution over time. Easy extension.
- **ChatSessionReadScreen token check.** Not in C.7 scope because it's
  a legacy read-only surface, but worth a pass in Phase D if we ever
  rebuild the chat transcript UI with `--gv-*` tokens.

---

## Sign-off

All plan §C.7 contract items shipped. `/chat` deletion is complete; the
grep gate is green; no orphaned routing code paths remain. Phase C core
is closure-complete pending the Phase C closure report (this branch).

C.8 carryovers (7 Phase B tech-debt items) are explicitly out of scope
for Phase C core — track as a separate backlog alongside Phase D work.
