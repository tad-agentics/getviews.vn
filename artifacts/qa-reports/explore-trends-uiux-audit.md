# Explore / Trends screen — UIUX reference audit

**Reference:** `artifacts/uiux-reference/screens/trends.jsx` (`TrendsScreen`)  
**Implementation:** `src/routes/_app/trends/ExploreScreen.tsx` (+ `TrendingSection.tsx`, `TrendingSoundsSection.tsx`, `VideoDangHocSidebar.tsx`, shared explore components)  
**Shell:** Reference is a bare screen; production wraps **`AppLayout`** (`active="trends"`) — expected integration delta.

---

## 1. Information architecture

| Reference (`trends.jsx`) | Production (`ExploreScreen.tsx`) | Verdict |
|--------------------------|----------------------------------|---------|
| Single **two-column** layout: main + **320px** rail | Main scroll column + **`lg:`** aside **`w-[290px]`** | **Partial** — rail present but width −30px; rail hidden &lt; `lg` (~1024px) vs reference **1100px** collapse |
| **Hero** “newsroom” card: week kicker, big stat, 4× `HeroStat`, editorial paragraph | **No** equivalent hero; replaced by **`TrendingSection`** + **`TrendingSoundsSection`** (data cards / horizontal strips) | **Gap** — different narrative hierarchy |
| Main: toolbar → **grid OR list** (`view` state) | **Grid only**; infinite scroll + skeleton; no list mode | **Gap** |
| Rail: three **`RailSection`** blocks (Video / Sounds / Format) with **curated copy** | Rail: **“Video nên xem”** + breakout / viral **rows** from `video_corpus`; **Sounds** live in **main** column; **Format** analytics in **main** below fold | **Partial** — content type overlap; **Sounds + Format** not in rail as in reference |

---

## 2. Layout & spacing (pixel intent from reference)

| Element | Reference | Production | Verdict |
|---------|-----------|------------|---------|
| Page background | `var(--canvas)` | Inherited via `AppLayout` / tokens (`--surface` columns) | **OK** (shell) |
| Main padding | `24px 28px 60px` | `px-7` (28px) + section `pt-14 md:pt-6` / `pb-4` — not a single 60px bottom on whole column | **Drift** |
| Main / rail divider | `borderRight: 1px solid var(--rule)` on main | Main: no right border; aside `border-l border-[var(--border)]` | **OK** (equivalent) |
| Grid | `repeat(auto-fill, minmax(190px, 1fr))` **gap 14** | `grid-cols-2 sm:3 lg:4` **`gap-2.5`** (10px) | **Drift** — denser tiles, different min width logic |
| Tile aspect | **9 / 16** | **9 / 14** (`VideoCard`) | **Drift** — taller reference tiles |
| Search | Fixed **260px** pill | `flex-1 min-w-[200px]` grows | **Drift** — behaviour differs |
| Toolbar title | `fontSize: 26` “Khám phá” + mono count | `font-extrabold` title from `exploreTitle` (count in string) | **Close** — typographic scale not matched to 26px spec |

Reference responsive hook:

```117:122:artifacts/uiux-reference/screens/trends.jsx
      <style>{`
        @media (max-width: 1100px) {
          .trends-layout { grid-template-columns: 1fr !important; }
          .trends-rail { border-top: 1px solid var(--rule); }
          .trends-hero { grid-template-columns: 1fr !important; gap: 18px !important; }
        }
```

Production stacks rail at **`lg`**, not **1100px** — **breakpoint mismatch** vs reference.

---

## 3. Components & patterns

| Reference pattern | Production | Verdict |
|-------------------|------------|---------|
| **`HeroStat`** mono label 9px, value 28px, delta `var(--pos-deep)` | No hero stats row; niche stats appear in **`useNicheIntelligence`** / low-corpus copy only | **Missing** |
| **`Pill`** filters + **grid/list** segmented control | **`FilterChip`** + URL state; **no** view toggle | **Partial** / **missing list** |
| **`VideoTile`** BREAKOUT / VIRAL badges (`var(--accent)` / `var(--accent-2)`), duration badge, bottom gradient, “Phân tích →” row | **`VideoCard`** metadata chips, breakout as **mono emerald** text, CTA **“Phân tích video này”**, **modal-first** not `setRoute('video')` | **Functional superset** — visual language differs |
| **`VideoList`** table row | Not implemented | **Missing** |
| **`RailSection`**: kicker `mono uc` 9px, title 22px + **ink** bottom border, dashed dividers, optional accent dot | Sidebar uses **`SidebarVideoRow`** + orange dot headers; **no** dashed rail item separators / `RailSection` typography mirror | **Drift** |

---

## 4. Design system & token hygiene

Per `.cursor/rules/design-system.mdc` (no raw hex in components; slop guard).

| Location | Issue |
|----------|--------|
| `ExploreScreen.tsx` — `TikTokIcon` / `IGIcon` / `YTIcon` | **Brand SVG fills** (`#69C9D0`, `#EE1D52`, `#FF0000`, Instagram gradient) — **intentional** for platform marks; document as exception or swap to tokenized marks if EDS requires |
| `ExploreScreen.tsx` — hook bar `rgba(100, 100, 120, …)` | **Raw RGBA** for bar fallback — prefer **`--gv-*`** scale |
| `ExploreScreen.tsx` — format rows `style={{ color: "var(--success, #22c55e)" }}` / `danger` | **Hex fallbacks** in inline style — prefer **semantic tokens only** |
| `TrendingSection.tsx` — `signalBarColor` | **`#F59E0B`**, **`#EF4444`** hardcoded — **token violation** |
| `TrendingSoundsSection.tsx` — `BreakoutSoundBanner` | **`💰`** in commerce label — conflicts with **“No emoji as visual design elements”** in design-system rules |

---

## 5. Accessibility & behaviour (vs reference)

| Topic | Reference | Production | Verdict |
|-------|-----------|------------|---------|
| Tile click | `<button>` | **`role="button"`** `div` + keyboard handlers | **Better a11y pattern** possible but valid if roving tabindex managed — currently OK |
| Search | Uncontrolled placeholder | **Controlled** + URL `q` | **Improvement** for shareability |
| Focus | Reference minimal | **focus-visible** rings on cards / chips | **Improvement** |

---

## 6. Summary scorecard

| Area | Match | Notes |
|------|-------|-------|
| Two-column discovery + rail | **~70%** | Width, breakpoint, rail content split differ |
| Hero + week editorial | **0%** | Not built; trending cards substitute part of intent |
| Toolbar (search, niche, sort, views) | **~75%** | Extra sort/format depth; no list toggle |
| Video grid tile visual | **~55%** | Aspect ratio, gap, badges, CTA copy differ |
| Sounds / Format “rail” | **~40%** | Moved to main / below fold |
| Tokens / slop guard | **Needs pass** | Hex oranges/reds, emoji commerce, rgba bars |

---

## 7. Recommended follow-ups (priority)

1. **Decide product scope:** Either add a **compact hero** (week summary + 4 stats) wired to `niche_intelligence` / corpus counts, or formally **deprecate** that block in `trends.jsx` and update the UIUX pack so reference matches shipped IA.
2. **Align breakpoints:** `lg:` rail vs **1100px** media query — pick one spec (update reference or Tailwind `min-[1100px]:`).
3. **List view:** Implement **`VideoList`**-equivalent or remove from reference to avoid false expectation.
4. **Token pass:** Replace `signalBarColor` hexes, format row inline hex fallbacks, hook bar rgba with **`--gv-*` / semantic** classes only; remove **emoji** from commerce chip or replace with text/icon.
5. **Grid geometry:** Reconcile **gap 14** + **minmax(190px,1fr)** vs current responsive 2/3/4 columns for closer Make fidelity.

---

**Sign-off:** Audit only — no code changes in this commit path.
