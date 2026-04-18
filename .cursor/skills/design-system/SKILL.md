---
name: design-system
description: Minimal design system reference. Produces a component inventory from `artifacts/uiux-reference/` + `src/components/ui/` and any EDS color/font summary. Read when running /foundation to catalog components.
disable-model-invocation: true
---

# Design System — Component inventory

Visual reference: **`artifacts/uiux-reference/`** (JSX + `styles.css`) plus production **`src/components/ui/`**. This skill produces a component inventory during Foundation.

**Output:** `artifacts/docs/design-system-spec.md` — component inventory only.

**Why this exists:** Product teams often add a **design system rules** layer so agents stop guessing. RAD does **not** require Figma MCP; this skill produces a **contract** from **the tracked UIUX pack + live `src/components/ui/`** — a single inventory doc agents read before integrating screens or adding shared UI.

---

## When This Runs

During `/foundation`, before building screens. The Product Designer or Tech Lead catalogs the reference + primitives to give the Frontend Developer a clear component map.

## Process

1. **Read `artifacts/uiux-reference/app.jsx`** — route ids and screen wiring (and optional gitignored `src/make-import/App.tsx`).

2. **Catalog `src/components/ui/`** — list every UI primitive (historically from Make):
   - Component name, props, variants
   - Note: these move to `src/components/ui/` as-is during Foundation

3. **Identify gaps** — compare Make's components against screen spec metadata:
   - Does Make provide loading states? (Usually no — add `SkeletonCard`)
   - Does Make provide error states? (Usually no — add `ErrorBanner`)
   - Does Make provide empty states? (Usually no — add `EmptyState`)
   - Any other shared component needed by 2+ screens that Make didn't generate?

4. **Extract color/font values** — scan Make's Tailwind classes for the brand palette:
   - Primary colors used across components
   - Font families referenced
   - Make typically defines these in a `theme.css` using CSS custom properties + Tailwind v4's `@theme inline`. Keep this CSS-based approach — copy into `src/app.css` during Foundation.

5. **Write `artifacts/docs/design-system-spec.md`**

## Output Format

````markdown
# Design System — [App Name]
**Source:** Figma Make code output

---

## Make UI Components (src/components/ui/)

Moved from Make as-is. Do not modify.

| Component | File | Props | Notes |
|---|---|---|---|
| Button | `button.tsx` | variant, size, disabled | Primary, secondary, ghost variants |
| Card | `card.tsx` | — | Container with padding |
| Dialog | `dialog.tsx` | open, onClose | Modal overlay |
| [catalog all from Make...] | | | |

## Additional Shared Components (build in Foundation)

| Component | File | Required states | Why needed |
|---|---|---|---|
| `EmptyState` | `src/components/EmptyState.tsx` | with/without CTA | Make has no empty states |
| `ErrorBanner` | `src/components/ErrorBanner.tsx` | with retry | Make has no error states |
| `SkeletonCard` | `src/components/SkeletonCard.tsx` | shimmer | Make has no loading states |
| [add only what's missing from Make...] | | | |

## Brand Tokens (if Make uses custom values)

Only document if Make's output uses custom token values. Make typically defines these in CSS custom properties via `@theme inline` — document the values here for reference, but keep them in CSS (do not migrate to `tailwind.config.ts`).

| Token | Value | Source |
|---|---|---|
| Primary color | `[value]` | Most frequent accent color in Make's components |
| Font family | `[value]` | Font referenced in Make's className strings |
````

---

## Quality Check

- Every Make UI component cataloged
- Gap analysis complete — missing states identified
- No placeholder entries — all from actual Make code
- Brand token values match what Make's code actually uses
