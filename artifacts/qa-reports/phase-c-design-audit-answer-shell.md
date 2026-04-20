# Phase C.1.5 — Design audit: `/app/answer` shell

**Date:** 2026-04-20  
**Sources:** `artifacts/uiux-reference/screens/answer.jsx`, `thread-turns.jsx` (plan refs) vs shipped `src/routes/_app/answer/`, `src/components/v2/answer/**`.

## C.1.4 — Confirmation (complete)

| Requirement | Evidence |
|-------------|----------|
| `answer_session_create` | `AnswerScreen.tsx` after `createAnswerSession` |
| `answer_turn_append` | After successful primary stream + follow-up stream |
| `templatize_click` | `TemplatizeCard.tsx` (guarded when `sessionId` falsy) |
| `logUsage` docs | `src/lib/logUsage.ts` JSDoc lists C.1 actions |
| DB | `idx_usage_events_c1_answer` + `COMMENT ON usage_events` (migration `20260430000007_usage_events_c1_answer.sql`) |

---

## Token check (plan §C.1.5)

**Method:** ripgrep on `src/components/v2/answer/**` and `src/routes/_app/answer/**`:

- Pattern `#[0-9a-fA-F]{3,8}` — **no hits** in TSX (hex in JSX).
- Banned CSS vars: `--ink-soft`, `--purple`, `--border-active`, `--gv-purple-*` — **no hits**.

**Fix shipped in this audit:** `SessionDrawer` overlay used `bg-[rgba(10,12,16,0.35)]`. Replaced with **`--gv-scrim`** in `src/app.css` and `bg-[color:var(--gv-scrim)]` so overlays resolve through a single `var(--gv-*)` token per plan.

**Status:** **GREEN** for token rules on answer shell files after `--gv-scrim` change.

---

## Section-by-section comparison

| Primitive (plan) | Shipped | Notes |
|------------------|---------|--------|
| **Route** `/app/answer` | `routes/_app/answer/route.tsx` + lazy `AnswerScreen` | Suspense fallback uses `var(--gv-canvas-2)` only. |
| **AnswerShell** | `AnswerShell.tsx` — `gv-route-main--answer`, 1280 grid, aside rail | Matches neo-brutalist column + 320px aside. |
| **QueryHeader** | Serif title, mono kicker, rule, meta slot | Aligns with answer.jsx header pattern. |
| **SessionDrawer** | 380px drawer, slide-in, list, “Phiên mới”, footer “Xem tất cả” | **Gap:** plan describes keyset pagination + `IntersectionObserver` for “load more”; current list is **single fetch** (limit from list query). |
| **FollowUpComposer** | `QueryComposer` + “Tiếp tục nghiên cứu” kicker | OK. |
| **Right rail** | `AnswerSourcesCard`, `TemplatizeCard` | OK. `RelatedQs` lives in main column (acceptable vs strict right-rail-only). |
| **TimelineRail** | Vertical rule when `turnCount > 1` | OK. |
| **ContinuationTurn** | Per-turn header + §J payload dispatch | OK; pattern uses `AnswerBlock` + C.2 placeholder. |
| **Research strip** | `ProgressPill`, `ResearchStepStrip`, `MiniResearchStrip` | OK (animation is illustrative until backend step events drive UI). |

---

## Tier list

### Must-fix

- **None** after replacing drawer scrim `rgba(...)` with **`var(--gv-scrim)`** (token compliance).

### Should-fix

1. **SessionDrawer pagination** — Plan: keyset on `updated_at`, load more on scroll (`IntersectionObserver`), default 30d scope. **Current:** client lists sessions returned by `fetchAnswerSessions` (single page). Add keyset + observer when product prioritizes parity with `thread-turns.jsx`.
2. **RelatedQs placement** — Plan sketch sometimes places related Qs in the right rail; **current** placement is under the main timeline. **OK** for C.1; revisit if UX research asks for rail-only.

### Consider

1. **Breakpoints 1100 / 720** — `AnswerShell` uses `lg:` / standard Tailwind breakpoints; no explicit `1100px` / `720px` tokens. **Consider** custom `min-[1100px]` / `max-[720px]` utilities if pixel-perfect parity with reference is required.
2. **C.2 placeholder copy** — Single line in `AnswerBlock`; sufficient until C.2 ships full sections.

---

## Verdict

**C.1.5 audit: PASS** — Token rules satisfied for answer shell after `--gv-scrim`; remaining gaps are **should-fix / consider** (drawer pagination, breakpoint parity), not blockers for closing C.1 from a design-token audit perspective.
