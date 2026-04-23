# GetViews.vn — Design System

**Source of truth:** `src/app.css` (tokens + utility classes), `src/components/v2/` (primitives), `.cursor/rules/copy-rules.mdc` (copy standards).

This document is the single reference for all new screens and components. Before writing any UI code, read this first. Do not introduce new tokens, colors, or component patterns without checking here.

-----

## 1. Design Philosophy

**Studio aesthetic.** Analytical, data-dense, confident. Every screen is a dashboard, not a landing page. The visual grammar comes from financial terminals and editorial newsrooms — not SaaS marketing.

**Gần gũi rule.** Every AI output must feel like a peer expert talking to a working Vietnamese creator, not a product talking at a user. Copy is direct, data-backed, Vietnamese-first.

**Light mode only.** `GetViews.vn` is permanently light. The `.dark` class forces light values. Do not implement or support dark mode.

**TikTok brand integration.** Two accents — pink (`#FE2C55`) and cyan (`#25F4EE`) — mirror TikTok's own palette. This is intentional and non-negotiable. They signal that the product understands TikTok natively.

-----

## 2. Color Tokens

All tokens are CSS custom properties defined in `:root` in `src/app.css`. **Never use raw hex values in JSX.** Always reference a token via `var(--gv-*)` or a Tailwind class.

### Surfaces

|Token          |Value    |Use                                          |
|---------------|---------|---------------------------------------------|
|`--gv-canvas`  |`#FBFCFD`|Page background, outer shell                 |
|`--gv-canvas-2`|`#F2F4F6`|Sidebar, subdued surface, confidence strip bg|
|`--gv-paper`   |`#FFFFFF`|Cards, popovers, inputs, modal content       |

### Ink (text + icon)

|Token       |Value    |Use                                                  |
|------------|---------|-----------------------------------------------------|
|`--gv-ink`  |`#0A0D12`|Headlines, primary text, ink-filled buttons          |
|`--gv-ink-2`|`#1A1E26`|Body text, secondary headings                        |
|`--gv-ink-3`|`#4A5260`|Captions, descriptions, metadata                     |
|`--gv-ink-4`|`#8A94A3`|Placeholders, disabled, subtle labels, kicker default|

### Rules (borders + dividers)

|Token        |Value    |Use                             |
|-------------|---------|--------------------------------|
|`--gv-rule`  |`#E6EAEF`|Card borders, default separators|
|`--gv-rule-2`|`#F0F3F6`|Subdued dividers inside cards   |

### Accent 1 — TikTok Pink

|Token             |Value    |Use                                                |
|------------------|---------|---------------------------------------------------|
|`--gv-accent`     |`#FE2C55`|Primary CTA, kicker dot, negative delta, `--gv-neg`|
|`--gv-accent-soft`|`#FFE8ED`|Tinted chip/tag backgrounds, accent-soft surfaces  |
|`--gv-accent-deep`|`#D11840`|Hover on pink surfaces, section kicker text        |

### Accent 2 — TikTok Cyan

|Token               |Value    |Use                             |
|--------------------|---------|--------------------------------|
|`--gv-accent-2`     |`#25F4EE`|Secondary emphasis, wordmark dot|
|`--gv-accent-2-soft`|`#D8FBFA`|Tinted chip backgrounds         |
|`--gv-accent-2-deep`|`#06B6B0`|Hover on cyan surfaces          |

### Semantic: Positive / Negative

Positive is **blue**. Negative is **pink** (same as accent). This is intentional — the accent doubles as "down."

|Token          |Value    |Use                                       |
|---------------|---------|------------------------------------------|
|`--gv-pos`     |`#009FFA`|▲ deltas, upward sparklines, positive KPIs|
|`--gv-pos-soft`|`#DBF0FF`|Tinted chip bg for positive values        |
|`--gv-pos-deep`|`#0070B8`|Hover on pos surfaces, pos chip text      |
|`--gv-neg`     |`#FE2C55`|▼ deltas (same as `--gv-accent`)          |
|`--gv-neg-soft`|`#FFE8ED`|Same as `--gv-accent-soft`                |
|`--gv-neg-deep`|`#D11840`|Same as `--gv-accent-deep`                |

### Severity

|Token           |Value    |Use                                                   |
|----------------|---------|------------------------------------------------------|
|`--gv-danger`   |`#B91C1C`|Destructive actions, error states, WhatStalled section|
|`--gv-warn`     |`#B45309`|Warning-level ops alerts (amber)                      |
|`--gv-warn-soft`|`#FEF3C7`|Warning tinted bg                                     |

### Data Viz

|Token                 |Value                 |Use                                      |
|----------------------|----------------------|-----------------------------------------|
|`--gv-lime`           |`oklch(0.92 0.18 122)`|Chart accent 1                           |
|`--gv-azure`          |`oklch(0.70 0.18 235)`|Chart accent 2                           |
|`--gv-chart-benchmark`|`rgb(0, 159, 250)`    |Benchmark stroke in video retention chart|

### Misc

|Token                     |Value                  |Use                                   |
|--------------------------|-----------------------|--------------------------------------|
|`--gv-scrim`              |`rgb(10 12 16 / 35%)`  |Modal/drawer backdrop                 |
|`--gv-forecast-primary-bg`|`rgb(255 255 255 / 8%)`|Forecast row bg on primary action card|

-----

## 3. Typography

### Font Stacks

|Token              |Stack                                        |Use                                               |
|-------------------|---------------------------------------------|--------------------------------------------------|
|`--gv-font-sans`   |TikTok Sans → Inter → system-ui              |All UI text                                       |
|`--gv-font-display`|TikTok Sans → Inter → system-ui              |Display headings (same stack — no second typeface)|
|`--gv-font-mono`   |JetBrains Mono → IBM Plex Mono → ui-monospace|All numerical data, kickers, code                 |

**TikTok Sans** is self-hosted under `public/fonts/` (variable woff2 + static fallbacks). It loads via `@font-face` in `src/app.css`. Never import it from Google Fonts.

**JetBrains Mono** loads via `@import url(...)` at the top of `src/app.css`. Use it for every number displayed in the UI — credit counts, statistics, corpus sizes, multipliers.

### Utility Classes

These are the **only** typography utilities — use them everywhere instead of writing custom letter-spacing or font-weight combinations.

#### `.gv-kicker`

Mono all-caps label. The `●` dot prefix is opt-in.

```
font-family: var(--gv-font-mono)
font-size: 10px
letter-spacing: 0.16em
text-transform: uppercase
color: var(--gv-ink-3)
font-weight: 600
```

**Modifiers:**

- `.gv-kicker--dot` — prepends a 6px pink dot before the label
- `.gv-kicker--dot.gv-kicker--muted` — grey dot
- `.gv-kicker--dot.gv-kicker--pos` — blue dot

#### `.gv-tight`

Display headline weight. Aggressive letter-spacing. Always pair with an explicit font-size.

```
letter-spacing: -0.035em
font-weight: 600
font-family: var(--gv-font-display)
```

#### `.gv-bignum`

56px display number for KPI and pulse cells. Responsive: 40px at 900px, 34px at 560px.

```
font-size: 56px
line-height: 0.95
letter-spacing: -0.04em
font-weight: 600
```

#### `.gv-serif`

Editorial heading weight — medium, tight tracking. Same font as body (no second typeface).

```
font-weight: 500
letter-spacing: -0.02em
```

#### `.gv-serif-italic`

Italic emphasis for headline words or quoted script titles. Use sparingly.

```
font-style: italic
font-weight: 500
```

#### `.gv-mono`

Standalone mono utility. Includes tabular numerals.

```
font-family: var(--gv-font-mono)
font-variant-numeric: tabular-nums
```

#### `.gv-uc`

Uppercase tracked — for small non-kicker labels.

```
text-transform: uppercase
letter-spacing: 0.08em
font-family: var(--gv-font-mono)
```

### Type Scale in Practice

|Context              |Class + size       |Example               |
|---------------------|-------------------|----------------------|
|Page / section kicker|`.gv-kicker` 10px  |`NGÁCH · SKINCARE`    |
|Section title        |`.gv-tight` 28px   |`Pattern đang thắng`  |
|Card heading         |`.gv-serif` 17–22px|`Hook Cảm xúc`        |
|Body text            |default 14px / 1.5 |Descriptions, insights|
|Caption / metadata   |default 13px ink-3 |`7 ngày · 94 video`   |
|Mono data            |`.gv-mono` 10–13px |`73%` `+11%` `#1`     |
|KPI display number   |`.gv-bignum`       |`2.8M`                |
