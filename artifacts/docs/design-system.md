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

-----

## 4. Spacing

8-point scale. Prefer Tailwind's spacing utilities (`p-4 = 16px`, `gap-6 = 24px`). Token fallbacks available for inline styles.

|Token         |Value|Tailwind        |
|--------------|-----|----------------|
|`--gv-space-1`|4px  |`p-1`, `gap-1`  |
|`--gv-space-2`|8px  |`p-2`, `gap-2`  |
|`--gv-space-3`|12px |`p-3`, `gap-3`  |
|`--gv-space-4`|16px |`p-4`, `gap-4`  |
|`--gv-space-5`|24px |`p-6`, `gap-6`  |
|`--gv-space-6`|32px |`p-8`, `gap-8`  |
|`--gv-space-7`|48px |`p-12`, `gap-12`|
|`--gv-space-8`|64px |`p-16`, `gap-16`|

-----

## 5. Radii

|Token           |Value|Use                                        |
|----------------|-----|-------------------------------------------|
|`--gv-radius-sm`|6px  |Segmented control, inline chips, small tags|
|`--gv-radius-md`|12px |Default cards, buttons, inputs             |
|`--gv-radius-lg`|18px |Hero cards, section surfaces               |
|`--gv-radius-xl`|20px |Neo-brutalist composer surface             |

In Tailwind: use `rounded-[6px]`, `rounded-[12px]`, `rounded-[18px]` or `rounded-[20px]` directly.

-----

## 6. Surfaces

### Card variants (via `<Card>` component)

|Variant         |Visual                                   |Use                               |
|----------------|-----------------------------------------|----------------------------------|
|`paper`         |White bg, `--gv-rule` border, 18px radius|Default content card              |
|`canvas`        |`--gv-canvas-2` bg, `--gv-rule-2` border |Subdued/secondary card            |
|`ink`           |`--gv-ink` bg, white text                |Pulse lead card, hero dark surface|
|`brutal`        |White bg, 2px ink border, 6px hard shadow|Composer, primary CTA             |
|`brutal-compact`|Same but 4px shadow, 18px radius         |FollowUp composer                 |

### `.gv-surface-brutal`

Hard-edge neo-brutalist surface. Used by the chat composer and primary CTA cards.

```css
background: var(--gv-paper);
border: 2px solid var(--gv-ink);
border-radius: var(--gv-radius-xl);
box-shadow: 6px 6px 0 var(--gv-ink);
```

`.gv-surface-brutal--compact` → 4px shadow, `--gv-radius-lg`.

-----

## 7. Layout

### Route column

All authenticated app screens use `.gv-route-main`:

```css
max-width: var(--gv-route-max-width);  /* 1280px */
margin: auto;
padding: 24px 28px 80px;
```

Variants:

- `.gv-route-main--answer` — `padding: 28px 28px 120px` (answer screen needs bottom space for composer + tab bar)

### Home screen column

`.gv-home-wrap` — `padding: 36px 28px 80px` (desktop), `2rem 1rem 4rem` (mobile).

### Navigation

- **Desktop:** sidebar (handled by `AppLayout.tsx`)
- **Mobile (≤900px):** `BottomTabBar` — 4 tabs: Trang chủ / Nghiên cứu / Xu hướng / Cài đặt. Fixed bottom, safe area padding for iOS.

### `TopBar` (per-screen sticky header)

`64px` desktop, `56px` mobile. Format: `gv-uc` kicker 9.5px + `.gv-tight` title 19px (24px desktop). Right slot for action buttons.

-----

## 8. Components — v2 Primitives

Import from `src/components/v2/`. These are the canonical primitives — do not recreate them.

### `<Kicker>`

```tsx
<Kicker dot>NGÁCH · SKINCARE</Kicker>
<Kicker tone="pos" dot>ĐANG LÊN</Kicker>
<Kicker tone="muted">BỔ SUNG</Kicker>
```

Props: `tone?: "default" | "muted" | "pos"`, `dot?: boolean`.

### `<SectionHeader>`

```tsx
<SectionHeader
  kicker="PATTERN TUẦN NÀY"
  title="Hook đang thắng"
  caption="Dựa trên 94 video · 7 ngày"
  right={<Btn variant="ghost" size="sm">Xem tất cả</Btn>}
/>
```

Renders: ● kicker (accent-deep mono 10px) + h2 28px tight + 13px caption inline.

### `<Card>`

```tsx
<Card variant="paper">...</Card>
<Card variant="brutal">...</Card>
```

Variants: `paper | canvas | ink | brutal | brutal-compact`.

### `<Btn>`

```tsx
<Btn variant="ink">Tạo kịch bản</Btn>
<Btn variant="ghost" size="sm">Xem thêm</Btn>
<Btn variant="accent">Nâng cấp</Btn>
<Btn variant="pos">Lên đầu bảng</Btn>
```

Variants: `ink | ghost | accent | pos`. Sizes: `sm (h-8) | md (h-10) | lg (h-12)`. All buttons are pill-shaped (`rounded-full`).

### `<Chip>`

```tsx
<Chip variant="pos">+31%</Chip>
<Chip variant="accent">Hook Cảm xúc</Chip>
<Chip onClick={handleClick}>Skincare</Chip>
```

Variants: `default | accent | pos | neg | ink | lime`. Renders as `<button>` when `onClick` is passed, else `<span>`.

### `<Segmented>`

```tsx
<Segmented
  value={mode}
  options={[
    { value: "win", label: "Thắng" },
    { value: "flop", label: "Flop" },
  ]}
  onChange={setMode}
/>
```

Hard-edge 2-button toggle. 1px ink border. Used for Win/Flop and Đang theo dõi/Khám phá.

### `<Bignum>`

```tsx
<Bignum tone="pos" suffix="VIEWS">2.8M</Bignum>
<Bignum tone="neg">-18%</Bignum>
```

56px display number. Tones: `ink | pos | neg`.

### `<KpiGrid>`

```tsx
<KpiGrid
  variant="channel"
  kpis={[
    { label: "AVG VIEWS", value: "3.2M", delta: "+12% vs tháng trước" },
    { label: "RETENTION", value: "71%", delta: "↑ 4pp" },
  ]}
/>
```

2×2 responsive KPI strip. Variants: `video` (30px values, paper cells) | `channel` (22px values, canvas cells).

### `<FilterChipRow>`

```tsx
<FilterChipRow label="LỌC THEO" trailing={<SearchInput />}>
  <Chip onClick={() => setNiche("skincare")}>Skincare</Chip>
  <Chip onClick={() => setNiche("beauty")}>Làm đẹp</Chip>
</FilterChipRow>
```

Filter ribbon with left-aligned chips and right-aligned search/action slot.

### `<TopBar>`

```tsx
<TopBar
  kicker="SOI KÊNH"
  title="Phân tích đối thủ"
  right={<Btn variant="ghost" size="sm">Lịch sử</Btn>}
/>
```

### `<SectionHeader>` vs `<TopBar>` — when to use which

|            |`TopBar`                    |`SectionHeader`                |
|------------|----------------------------|-------------------------------|
|Position    |Sticky, top of screen       |Inside content flow            |
|Title size  |19–24px `.gv-tight`         |28px `.gv-tight`               |
|Kicker style|`.gv-uc` 9.5px              |`gv-uc` 10px with `●`          |
|Use for     |Per-screen navigation header|Section heading inside a screen|

-----

## 9. Report Components

Report bodies live in `src/components/v2/answer/`. Each report type has a dedicated `*Body.tsx`.

### `<AnswerBlock>`

The outer shell wrapping any report body. Pink mono kicker + white bordered card.

```tsx
<AnswerBlock kicker="Pattern">
  <PatternBody report={report} />
</AnswerBlock>
```

### `<ConfidenceStrip>`

Always render at the top of every report body. Shows `N=`, window, niche, freshness.

- `thinSample` (sample_size < 30) → renders orange "MẪU MỎNG" toggle
- `intent_confidence: "low"` with `sample_size: 0` → fixture data signal

### `<HookFindingCard>`

Ranked hook finding. Grid: rank number left, pattern + insight centre, retention/delta right. Lifecycle pill inline.

### Confidence and data honesty

- Never show a report without `<ConfidenceStrip>` at the top
- If data is fixture (sample_size = 0), `intent_confidence` must be `"low"` — the strip shows "MẪU MỎNG"
- The `execution_tip` field from `niche_insights` is the most actionable data point — surface it prominently in Pattern and Ideas reports

-----

## 10. Animation

|Name    |Duration |Use                                         |
|--------|---------|--------------------------------------------|
|Instant |0ms      |Toggles, active press state                 |
|Fast    |120ms    |Hover, focus, border color, icon color      |
|Normal  |200ms    |Panel slide, tab switch, tooltip            |
|Emphasis|400ms    |Diagnosis row reveal, bar fill, card stagger|
|Slow    |600–800ms|Dopamine moments only (D1–D4)               |

**Hard rule: nothing > 800ms.**

`.gv-fade-up` — light entrance animation (0.45s ease-out, 8px Y translate). Use for streaming content reveals. Delay variants: `.gv-fade-up-delay-1` (60ms), `.gv-fade-up-delay-2` (120ms), `.gv-fade-up-delay-3` (140ms).

`@keyframes gv-pulse` — live dot heartbeat. `opacity + scale` oscillation over 1 cycle.

-----

## 11. Icons

**Lucide React** is the only icon library. Import directly:

```tsx
import { TrendingUp, Film, Eye } from "lucide-react";
```

Do not install or use Heroicons, Phosphor, or any other icon set. `strokeWidth={1.7}` is the standard for UI icons at 16–20px.
