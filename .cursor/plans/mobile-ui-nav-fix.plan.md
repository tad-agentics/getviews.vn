# Mobile UI & Nav Fix Plan

**Created:** 2026-05-18  
**Branch target:** `main`  
**Scope:** All `/app/*` screens — navigation shell, touch targets, safe-area, padding, grids, inputs

---

## Complete Findings

### Category 1 — Navigation (CRITICAL / HIGH)

| # | Issue | File | Line | Severity |
|---|-------|------|------|----------|
| N1 | Session history **completely unreachable** on mobile — no hamburger, no drawer, `SidebarContent` only renders in `hidden lg:flex` branch | `AppLayout.tsx` | 893 | CRITICAL |
| N2 | **Navigation dead zone 768–1023px** — `BottomTabBar` uses `md:hidden` (gone at 768px), sidebar appears at `lg:` (1024px). Tablets and large phones get zero navigation | `BottomTabBar.tsx` | 44 | HIGH |
| N3 | `AdminScreen` has no `enableMobileSidebar` — no bottom tabs, no access to nav on mobile | `AdminScreen.tsx` | 43/55/59 | MEDIUM |

---

### Category 2 — Touch Targets (HIGH)

| # | Issue | File | Line | Severity |
|---|-------|------|------|----------|
| T1 | Breadcrumb "← Studio" back button `min-h-[30px]` — 30px, 14px below minimum | `AnswerScreen.tsx` | 549 | HIGH |
| T2 | Sidebar "+" new-chat button `h-8 w-8` = 32px | `AppLayout.tsx` | 675 | HIGH |
| T3 | Sidebar "×" close button `h-8 w-8` = 32px | `AppLayout.tsx` | 683 | HIGH |
| T4 | Session row "⋯" menu button `h-8 w-8` = 32px | `AppLayout.tsx` | 425 | HIGH |
| T5 | `Btn size="sm"` → `h-8` = 32px — used widely ("Phân tích mới", "Tạo kịch bản") | `Btn.tsx` | 27 | HIGH |
| T6 | ExploreScreen filter chips `h-6` = 24px — primary action area | `ExploreScreen.tsx` | 388 | HIGH |
| T7 | Explore dialog close button `p-2` + 16px icon ≈ 24px | `ExploreScreen.tsx` | ~188 | MEDIUM |
| T8 | SettingsScreen toggle `h-[22px] w-[38px]` — common pattern but no hit-area wrapper | `SettingsScreen.tsx` | 156 | LOW |
| T9 | Rename ✓ confirm button in session row ~20px | `AppLayout.tsx` | 379 | MEDIUM |

---

### Category 3 — Layout & Padding (HIGH / MEDIUM)

| # | Issue | File | Line | Severity |
|---|-------|------|------|----------|
| L1 | `.gv-route-main` has **no mobile override** — `padding: 24px 28px 80px` applies at all widths. At 360px this gives only `360 - 56px = 304px` of usable content width. Should be `16px` horizontal on mobile | `app.css` | 591–597 | HIGH |
| L2 | `.gv-route-main--answer` same issue — `padding: 28px 28px 120px` at all widths | `app.css` | 604–605 | HIGH |
| L3 | `.gv-home-wrap` correctly has `padding: 2rem 1rem` mobile and `36px 28px` at md — this is the **right pattern**; others should match | `app.css` | 581–586 | (reference) |
| L4 | `VideoBody` 9/16 aspect ratio thumbnail — on mobile single-column this renders as a very tall image (e.g. 360px wide = 640px tall) before the report. Should have `max-h-[60vh]` cap or be hidden on mobile with just the title showing | `VideoBody.tsx` | 306 | HIGH |
| L5 | `VideoBody` main grid `grid-cols-[320px_1fr]` at 900px — correct. But the aside+thumbnail is the full width on mobile, with no visual cue that the report body continues below. No "↓ scroll to report" affordance | `VideoBody.tsx` | 294 | MEDIUM |
| L6 | ExploreScreen's extra `pb-[60px]` inside a shell that already pads for tab bar — possible double-pad | `ExploreScreen.tsx` | ~900 | LOW |
| L7 | `DiagnosisSectionRenderer` finding cards `max-w-[640px]` — has no effect on mobile (good), but the card layout `flex items-start gap-4` may feel cramped at 360px with icon + text | `DiagnosisSectionRenderer.tsx` | 95 | LOW |

---

### Category 4 — Input Font Size / iOS Zoom (MEDIUM)

iOS zooms in when an `<input>` or `<textarea>` has `font-size < 16px`. Tailwind utility classes override the global `app.css` rule `font-size: max(16px, 1rem)`.

| # | Issue | File | Line | Severity |
|---|-------|------|------|----------|
| I1 | Channel URL input `text-[15px]` — 1px below iOS zoom threshold | `ChannelScreen.tsx` | 207 | MEDIUM |
| I2 | Channel niche/filter inputs `text-sm` (14px) | `ChannelScreen.tsx` | 361, 386 | MEDIUM |
| I3 | ExploreScreen search field `text-[13px]` | `ExploreScreen.tsx` | ~996 | MEDIUM |
| I4 | HistoryScreen rename input `text-sm` | `HistoryScreen.tsx` | ~356 | MEDIUM |

---

### Category 5 — Safe Area (MEDIUM / LOW)

| # | Issue | File | Line | Severity |
|---|-------|------|------|----------|
| S1 | Landing sticky CTA bar `fixed bottom-0` — no `pb-[env(safe-area-inset-bottom)]`. iPhone home indicator clips the button | `LandingPage.tsx` | 772 | MEDIUM |
| S2 | Spacer div for landing CTA `h-14` — doesn't account for home bar extra height | `LandingPage.tsx` | 1261 | MEDIUM |
| S3 | `TopBar` `sticky top-0` — no `pt-[env(safe-area-inset-top)]`. Only affects PWA standalone mode | `TopBar.tsx` | 23 | LOW |

---

### Category 6 — Video Report Mobile Layout (HIGH)

The video report is the **core product experience**. These affect every analysis.

| # | Issue | File | Severity |
|---|-------|-------|----------|
| V1 | Full 9/16 thumbnail takes ~60-70% of viewport height on mobile before the user sees any analysis text. No scroll cue. | `VideoBody.tsx` L306 | HIGH |
| V2 | `KpiGrid` always `grid-cols-2` — fine, but `p-[18px]` per cell = 36px horizontal padding total inside a ~332px content area at 360px. Values like "6.085" in JetBrains Mono fit but may wrap at worst case | `KpiGrid.tsx` L36 | MEDIUM |
| V3 | `ChannelProofBlock` top/bottom video cards `grid-cols-1 gap-3 min-[700px]:grid-cols-2` — correct single-column on mobile ✓ | `ChannelProofBlock.tsx` L134 | OK |
| V4 | `FormatCardsGrid` `grid-cols-1 gap-3 md:grid-cols-2` — correct ✓ | `FormatCardsGrid.tsx` | OK |
| V5 | `CrossFormatPanel` (v5 only now) `grid-cols-1 sm:grid-cols-2` — correct ✓ | `CrossFormatPanel.tsx` | OK |

---

## Task List (Prioritized)

### Sprint 1 — Navigation & Critical Layout (do first, unblocks users)

**T1 — Mobile hamburger drawer for session history** *(CRITICAL)*  
Add `AlignLeft` hamburger button to mobile header → Radix `<Sheet side="left">` → `SidebarContent`.  
Files: `AppLayout.tsx`

**T2 — Fix nav dead zone: `md:hidden` → `lg:hidden` on BottomTabBar** *(1-line fix)*  
Files: `BottomTabBar.tsx` line 44

**T3 — Fix `.gv-route-main` horizontal padding at mobile** *(HIGH — affects all screens)*  
Add mobile override: `padding: 20px 16px 80px` at `< 768px`.  
Files: `app.css`

```css
/* BEFORE: */
.gv-route-main {
  padding: 24px 28px 80px;
}

/* AFTER: */
.gv-route-main {
  padding: 20px 16px 80px;    /* mobile */
}
@media (min-width: 768px) {
  .gv-route-main {
    padding: 24px 28px 80px;  /* tablet+ */
  }
}

/* Same fix for --answer: */
.gv-route-main--answer {
  padding: 28px 16px 120px;   /* mobile */
}
@media (min-width: 768px) {
  .gv-route-main--answer {
    padding: 28px 28px 120px;
  }
}
```

**T4 — Video thumbnail mobile cap** *(HIGH — core product UX)*  
Cap the 9/16 thumbnail to `max-h-[56vh]` on mobile with `object-cover`. Add subtle "↓" scroll indicator below it.  
Files: `VideoBody.tsx` line 306

```tsx
// Before:
className="relative aspect-[9/16] overflow-hidden rounded-[18px] ..."

// After: cap height on mobile, let it be full 9/16 on desktop where the aside is sticky
className="relative aspect-[9/16] max-h-[56vh] min-[900px]:max-h-none overflow-hidden rounded-[18px] ..."
```

---

### Sprint 2 — Touch Targets & Inputs

**T5 — Raise `Btn size="sm"` to at least 36px, add tap-target on mobile** *(HIGH)*  
Files: `Btn.tsx`

```tsx
// In size map, sm:
"h-9 min-w-[36px] px-3 text-[13px]"  // was h-8
// Or add mobile-specific override:
"h-8 min-h-[44px] ..."  // visual stays 32px but tap area is 44px via padding
```

Best approach: use `min-h-[44px]` on `sm` so the tap target expands without changing visual layout.

**T6 — Fix breadcrumb back button `min-h-[44px]`** *(HIGH)*  
Files: `AnswerScreen.tsx` line 549

```tsx
// Before: min-h-[30px]
// After:  min-h-[44px]
```

**T7 — Fix AppLayout icon buttons to 44px** *(HIGH)*  
Session row "⋯", sidebar "+", sidebar "×":  
Files: `AppLayout.tsx` lines 425, 675, 683

```tsx
// Before: h-8 w-8 (and md:h-9 md:w-9)
// After: h-11 w-11  (44px)
```

**T8 — Fix ExploreScreen filter chips minimum tap area** *(HIGH)*  
`KHO_FILTER_CHIP_H = "h-6"` → wrap in a container with `min-h-[44px]` touch area, keep visual `h-6`.  
Files: `ExploreScreen.tsx` lines 388–430

Option: add `py-[9px]` invisible padding to the wrapper div, making the effective tap zone 24+18+18 = 60px while the visible chip stays 24px.

**T9 — Fix input font sizes (iOS anti-zoom)** *(MEDIUM)*  
Files: `ChannelScreen.tsx`, `ExploreScreen.tsx`, `HistoryScreen.tsx`

Change all `text-sm` / `text-[13px]` / `text-[15px]` on `<input>` elements to `text-[16px]` or `text-base`.

---

### Sprint 3 — Safe Area & Polish

**T10 — Landing sticky CTA safe-area** *(MEDIUM)*  
Files: `LandingPage.tsx` lines 772, 1261

**T11 — TopBar PWA standalone safe-area** *(LOW)*  
Files: `TopBar.tsx`, `app.css`

**T12 — AdminScreen `enableMobileSidebar`** *(LOW)*  
Files: `AdminScreen.tsx`

---

## Commit Plan

```
feat(mobile): T1 — hamburger drawer for session history (Sheet + SidebarContent)
fix(mobile): T2 — extend bottom tabs to 1024px breakpoint
fix(mobile): T3 — fix gv-route-main horizontal padding on small screens
fix(mobile): T4 — cap video thumbnail height on mobile (max-h-[56vh])
fix(mobile): T5 — raise Btn sm min-h to 44px touch target
fix(mobile): T6 — raise answer breadcrumb min-h to 44px
fix(mobile): T7 — raise AppLayout icon buttons to 44px
fix(mobile): T8 — wrap ExploreScreen filter chips in 44px tap zone
fix(mobile): T9 — fix input font sizes to prevent iOS zoom
fix(mobile): T10 — add safe-area-inset-bottom to landing CTA
fix(mobile): T11 — PWA safe-area-inset-top on TopBar
fix(mobile): T12 — enable mobile nav on AdminScreen
```

---

## Out of Scope (Wave 2)

- Swipe-to-open drawer gesture
- Tablet two-column mini-rail sidebar (768–1023px)
- Pull-to-refresh on session list
- Bottom sheet for filter chips (vs current Radix dialog)
