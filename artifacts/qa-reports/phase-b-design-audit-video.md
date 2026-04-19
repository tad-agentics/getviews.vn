# Phase B · B.1.7 — `/app/video` design audit

**Date:** 2026-04-19  
**Reference:** `artifacts/uiux-reference/screens/video.jsx`  
**Shipped:** `src/routes/_app/video/*`, `src/components/v2/*` (RetentionCurve, Timeline, HookPhaseCard, KpiGrid, IssueCard), `src/components/SectionMini.tsx`

**Verdict:** **Green** — token gate passed; must-fix parity items below were shipped in the same change set as this report.

---

## B.1.6 — Retire `video_diagnosis` chat CTA (audit)

| Requirement (plan) | Status | Evidence |
|--------------------|--------|----------|
| “Soi video” quick-action → `/app/video` (not chat modal) | **Pass** | `EmptyStates.tsx`: first card uses `href: "/app/video"` + `openQuickAction` → `navigate`. |
| Remove dedicated chat modal for Soi Video | **Pass** | `QuickActionModal.tsx`: `soi-video` config removed. |
| Home / studio entry not pushing TikTok-soi into chat composer | **Pass** | `HomeScreen.tsx`: “Dán link video” chip → `navigate("/app/video")`. `QuickActions.tsx`: `video` → `/app/video`. |
| Typed TikTok URL in chat still routable to `video_diagnosis` | **Pass (intentional)** | `intent-router.ts` + `ChatScreen.tsx` still handle URL-in-message; B.1.6 scopes **CTAs**, not backend intent removal. |
| Marketing / landing “Soi Video” copy | **Out of scope** | `LandingPage.tsx` — not the in-app chat CTA targeted by B.1.6. |
| Legacy modal key `video` (TikTok URL prompt) | **Residual** | Still in `MODAL_CONFIGS` for backward compatibility if any caller passes `modalKey="video"`; no current in-app path from audited routes. **Consider:** remove when history confirms zero use. |

---

## Section-by-section vs `video.jsx`

### Shell / layout

| Reference (`video.jsx`) | Shipped | Tier |
|-------------------------|---------|------|
| `maxWidth: 1280`, padding `24px 28px 80px` | `max-w-[1280px]`, `pt-6` (24px) `pb-20` (80px), was `px-5` (20px) & `px-7` (28px) ≥900px | **Must-fix (shipped):** default horizontal padding below 900px was 20px; aligned to **24px** (`px-6`) to match reference. |
| Grid `320px 1fr`, gap 32, stack &lt;900px | `min-[900px]:grid-cols-[320px_1fr]`, `gap-8` (32px) | **Pass** |

### Win mode — hero column

| Reference | Shipped | Tier |
|-----------|---------|------|
| BREAKOUT pill top-left on phone mock | Conditional on `meta.is_breakout` | **Must-fix (shipped):** badge when API marks breakout. |
| Play affordance center | Not implemented (static thumbnail) | **Consider** — optional product polish. |
| Top row: Lưu, Copy hook, Tạo kịch bản | Only “Quay lại Xu hướng” | **Should-fix** — wire actions when bookmarks / clipboard / shot intent exist. |
| KPI grid, timeline, hook phases, lessons | `KpiGrid`, `Timeline`, `HookPhaseGrid`, lessons list | **Pass** |
| Per-lesson “Áp dụng” chip | No per-row CTA (flop uses `IssueCard` handoff instead) | **Should-fix** — add optional `onApply` per lesson or single “Áp vào kịch bản” for win. |

### Flop mode

| Reference | Shipped | Tier |
|-----------|---------|------|
| URL input row (2px ink border) | `VideoUrlCapture` hero/compact + gv tokens | **Pass** (B.1.5) |
| Summary strip + retention + issues + projection CTA | `FlopDiagnosisStrip`, `RetentionCurve`, `IssueCard`, projection bar | **Pass** |
| High-severity issue: full border accent + 4px left accent | Previously: rule border + accent left only | **Must-fix (shipped):** full `border-[color:var(--gv-accent)]` for `sev === "high"`. |
| Issue row CTA “Áp vào kịch bản” | `IssueCard` `onApplyToScript` | **Pass** |

### Mode toggle (win / flop)

| Reference | Shipped | Tier |
|-----------|---------|------|
| Client toggle switching fixtures | API-driven `data.mode` only | **Consider** — data-driven is correct for production; toggle only needed for design preview. |

### Primitives (RetentionCurve, Timeline, SectionMini, etc.)

| Check | Result |
|-------|--------|
| Section order vs reference (KPI → retention → timeline → hook → lessons / flop issues) | **Pass** |
| `SectionMini` kicker + ink rule | **Pass** — `SectionMini.tsx` uses `var(--gv-ink)` rule. |

---

## Token gate (B.1.7 non-negotiable)

**Scope:** `src/routes/_app/video/*.tsx`, `src/components/v2/*`, `src/components/SectionMini.tsx`

| Check | Result |
|-------|--------|
| Raw hex `#rgb` / `#rrggbb` in JSX/class strings | **None found** |
| Banned purple-era tokens (`--ink-soft`, `--purple`, `--border-active`, `--gv-purple-*`) | **None found** |
| Color usage | **Pass** — `var(--gv-*)` and `color-mix(..., var(--gv-*) ...)` only in audited paths |

---

## Tier summary

### Must-fix (shipped with this audit)

1. **Shell padding:** `VideoScreen` main container `px-5` → `px-6` so horizontal padding is 24px below the 900px breakpoint (matches `video.jsx` 24px side padding).
2. **Flop high-severity card border:** `IssueCard` — for `sev === "high"`, entire card border uses `var(--gv-accent)` per reference (not only left accent).
3. **Win BREAKOUT badge:** When `meta.is_breakout` and `data.mode === "win"`, show a top-left mono pill on the phone preview (reference lines 54–56).

### Should-fix (not blocking B.1 close; track in backlog)

1. Win header actions: Lưu, Copy hook, “Tạo kịch bản từ video này” (reference `WinAnalysis` top row).
2. Win lessons: optional “Áp dụng” per lesson or a single handoff CTA mirroring flop.
3. Play overlay / video preview interaction (reference centered play).
4. Remove legacy `QuickActionModal` key `video` once confirmed unused.

### Consider

1. Client-only win/flop toggle for demos (separate from API mode).
2. Serif / display treatment for flop headline (reference uses serif on flop H1).
3. `AppLayout` active state: `/app/video` has no dedicated nav key; entries from Home vs Trends could drive different `active` hints later.

---

## Sign-off

- **B.1.6:** Chat and home **Soi video** entry points route to `/app/video`; chat modal path removed. Intent + history labels for `video_diagnosis` remain valid.  
- **B.1.7:** Token audit **green**; must-fix design parity items **shipped** as listed above.
- **B.1 checkpoint:** `usage_events` + `logUsage()` + `artifacts/sql/b1-checkpoint-flop-cta.sql` (see `phase-b-plan.md` §B.1 checkpoint).
