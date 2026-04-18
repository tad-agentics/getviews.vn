# Studio Home — pixel audit vs UIUX reference

**Reference:** `artifacts/uiux-reference/screens/home.jsx` + `artifacts/uiux-reference/styles.css`  
**Implementation:** `src/routes/_app/home/*`, `src/components/v2/{SectionHeader,Composer}.tsx`, `src/app.css` (`--gv-*` tokens)  
**Date:** 2026-04-19

Tokens in code map 1:1 to reference (`--gv-canvas` ↔ `--canvas`, `--gv-accent-deep` ↔ `--accent-deep`, etc.) except where noted below.

---

## Shell not in static reference

| Element | Reference | App |
|--------|-----------|-----|
| Top bar (“STUDIO · Sảnh Sáng Tạo”) | Not in `home.jsx` (starts at `Ticker`) | Present — intentional product shell |
| Mobile bottom tab bar | Not modeled | Present |

---

## Page frame

| Spec | Reference | App (target) |
|------|-----------|----------------|
| Max width | `1320px` | `max-w-[1320px]` via `.gv-home-wrap` |
| Horizontal padding | `28px` | `36px 28px` at `md+` in `.gv-home-wrap` |
| Bottom padding | `80px` | `80px` at `md+` |

---

## Ticker

| Spec | Reference | Notes |
|------|-----------|--------|
| Background | `var(--ink)` | Match `--gv-ink` |
| Text | `mono` 11px | Align `TickerMarquee` to 11px |
| Tag color | `var(--accent)` 600 | `--gv-accent` |
| Padding | `8px 0` | Verify vertical padding |

---

## Greeting row + H1

| Spec | Reference | Notes |
|------|-----------|--------|
| Row gap under chips / date | `marginBottom: 14` before H1 | Use `mb-3.5` on chip row |
| H1 max width | `880px` | Use `max-w-[880px]` for pixel parity (was widened to 1180 for layout preference) |
| H1 size | `clamp(36px, 4.6vw, 60px)`, lh `1.02`, tracking `-0.04em`, weight `600` | Matches |
| Niche pill | `padding: 0 10px`, `borderRadius: 10`, `rotate(-1deg)`, bg accent | Matches `px-2.5`, `rounded-[10px]` |
| Hook count color | `rgb(0, 159, 250)` | `--gv-pos` `#009FFA` |

---

## Composer

| Spec | Reference | Notes |
|------|-----------|--------|
| Outer padding | `4px` (`padding: 4`) | `p-1` on brutal shell |
| Textarea inset | `18px 22px 8px` | Inner wrapper `pt-[18px] px-[22px] pb-2` |
| Textarea | `17px`, `lineHeight: 1.5` | Matches `studio` layout |
| Toolbar | `borderTop` rule, `padding: 10px 14px` | `py-[10px] px-[14px]` |

---

## Suggested chips

| Spec | Reference `.chip` | Notes |
|------|---------------------|--------|
| Font | `12px`, weight `500` | `text-xs` |
| Padding | `6px 12px` | `py-1.5 px-3` |
| Gap | `8px` | `gap-2` |
| Section margin below | `56px` before `<hr>` | `mb-14` on chip row |

---

## Section header (editorial block)

| Spec | Reference | Implemented |
|------|-----------|-------------|
| Kicker | `mono` + `uc`, **10px**, color **`accent-deep`**, `●` + label, `marginBottom: 6` | `text-[10px]`, `text-[color:var(--gv-accent-deep)]`, `●`, `mb-1.5` |
| Title | `tight`, **28px**, lh `1`, weight `600` | `gv-tight` + `text-[28px] leading-none` |
| Caption | **13px**, `ink-3`, **beside** title (`flex`, `baseline`, `gap: 12`) | Inline row with `gap-3` |
| Header align | `alignItems: flex-end` | `items-end` with optional `right` action |

---

## `<hr />` rules

| Spec | Reference | Notes |
|------|-----------|--------|
| Margin below rule | `36px` | `mb-9` / section spacing |

---

## Morning ritual (3 cards)

| Spec | Reference | Notes |
|------|-----------|--------|
| Grid gap | `12px` | `gap-3` |
| Card padding | `18px 18px 16px` | `px-[18px] pt-[18px] pb-4` |
| Internal gap | `10px` | `gap-2.5` |
| Min height | `180px` | `min-h-[180px]` |
| Hero hover | `translate(-2px,-2px)`, shadow `4px 4px 0` accent | `-translate-x-0.5 -translate-y-0.5` + shadow |
| Non-hero hover | shadow `4px 4px 0` ink | Matches |
| Title | serif block **20px** (reference `fontFamily: var(--serif)`) | `gv-serif-italic text-[20px]` |

---

## Quick actions + Pulse grid

| Spec | Reference | Notes |
|------|-----------|--------|
| Grid columns | `2fr` / `1fr`, `gap: 36` | `gap-9` (36px) |
| Section margin | `marginBottom: 56` | `mb-14` (56px) after block |
| Quick grid | `gap: 1`, hairline grid, `borderRadius: 8` | Already hairline + rounded |

---

## Hooks table + Breakout order

| Spec | Reference `home.jsx` | App |
|------|----------------------|-----|
| Order | Hooks section **then** Breakout | Match reference: **Hooks → Breakout** |

---

## Breakout grid

| Spec | Reference | Notes |
|------|-----------|--------|
| Grid | `minmax(280px,1fr)`, `gap: 18` | `gap-[18px]`, responsive cols |
| Tile aspect | **`4 / 5`** | `aspect-[4/5]` |
| Tile radius | **`10px`** | `rounded-[10px]` |
| BREAKOUT chip | accent bg, **10px** bold uppercase ~`0.05em` | Align badge typography |
| Duration | `mono` **11px** top-right | `text-[11px]` |
| Quote on tile | `tight` **22px**, lh `1.1`, text shadow | `text-[22px] leading-[1.1]` |
| Row below | creator `mono` 11 `ink-3`; views **`accent-deep`** **700** `↑` | `text-[color:var(--gv-accent-deep)]` |
| Hook line | **12px** `ink-3`, hook phrase **600** `ink-2` | Match |

---

## Pulse card

Reference `PulseCard` is a lighter **paper** card with bignum; app uses **ink** `Card variant="ink"` for emphasis. Treated as **intentional** product differentiation — flag if marketing wants strict parity.

---

## Checklist for future QA

- [ ] Compare screenshot overlay on `1320px` and `390px` widths  
- [x] Ticker: full row `gv-mono` **11px**; tag **600** + accent bucket color; headline **85%** opacity; separator **40%** (2026-04-19)  
- [ ] Niche picker (`NichePicker`) vs reference `padding: 10px 16px`, `1px solid ink`  

---

## Implementation pass (2026-04-19)

Aligned in code:

- **`SectionHeader`:** ● kicker in **`accent-deep`** mono 10px; **`mb-4`** (16px); title **28px**; caption **13px** `ink-3` **beside** title (`flex-wrap` + baseline); **`items-end`** when `right` action present.  
- **`Composer` (studio):** Shell **`p-1` (4px)**; textarea inset **`18px 22px 8px`**; toolbar **`10px 14px`** + rule border.  
- **`HomeScreen`:** Chip row **`mb-3.5`** (14px); H1 + composer + chips **`max-w-[880px]`**; suggested **`text-xs`**, chip hover; suggested block **`mb-14`** (56px); rules **`mb-9`** only; morning block **`mb-12`** (48px); two-column **`gap-9`** + **`mb-14`**; section order **Hooks → Breakout**; hooks block **`mb-12`**.  
- **`QuickActions` / `HooksTable`:** Removed extra **`mt-5`** under headers (spacing from **`SectionHeader` `mb-4`**).  
- **`HomeMorningRitual`:** Grid **`gap-3`** (12px); cards **`min-h-[180px]`**, padding **`18/18/16`**, **`gap-2.5`**; hover **`translate(-2px,-2px)`** + shadow.  
- **`BreakoutGrid`:** **`auto-fit minmax(280px,1fr)`**, **`gap-[18px]`**, **`aspect-[4/5]`**, **`rounded-[10px]`**; **`BREAKOUT`** badge; title **22px** + shadow; **`↑`** views **`accent-deep`** **11px** **700**; hook line **12px**. Thumbnails: bottom **readability gradient**.  
- **`PulseCard`:** Wrapper **`mt-4`** removed (spacing from header).  

**Still divergent (by choice or not yet ported):** TopBar shell; `PulseCard` **ink** surface vs reference **paper** card; `NichePicker` dimensions.
