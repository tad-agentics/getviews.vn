# Design tokens v2 — Getviews Studio

Phase A · A3.1 ships the token foundation that every new screen (Home,
Video, Channel, Kênh Tham Chiếu, Kịch Bản, Answer) will consume from A3.2
onwards. Living reference for what's available and how to use it.

Source: `src/app.css` (appended below the existing purple-era tokens).
Consumed via `--gv-*` CSS custom properties and the `.gv-*` utility
classes, or through the primitives in `src/components/v2/`.

## Why a separate namespace

The shadcn/Radix alias layer binds `--accent`, `--primary`, `--radius`
etc. to the old brand. Redefining them would break existing shadcn
components. All redesign tokens live under `--gv-*` so the two systems
coexist during A3.1 → A3.3 while old screens are still live.

## Colours

### Surfaces
| Token | Value | Use |
|---|---|---|
| `--gv-canvas` | `#FBFCFD` | Page background |
| `--gv-canvas-2` | `#F2F4F6` | Sidebar, subdued surfaces |
| `--gv-paper` | `#FFFFFF` | Cards, popovers |

### Ink scale
| Token | Value | Use |
|---|---|---|
| `--gv-ink` | `#0A0D12` | Headlines, primary text, ink-filled buttons |
| `--gv-ink-2` | `#1A1E26` | Hover state on ink surfaces |
| `--gv-ink-3` | `#4A5260` | Body text, captions |
| `--gv-ink-4` | `#8A94A3` | Faint labels, placeholders |

### Rules
| Token | Value | Use |
|---|---|---|
| `--gv-rule` | `#E6EAEF` | Card borders, default separators |
| `--gv-rule-2` | `#F0F3F6` | Subdued dividers inside cards |

### Accent 1 — pink
| Token | Value | Use |
|---|---|---|
| `--gv-accent` | `#FE2C55` | Primary CTA, pink dot in kicker, deltas (down) |
| `--gv-accent-soft` | `#FFE8ED` | Tinted backgrounds, selected row bg |
| `--gv-accent-deep` | `#D11840` | Hover on pink surfaces |

### Accent 2 — cyan
| Token | Value | Use |
|---|---|---|
| `--gv-accent-2` | `#25F4EE` | Secondary emphasis (wordmark dot, specific highlights) |
| `--gv-accent-2-soft` | `#D8FBFA` | Same tinting rule as accent-soft |
| `--gv-accent-2-deep` | `#06B6B0` | Hover on cyan surfaces |

### Semantic pos/neg
Every delta in the redesign is coloured by direction, not by brand.
Positive is blue, negative is pink (same palette as the accent — the
accent doubles as the "down" colour).

| Token | Value | Use |
|---|---|---|
| `--gv-pos` | `#009FFA` | ▲ deltas, upward sparklines |
| `--gv-pos-soft` | `#DBF0FF` | Tinted chip backgrounds |
| `--gv-pos-deep` | `#0070B8` | Hover / text on pos surfaces |
| `--gv-neg` | `#FE2C55` | ▼ deltas |
| `--gv-neg-soft` | `#FFE8ED` | — |
| `--gv-neg-deep` | `#D11840` | — |

### Data-viz accents
| Token | Value | Use |
|---|---|---|
| `--gv-lime` | `oklch(0.92 0.18 122)` | Chart accent |
| `--gv-azure` | `oklch(0.70 0.18 235)` | Chart accent |

## Typography

**TikTok Sans** is the primary UI sans: variable + static `@font-face` rules
at the top of `src/app.css` (files under `public/fonts/`). **Inter** loads from
Google Fonts in `app/root.tsx` as a fallback. **JetBrains Mono** loads via `@import` on the **first** line of `src/app.css`
(before `@import "tailwindcss"`) so the stylesheet stays valid CSS.

| Token / class | Stack |
|---|---|
| `--font-sans` (shadcn / legacy Make) | TikTok Sans → Inter → system |
| `--gv-font-display`, `--gv-font-sans`, `--gv-font-serif` | TikTok Sans → Inter → system (same stack; “serif” naming is legacy) |
| `--gv-font-mono` | JetBrains Mono → IBM Plex Mono → ui-monospace |

### Utility classes

| Class | Effect |
|---|---|
| `.gv-kicker` | Mono 10px / 0.18em tracked / uppercase / pink `●` prefix. Variants `.gv-kicker--pos` (blue dot), `.gv-kicker--muted` (grey dot). |
| `.gv-tight` | Display stack (TikTok Sans), `letter-spacing: -0.035em`, `font-weight: 600`. Pair with an explicit font-size at call sites. |
| `.gv-bignum` | Sans stack, `56px / line-height 1 / letter-spacing -0.04em / font-weight 600`. For pulse numbers and KPIs. |
| `.gv-serif` | Same sans stack, `font-weight: 500`, `letter-spacing: -0.02em` — editorial headings without a second typeface. |
| `.gv-serif-italic` | TikTok Sans italic emphasis (`font-style: italic`, weight 500). |
| `.gv-mono` | JetBrains Mono + tabular nums. |
| `.gv-uc` | Mono, uppercase, 0.08em tracked — for non-kicker small labels. |

## Spacing

Direct tokens (`--gv-space-1` through `--gv-space-8`: 4 / 8 / 12 / 16 / 24
/ 32 / 48 / 64 px) are available, but Tailwind's own scale matches 1:1
and is usually more ergonomic (`p-4`, `gap-6`, etc.). Prefer Tailwind
spacing; the tokens exist for inline styles where Tailwind can't reach.

## Radii

| Token | Value | Use |
|---|---|---|
| `--gv-radius-sm` | `6px` | Segmented control, chips |
| `--gv-radius-md` | `12px` | Default cards, buttons, inputs |
| `--gv-radius-lg` | `18px` | Hero cards, section surfaces |
| `--gv-radius-xl` | `20px` | Neo-brutalist composer |

## Surfaces

### `.gv-surface-brutal` + `.gv-surface-brutal--compact`

2px ink border + 6px hard offset shadow. Used by `<Composer>` and any
hero CTA card. The `--compact` variant drops the shadow to 4px and
radius to `--gv-radius-lg` for smaller composers (FollowUpComposer
inside a research thread).

```
<div class="gv-surface-brutal p-5">...</div>
```

## Primitives

Everything below lives in `src/components/v2/`. Import from the barrel:

```ts
import { Kicker, SectionHeader, Chip, Btn, Card, Composer,
         Segmented, Bignum } from "@/components/v2";
```

| Component | Purpose |
|---|---|
| `Kicker` | Wraps `.gv-kicker` with tone variants (`default` / `pos` / `muted`). |
| `SectionHeader` | Kicker + tight h2 + caption + optional right-side action. One call per section. |
| `Chip` | Pill. Variants: `default` / `accent` / `pos` / `neg` / `ink` / `lime`. Renders `<button>` when `onClick` passed, else `<span>`. |
| `Btn` | Pill button. Variants: `ink` / `ghost` / `accent` / `pos`. Sizes: `sm` / `md` / `lg`. |
| `Card` | Generic container. Variants: `paper` / `canvas` / `ink` / `brutal` / `brutal-compact`. |
| `Composer` | Neo-brutalist textarea + accent submit button. Enter submits (Shift+Enter newline). |
| `Segmented<V>` | Hard-edge 2+ button tab control. Ink-filled on active. Typed on the value union. |
| `Bignum` | 56px display number. Tone `ink` / `pos` / `neg`. Optional uppercase-mono suffix. |

## What this ships

- A3.1 wired the token layer + primitives into `ReferenceChannelsStep`
  (onboarding step 2) and the refactored `NicheSelector`. The rest of
  the app stayed on purple tokens.
- A3.2 added `/app/home` built entirely on v2 primitives; `/app/home`
  and `/app` both rendered HomeScreen.
- A3.3 is the route swap: `/app` IS Home; chat moves to `/app/chat`.
  Legacy `/app?session=X` URLs redirect into `/app/chat?session=X`. The
  sidebar gains two "Sắp có" placeholder nav entries for the forthcoming
  Kênh Tham Chiếu + Kịch Bản screens, plus a "Ngách của bạn" mini-block
  backed by the same pulse endpoint HomeScreen uses. Mobile adds a
  4-item bottom tab bar (Trang chủ / Chat / Xu hướng / Cài đặt).

## What not to do

- Don't redefine `--accent`, `--primary`, or `--radius`. They're the
  shadcn alias layer and rewriting them will silently break existing
  components.
- Don't reach for hex codes directly in JSX. If you need a colour that's
  not listed above, add a token here first — the redesign's discipline
  is that every colour has a token name.
- Don't use `.gv-serif-italic` except on headline emphasis words.
  Overuse turns it editorial-heavy and fails the studio feel.
