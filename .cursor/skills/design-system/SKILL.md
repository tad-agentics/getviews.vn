---
name: design-system
description: Minimal design system reference for Figma Make projects. Produces a component inventory from Make's code output and any EDS color/font summary needed for the Make prompt guide. No token generation — Make handles visual design. Read this when running /foundation to catalog Make's components.
disable-model-invocation: true
---

# Design System — Make Component Inventory

Figma Make handles visual design — colors, typography, spacing, component styling. There is no separate token extraction or theme generation step. This skill produces a component inventory from Make's code output during Foundation.

**Output:** `artifacts/docs/design-system-spec.md` — component inventory only.

**Why this exists:** Product teams often add a **design system rules** layer so agents stop guessing. Figma’s MCP-oriented version ([Create Design System Rules](https://developers.figma.com/docs/figma-mcp-server/skill-figma-create-design-system-rules/)) bakes in discovery paths, tokens, and a mandatory implement flow. RAD does **not** require Figma MCP; this skill produces the **same kind of contract** from **Make’s code output** — a single inventory doc agents read before integrating screens or adding shared UI, so conventions stay consistent without re-prompting.

---

## When This Runs

During `/foundation`, before building screens. The Product Designer or Tech Lead catalogs Make's output to give the Frontend Developer a clear component map.

## Process

1. **Read `src/make-import/`** — understand the full component tree from `App.tsx`

2. **Catalog `src/make-import/components/ui/`** — list every UI primitive Make generated:
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
