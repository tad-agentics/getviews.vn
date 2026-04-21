# Phase C.9 — Trends / Explore restyle

> Scope: bring `/app/trends` (`src/routes/_app/trends/ExploreScreen.tsx` + `TrendingSection.tsx` + `TrendingSoundsSection.tsx` + `VideoDangHocSidebar.tsx`) to design + functional parity with `artifacts/uiux-reference/screens/trends.jsx`, while fixing two latent backend bugs that today silently kill the page’s analytics zone.
> **Umbrella:** new milestone **C.9** under `artifacts/plans/phase-c-plan.md`. Inherits Phase C token gate, design-audit closure rule (same as B.1.6 / B.2.x / B.3.x / B.4.6 / C.x), commit convention, Vietnamese kickers.
> **T.0 decisions locked** (see §3 — only data-source confirmations remain): hero editorial source, `format_lifecycle` source, brand SVG handling.

---

## 0. Why this needs a plan, not a PR

The audit (`artifacts/qa-reports/explore-trends-uiux-audit.md`) catalogues drift correctly but treats two deltas as cosmetic when they are not:

- `nicheIntel.video_count_7d` is referenced in `ExploreScreen.tsx:542` but the column no longer exists on the materialized view (`supabase/migrations/20260411000020_add_corpus_classification_columns.sql` + `20260411000028_distribution_annotations.sql` rebuilt `niche_intelligence` without it). `lowVideoCorpus` is therefore **always `true` for every niche** → the **Hook đang chạy** ranking and **Format đang lên / đang giảm** sections render **never**, regardless of corpus volume.
- `format_lifecycle` has **no Cloud Run writer** (`artifacts/docs/supabase-pipeline-table-audit.md` §Gaps&Risks #1). Even after fix #1, `risingFormats` / `fallingFormats` will be empty arrays.

Any restyle that ignores these will paint over a non-functional half of the screen. The plan therefore couples **UI parity** with **data plumbing** in the same gate.

Aliases used below:
- **Reference**: `artifacts/uiux-reference/screens/trends.jsx` (`TrendsScreen`).
- **Production**: `src/routes/_app/trends/ExploreScreen.tsx`.
- **Token gate**: zero raw hex / zero `var(--purple)` / `var(--ink-soft)` / `var(--border-active)` / `var(--gv-purple*)` / zero emoji-as-icon in components, per `.cursor/rules/design-system.mdc`.

---

## 1. Guiding principles

1. **Reference is a hypothesis, not law.** Where Production has a documented improvement (URL-state filters, focus-visible, infinite scroll, `VideoPlayerModal` deep dive, `TrendingSection` carousel) keep it and update the reference doc instead. Where Reference is the truer target (hero, two-column rail content split, list view, breakpoint, grid geometry, tile aspect) bring code to it.
2. **No silent zones.** Every analytics block on the screen must either render with data or render an explicit humility / empty / loading state. Today three sections collapse silently because of bug §0.
3. **Data contract first.** UI is a pure function of the payload. If a section needs a metric (e.g. `video_count_7d`, `video_count_total`, `top_breakout_count`, `editorial_summary`), the metric ships first as a typed RPC / MV column / table row, then the UI binds.
4. **Token gate is part of the milestone.** No milestone closes with raw hex or emoji-as-icon committed; brand SVG hex (`#69C9D0`, `#EE1D52`, `#FF0000`, IG gradient) is the **only** documented exception and gets an inline allowlist comment.
5. **Mobile parity.** `AppLayout` shell + 1100 px breakpoint stays — rail collapses below the main column at 1100 px (not 1024 px). Touch targets ≥ 44 px.
6. **Commit convention.** Per `AGENTS.md`: `feat(trends): backend complete`, `feat(trends): screens complete`, `test(trends): qa pass`. Bugfixes that ship before the gate are `fix(trends): …`.

---

## 2. Recommended order

T.0 (spike) → T.1 (data backfill) → T.2 (token & slop pass) → T.3 (hero + toolbar) → T.4 (grid + list view) → T.5 (rail content reshape) → T.6 (analytics zone unblock + render) → T.7 (design audit close-out + measurement wiring).

Hard ordering: **T.1 must land before T.6.** T.2 can run in parallel with T.3–T.5 if a separate engineer is available.

---

## 3. T.0 — Spike (1 week)

**Goal.** Resolve every product/data ambiguity before any pixel moves. Output is a written decision record under `artifacts/decisions/trends-restyle/`.

**T.0.1 — Hero block (locked: ADOPT).**
Four `HeroStat` metrics + week label + editorial paragraph. Window frozen at **7 days** so every value matches the rest of the screen.

| Slot | Source |
|------|--------|
| Big stat ("**N** video được giải mã") | `niche_intelligence.video_count_7d` (restored in T.1) |
| `VIEW TỔNG` | `niche_intelligence.total_views_7d` (new in T.1) |
| `TĂNG TUẦN TRƯỚC` | `(total_views_7d − total_views_prev_7d) / total_views_prev_7d` |
| `ĐỘT PHÁ` | `niche_intelligence.breakout_count_7d` (`breakout_multiplier >= 1.5 AND indexed_at > now() - 7d`); delta line vs `breakout_count_prev_7d` |
| `HOOK MỚI` | `niche_intelligence.new_hook_count_7d` — `hook_type` values present in 7d window AND absent in prior 28d |
| Week kicker (`'TUẦN N · DD—DD THÁNG M'`) | `niche_intelligence.editorial_week_label` (server-formatted ISO week) |
| Editorial paragraph | `niche_intelligence.editorial_summary TEXT` (nullable; LLM-generated nightly — see T.1) |

If `editorial_summary IS NULL` the third hero column collapses; the layout still holds because columns 1+2 are independently grid-placed. Cross-niche fallback (no niche selected) renders an aggregated hero from a new `get_global_weekly_stats()` RPC; if that RPC isn't ready by T.3, hero hides and the toolbar pulls up — wire the empty state in T.3 either way.

**T.0.2 — List view decision.**
- Reference §`VideoList` (`trends.jsx` 226–250) is a 6-column table row (thumb · title+meta · views · hook · duration · CTA). Decide adopt vs drop. If adopt: define column widths, sort behaviour for each column, and whether `?view=list` lives in the URL (yes — keep parity with existing URL-state filters).
- Decision record: `artifacts/decisions/trends-restyle/list-view.md`.

**T.0.3 — Rail content split.**
- Reference rail = three `RailSection` blocks (Video / Sounds / Format). Production today: rail = breakout + viral video rows; sounds + format live in main column.
- Decide: move sounds and format into rail (matches Reference + frees vertical space in main), keep main as dense video grid; OR keep current main-column placement and update Reference. Bias: move into rail — fewer competing narratives in main column.
- Decision record: `artifacts/decisions/trends-restyle/rail-split.md`.

**T.0.4 — Tile geometry & breakpoint.**
- Pick: `aspect-ratio 9/16` (Reference) vs `9/14` (Prod), `gap 14px` (Reference) vs `gap 10px` (Prod), `repeat(auto-fill, minmax(190px, 1fr))` (Reference) vs `2/3/4 col Tailwind grid` (Prod).
- Pick: rail collapse breakpoint **1100 px** (Reference) vs **`lg` 1024 px** (Prod).
- Bias: take Reference for both (geometry + 1100 px) — geometry is design language and should be consistent across `/video`, `/kol`, `/script`, `/answer` thumbnails. Confirm against `phase-c-plan.md` C.0(iv) width decision.
- Decision record: `artifacts/decisions/trends-restyle/geometry.md`.

**T.0.5 — Brand SVG (locked: REMOVE per Reference parity).**
Reference uses **monochrome generic icons only** — no platform marks anywhere on the screen. The SVGs in `ExploreScreen.tsx:99-145` (`TikTokIcon`, `IGIcon`, `YTIcon`) are dead code today: `IGIcon` and `YTIcon` are never rendered, `TikTokIcon` only renders inside `FilterChip` when `label === "App"` and no chip uses that label.
- Delete `IGIcon`, `YTIcon`, `TikTokIcon`, and the `label === "App"` branch in `FilterChip` (lines 336–340).
- No allowlist clause needed in `.cursor/rules/design-system.mdc`.
- If a future "platform" filter chip lands, use a monochrome `lucide-react` icon (`Music2` for TikTok, `Instagram`, `Youtube`) coloured with `var(--ink)`.

**T.0.6 — `format_lifecycle` source (locked: DERIVE from `niche_intelligence`).**
Path B picked. `format_lifecycle` table stays in schema (existing reads keep working) but **no Cloud Run writer is built**.

- T.1 adds `niche_intelligence.format_distribution_prev_7d JSONB` (snapshot of the 7-day-prior `format_distribution`).
- A new `useFormatTrend(nicheId)` hook computes rising/falling client-side as the `(current.cnt − prev.cnt) / prev.cnt` ratio per `content_format` key, sorts, slices top 5 rising / top 3 falling.
- `useFormatLifecycle.ts` is retired from `ExploreScreen.tsx`; consumers elsewhere (if any — confirm via grep) keep working off the legacy table until separately migrated.
- Cadence is week-over-week, matches every other metric on the page.

**Spike exit gate:** the two locked decisions above are confirmed in writing (this plan ✅); only T.0.2 (list view shape), T.0.3 (rail split), T.0.4 (geometry/breakpoint) remain to lock. Goal: ≤ 3 days of spike work, not a full week.

---

## 4. T.1 — Backend data plumbing (1 week)

**Goal.** Restore the three metrics the screen reads but the database no longer exposes, and add what the hero needs.

### Data model (locked)

Strategy: extend `niche_intelligence` MV with weekly columns + the editorial slot + a previous-week format snapshot. One MV, one nightly refresh, one client cache contract. If MV refresh latency on staging exceeds ~60 s after the new columns land, split off `niche_intelligence_weekly` as a sibling MV refreshed in the same Cloud Run job — schema stays additive so the SPA hook keeps working.

New columns on `niche_intelligence`:

| Column | Type | Source |
|--------|------|--------|
| `video_count_7d` | `INTEGER` | `COUNT(*) FILTER (WHERE indexed_at > now() - interval '7 days')` |
| `video_count_total` | `INTEGER` | `COUNT(*)` |
| `total_views_7d` | `BIGINT` | `SUM(views) FILTER (WHERE indexed_at > now() - 7d)` |
| `total_views_prev_7d` | `BIGINT` | same for `[14d, 7d)` |
| `breakout_count_7d` | `INTEGER` | `COUNT(*) FILTER (WHERE breakout_multiplier >= 1.5 AND indexed_at > now() - 7d)` |
| `breakout_count_prev_7d` | `INTEGER` | same for `[14d, 7d)` |
| `new_hook_count_7d` | `INTEGER` | `hook_type` values present in 7d window AND absent in prior `[35d, 7d)` |
| `format_distribution_prev_7d` | `JSONB` | snapshot of `format_distribution` aggregated over `[14d, 7d)` — powers T.0.6 client-side trend computation |
| `editorial_summary` | `TEXT` | LLM-generated nightly (see Cloud Run section below); nullable |
| `editorial_week_label` | `TEXT` | `'TUẦN N · DD—DD THÁNG M'` server-formatted from `date_trunc('week', now())` |
| `editorial_generated_at` | `TIMESTAMPTZ` | When the LLM last wrote `editorial_summary` — for staleness UI |

Refresh path stays `corpus_ingest.py → rpc("refresh_niche_intelligence")` (already wired). Editorial generation is a separate step **after** the MV refresh, then a targeted `UPDATE niche_intelligence SET editorial_summary = …, editorial_generated_at = now() WHERE niche_id = $1` per niche — MVs in Postgres can't be partially mutated, so this requires either:
- promoting `editorial_summary` + `editorial_generated_at` to a sibling **regular table** `niche_editorial(niche_id PK, …)` joined in the SPA hook, **or**
- generating the editorial copy as part of the SQL refresh by calling out to a Postgres function that hits Vertex (heavy; not recommended).

**Locked**: sibling regular table `niche_editorial`. The MV stays purely a SQL aggregation; the writable table stays a row-per-niche update target. Hook joins both server-side via a thin RPC `get_niche_intelligence(niche_id)` (or extends the existing `useNicheIntelligence` query with a parallel select). This keeps both the MV refresh and the editorial write idempotent and independently retriable.

### Migrations

- `supabase/migrations/<ts>_niche_intelligence_weekly_columns.sql` — `DROP MATERIALIZED VIEW IF EXISTS niche_intelligence CASCADE;` + recreate with all current columns **plus** the nine new weekly + format-snapshot columns above. Re-create unique index `idx_niche_intelligence_pk` and `GRANT SELECT ON niche_intelligence TO authenticated`. Same pattern as `20260411000028_distribution_annotations.sql`.
- `supabase/migrations/<ts>_niche_editorial.sql` — `CREATE TABLE niche_editorial (niche_id INTEGER PRIMARY KEY REFERENCES niche_taxonomy(id), editorial_summary TEXT, editorial_week_label TEXT, editorial_generated_at TIMESTAMPTZ DEFAULT now())`. RLS: `SELECT` for `authenticated`, `INSERT/UPDATE` for `service_role` only. No DELETE policy — niche churn is rare and gets manual cleanup.
- `format_lifecycle` table is **not** modified; no migration needed for T.0.6 path B.

### Cloud Run module

- `cloud-run/getviews_pipeline/corpus_ingest.py` — confirm `rpc("refresh_niche_intelligence")` continues to fire after corpus upserts; add an integration check that the new weekly columns are non-null for at least the seed niche.
- `cloud-run/getviews_pipeline/niche_editorial.py` — **new module**. After the MV refresh:
  1. For each niche with `video_count_7d >= threshold` (default 30 — rebase against `phase-c-plan.md` C.0(iii) sample-size gates), build a small prompt from the niche's `format_distribution`, `format_distribution_prev_7d`, top hooks (from `hook_effectiveness`), and breakout count.
  2. Call Gemini via the existing `gemini_calls` accounting path (writes the call + cost to `gemini_calls`).
  3. Constrain output: ≤ 220 chars, must reference one rising format + one declining format + one notable hook, no emoji, no exclamation marks, Vietnamese.
  4. `UPSERT` into `niche_editorial(niche_id, editorial_summary, editorial_week_label, editorial_generated_at)`.
  5. Failure mode: log + skip the niche; the SPA renders the hero without the paragraph (already handled by the column being nullable).
- `cloud-run/getviews_pipeline/niche_editorial.py` is invoked at the end of the existing nightly job; idempotent; safe to re-run.

### Frontend

- Update `src/hooks/useNicheIntelligence.ts` return type to include the new columns; widen the query to `LEFT JOIN niche_editorial USING (niche_id)` (or run two queries in parallel and merge — pick what reads cleaner).
- Update `lowVideoCorpus` derivation in `ExploreScreen.tsx:538-543` to read from the restored `video_count_7d` field — this single-line fix unblocks both the Hook ranking and Format trend sections that have been silently dark.
- New hook `src/hooks/useFormatTrend.ts` — pure client-side reducer over `niche_intelligence.format_distribution` and `format_distribution_prev_7d`. Returns `{ rising: FormatTrend[], falling: FormatTrend[] }`. Replaces `useFormatLifecycle` calls in `ExploreScreen.tsx` only; legacy consumers untouched.
- No UI render changes in T.1 — that ships in T.6.

### Tests

- `cloud-run/tests/test_niche_intelligence_weekly.py` — golden numbers from a fixture niche for all nine new columns.
- `cloud-run/tests/test_niche_editorial.py` — prompt assembly, length / emoji / exclamation guards, fallback on empty distributions, `gemini_calls` row written on success.
- `src/__tests__/useNicheIntelligence.test.ts` — type round-trip including the joined `niche_editorial` fields, null safety when editorial row absent.
- `src/__tests__/useFormatTrend.test.ts` — three fixtures: full rising + falling, all-rising, empty distribution → empty arrays.

### Milestone gate

Type-check passes (`npm run typecheck`); MV refresh on staging produces non-zero values for at least one fully populated niche (e.g. `niche_id = 1` per `SUGGESTED_FULL_DATA_NICHE_ID`); `nicheIntel.video_count_7d` > 0 readable from devtools on staging; commit `feat(trends-data): backend complete`.

---

## 5. T.2 — Token & slop pass (3 days)

**Goal.** Land the lowest-risk cleanup so subsequent milestones don’t re-touch the same lines.

**Targets** (audit §4 + this plan):

| File | Change |
|------|--------|
| `src/components/explore/TrendingSection.tsx:17-23` (`signalBarColor`) | `#F59E0B` → `var(--gv-warning)` (introduce token if missing); `#EF4444` → `var(--gv-danger)`. Drop `rgba(...)` fallbacks. |
| `src/routes/_app/trends/ExploreScreen.tsx:879` (hook bar fade) | `rgba(100,100,120, …)` → `var(--gv-ink-3)` with `opacity` modifier or a token-driven alpha scale. |
| `src/routes/_app/trends/ExploreScreen.tsx:923, 940` (format trend chips) | `style={{ color: "var(--success, #22c55e)" }}` / `danger` → semantic class only (`text-[var(--gv-success)]`). Hex fallback removed. |
| `src/components/explore/TrendingSoundsSection.tsx:54-56` (`💰 Commerce` chip) | Replace emoji with text (`Mua bán`) or `lucide-react` `ShoppingBag` icon at `w-3 h-3`. |
| `src/routes/_app/trends/ExploreScreen.tsx:99-145` (`TikTokIcon`/`IGIcon`/`YTIcon`) | **Delete** all three components per T.0.5; remove the `label === "App"` branch in `FilterChip` (lines 336–340). |
| `src/routes/_app/trends/ExploreScreen.tsx:975, 1010` (orange dot rail headers) | `bg-orange-500` → `bg-[var(--gv-accent)]` (matches Reference `var(--accent)` dot in `RailSection` line 267). |
| `src/components/explore/TrendingSoundsSection.tsx:54` (`bg-amber-50 text-amber-700`) | Tailwind colour palette → `bg-[var(--gv-warning-soft)] text-[var(--gv-warning)]`. |

**Tooling.** Bake the grep gate into the milestone so it runs in CI (no allowlist needed since brand SVGs are deleted):

```bash
# zero hits required across the trends surface
rg -n --no-heading -g '!*.lock' -g '!artifacts/**' -e '#[0-9a-fA-F]{3,8}\b' \
  src/routes/_app/trends src/components/explore src/components/trends
```

Wire this into the existing `npm run check-tokens` script (`scripts/check-tokens.mjs`) so it runs on every typecheck.

**Tests.** Vitest snapshot for `TrendingSection`, `TrendingSoundsSection`, `ExploreScreen` toolbar.

**Milestone gate.** Grep returns 0 hits; existing visual snapshots pass; commit `fix(trends): token & slop pass`.

---

## 6. T.3 — Hero + toolbar (1 week)

**Goal.** Bring information hierarchy to Reference parity for the top 600 px of the screen.

### Design spec (cite Reference)

- Hero card: `background: var(--ink)`, `color: var(--canvas)`, `borderRadius: 12`, `padding: 28px 32px`, three-column grid `1fr 1fr 1fr` `gap: 32`. Collapses to single column at 1100 px with `gap: 18`. (`trends.jsx:21-48` + media query 117–122.)
- Hero column 1: `mono uc 9px` kicker (week label), `36px` line-height-1 stat with accent half (`var(--gv-accent)`), `12px var(--gv-ink-3)` editorial subline.
- Hero column 2: 2×2 `HeroStat` grid `gap: 16`, each `9px` mono kicker / `28px` value / `10px` `var(--pos-deep)` delta. (`trends.jsx:128-136`.)
- Hero column 3: `9px` mono kicker `TÓM TẮT BIÊN TẬP`, `16px tight` paragraph with `<em>` for highlighted phrases.
- Toolbar title: `font-size: 26`, kicker count beside it `font-size: 13 mono var(--gv-ink-3)`. Today: `font-extrabold` (no fixed size). (`trends.jsx:56`.)
- Search input: fixed `width: 260px`, `border-radius: 999`, `padding: 6px 12px`, `font-size: 12`. Today: `flex-1 min-w-[200px]`. (`trends.jsx:138-153`.)
- Pill segmented `grid/list` toggle (Reference 66–77) — ships in T.4 but the toolbar slot is reserved here.

### New primitives

- `src/components/trends/TrendsHero.tsx` — accepts `{ weekLabel, totalVideos, accentHalfCopy, editorialBody, stats: HeroStatProps[] }`.
- `src/components/trends/HeroStat.tsx` — `{ label, value, delta }` props; `delta` colour token-driven (positive vs negative).
- `src/components/trends/TrendsToolbar.tsx` — wraps the existing filter chips + search + (T.4) view toggle into one component so the toolbar can be tested in isolation.

### Frontend route

- `ExploreScreen.tsx` adds `<TrendsHero …>` above the discovery zone; keep `TrendingSection` carousel below the hero (carousel is a Production improvement, see §1.1).
- Hero data binds to the columns added in T.1. If `nicheIntel.video_count_7d == null` (no niche selected), hero renders an aggregated **all-niches** variant — wire to a new RPC `get_global_weekly_stats()` or hide hero entirely with a friendly empty state.

### Empty / loading / error states (humility)

- Loading: skeleton with the same hero footprint (avoid layout shift).
- Empty (no niche selected): aggregated cross-niche hero from `get_global_weekly_stats()`. If RPC not ready by T.3 ship, hero hides entirely and the toolbar pulls up — wire the empty state either way.
- Empty (niche has no 7d data): `Tuần này chưa có dữ liệu — đang đợi Cloud Run job kế tiếp.` with `mono uc` kicker `ĐANG CẬP NHẬT`.
- Editorial paragraph absent (`niche_editorial.editorial_summary IS NULL`): third hero column collapses, columns 1+2 keep their grid placement.
- Editorial stale (`now() − editorial_generated_at > 36h`): paragraph still renders, but a `mono uc 9px` `CŨ HƠN 36 TIẾNG` kicker appears under it (same pattern as the existing hook-data stale banner at `ExploreScreen.tsx:854-858`).
- Error: same shape as `ExploreScreen.tsx:789-799` retry card.

### Tests

- `src/components/trends/__tests__/TrendsHero.test.tsx` — render with full payload, with nulls, with one stat missing, with editorial empty.
- Storybook / preview entry under `src/components/trends/TrendsHero.stories.tsx` (skip if Storybook is not in repo — fall back to a route-level dev preview).

### Milestone gate

Lighthouse paints hero before discovery zone; no CLS > 0.05 on hero load; design audit screenshot diff < 5 % on Reference; commit `feat(trends): hero + toolbar`.

---

## 7. T.4 — Grid + list view (1 week)

**Goal.** Bring the main-column tile language and add the missing list view.

### Grid changes

- Container: `repeat(auto-fill, minmax(190px, 1fr))` `gap: 14px` (Reference 170–174). Replaces current `grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5`.
- Tile aspect: `9/16` (Reference 186). Replaces current `9/14`.
- Tile chrome:
  - Top-left badges: `BREAKOUT` (`var(--gv-accent)`) and `VIRAL` (`var(--gv-accent-2)` — introduce if missing) at `9px font-weight 700 letter-spacing 0.05em`. (`trends.jsx:191-195`.) Replaces current emerald mono `breakout_multiplier` text.
  - Top-right: duration badge `rgba(0,0,0,0.5)` chip — keep dark overlay token-driven via `bg-[var(--gv-overlay)]`.
  - Bottom: white views (`mono 11px ↑ N`) + 2-line title (`12px font-weight 500`) over a top-to-bottom black gradient.
  - Footer row (below thumb): `creator` mono left, `date` mono right.
  - “Phân tích →” chip: `padding: 6px 10px`, `border 1px var(--rule)`, `border-radius: 6` — wraps the existing `onNavigate` button. Replaces current `Phân tích video này` overlaid CTA.

### List view (new)

- Component: `src/components/trends/VideoList.tsx`. Layout per Reference 226–250: `grid-template-columns: 60px 1fr 100px 100px 100px 80px`, `gap: 14`, `padding: 12px 16px`, row border-bottom `1px var(--rule)`.
- Columns: thumb (64×aspect 9/16) · title + creator/niche meta · views (`mono ↑`) · hook (italic `tight`) · duration (`mono 11px`) · CTA (`Phân tích → var(--pos-deep)`).
- Wire `?view=list` URL param via `setFilter({ view: 'list' })`. Default: `grid`.
- Segmented toggle in `TrendsToolbar.tsx` (slot reserved in T.3).

### Decision: keep modal-first deep-dive?

- Production tile opens `VideoPlayerModal` first, then optionally navigates to `/app/video?video_id=…`. Reference jumps straight to the video screen.
- Recommendation: keep modal for grid (matches discovery flow), force navigation for list (denser, user already committed). Wire via `viewMode === 'list' ? navigate(…) : openModal(…)`.

### Tests

- `VideoCard` snapshot — aspect, badges, footer.
- `VideoList` snapshot + URL state round-trip.
- A11y: each tile is a `<button>` (Reference 184) — drop the `role="button"` + `div` pattern.

### Milestone gate

Both views render parity-screens; tab-key path through grid → toolbar → list and back works; design audit diff < 8 %; commit `feat(trends): grid + list views`.

---

## 8. T.5 — Rail reshape (3 days)

**Goal.** Move the Sounds and Format narratives into the rail per T.0.3 decision; keep the rail at **320 px** width (Reference 15) instead of current `290 px`; respect 1100 px collapse.

### Frontend

- Rename rail container to use `RailSection` primitive equivalents (`src/components/trends/RailSection.tsx` — kicker `mono uc 9px`, title `22px tight` with bottom border `1px solid var(--ink)`, items separated by `1px dashed var(--rule)`, optional accent dot `6×6 var(--gv-accent)`).
- Rail order:
  1. **Video nên xem** — keep `VideoDangHocSidebar` content but render through `RailSection` (current orange dot + bold header replaced with kicker + ink-bordered title).
  2. **Âm thanh đang lên** — re-host `TrendingSoundsSection` rows in rail (3 items max) using `RailSection` typography. `BreakoutSoundBanner` stays in main column above the grid (cross-niche signal earns the visual weight) — confirm with T.0.3 decision.
  3. **Hình thức hot** — three rising format rows from the source picked in T.0.6.
- Container: `width: 320px`, `padding: 24px 22px`, gap `24` between sections. Border-left stays.
- Below 1100 px (`max-[1100px]:`) rail collapses below main with `border-top: 1px solid var(--rule)` (Reference 117–122).

### Cleanup

- Delete the existing in-main-column `TrendingSoundsSection` placement at `ExploreScreen.tsx:673`.
- Move `risingFormats`/`fallingFormats` rendering out of the analytics zone and into the rail.

### Tests

- Rail renders three sections at 1280 px; collapses at 1099 px; no horizontal scroll on iPad portrait (768 px).
- Vitest: `RailSection` snapshot with 1 item, 3 items, accent dot on / off.

### Milestone gate

Visual audit pass at 1280 / 1100 / 900 / 720 / 375 widths; commit `feat(trends): rail reshape`.

---

## 9. T.6 — Analytics zone unblock + render (1 week)

**Goal.** Make the **Hook đang chạy** ranking and **Format đang lên / đang giảm** sections actually render, now that T.1 fixed `lowVideoCorpus` and T.0.6 fixed the format source.

### Frontend changes

- `ExploreScreen.tsx:538-543` — `lowVideoCorpus` now sees real values; verify the threshold (`< 10`) is still right or rebase per `phase-c-plan.md` C.0(iii) sample-size gates.
- `ExploreScreen.tsx:849-911` (hook ranking section) — keep render path, replace inline rgba bar fallback with token (already done in T.2), add an explicit `Sample size: N` row (Reference precedent: see `phase-c-plan.md` Pattern format `ConfidenceStrip`).
- `ExploreScreen.tsx:914-948` (format up/down) — bind to `useFormatTrend(nicheId)` from T.1. The hook's `rising`/`falling` arrays drop straight into the existing render. Delete the `useFormatLifecycle` import for this screen.
- Add humility states for both sections: when `sample_size < threshold`, render a `mono uc 9px` kicker `MẪU CHƯA ĐỦ — N video / cần ≥ M`.

### Tests

- Vitest with three fixture niches: full-data, sparse, zero. Each renders correct branch (rendered ranking, humility, hidden).
- Pytest in `cloud-run/tests/test_niche_intelligence_weekly.py` — golden numbers for the three fixtures.

### Milestone gate

For `niche_id = 1` on staging: `Hook đang chạy` shows ≥ 5 rows, `Format đang lên` shows ≥ 1 row, `Format đang giảm` shows ≥ 1 row. For a sparse fixture niche: all three render the humility state (not blank). Commit `feat(trends): analytics zone live`.

---

## 10. T.7 — Design audit close-out + measurement (3 days)

### Design audit

- Run the grep gate from T.2 against `src/routes/_app/trends/**` and `src/components/explore/**` and `src/components/trends/**`. Zero hits.
- Screenshot diff at 1440 / 1280 / 1100 / 900 / 720 / 375 px against Reference (and against pre-restyle Production for regression).
- Confirm `aside` is `width: 320px` and collapses at 1100 px (Reference parity, audit §1 row 1 fixed).

### Measurement

Add the following SPA-side `logUsage` events (file `src/lib/logUsage.ts` already routes to `usage_events` per `phase-c-plan.md` Measurement pattern):

| Action | Trigger | Properties |
|--------|---------|------------|
| `trends_screen_load` | `ExploreScreen` mount | `niche_id`, `view_mode (grid|list)`, `from_url_filters: bool` |
| `trending_card_click` | `TrendingCardItem` click | `card_id`, `signal`, `niche_id` |
| `trending_sound_click` | sound card click in main or rail | `sound_id`, `commerce_signal`, `placement (rail|main)` |
| `explore_filter_apply` | any filter chip change | `type (sort|format|min_views|niche|q)`, `value`, `result_count` |
| `explore_view_toggle` | grid/list segmented control | `to (grid|list)` |
| `trends_hero_render` | Hero successfully renders with non-null payload | `niche_id`, `video_count_7d` |
| `trends_hero_empty` | Hero renders empty state | `niche_id`, `reason (no_data|no_niche|error)` |

Add to `artifacts/qa-reports/phase-d-d0-measurement-read.md` action list so the next 7-day audit picks them up.

### Milestone gate

Audit report saved to `artifacts/qa-reports/trends-restyle-audit.md` with screenshots embedded; events visible in staging `usage_events`; commit `test(trends): qa pass`.

---

## 11. Things retired when this lands

- `TrendingSoundsSection` rendered in main column (`ExploreScreen.tsx:673`) — moves to rail (T.5).
- Inline `Phân tích video này` button on `VideoCard` — replaced by `Phân tích → niche` footer chip (T.4).
- `lowVideoCorpus` ever being silently `true` with no UI feedback (T.1 + T.6).
- `bg-orange-500` rail dot (T.2).
- `💰` emoji as commerce mark (T.2).

---

## 12. Deferred to later

- **Personalised hero** — hero changes copy / stats based on viewer persona (creator vs strategist). Out of scope; Phase D candidate.
- **Editorial CMS** — admin UI for `editorial_summary` writes. T.6 picks one of LLM-generated or curated table; admin UI is a follow-up.
- **Cross-niche hero** — when no niche selected, hero shows aggregated stats. Backed by RPC `get_global_weekly_stats()`; deferred unless T.3 spike says it’s blocking.
- **Rail “Đang viral” second list** — current Production splits the same `breakoutSidebarItems` into two slices (lines 979 / 1014) which double-counts when fewer than 6 items exist. Replace with a real `viral_videos` query in T.5 if data source agreed; otherwise remove the second section to avoid the bug.

---

## 13. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| `niche_intelligence` MV refresh time grows past acceptable nightly window after adding new columns | Medium | Pick Option B (sibling MV) in T.0; profile refresh on staging before T.1 ships |
| `format_lifecycle` writer (T.0.6 path A) blocks for weeks on Cloud Run cycle | High | Default to T.0.6 path B (derive from `niche_intelligence.format_distribution`); write the writer only if path B insufficient |
| Hero editorial paragraph requires manual editorial workflow we don’t have today | Medium | T.0.1 picks LLM-generated path; if that’s also out, drop the column entirely from the hero |
| Brand SVG hex linter exception leaks to other components | Low | T.0.5 documents the allowlist; CI grep allowlists by file path, not by colour |
| 1100 px breakpoint disagrees with current Tailwind config used by other screens | Medium | Add `screens.trends: '1100px'` to `tailwind.config.ts` rather than hardcoding `min-[1100px]:` everywhere |
| `?view=list` URL param collision with existing screen state | Low | Audit `useSearchParams` uses; `view` is currently free |

---

## 14. Testing strategy

- **Backend**: pytest in `cloud-run/tests/test_niche_intelligence_weekly.py` — three fixtures (full / sparse / zero), assert returned columns, refresh-RPC contract.
- **Frontend unit**: vitest for `TrendsHero`, `HeroStat`, `RailSection`, `VideoList`, `VideoCard` (post-restyle), `useNicheIntelligence` (type round-trip).
- **Frontend smoke**: `artifacts/qa-reports/smoke-trends.sh` — boot dev server, hit `/app/trends`, screenshot at three widths, exit non-zero on console errors / failed hero data.
- **Token gate**: T.2 grep wired into `npm run check-tokens` (already exists per `package.json`); CI fails on non-zero hits inside `src/{routes/_app/trends,components/explore,components/trends}`.
- **A11y**: Tab path covers toolbar → grid/list toggle → first tile → rail; `axe-core` clean on `/app/trends`.
- **Visual**: Reference screenshots at 1440/1280/1100/900/720/375 stored under `artifacts/uiux-reference/screens/trends/` for diffing.

---

## 15. Responsive breakpoints

Match Reference 117–122 exactly:

- `> 1100 px` — 2-column layout, hero 3-column.
- `≤ 1100 px` — single-column layout, rail collapses below main with `border-top: 1px solid var(--rule)`, hero collapses to single column with `gap: 18`.
- `≤ 900 px` — toolbar wraps to two rows; grid stays `minmax(190px, 1fr)` (so 2–3 columns at this width); list view becomes scroll-x table.
- `≤ 720 px` — toolbar pills become a horizontally-scrollable strip; sounds carousel keeps current `[scrollbar-width:none]` pattern.
- `≤ 375 px` — hero single column with `padding: 20px 18px`; tile aspect stays `9/16`.

Add `screens.trends: '1100px'` to `tailwind.config.ts` and use `trends:` prefixed utilities everywhere on this screen.

---

## 16. Timeline

| Sub-phase | Estimate |
|-----------|----------|
| T.0 spike | 1 week |
| T.1 backend data | 1 week |
| T.2 token & slop pass | 3 days |
| T.3 hero + toolbar | 1 week |
| T.4 grid + list view | 1 week |
| T.5 rail reshape | 3 days |
| T.6 analytics zone unblock + render | 1 week |
| T.7 design audit close-out + measurement | 3 days |
| Buffer (design audit + bugfix loop) | 1 week |
| **Total** | **~7 weeks** |

T.2 can run in parallel with T.3–T.5 if a second engineer picks it up — saves ~3 days off critical path.

---

## 17. Non-negotiables

1. **No silent zones.** T.6 cannot close while the Hook ranking and Format up/down sections render blank for the seed niche on staging.
2. **Token gate green.** T.2 closes only when grep returns zero hits inside `src/{routes/_app/trends,components/explore,components/trends}`. Brand SVG colours are the only allowed hex, with an inline allowlist comment.
3. **Reference deviations documented.** Anywhere we keep a Production improvement (URL filters, focus-visible, modal-first deep dive, infinite scroll, breakout carousel) we update `artifacts/uiux-reference/screens/trends.jsx` (or a sibling note) so the reference stops disagreeing with shipped code.
4. **Data contract first.** No UI binds to a column or RPC that doesn’t exist on staging. `nicheIntel.video_count_7d` was the warning sign — every new field gets a migration in T.1 before any T.3+ render binds to it.
5. **Commit convention** per `AGENTS.md` — phase gates `feat(trends): backend complete`, `feat(trends): screens complete`, `test(trends): qa pass`. Bugfixes that ship before the gate are `fix(trends): …`.
6. **Audit doc updated.** `artifacts/qa-reports/explore-trends-uiux-audit.md` gets a closing addendum at T.7 marking each row in §6 scorecard as resolved / accepted-as-improvement / deferred.

---

## 18. Locked decisions (this revision)

| Decision | Outcome | Source |
|----------|---------|--------|
| Umbrella | **C.9** under `phase-c-plan.md` | User answer #1 |
| Hero editorial source | **LLM-generated**, persisted nightly to `niche_editorial.editorial_summary` (sibling table; MV stays read-only); ≤220 chars, Vietnamese, no emoji / no exclamation | User answer #2 + recommendation |
| `format_lifecycle` source | **Derive client-side** from `niche_intelligence.format_distribution` vs new `format_distribution_prev_7d` snapshot; no Cloud Run writer; legacy table untouched | User answer #3 + recommendation |
| Brand SVG | **Delete** `TikTokIcon`/`IGIcon`/`YTIcon` and the `label === "App"` branch; Reference uses monochrome icons only — no allowlist clause needed | User answer #4 |

## 19. Still to lock in T.0 (≤ 3 days)

1. **List view shape (T.0.2).** Adopt the 6-col Reference table or drop list mode entirely? — current Production has no list view.
2. **Rail content split (T.0.3).** Move Sounds + Format into rail (recommended) or keep current main-column placement and update the Reference?
3. **Tile geometry + breakpoint (T.0.4).** Ratify `9/16` aspect, `gap 14`, `minmax(190px, 1fr)`, and `1100 px` rail collapse breakpoint — confirm against `phase-c-plan.md` C.0(iv) width decision so all screens stay aligned.
4. **`get_global_weekly_stats()` RPC.** Build for the no-niche hero variant (T.3) or hide the hero when no niche selected? Cheaper to hide; small UX cost.
