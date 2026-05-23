# UIUX Improvement Plan — GetViews.vn

**Date:** 2026-05-23 (full-coverage audit refresh)  
**Status:** Draft — Tech Lead review  
**Branch baseline:** `main` @ `b479f64` (Post-W5 launch gate)  
**Gate:** Blocks `/pre-handoff` until Phase 0 decisions land + visual audit B-01/B-02 closed

### Compliance snapshot (FE vs `design-system.html`)

| Scan scope | Count |
|------------|-------|
| Files scanned | **364** (excl. tests) |
| Major routes scored | **20** (§2.6.1) |
| UI primitives scored | **10** (§2.6.3) |
| `.gv-fade-up` usages | **44** across 9 answer/home/admin files |

| Severity | Open | Summary |
|----------|------|---------|
| **BLOCKING** | V-01–V-04 | Motion, PRM loops, lime fill, icon aria |
| **HIGH** | V-05–V-10, V-16–V-18 | Cards, data, copy, hex, multi-CTA, shadows |
| **MEDIUM/LOW** | V-11–V-15, V-19–V-20 | Focus, trends, radius, touch |
| **Route verdicts** | **0 PASS · 13 CONCERNS · 7 FAIL** | No major screen fully clean |
| **Global PASS** | 14 checks | §2.5.1 — forbidden colors, fonts, slop |

---

## Sources

| Document | Role |
|----------|------|
| [`artifacts/docs/branding-guideline.html`](../docs/branding-guideline.html) | Brand SSOT v1.1 — logo, palette origin, voice, do/don't |
| [`artifacts/docs/design-system.html`](../docs/design-system.html) | Product DS v1.0 — tokens, components, motion, a11y, 32 anti-patterns |
| [`artifacts/qa-reports/visual-audit-launch-2026-05-23.md`](../qa-reports/visual-audit-launch-2026-05-23.md) | Launch visual fidelity audit (PASS_WITH_CONCERNS) |
| [`artifacts/docs/emotional-design-system.md`](../docs/emotional-design-system.md) | EDS — emotional thesis, dopamine moments D1–D4, interaction timing (**§5 colors stale**) |
| [`artifacts/docs/design-system-spec.md`](../docs/design-system-spec.md) | Make component inventory (Foundation) |
| [`artifacts/uiux-reference/`](../uiux-reference/) | Studio UIUX pack — screen JSX reference (may lag token pivot) |
| [`src/app.css`](../../src/app.css) | Runtime token implementation (`--gv-*` namespace) |
| [`.cursor/rules/design-system.mdc`](../../.cursor/rules/design-system.mdc) | AI Slop Guard + token compliance rules |

---

## 1. Executive summary

**Current state:** Production at https://www.getviews.vn implements the **Getviews Magenta** pivot (`#F72585`) consistently via `--gv-accent` / `--primary`. The launch visual audit flagged this as BLOCKING because EDS §5 still documents **TikTok Purple** `#7C3AED`. The newly imported **Branding Guideline** and **Design System** HTML docs explicitly canonize magenta + sky as the independent palette — production is **correct per brand**; documentation hierarchy was wrong, not the UI.

**Gap summary:**

| Layer | Accent primary | Ink anchor | Page canvas | Sans stack |
|-------|----------------|------------|-------------|------------|
| EDS §5 (Apr 2026) | `#7C3AED` purple | `#18181B` | `#EDEDEE` | TikTok Sans |
| Branding Guideline v1.1 | `#F72585` magenta (`--accent`) | `#0A0D12` | `#FBFCFD` | Space Grotesk (doc specimen) |
| Design System v1.0 | `#F72585` (`--accent`) | `#0A0D12` | `#FBFCFD` | Space Grotesk (doc specimen) |
| `src/app.css` (live) | `#F72585` (`--gv-accent`) | `#0A0D12` (`--gv-ink`) | `#FBFCFD` (`--gv-canvas`) | **TikTok Sans** (ship decision) |

**Recommended canonical hierarchy (highest wins for conflicts):**

1. **`src/app.css` `--gv-*`** — implementation truth for engineers  
2. **`artifacts/docs/branding-guideline.html` + `design-system.html`** — brand + component spec for designers/QA  
3. **`artifacts/docs/emotional-design-system.md`** — emotion, copy, motion tiers, D1–D4 (update §5 to match brand)  
4. **`artifacts/uiux-reference/`** — screen layout/composition reference; defer to tokens above for colors/type  
5. **`artifacts/docs/design-system-spec.md`** — legacy Make inventory; update incrementally, do not treat purple-era tokens as authoritative

**B-01 resolution (recommendation): Option A+** — Do **not** revert to purple. Update EDS §5 + `design-system-spec.md` header to reference Branding §04. Mark visual audit B-01 **CLOSED** once EDS is patched. Completeness: 10/10.

**FE compliance (§2.5):** Tokens/colors align with Branding v1.1. **Implementation gaps** are concentrated in motion (V-01/V-02), data formatting (V-06), copy (V-07/V-08), and a banned component pattern (V-05 left-border cards). No forbidden platform colors or AI slop patterns in production TSX.

---

## 2. Token & brand alignment

### 2.1 Brand → `--gv-*` mapping (verified)

| Brand / DS token | Hex | `src/app.css` | Status |
|------------------|-----|---------------|--------|
| `--accent` | `#F72585` | `--gv-accent` | ✅ Aligned |
| `--accent-soft` | `#FDD9EA` | `--gv-accent-soft` | ✅ Aligned |
| `--accent-deep` | `#B8175F` | `--gv-accent-deep` | ✅ Aligned |
| `--accent-2` | `#4CC9F0` | `--gv-accent-2` | ✅ Aligned |
| `--accent-2-soft` | `#DAF1FB` | `--gv-accent-2-soft` | ✅ Aligned |
| `--ink` | `#0A0D12` | `--gv-ink` | ✅ Aligned |
| `--ink-2` … `--ink-4` | per DS §02 table | `--gv-ink-2` … `--gv-ink-4` | ✅ Aligned |
| `--canvas` | `#FBFCFD` | `--gv-canvas` | ✅ Aligned |
| `--canvas-2` | `#F2F4F6` | `--gv-canvas-2` | ✅ Aligned |
| `--rule` / `--rule-2` | `#E6EAEF` / `#F0F3F6` | `--gv-rule` / `--gv-rule-2` | ✅ Aligned |
| `--paper` | `#FFFFFF` | `--gv-paper` | ✅ Aligned |
| `--pos` / `--pos-soft` | `#009FFA` / `#DBF0FF` | `--gv-pos` / `--gv-pos-soft` | ✅ Aligned |
| `--neg` | `#F72585` (shares accent) | `--gv-neg` | ✅ Aligned by design |
| `--lime` | `#D7F542` | `--gv-lime` (oklch equiv) | ✅ Aligned |

### 2.2 Legacy shadcn alias layer

`--primary`, `--ring`, `--sidebar-primary` → `var(--gv-accent)`. No change needed post B-01 doc fix.

### 2.3 Intentional ship deviations (document, don't "fix")

| Topic | Brand/DS doc | Production | Action |
|-------|--------------|------------|--------|
| **Sans stack** | Space Grotesk | TikTok Sans (self-hosted) | Add footnote to DS HTML + EDS §5: "Ship uses TikTok Sans for VN diacritics + creator familiarity" |
| **Background token name** | `--canvas` | Also `--background: oklch(0.93…)` legacy | Migrate landing to `--gv-canvas` where still on `#EDEDEE` |
| **EDS success color** | Green oklch | `--success` green + `--gv-pos` blue for trends | EDS §5 semantic table → match DS `--pos` for "up" |
| **Dark mode** | DS documents overrides | v1 light-only per EDS | Out of scope until v2 |

### 2.4 Conflicts requiring human decision

| ID | Conflict | Options | Recommendation |
|----|----------|---------|----------------|
| **H-01** | Sans: Space Grotesk (brand pack) vs TikTok Sans (live) | A) Keep TikTok Sans B) Switch to Space Grotesk + self-host | **A** — already shipped, VN market fit |
| **H-02** | Trends active chip uses ink fill (NB-06) vs DS "one accent per surface" | A) Magenta-soft active chip B) Keep ink (editorial) | **A** for filter chips — ink reserved for primary CTAs per Branding §04 |
| **H-03** | Landing corpus "1.500+" vs system-design "46,000+" | See §7 | **Dynamic stat** from DB with humility tier |
| **H-04** | EDS D1–D4 allows 600–800ms emphasis; DS §06 caps transitions at **400ms** (loops excepted) | A) Amend DS for diagnosis reveal tier B) Cap D1 at 400ms | **DECIDED 2026-05-23: Option B** — strict 400ms cap everywhere including D1–D4; EDS §6 updated |

---

## 2.5 Rule-based compliance scan (2026-05-23)

Automated scan of `src/` against **Design System v1.0** §17 **32 never rules** + token patterns. Excludes `*.test.*`. **Superseded for screen coverage by §2.6** — keep for global PASS evidence.

### 2.5.1 PASS — no action required

| DS rule | Check | Result |
|---------|-------|--------|
| Never TikTok pink `#FE2C55` / Douyin `#FF0050` | TSX/className | **0 hits** |
| Never purple `#7C3AED` in product TSX | className | **0 hits** (EDS stale only) |
| Never traffic-light green/red for trends | `text-green-*`, `bg-red-*`, `#22C55E`, `#EF4444` on trend UI | **0 hits** on `/app` trend surfaces |
| Never Inter/Roboto/Arial as product font | `font-family` in TSX | **0 hits** — TikTok Sans via `gv-studio-type` |
| Never Title Case buttons | Heuristic on `Button`/`Btn` labels | **0 hits** |
| Never nest cards >1 level | Radix `Card` inside `Card` inside `Card` | **0 hits** |
| Never two magenta CTAs same viewport | `Btn variant="accent"` / `gradient-cta` per route | **0 simultaneous** — ink CTAs used elsewhere ✓ |
| Never bouncy cubic-bezier (CSS) | negative control points in CSS | **0 hits** |
| Never `quý khách` | product strings | **0 hits** |
| Never vague Submit/Start/Go | button labels | **0 hits** |
| Never static hex in `style={{}}` | inline styles | **0 hits** (dynamic values only) |
| Never large cyan/sky body fill | `--gv-accent-2` backgrounds | **0 large fills** |
| Instrument Serif whole-headline | `gv-serif-italic` usage | **Compliant** — single `<em>` words (onboarding, hero strips) |
| AI Slop Guard (design-system.mdc) | gradient purple bg, 3-col icon grids, decorative blobs | **0 hits** on audited routes |
| Diagnosis ✓/✕ markers | EDS + copy-rules | **Allowed** — not emoji-as-chrome |

### 2.5.2 BLOCKING violations

#### V-01 — Transition duration >400ms (DS §06, rule #20)

**Rule:** "Never animate for longer than 400ms" (loops/shimmer excepted).

| Location | Duration | Scope |
|----------|----------|-------|
| `src/app.css:637-638` | **450ms** `.gv-fade-up` | **~30+ sections** — `PatternBody`, `IdeasBody`, `DiagnosticBody`, `LifecycleBody`, `TimingBody`, `GenericBody`, `HomeScreen`, `AdminScreen` |
| `src/components/ui/sheet.tsx:61` | **500ms** open | Drawer/sheet globally |
| `src/routes/_app/channel/components/StepProgress.tsx:59` | **500ms** | Channel SSE progress bar |
| `src/routes/_app/settings/SettingsScreen.tsx:416` | **900ms** | Credit usage bar `motion` transition |
| `src/routes/_index/LandingPage.tsx:809,863` | 500–600ms | Marketing motion stubs |
| `src/routes/_auth/login/route.tsx:218` | 450ms | Auth panel entrance |

**Note:** `.gv-fade-up` has PRM disable ✓ but duration still violates cap. **Fix:** reduce to `0.32s` (DS slow tier) or `0.24s` (base tier); sheet → `duration-300` max; StepProgress → `duration-300`.

**Conflict H-04:** EDS §6 D1 specifies 600–800ms diagnosis reveal — reconcile before changing answer result animations.

#### V-02 — Loops without `prefers-reduced-motion` (DS §06, rule #21)

| Location | Loop | PRM guard? |
|----------|------|------------|
| `src/app.css:241-252` | `.animate-scroll-infinite`, `.animate-scroll-ticker` (20s / 40s) | **No** |
| `src/routes/_app/home/components/TickerMarquee.tsx:71` | `animate-scroll-ticker` | **No** |
| `src/routes/_index/LandingPage.tsx:957` | hook ticker scroll | **No** |
| `src/routes/_app/home/HomeScreen.tsx:285` | inline `gv-pulse` 1.6s infinite on live dot | **No** |

**Fix:** Add to `app.css`:
```css
@media (prefers-reduced-motion: reduce) {
  .animate-scroll-infinite, .animate-scroll-ticker { animation: none; }
}
```
+ disable `gv-pulse` animation under PRM.

#### V-03 — Lime as surface/body fill (DS rule #5)

**Rule:** "Never use lime as a body or surface fill — it's a flag, not a colour."

| File | Line | Usage |
|------|------|-------|
| `src/routes/_app/home/HomeScreen.tsx` | 281 | Live badge pill `style={{ background: 'var(--gv-lime)' }}` |
| `src/components/v2/Chip.tsx` | 22 | Chip variant `[background:var(--gv-lime)]` |

**Fix:** Lime dot/border only (6px flag), or `--gv-accent-soft` chip; keep lime for `TickerMarquee` **text** color (`text-[color:var(--gv-lime)]`) ✓.

#### V-04 — Icon-only buttons missing `aria-label` (DS §18)

Confirmed + heuristic hits:

| File | Issue |
|------|-------|
| `src/components/AppLayout.tsx` | ~993 — profile/history modal close `<X>` button, no `aria-label` |
| `src/routes/_app/answer/AnswerScreen.tsx` | ~794 — icon-only control (verify) |
| `src/routes/_app/onboarding/OnboardingScreen.tsx` | ~131 — icon-only control (verify) |

**Fix:** `aria-label="Đóng"` / action-specific VN label on every icon-only `<button>`.

### 2.5.3 HIGH violations

#### V-05 — Accent left-border card pattern (DS rule #14, §17-C)

**Rule:** "Never use a rounded card with an accent-coloured left border."

| File | Pattern |
|------|---------|
| `src/components/v2/answer/timing/TimingBody.tsx:59` | `border-l-4 border-[color:var(--gv-accent)] rounded-lg` |
| `src/routes/_app/components/DiagnosisRow.tsx:18` | `border-l-2 border-[var(--gv-accent)]` on first fail row |
| `src/components/v2/answer/pattern/HookFindingCard.tsx:128` | `border-l-2 border-[color:var(--gv-accent)]` |
| `src/components/v2/answer/diagnostic/DiagnosticBody.tsx:91` | `border-l-2 border-[color:var(--gv-accent)]` |

**Fix:** Replace with `--gv-canvas-2` fill + `--gv-accent` **kicker dot** or header weight — not coloured edge. `DiagnosisRow` first-fail emphasis: use `--gv-accent-soft` bg tint instead.

#### V-06 — Raw view counts >10K via `toLocaleString` (DS rule #22)

**Rule:** Format as 1.2K / 4.2M — never raw millions in product UI.

`formatViews()` exists in `src/lib/formatters.ts` and is used in **19 files**, but **16+ creator-facing call sites** still use `.toLocaleString("vi-VN")` on views/play_count:

| File | Lines (sample) |
|------|----------------|
| `src/components/v2/answer/video/EvidenceVideoEmbed.tsx` | 31, 98 |
| `src/components/v2/answer/video/blocks/ChannelProofBlock.tsx` | 231, 275 (+ local duplicate formatter) |
| `src/components/v2/answer/video/blocks/FormatCardsGrid.tsx` | 111 |
| `src/components/v2/answer/ResearchStrip.tsx` | 229 |
| `src/components/v2/answer/pattern/PatternBody.tsx` | 33 |
| `src/routes/_app/answer/AnswerScreen.tsx` | 815 (corpus sample count — OK if <10K) |

**Also:** local `formatViews` / `formatViewsVi` duplicates in `VideoTileRow.tsx`, `HooksTable.tsx`, `BreakoutGrid.tsx`, `FlopDiagnosisStrip.tsx`, `ChannelProofBlock.tsx`, `CreatorCard.tsx`, `PatternSpreadStrip.tsx` — consolidate to `@/lib/formatters`.

**Exclude:** Admin panels (`EnsembleCreditsPanel`, funnel counts) — operational numbers OK with locale separators.

#### V-07 — "viral" in product surfaces (DS rule #29)

**Rule:** Marketing words ("viral", "10x", "game-changer") stay out of product UI.

| File | Copy |
|------|------|
| `src/routes/_app/trends/TrendsRail.tsx` | "Đang Viral", "Top 5 viral all-time…" |
| `src/routes/_app/trends/TrendsPatternGrid.tsx` | "Công thức từ video viral trong ngách" |
| `src/routes/_app/trends/ExploreScreen.tsx` | `VIRAL` badge label |
| `src/components/v2/ShotReferenceStrip.tsx` | "VIDEO VIRAL" kicker |
| `src/components/v2/answer/video/VideoBody.tsx` | "MỔ VIDEO VIRAL" kicker |
| `src/routes/_app/learn-more/LearnMoreScreen.tsx` | "đang viral mỗi tuần" |
| `src/routes/_auth/login/route.tsx` | "viral" in hero (auth = product surface) |

**Note:** `intent-router.ts` regex matching user input "viral" is **OK** (routing, not display). Landing page has **+9** additional "viral" strings — marketing tier; still prefer copy-rules alternatives.

**Fix copy alternatives:** "đang nổi", "view cao", "leo đỉnh", "breakout" — align with Trends rails naming.

#### V-08 — Emoji in product UI (DS rule #26)

**Rule:** No emoji in product surfaces (✓/✕ diagnosis markers are typographic — allowed).

| File | Emoji | Context |
|------|-------|---------|
| `src/routes/_app/home/components/StudioHero.tsx` | 🔥 | "Đăng trong 48h" ritual row |
| `src/components/v2/answer/pattern/PatternActionCards.tsx` | ✨ 🔎 📅 | Action card icons |
| `src/components/v2/answer/ideas/IdeasActionCards.tsx` | ✨ | Action card icons |
| `src/components/chat/TrendingSoundCard.tsx` | 🎵 💰 | Chat intent cards |
| `src/components/v2/DurationInsight.tsx` | ★ ⚠ | Duration benchmark messages |
| `src/components/v2/CitationTag.tsx` | ✻ | Citation prefix |
| `src/components/v2/answer/ResearchStrip.tsx` | ⚠ | Warning strip |
| `src/components/chat/VideoRefCard.tsx` | ★ | Breakout highlight |

**Fix:** Replace with Lucide icons (individual imports) or mono text markers (✓/✕/↑/↓). DurationInsight: use `gv-kicker` + data, not ★/⚠ emoji.

#### V-09 — Spring / bouncy easing (DS §06-D, rule #19)

| File | Pattern |
|------|---------|
| `src/routes/_app/settings/SettingsScreen.tsx:95,482` | `transition={{ type: "spring", stiffness: 500/400 }}` |
| `src/routes/_app/pricing/PricingScreen.tsx:242` | `transition={{ type: "spring", stiffness: 400 }}` |

**Fix:** Replace with `type: "tween", ease: [0.2, 0.8, 0.2, 1], duration: 0.24` per DS §06.

#### V-10 — Raw hex in Tailwind arbitrary classes

| File | Value | Verdict |
|------|-------|---------|
| `src/routes/_auth/login/route.tsx:282` | `bg-[#1877F2]` | **Acceptable exception** — Facebook brand requirement; document in plan |
| `src/components/v2/answer/ResearchStrip.tsx:201` | `bg-[#010101]` | **Violation** — use `bg-[color:var(--gv-ink)]` |
| `src/routes/_app/home/components/BreakoutGrid.tsx:30` | `bg-[#2d2640]` etc. | **Violation** — use `--gv-shot-*` or `--gv-avatar-*` tokens already in `app.css` |

### 2.5.4 MEDIUM violations

#### V-11 — Focus ring removed without replacement (DS §18, rule #25)

Custom inputs using `outline-none` + border change only (no 2px accent ring):

| File | Element |
|------|---------|
| `src/routes/_app/channel/ChannelScreen.tsx` | 233, 400, 425 — handle input |
| `src/components/v2/QueryComposer.tsx` | 86 — textarea |
| `src/components/AppLayout.tsx` | 379 — inline search |

**Contrast:** Radix/shadcn primitives use `focus-visible:ring-2 focus-visible:ring-ring` ✓.

**Fix:** Add `focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--gv-accent)]` to match DS §18 demo.

#### V-12 — Trend direction without ↑/↓ glyph (DS rule #23)

| File | Issue |
|------|-------|
| `src/components/v2/answer/pattern/HookFindingCard.tsx` | `TonePill` — colored ● dot, no arrow |
| `src/components/v2/answer/pattern/PatternBody.tsx` | `sumToneClass` color only on trend cells |

**Contrast:** `src/routes/_app/channel/components/ScoreCard.tsx` uses +/- prefix ✓.

#### V-13 — Duplicate view formatters (maintainability + DS compliance)

Eight local `formatViews` / `formatViewsVi` implementations shadow `@/lib/formatters`. Consolidation prevents regression on V-06.

#### V-14 — Legacy `--background` token (#EDEDEE)

`src/app.css:59` — `--background: oklch(0.93…)` (#EDEDEE) vs product `--gv-canvas` (#FBFCFD). Landing uses gv tokens; shadcn `bg-background` on some surfaces may drift. Low visual delta but breaks DS surface ladder.

#### V-15 — Chat surfaces using `text-gray-400`

`TrendingSoundCard.tsx`, `ShotListCard.tsx`, `MarkdownRenderer.tsx` — Tailwind gray not `--gv-ink-4`. Chat path may predate Studio pivot; migrate to `text-muted-foreground` / `text-[color:var(--gv-ink-4)]`.

### 2.5.5 Violation registry (quick reference)

| ID | DS § | Severity | Count | Primary fix | Phase |
|----|------|----------|-------|-------------|-------|
| V-01 | §06 | BLOCKING | 30+ sites | Cap `.gv-fade-up` at 320ms; sheet/StepProgress ≤300ms | 2 |
| V-02 | §06 | BLOCKING | 4 loops | PRM block for scroll + pulse | 1 |
| V-03 | §02 | BLOCKING | 2 | Lime → dot/chip only | 1 |
| V-04 | §18 | BLOCKING | 6+ | `aria-label` on icon buttons | 1 |
| V-05 | §17-C | HIGH | 4 files | Remove left-border accent cards | 2 |
| V-06 | §17-E | HIGH | 16+ | `formatViews()` everywhere views >999 | 2 |
| V-07 | §17-E | HIGH | 17+ | Replace "viral" product copy | 1 |
| V-08 | §17-E | HIGH | 22+ | Remove emoji → Lucide/mono | 2 |
| V-09 | §06 | HIGH | 3 | Drop spring → DS easing | 3 |
| V-10 | §02 | HIGH | 3 files | Tokenize arbitrary hex | 2 |
| V-11 | §18 | MEDIUM | 6 | Focus-visible accent ring | 2 |
| V-12 | §17-E | MEDIUM | 3 | Add ↑/↓ to trend pills | 2 |
| V-13 | — | MEDIUM | 8 dupes | Single `formatViews` import | 2 |
| V-14 | §02 | LOW | 1 | Alias `--background` → `--gv-canvas` | 3 |
| V-15 | §02 | LOW | 3 | Chat gray → gv ink scale | 3 |
| V-16 | §17 | HIGH | 2 routes | ≤1 magenta CTA per viewport; split empty states | 2 |
| V-17 | §09 | HIGH | 10 files | `disabled:opacity-50` on accent — use `bg-faint` | 1 |
| V-18 | §05 | HIGH | 13 files | `shadow-lg/xl` on cards — DS prefers 1px rule | 2 |
| V-19 | §05 | MEDIUM | 31 | Arbitrary `rounded-[Npx]` not in 6/12/18 scale | 3 |
| V-20 | §18 | MEDIUM | 9 files | Buttons `h-6`–`h-9` without `min-h-[44px]` | 2 |

---

## 2.6 Full-coverage component audit (2026-05-23)

**Method:** Node script over all **364** non-test source files + per-screen checklist on **20 major routes** and **10 UI primitives**. Checks DS **§05 Shape**, **§06 Motion**, **§09 Controls**, **§10 Inputs**, **§11 Surfaces**, **§17 Avoid**, **§18 A11y**.

**Not manually pixel-diffed:** every individual DOM node in production (that requires `/visual-audit` browser pass). This section is **exhaustive at the file/component level** — every major screen and primitive is scored.

### 2.6.1 Major route verdicts

| Screen | File | Verdict | Buttons | Inputs | Cards/borders | Motion | Copy | **Type** |
|--------|------|---------|---------|--------|---------------|--------|------|----------|
| Landing | `_index/LandingPage.tsx` | **FAIL** | ink CTA ✓ | NB-01 placeholder | shadow-lg ×9 (V-18) | scroll ticker no PRM (V-02) | viral (V-07) |
| Login | `_auth/login/route.tsx` | **FAIL** | 1 primary ✓ | — | shadow (V-18) | 450ms entrance | viral, emoji, `#1877F2` OK |
| Signup | `_auth/signup/route.tsx` | CONCERNS | — | — | — | — | emoji (V-08) |
| Studio Home | `home/HomeScreen.tsx` | **FAIL** | ink ✓ | composer NB-03 | — | gv-fade-up ×7, pulse (V-01/02) | 🔥 emoji, lime fill (V-03) |
| Trends grid | `trends/TrendsPatternGrid.tsx` | CONCERNS | — | — | — | — | viral heading (V-07) |
| Trends Explore | `trends/ExploreScreen.tsx` | **FAIL** | 1 accent ✓ | search no ring (V-11) | shadow (V-18) | — | viral badge, emoji, views (V-06) |
| Channel | `channel/ChannelScreen.tsx` | CONCERNS | Khám ink ✓ | handle outline-only (V-11) | `rounded-[14px]` (V-19) | StepProgress 500ms | NB-08 Sâu guard |
| Answer shell | `answer/AnswerScreen.tsx` | CONCERNS | — | QueryComposer (V-11) | — | — | corpus toLocaleString (V-06) |
| History | `history/HistoryScreen.tsx` | CONCERNS | **2 primary** empty states (V-16) | filter ribbon | — | — | emoji |
| Settings | `settings/SettingsScreen.tsx` | **FAIL** | **2 accent** (V-16) | 6 fields | shadow | spring + 900ms bar (V-09/01) | viral, emoji |
| Pricing | `pricing/PricingScreen.tsx` | **FAIL** | — | — | shadow | spring (V-09) | emoji |
| Checkout | `checkout/CheckoutScreen.tsx` | CONCERNS | — | — | — | — | emoji; small touch (V-20) |
| Payment success | `payment-success/…` | CONCERNS | — | — | — | — | emoji |
| Onboarding | `onboarding/…` | CONCERNS | ink ✓ | — | — | — | emoji |
| Learn more | `learn-more/…` | CONCERNS | — | — | — | — | viral, emoji |
| Compare | `compare/CompareScreen.tsx` | CONCERNS | ink ✓ | — | — | — | emoji |
| Douyin | `douyin/DouyinScreen.tsx` | CONCERNS | — | toolbar no ring | — | — | emoji |
| Admin | `admin/AdminScreen.tsx` | CONCERNS | — | — | — | gv-fade-up ×14 (V-01) | emoji (ops OK to defer) |
| Chat read | `history/ChatSessionReadScreen.tsx` | CONCERNS | — | — | — | — | ✓/✕ transcript |

**Summary:** 0/20 routes fully PASS. **7 FAIL**, **13 CONCERNS**.

> **DS §03 re-audit (2026-05-23):** Baseline @ [`uiux-ds-audit-2026-05-23.json`](../qa-reports/uiux-ds-audit-2026-05-23.json) via `node scripts/uiux-compliance-scan.mjs`. **Type** column = T-01–T-12 typography hits (arbitrary px, kicker drift, metric tabular-nums, serif misuse). Top offenders: `LandingPage.tsx`, `ExploreScreen.tsx`, `VideoBody.tsx`, admin panels.

### 2.6.2 Answer report bodies (embedded UI — not separate routes)

Heavy diagnosis UI lives in `components/v2/answer/*`. Audited all **9** files with `.gv-fade-up`:

| Body component | `.gv-fade-up` count | Other issues |
|----------------|---------------------|--------------|
| `pattern/PatternBody.tsx` | **10** | left-border in HookFindingCard (V-05); TonePill no arrow (V-12) |
| `ideas/IdeasBody.tsx` | 4 | IdeasActionCards emoji (V-08) |
| `diagnostic/DiagnosticBody.tsx` | 3 | left-border quote (V-05) |
| `lifecycle/LifecycleBody.tsx` | 3 | toLocaleString creators (V-06) |
| `timing/TimingBody.tsx` | 1 | left-border callout (V-05) |
| `generic/GenericBody.tsx` | 1 | — |
| `ReportNarrativeHeadline.tsx` | 1 | — |
| `video/VideoBody.tsx` | 0 | "VIDEO VIRAL" kicker (V-07); emoji; local formatters (V-06) |
| `script/ScriptBody.tsx` | 0 | arbitrary radius (V-19) |

**Total:** 44 staggered entrance animations — all inherit **450ms** from `.gv-fade-up` (V-01).

### 2.6.3 UI primitive library

| Primitive | Verdict | DS gaps |
|-----------|---------|---------|
| `v2/Btn.tsx` | **Fix in Phase 1** | `disabled:opacity-50` on all variants (V-17); accent hover ✓; focus ring ✓; sm has `min-h-[44px]` ✓ |
| `ui/Button.tsx` | **Fix in Phase 1** | `variant=primary` = magenta; `disabled:opacity-50` (V-17); `rounded-lg` not DS pill (§09 uses full pill for actions) |
| `ui/shadcn-button.tsx` | Review | Radix legacy — used in chat/admin paths |
| `ui/Input.tsx` | CONCERNS | `outline-none` + ring pattern — verify 2px accent offset (V-11) |
| `ui/textarea.tsx` | CONCERNS | Same as Input |
| `v2/QueryComposer.tsx` | **Fix Phase 2** | textarea `outline-none` no ring (V-11); send uses accent ✓ |
| `v2/Chip.tsx` | **Fix Phase 1** | lime variant full fill (V-03) |
| `ui/sheet.tsx` | **FAIL** | `duration-500` open (V-01); float shadow (V-18) |
| `ui/dialog.tsx` | CONCERNS | elevation-3 shadow — acceptable for modal per DS §05 |
| `ui/alert-dialog.tsx` | CONCERNS | shadow + destructive actions — verify ink vs accent |

### 2.6.4 Buttons — full inventory findings

| Check | Result |
|-------|--------|
| Total files with `<button` / `<Btn` / `<Button` | **~70** |
| Magenta `variant=accent` or `primary` per route ≥2 | **2 files** — `HistoryScreen` (mutually exclusive empty states), `SettingsScreen` (V-16 — verify viewport) |
| Systemic disabled state | **10 files** use `disabled:opacity-50` on primary/accent including **`Btn.tsx` + `Button.tsx`** (V-17) |
| Touch target `<44px` heuristic | **9 files** — `VideoThumb`, `ResearchStrip`, `VideoBody`, checkout, pricing, settings, Douyin modal, TrendsDouyinCard, landing |
| Vague verb labels | **0** (Submit/Go/Start) |
| Ink vs accent discipline | **Mostly compliant** — Channel Khám, Home send, depth pickers use ink/ghost correctly |

### 2.6.5 Inputs — full inventory findings

| Check | Result |
|-------|--------|
| Files with input/textarea/select | **~18** |
| `outline-none` without `focus-visible:ring` | **5** — `AppLayout`, `QueryComposer`, `ChannelScreen`, `DouyinToolbar`, `LandingPage` (V-11) |
| Font ≥16px on inputs | **Global** via `app.css` `max(16px, 1rem)` ✓ |
| `aria-invalid` + `aria-describedby` on errors | **Not audited** — manual pass needed on login/checkout/settings |
| OTP input `duration-1000` | `ui/input-otp.tsx` — caret blink loop (V-01 edge case) |

### 2.6.6 Cards, surfaces, borders

| Check | Result |
|-------|--------|
| Accent left-border cards | **4** — unchanged (V-05) |
| Triple-nested `<Card>` | **0** ✓ |
| `shadow-lg` / `shadow-xl` | **13 files** — worst: Landing ×9, AppLayout ×3, Explore ×2 (V-18) |
| Arbitrary radius not in 6/12/18 | **31** — channel panels use **`rounded-[14px]`** (8 files); admin/v2 chips use 2–10px (V-19) |
| Neo-brutalist `gv-surface-brutal` | Compliant — 2px ink border per DS ✓ |
| Nested card depth | **0** violations ✓ |

### 2.6.7 Animations — full inventory

| Check | Result |
|-------|--------|
| `.gv-fade-up` | **44 usages** in 9 files @ **450ms** (V-01) — PRM disabled ✓ |
| Scroll/marquee loops | **3** without PRM (V-02) |
| Spring (`framer-motion`) | **2 files** — Settings, Pricing (V-09) |
| `duration-500+` in UI | sheet, StepProgress, Settings 900ms bar, input-otp |
| `prefers-reduced-motion` in `app.css` | **Only** `.gv-fade-up` — loops/pulse missing (V-02) |
| Accordion 200ms | Compliant ✓ |
| Named DS loops (1.6s pulse, 40s marquee) | Present — need PRM off switch |

### 2.6.8 Copy sweep (product surfaces)

| Check | Files hit |
|-------|-----------|
| Emoji (excl. allowed ✓/✕ diagnosis) | **~20 product files** — action cards, chat, StudioHero, DurationInsight |
| "viral" display copy | **16 files** — Trends rails, VideoBody, login, landing, settings |
| Exclamation in strings | **0** product hits ✓ |
| Forbidden marketing words (10x, game-changer) | **0** ✓ |

### 2.6.9 Coverage gaps (still manual)

These require browser `/visual-audit` or QA walk — not fully automatable:

- Hover/focus states on every control in situ  
- **≤1 magenta button per viewport** (not just per file) — needs runtime check  
- Modal vs drawer vs inline notice appropriateness (DS §17-C)  
- D1–D4 dopamine timing with live SSE  
- Loading / error / empty states on all 20 routes  
- Share card rendering  

---

## 3. Visual audit carryover

| ID | Priority | Owner | Effort | Acceptance criteria |
|----|----------|-------|--------|---------------------|
| **B-01** | P0 BLOCKING | Design + Tech Lead | 30 min | EDS §5 updated to magenta/sky; audit report annotated CLOSED; no purple in active docs |
| **B-02** | P0 BLOCKING | Backend + FE | 1–2 hr | `SELECT COUNT(*)` from `video_corpus`; landing copy uses real count or dynamic `/api/landing-stats` field; humility tier if thin |
| **NB-01** | P3 | FE | 15 min | Landing input placeholder matches product intent (URL vs VN prompt) — product sign-off |
| **NB-02** | — | — | — | **CLEARED** — copy passes quality test |
| **NB-03** | P2 | FE | 30 min | Disabled Gửi: `bg-faint text-muted cursor-not-allowed` per DS §09 disabled control |
| **NB-04** | P2 | FE | 10 min | `<link rel="canonical" href="https://www.getviews.vn/">` in `_index/route.tsx` meta |
| **NB-05** | P2 | FE | 20 min | Social proof block: single `aria-label` with full "TRƯỚC 2.000 view … SAU 45.000 view" |
| **NB-06** | P2 | FE | 30 min | Trends niche active chip: `bg-accent-soft text-accent` not `#0A0D12` fill |
| **NB-07** | — | — | — | **CLEARED** |
| **NB-08** | P1 | FE | 45 min | Channel Sâu pill disabled + tooltip when credits < 3; matches billing UX |
| **D1–D4** | P1 | QA + FE | 1 hr | One credited analysis run; verify 600–800ms emphasis, bar fill, brief animation, "Miễn phí ✓" pill |

---

## 4. Screen-by-screen backlog

**Authoritative verdicts:** §2.6.1 (full coverage). Visual audit (May 23) = production spot-check only.

Legend: **FAIL** / **CONCERNS** / PASS · route file path relative to `src/`

| Screen | Route | §2.6 verdict | Top fixes |
|--------|-------|--------------|-----------|
| Landing | `/` | **FAIL** | V-02, V-07, V-18, B-02, NB-04/05 |
| Login | `/login` | **FAIL** | V-07, V-08, V-10 (FB excepted), V-18 |
| Signup | `/signup` | CONCERNS | V-08 |
| Studio Home | `/app` | **FAIL** | V-01, V-02, V-03, NB-03 |
| Trends | `/app/trends` | CONCERNS | V-07, NB-06 |
| Explore corpus | `/app/trends` (explore tab) | **FAIL** | V-06, V-07, V-08, V-11, V-18 |
| Channel | `/app/channel` | CONCERNS | V-11, V-19, NB-08 |
| Answer | `/app/answer` | CONCERNS | V-06, V-11 + all answer bodies §2.6.2 |
| History | `/app/history` | CONCERNS | V-16, V-08 |
| Settings | `/app/settings` | **FAIL** | V-09, V-16, V-17, V-07 |
| Pricing | `/app/pricing` | **FAIL** | V-09, V-18, V-08 |
| Checkout | `/app/checkout` | CONCERNS | V-08, V-20 |
| Payment success | `/app/payment-success` | CONCERNS | V-08 |
| Onboarding | `/app/onboarding` | CONCERNS | V-08 |
| Learn more | `/app/learn-more` | CONCERNS | V-07, V-08 |
| Compare | `/app/compare` | CONCERNS | V-08 |
| Douyin | `/app/douyin` | CONCERNS | V-08, V-11 |
| Admin | `/app/admin` | CONCERNS | V-01 (ops — defer polish) |
| OAuth callback | `/auth/callback` | **Not scored** | Verify `RouteScreenFallback` |
| Video diagnosis | `/app/video/:id` | **Via VideoBody** | V-07, V-06, V-19 |

### Cross-cutting (all `/app/*`)

- Shell: sidebar lg + bottom tab mobile — verify DS §08 nav active = ink or accent-soft (not mixed)
- `.gv-studio-type` 14px body — DS allows 14px studio / 16px inputs ✓
- **V-10:** 3 files still use raw hex arbitrary classes — see §2.5.3
- **V-01/V-02:** Motion compliance — `.gv-fade-up` 450ms + scroll loops without PRM (§2.5.2)
- **V-06/V-13:** Consolidate view formatting to `@/lib/formatters` (§2.5.3)
- AI Slop Guard — maintain zero gradient backgrounds / 3-col icon grids ✓

---

## 5. Dopamine moments (D1–D4)

Per EDS §6 + visual audit gap. **Requires one credited live analysis** before `/pre-handoff`.

| ID | Moment | Timing | Verify on | Pass criteria |
|----|--------|--------|-----------|---------------|
| **D1** | First diagnosis row reveal | 600–800ms emphasis | Answer/video result | Stagger visible; no >800ms |
| **D2** | Hook ranking bar fill | 400ms cubic-bezier | Diagnosis hook section | Bars animate from 0; tabular nums |
| **D3** | Brief completion | 400–600ms | Brief intent result | No upsell interrupt (EDS rule 6) |
| **D4** | Free query "Miễn phí ✓" pill | Instant | Studio first free query | Pill visible; credit not deducted |

**QA artifact:** extend `visual-audit-launch-2026-05-23.md` § Dopamine with screenshots + timestamps after run.

---

## 6. Mobile & accessibility

| Item | Spec source | Current | Fix |
|------|-------------|---------|-----|
| Viewport baseline | DS §07, project.mdc | 375px audited ✓ | Maintain on every new screen |
| Touch targets | ≥44×44px | ✓ on audited routes | History/settings checkout pass |
| Input font | ≥16px | ✓ `max(16px, 1rem)` in app.css | — |
| Contrast | DS §02 AAA ladder | Spot-check magenta on white (CTA) | Document 4.5:1 min on `--accent` buttons |
| Canonical URL | SEO | Missing NB-04 | Phase 1 |
| Social proof a11y | NB-05 | Split DOM | Phase 1 |
| Focus rings | DS §09 | `--ring: var(--gv-accent)` | Verify visible on keyboard nav |
| Reduced motion | DS §06 | Partial — `.gv-fade-up` only | V-02: PRM for scroll loops + gv-pulse |

---

## 7. Copy & corpus integrity (B-02)

**Problem:** Landing claims "1.500+ video" in 3 places; system-design references 46k+ corpus; in-app niche shows "278+ video" for Skincare.

**Resolution path:**

1. Run production query:
   ```sql
   SELECT COUNT(*)::int AS total,
          COUNT(*) FILTER (WHERE content_class_id IS NOT NULL)::int AS indexed
   FROM video_corpus;
   ```
2. **If indexed ≥ 5,000:** Update landing to formatted real count (e.g. "12.000+ video đã phân tích") — dot separators per copy-rules.
3. **If ~1,500:** Keep copy; add footnote "số liệu cập nhật hàng tuần" + wire dynamic count via extended `/api/landing-stats`.
4. Apply **claim tier** from `claim_tiers.py` — never fabricate; thin corpus → humility copy only.

**Files:** `src/routes/_index/LandingPage.tsx`, `api/landing-stats.ts`, FAQ item in `faqs[]`.

---

## 8. Phased rollout

### Phase 0 — Decisions & doc sync (1 day, blocks pre-handoff)

| Task | Deps | Owner |
|------|------|-------|
| Patch EDS §5 colors → magenta/sky/ink/canvas table | Branding §04 | Design |
| Resolve **H-04** EDS D1 600–800ms vs DS 400ms cap | Design + Tech Lead | Design |
| Close B-01 in audit report | EDS patch | Tech Lead |
| Run corpus COUNT + close B-02 | SQL access | Backend |
| Human sign-off H-01 (TikTok Sans) | — | Tech Lead |

**QA gate:** EDS + landing copy PR reviewed; B-01/B-02 marked closed in audit.

### Phase 1 — Primitives + global (1–2 days)

| Task | IDs |
|------|-----|
| PRM guards for scroll-infinite/ticker + gv-pulse | V-02 |
| Fix `Btn.tsx` + `Button.tsx` disabled state (not opacity on accent) | V-17 |
| Lime chip variant → flag-only | V-03 |
| Icon-only button `aria-label` sweep | V-04 |
| Replace product "viral" copy on Trends/auth | V-07 |
| Dynamic or verified corpus stat | B-02 |
| Canonical link, social proof aria | NB-04, NB-05 |

**QA gate:** `prefers-reduced-motion: reduce` manual test on Home + Landing tickers.

### Phase 2 — Screens + answer bodies (3–5 days)

| Task | IDs |
|------|-----|
| Cap `.gv-fade-up` 450ms → 320ms (**44** usages, 9 files) | V-01 |
| sheet + StepProgress duration ≤300ms | V-01 |
| Remove accent left-border cards (4 files) | V-05 |
| `formatViews()` consolidation | V-06, V-13 |
| Tokenize ResearchStrip/BreakoutGrid hex | V-10 |
| Input focus rings (5 files + QueryComposer) | V-11 |
| Trend TonePill ↑/↓ glyphs | V-12 |
| Landing shadow-lg → elev-1 | V-18 |
| History/Settings dual-primary review | V-16 |
| Channel Sâu credit guard | NB-08 |
| Trends active chip tint | NB-06 |
| Composer disabled state | NB-03 |
| D1–D4 verification (post H-04) | §5 |

**QA gate:** `qa-agent` on channel + trends + one full diagnosis path; grep audit for V-05/V-06 zero hits.

### Phase 3 — Polish + radius + remaining routes (5–7 days)

| Task | Scope |
|------|-------|
| Emoji → Lucide/mono (20 files) | V-08 |
| Spring → DS easing (Settings, Pricing) | V-09 |
| `rounded-[14px]` channel panels → `rounded-[12px]` or token | V-19 |
| Touch target pass (9 files) | V-20 |
| Chat gray → gv ink | V-15 |
| `--background` → `--gv-canvas` | V-14 |
| Browser `/visual-audit` all 20 routes @ 375px | §2.6.9 gaps |
| Re-run automated scan — target 0 FAIL routes | §11 script |

**QA gate:** Full `/visual-audit` all routes; re-run §2.5 compliance grep — target 0 BLOCKING/HIGH.

---

## 9. Out of scope

- English UI strings  
- Dark mode v1 (documented in DS, deferred per EDS)  
- Revert to TikTok Purple `#7C3AED` unless explicit brand rollback  
- Figma MCP / new Make export — use tracked HTML + uiux-reference  
- Native app / Expo  
- Reels/Shorts surfaces  

---

## 10. Top 5 prioritized tasks

1. **V-02 PRM guards** — scroll tickers + live pulse (a11y BLOCKING, ~1 hr CSS)
2. **H-04 + V-01 motion cap** — reconcile EDS D1 vs DS 400ms; fix `.gv-fade-up` 450ms → 320ms
3. **V-07 "viral" copy purge** — Trends rails + auth hero (DS rule #29, copy-rules)
4. **V-06 view formatting** — replace 16+ `toLocaleString` on play_count/views with `formatViews()`
5. **B-02 corpus count** — verify DB + landing dynamic stat (trust BLOCKING)

**Next batch:** V-05 left-border cards · V-04 aria-labels · NB-08 Sâu credit guard · V-03 lime fill

---

## 11. Tracking

| Milestone | Target | Status |
|-----------|--------|--------|
| Phase 0 complete (docs + H-04) | Before `/pre-handoff` | ✅ 2026-05-23 |
| Phase 0.5 DS audit + scan script | Before Phase 1 | ✅ 2026-05-23 |
| BLOCKING violations = 0 | After Phase 1–2 | ✅ V-01–V-04 cleared in code |
| HIGH violations = 0 | After Phase 2–3 | ◐ T-01 arbitrary px remain on admin/legacy paths |
| Route FAIL = 0 | After Phase 3 + visual audit | ◐ Landing typography partial; browser audit pending |
| Launch re-audit PASS | After Phase 2 | ✅ `uiux-phase2-baseline.json` |
| Full app visual PASS | After Phase 3 | ◐ `/visual-audit` human pass pending |

### Compliance re-check command (for QA)

After each phase, re-run from repo root:

```bash
# Left-border slop
rg 'border-l-[24].*accent' src --glob '*.tsx'

# Raw view formatting (manual review hits)
rg '\.toLocaleString\(' src --glob '*.tsx' | rg -i 'view|play_count'

# Product emoji (exclude tests)
rg '[🔥✨🎵💰★⚠✻]' src/routes src/components --glob '*.tsx'

# Viral in product UI
rg -i 'viral' src/routes/_app src/components --glob '*.tsx'

# Motion >400ms in CSS
rg '0\.[4-9][0-9]s|duration-500|duration-\[0\.[5-9]' src/app.css src --glob '*.{css,tsx}'

# Full re-scan (same script as §2.6 audit)
node scripts/uiux-compliance-scan.mjs   # TODO: commit script from audit
```

**Related:** [`visual-audit-launch-2026-05-23.md`](../qa-reports/visual-audit-launch-2026-05-23.md) · [`incremental-v1-roadmap.md`](incremental-v1-roadmap.md) §13 GTM gates
