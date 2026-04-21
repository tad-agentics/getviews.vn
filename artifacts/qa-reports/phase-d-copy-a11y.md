# Phase D.3.5 — Copy + a11y + CLAUDE.md staleness sweep

**Date:** 2026-04-21
**Status:** Sweep complete. 5 must-fix violations surfaced + fixed; 3 a11y
dimensions (keyboard nav / focus indicators / touch targets / Lighthouse)
require a live browser + are deferred to human-driven D.3 closeout.

---

## What this stream covered

Per the plan, D.3.5 is a code-accessible audit pass (grep + static
analysis). Streams that require a running app / browser (D.3.1 route
coverage, D.3.3 report format edge cases, D.3.4 integration boundaries,
D.3.6 perf / Lighthouse) are NOT in scope here — they need human QA
execution against a deployed Cloud Run + live data.

## Copy-rule violations (fixed inline)

Grep across `src/**/*.tsx` against `.cursor/rules/copy-rules.mdc`
forbidden openers (`Chào bạn`, `Tuyệt vời`, `Wow`) + forbidden words
(`bí mật`, `công thức vàng`, `triệu view`, `bùng nổ`). Five hits in
user-facing copy; all replaced with rule-compliant phrasing:

| # | File | Before | After |
|---|---|---|---|
| 1 | `src/routes/_index/LandingPage.tsx:89` | "video đối thủ triệu view" | "video đối thủ lên xu hướng" |
| 2 | `src/routes/_index/LandingPage.tsx:379` | `reveal: "Tiết lộ bí mật"` | `reveal: "Tiết lộ sự thật"` |
| 3 | `src/routes/_index/LandingPage.tsx:396` | "mang lại triệu view cho đối thủ" | "đẩy view ổn định cho đối thủ" |
| 4 | `src/routes/_index/LandingPage.tsx:845` | "89% video triệu view mở bằng mặt" | "89% video top view mở bằng mặt" |
| 5 | `src/components/v2/answer/pattern/PatternBody.tsx:99` | "video dùng pattern này đang bùng nổ" | "video dùng pattern này đang lên" |

Not-a-violation (excluded from fix list):
- `src/routes/_app/intent-router.ts` uses `bùng nổ|đang nổ` as part of
  a trend-detection regex (input-side, not output). Leaving it lets
  users who type "đang bùng nổ" still route to the trend intent.
- `src/routes/_app/intent-router.test.ts` + `src/routes/_app/home/
  HomeScreen.test.tsx` use `Chào bạn` as fixture input for regex /
  greeting detection tests. Fixtures, not UI.

Post-fix grep returns zero hits in user-facing `src/**/*.tsx` outside
the two test / routing exceptions above.

## CLAUDE.md staleness

Two stale claims found and corrected:

| Line | Before | After |
|---|---|---|
| 99 | "…`/app/*` routes: `chat`, `onboarding`, …" | `chat` removed; `answer`, `history/chat/:sessionId` (read-only), `script/shoot/:draftId` added — matches actual `src/routes.ts` post-Phase-C. |
| 101 | "…the real screen lives alongside (e.g. `ChatScreen.tsx`)." | Updated example to `AnswerScreen.tsx` — `ChatScreen.tsx` was deleted in Phase C.7. |
| 143 | "… OnboardingScreen (niche set inline on first ChatScreen session)." | Removed entirely — OnboardingScreen shipped in A.3.5 and ChatScreen is gone; the claim was wrong on both sides. |

Remaining `ChatScreen` references in `src/` are comments in helper
modules (`EmptyStates.tsx`, `MorningRitualBanner.tsx`, `NicheSelector.
tsx`, `AgentStepLogger.tsx`, `useDailyRitual.ts`, `CreatorCard.tsx`,
`VideoGridBlock.tsx`) — historical breadcrumbs inside components that
still work. Not stale claims against reality; left in place so future
Phase-B / C history archaeology stays readable.

## a11y — what was verified (code-accessible)

- **`alt` attributes on `<img>`:** every `<img>` in `src/components/`
  and `src/routes/` carries `alt=""` or a real alt string. Single-line
  grep appeared to miss them; multi-line confirmation shows all
  `<img>` tags have an `alt` attribute immediately following
  (decorative `alt=""` is valid per WCAG for presentational images
  alongside labelled adjacent text).
- **Icon-only button aria-labels:** grep for `<button>…<Icon/>…</button>`
  without `aria-label` / `title` returned zero hits. Every icon-only
  button in the codebase carries either `title="…"` (the existing
  pattern — e.g. `title="Đổi tên"` on HistoryScreen's rename / delete
  buttons) or `aria-label`.
- **Copy rules inside Vietnamese strings:** fixed above. No
  English-UI slippage detected.

## a11y — deferred to human D.3 closeout (needs live browser)

These dimensions require a running app + keyboard / pointer interaction:

- **Keyboard navigation** — tab order, focus visible, escape closes
  modals / drawers, enter submits forms.
- **Focus indicators** — ring visibility on every interactive element
  in the `--gv-*` token palette. Programmatic check is possible
  (Playwright) but needs a live build.
- **Touch targets ≥ 44 × 44 px** — hit-area audit needs rendered
  layout; the design system nominally enforces via `h-[44px]
  min-w-[44px]` class utilities but a live pass should confirm no
  dropped cells.
- **Heading hierarchy** — needs rendered DOM across all 15 screens;
  a grep for `<h[1-6]>` tags isn't reliable because some components
  emit headings conditionally.
- **Lighthouse LCP / CLS / TTI** (rolled into D.3.6) — strictly
  requires a live preview URL.

**Recommendation:** queue these under D.3.7 as a one-session Playwright
+ manual sweep against the next production preview. Cost: ~4h.

## Tests after fixes

- `npx vitest run`: 169/169 pass.
- `pytest`: 468/468 pass.
- No test needed replacement — the copy changes land in static
  strings; `src/routes/_app/home/HomeScreen.test.tsx` asserts
  `"Chào bạn"` as fixture input to `detectIntent`, which is a legal
  user-entered greeting (not a UI string we emit).

## Sign-off for D.3.5

Code-accessible portion complete. 5 copy-rule violations fixed + 3
CLAUDE.md stale claims corrected. Live-browser a11y streams explicitly
deferred to a human D.3.7 pass.
