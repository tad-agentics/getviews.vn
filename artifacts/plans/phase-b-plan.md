# Phase B — Deterministic analysis screens

Four screens that take the creator beyond the Home/morning-ritual loop into
the per-video, per-channel, per-KOL, per-script workflows. Every screen is
deterministic-first: backend emits structured fields, frontend slots them
into a fixed layout, LLM is confined to bounded text.

**Design source of truth**: `artifacts/uiux-reference/screens/` (`video.jsx`,
`channel.jsx`, `kol.jsx`, `script.jsx`) + `artifacts/uiux-reference/data.js`
fixtures for `CHANNEL_DETAIL`, `VIDEOS`, `CREATORS`, `HOOKS`.

## Guiding principles

- **One screen at a time.** Each sub-phase lands an atomic PR with its own
  backend aggregations + migration + tests + docs. Partial screens don't ship.
- **Claim tiers gate visibility, not disclaim inline.** A thin-corpus niche
  renders fewer cards, not a 42%-disclaimer caption.
- **Slots beat prompts.** If a number is computable from corpus, compute it.
  Gemini stays for TL;DR paragraphs and "why it works" blurbs.
- **Retire chat fallbacks as each screen ships.** `/app/chat` loses its
  corresponding quick-action CTA once the dedicated screen is live.
- **`src/lib/api-types.ts` is created on day 1 of B.1.1** — all response
  types defined there before any frontend route work.

## Recommended order

| # | Screen | Rationale |
|---|---|---|
| B.1 | `/video` Phân Tích Video | Highest-traffic intent ("Soi video"). Validates the whole deterministic-slot pattern. Medium complexity. |
| B.2 | `/kol` Kênh Tham Chiếu | Lowest-risk. `creator_velocity` + `starter_creators` already exist. Match score is the only net-new computation. |
| B.3 | `/channel` Phân Tích Kênh | Extends B.1's structural decomposition from single video → creator scale. |
| B.4 | `/script` Xưởng Viết | Most generative + most complex. Closes the morning-ritual loop (hook card → full shot list). Save for last. |

Estimated **10–12 weeks** (includes 1 spike week + 1 week buffer for
design-audit rounds per screen).

---

## Pre-kickoff decisions (lock before B.1 starts)

Decisions 1–2 are resolved in B.0. Remaining:

1. **Channel formula refresh** (B.3) — TTL cache: recompute only if
   `computed_at` > 7 days old. Never recompute on open.
2. **Scene intelligence** (B.4) — nightly batch job per niche (not
   recomputed on open). Skip niches with < 30 winning videos per scene type.
3. **`niche_intelligence` already covers niche benchmark** — no new columns
   needed for B.1.2's niche side. The view already has `avg_face_appears_at`,
   `pct_face_in_half_sec`, `avg_transitions_per_second`, duration stats,
   `hook_distribution`. Refresh after corpus ingest, not per-video.
4. **B.4 forecast vs Phase C `/answer`** — B.4's forecast is deterministic
   (formula: hook_score × duration_band × niche median). Phase C's is
   LLM-driven reasoning. No overlap if that line holds.

---

## B.0 — Spike & pre-kickoff (1 week)

Unblock three decisions before writing a line of B.1 code.

### B.0.1 Retention curve source (1–2d)

Hit the EnsembleData API. Check whether any endpoint returns a per-video
retention curve (time-series % of viewers remaining at each second).

- **If yes**: document the endpoint, response shape, and rate limits.
  Wire it into `video_structural.model_retention_curve()` as the primary
  source. Skip the sigmoid model.
- **If no**: write a one-page proxy spec — parameterized sigmoid anchored to
  `breakout_multiplier` + niche median retention from `niche_intelligence`.
  UI labels the curve `ĐƯỜNG ƯỚC TÍNH` (not `ĐƯỜNG GIỮ CHÂN`) when modeled.

**Deliverable**: `artifacts/plans/retention-curve-decision.md` — decision
record with chosen approach, evidence, and UI label spec.

### B.0.2 Match score formula (1d)

Define the rule-based formula with weights summing to 1.0:

```text
match = 0.40 × niche_match
      + 0.30 × follower_range_overlap
      + 0.20 × growth_percentile
      + 0.10 × reference_channel_overlap
```

Each component normalized 0–1:

- `niche_match`: 1.0 if creator `niche_id` == user `primary_niche`, else 0.
- `follower_range_overlap`: `1 − |log10(creator_followers / user_followers)| / 2`,
  clamped 0–1. Zero if gap > 100×.
- `growth_percentile`: creator's `growth_30d_pct` percentile rank within
  same niche in `creator_velocity`. Normalized 0–1.
- `reference_channel_overlap`: fraction of `profiles.reference_channel_handles`
  that are also in `starter_creators` for the same niche. 1.0 if all overlap.

Worked example — user has 50K followers, niche=Tech, references=[@sammie]:
- niche_match: 1.0 → 0.40
- follower_range (creator 412K): `1 − log10(412/50)/2 = 1 − 0.46 = 0.54` → 0.16
- growth_percentile (12% → 70th pct): 0.70 → 0.14
- reference_overlap (1/1): 1.0 → 0.10
- **total: 0.80 → displayed as 80/100**

Score cached per `(user_id, handle)` in `creator_velocity` or a separate
`match_scores` JSONB column on `profiles`. Invalidated when user updates
`primary_niche` or `reference_channel_handles`.

**Deliverable**: formula section merged into B.2 spec (below). No new file.

### B.0.3 `creator_pins` vs `reference_channel_handles` (0.5d)

**Decision**: drop `creator_pins` table. `profiles.reference_channel_handles`
is the pin list, capped at 10 handles. The "Đang theo dõi" tab reads directly
from this column. "Ghim" / "Bỏ ghim" buttons call a Supabase RPC
`toggle_reference_channel(handle TEXT)` that upserts/removes from the array,
respecting the cap.

"Khám phá" tab is a read-only view: `starter_creators` filtered by
`niche_id = user.primary_niche`, sorted by `avg_views` desc. No separate
pin store.

**Impact on B.2**: remove `creator_pins` table + `/kol/pin` + `/kol/unpin`
endpoints. Replace with single `POST /kol/toggle-pin` (calls
`toggle_reference_channel` RPC). B.2 spec updated below.

---

## B.1 — `/video` Phân Tích Video (~3 weeks)

### Exact design spec (from `video.jsx`)

**Layout**: `maxWidth: 1280`, `padding: 24px 28px 80px`, responsive breakpoint
at 900px (single-column).

**Mode toggle** (top, before content): two-button toggle — `[sparkle] Vì sao
video NỔ` / `[flame] Vì sao video FLOP`. Active button: `background: ink,
color: canvas`. Inactive: transparent. Border: `1px solid ink` wraps both.

#### Win mode (`WinAnalysis`)

**Crumb bar**: `← Quay lại Xu Hướng` (btn-ghost) | right: `[bookmark] Lưu` +
`[copy] Copy hook` + `[script] Tạo kịch bản từ video này` (primary btn).

**Grid**: `320px | 1fr`, gap 32.

**Left col — phone preview**:
- `9/16` aspect, `borderRadius: 18`, `border: 8px solid ink`,
  `boxShadow: 0 30px 60px -30px rgba(0,0,0,0.4)`
- Gradient overlay `180deg transparent 50% → rgba(0,0,0,0.6)`
- Top-left badge: `BREAKOUT` in `var(--accent)` background, white text,
  `fontSize: 10`, `fontWeight: 700`, `letterSpacing: 0.05em`
- Center: play button — `56×56`, `borderRadius: 50%`,
  `background: rgba(255,255,255,0.2)`, `backdropFilter: blur(10px)`
- Bottom overlay: `creator · dur` in mono 11px + title in serif 18px
- Below card: `Đăng {date} · {views} · {saves} · {shares}` — mono 11px,
  `color: ink-4`, centered

**Right col — analysis**:
- Kicker: `BÁO CÁO PHÂN TÍCH · {niche}` — mono 9.5px, ink-4
- H1: `fontSize: 42, lineHeight: 1.05` serif-tight — LLM generates this
  headline ("Tại sao '…' lại nổ?")
- Subtext: 15px, ink-3, maxWidth 640 — LLM generates (views + timeframe +
  "4 yếu tố chính")

**KPI grid** (`Big numbers`): `repeat(auto-fit, minmax(140px, 1fr))` inside
`border: 1px solid rule, borderRadius: 10, overflow: hidden`. Each cell:
`padding: 18, background: paper, borderRight: 1px solid rule` (except last).
Fields: `label` (mono 9px uc, ink-4) + `value` (tight 30px) +
`delta` (mono 10px, `pos-deep`). Four metrics: VIEW / GIỮ CHÂN / SAVE RATE /
SHARE.

**Timeline** (`SectionMini` + `Timeline` component):
- Kicker: `DÒNG THỜI GIAN`, title: `Cấu trúc {duration}s`
- Timeline bar: `height: 36, borderRadius: 6, overflow: hidden,
  border: 1px solid rule`. Segments as `flex: {pct}` divs, each with segment
  name (mono 10px, fontWeight 600, letterSpacing 0.05em). Colors from design:
  HOOK=accent, PROMISE=ink-2, APP 1-5 alternating ink-3/ink-2, CTA=accent-deep.
- Below: timestamps `0:00 / 0:15 / 0:30 / 0:45 / {end}` — mono 10px, ink-4.

**Hook breakdown** (3-col grid, gap 12): Each card `className="card"
padding: 16`. Fields: timestamp (`mono 10px, accent-deep`) + label (`tight
16px`) + body (`12px, ink-3`). Three phases: `0.0–0.8s` / `0.8–1.8s` /
`1.8–3.0s`. Content is LLM-generated from `analysis_json.hook_analysis`.

**Lessons** (`BÀI HỌC ÁP DỤNG`): `3 điều bạn có thể copy`. Each row:
`grid-template-columns: 40px 1fr auto`, `padding: 14px 18px`,
`background: paper, border: 1px solid rule, borderRadius: 8`.
Number: `tight 24px, accent`. Text: title `tight 17px` + body `12px ink-3`.
Right: `<button className="chip">Áp dụng</button>`. Content: 3 LLM-generated
lessons with Vietnamese copy.

#### Flop mode (`FlopDiagnostic`)

**URL input bar**: `border: 2px solid ink, background: paper, padding: 16`,
flex row. Film icon + text input (mono font, transparent bg) +
`[sparkle] Phân tích` btn-accent. Full-width.

**After analysis** (`analyzed === true`):

**Summary block** (`borderTop: 2px solid ink, paddingTop: 22, marginBottom: 28`):
- Kicker: `CHẨN ĐOÁN · {N} ĐIỂM LỖI CẤU TRÚC` — mono 10px, accent, uc,
  letterSpacing 0.18em, fontWeight 600
- H1: `fontFamily: serif`, `fontSize: clamp(26px, 3vw, 36px)`,
  `fontWeight: 500`, `letterSpacing: -0.02em`, `maxWidth: 820`. Accent color
  for view count, `rgb(0, 159, 250)` for prediction.
- Meta row: mono 12px — `{views} · {retention}% retention · {ctr}% CTR` /
  `Ngách {niche} TB: {avg_views} · {avg_ret}% ret · {avg_ctr}% CTR` /
  `So sánh với {n} video thắng`

**Retention curve**: `border: 1px solid rule, background: paper, padding: 18,
marginBottom: 24`. Kicker `ĐƯỜNG GIỮ CHÂN · VS NGÁCH`. SVG `viewBox="0 0 400
80"`, `width: 100%, height: 80`. Two paths: user's video (accent, strokeWidth
2.5) + niche benchmark (rgb(0,159,250), strokeWidth 1.5, strokeDasharray "4
3"). Annotation text for drop points (mono 9px). Timestamp axis below: `0s /
15s / 30s / 45s / {end}s`.

**Issues list** (`LỖI CẤU TRÚC · XẾP THEO ẢNH HƯỞNG`): each row `grid-
template-columns: 80px 1fr auto`, `padding: 14px 16px`, `background: paper`.
Border: `1px solid` — accent if `sev === 'high'`, rule otherwise. Left border
`4px solid` — accent if high, ink-4 otherwise.
- Left col: timestamp `{t}s – {end}s` (mono 11px, ink-4) + severity badge
  (`CAO` or `TB`) — mono 9px uc, accent/ink-4.
- Middle: title (serif 18px, fontWeight 500) + detail (13px, ink-3,
  lineHeight 1.55) + FIX inline block (`background: canvas-2`, kicker `FIX`
  in mono 9px accent + fix text 12px ink-2).
- Right: `Áp vào kịch bản` btn-ghost, routes to `/script`.

**Dark summary bar**: `background: ink, color: canvas`, flex row,
`padding: 16px 20px`. Left: kicker `NẾU ÁP DỤNG 2 FIX CAO` (mono 9.5px uc
opacity 0.5) + prediction line (serif 22px fontWeight 500) with
`rgb(0,159,250)` highlights. Right: `Viết lại kịch bản →` btn-accent,
routes to `/script`.

### Data model

**Win mode fields** (from `analysis_json` + corpus aggregation):
- `video_id`, `creator_handle`, `views`, `likes`, `comments`, `shares`,
  `save_rate` (computed), `breakout_multiplier`, `niche_id`, `thumbnail_url`
- `duration_seconds` (from `analysis_json`)
- `hook_analysis` (first_frame_type, face_appears_at, first_speech_at,
  hook_phrase, hook_type, hook_notes, hook_timeline)
- `scenes[]` → mapped to Timeline segments (HOOK/PROMISE/APP 1-5/CTA)
- Three hook phase cards: derived from scenes[0] + hook_timeline
- LLM: analysis headline + subtext + 3 lesson blurbs (bounded, cached in
  `video_diagnostics`)

**Flop mode fields**:
- Same video fields as Win, plus niche benchmark from `niche_intelligence`:
  `avg_face_appears_at`, `avg_transitions_per_second`, duration stats,
  `hook_distribution`, `avg_engagement_rate`
- Retention curve: approach resolved in B.0.1 decision record
  (`artifacts/plans/retention-curve-decision.md`). B.1.2 implements that
  outcome — no further decision needed here.
- Issues list: Gemini structured output
  `[{sev: "high"|"mid"|"low", t, end, title, detail, fix}]` — schema-
  enforced via pydantic, cached in `video_diagnostics`
- Flop threshold: `views < niche_median_views × 0.5` OR
  `engagement_rate < niche_median_er × 0.6` — either triggers flop mode

### New table: `video_diagnostics`

```sql
CREATE TABLE video_diagnostics (
  video_id          TEXT PRIMARY KEY REFERENCES video_corpus(video_id),
  analysis_headline TEXT,                 -- LLM win-mode headline
  analysis_subtext  TEXT,                 -- LLM win-mode subtext
  lessons           JSONB NOT NULL DEFAULT '[]',  -- [{title, body}] × 3
  hook_phases       JSONB NOT NULL DEFAULT '[]',  -- [{t_range, label, body}] × 3
  segments          JSONB NOT NULL DEFAULT '[]',  -- [{name, pct, color_key}] × 8
  flop_issues       JSONB,               -- [{sev, t, end, title, detail, fix}]
  retention_curve   JSONB,               -- [{t, pct}] × 20 — modeled or real
  niche_benchmark_curve JSONB,           -- [{t, pct}] × 20 from niche_intelligence
  computed_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Service-role writes only. No RLS INSERT policy. Authenticated users may read.

### New Cloud Run module: `video_structural.py`

- `decompose_segments(analysis_json)` → list of `{name, pct, color_key}`
  from `scenes[]` timestamps. Pure deterministic.
- `extract_hook_phases(analysis_json)` → 3 `{t_range, label, body}` cards
  from `hook_analysis` + `scenes[0]`. Gemini labels body text only.
- `model_retention_curve(views, breakout_multiplier, niche_benchmark)` →
  20-point curve. Parameterized sigmoid anchored to known drop-off zones.
- `diagnose_flop(video_data, niche_benchmark)` → Gemini call with pydantic
  schema. Only fires when flop threshold met.
- `generate_win_analysis(video_data, corpus_context)` → Gemini call for
  headline + subtext + 3 lessons. Cached in `video_diagnostics`.

### New Cloud Run endpoints

- `POST /video/analyze` — body `{video_id?, tiktok_url?}`. Checks
  `video_diagnostics` cache first. If stale or missing: run
  `video_structural.py` pipeline → upsert → return. Response shape:
  ```json
  {
    "video_id": "...",
    "mode": "win"|"flop",
    "meta": { "creator", "views", "likes", "comments", "shares",
              "save_rate", "duration_sec", "thumbnail_url", "date_posted" },
    "kpis": [{ "label", "value", "delta" }],
    "segments": [{ "name", "pct", "color_key" }],
    "hook_phases": [{ "t_range", "label", "body" }],
    "lessons": [{ "title", "body" }],
    "analysis_headline": "...",
    "analysis_subtext": "...",
    "flop_issues": [{ "sev", "t", "end", "title", "detail", "fix" }],
    "retention_curve": [{ "t", "pct" }],
    "niche_benchmark_curve": [{ "t", "pct" }],
    "niche_meta": { "avg_views", "avg_retention", "avg_ctr", "sample_size" }
  }
  ```
- `GET /video/niche-benchmark?niche_id=X` — returns niche aggregate from
  `niche_intelligence`. Cached; refreshes after batch ingest.

### Frontend: `/app/video` route

- Route file: `src/routes/_app/video/route.tsx`
- Reads `?url=` or `?video_id=` query param (prefillUrl pattern from Chat)
- TanStack Query key: `['video-analysis', videoIdOrUrl]`
- `staleTime: 1000 * 60 * 60` (1h — diagnostics don't change by the hour)
- New primitives needed:
  - `RetentionCurveSVG` — SVG component, two paths, annotation text,
    timestamp axis. Exact viewBox `0 0 400 80`.
  - `TimelineBar` — flex bar with named segments, color_key → CSS var map,
    timestamp labels below.
  - `IssueCard` — grid `80px 1fr auto`, left-border severity indicator.
  - `KpiGrid` — `repeat(auto-fit, minmax(140px, 1fr))`, shared with
    later screens.
  - `SectionMini` — already in `video.jsx`: kicker + title +
    `borderBottom: 1px solid ink`. Implement once, export from
    `src/components/SectionMini.tsx`.
- Reuses: `Btn`, `Card`, existing icon set.

### Milestones

1. **B.1.1** (3d) — `video_diagnostics` migration + `src/lib/api-types.ts`
   (all Phase B types) + `video_structural.py` segment decomposition + hook
   phase extraction + unit tests
2. **B.1.2** (3d) — retention curve per B.0.1 decision record + niche
   benchmark endpoint + cache wiring (no spike here — B.0.1 already decided)
3. **B.1.3** (2d) — flop diagnostic Gemini endpoint + pydantic schema +
   win-mode LLM generation + `video_diagnostics` upsert + tests
4. **B.1.4** (4d) — `/app/video` Win mode + all new primitives + data wiring
5. **B.1.5** (2d) — Flop mode + URL input flow (reuse prefillUrl pattern)
6. **B.1.6** (1d) — retire `video_diagnosis` chat CTA; "Soi video"
   quick-action routes to `/app/video`
7. **B.1.7** (1d) — design-audit pass: pixel-compare against `video.jsx`
   reference, fix spacing/color/font regressions before merging PR

### B.1 checkpoint (measure for 2 weeks post-ship)

Gate metric: **≥ 30% of `/app/video` Flop-mode sessions end with an
"Áp vào kịch bản" CTA click** (tracked as a `chat_sessions` row with
`intent_type = 'shot_list'` opened within 10 min of `/video` load).

Instrument: Supabase query — count sessions where `created_at` within 10 min
of a `/video` page load event (log page loads as `anonymous_usage` rows with
`action = 'video_screen_load'`). Both events exist in current schema.

If gate fails after 2 weeks: pause B.2, revisit whether the deterministic-slot
thesis holds or whether users need a different entry point.

---

## B.2 — `/kol` Kênh Tham Chiếu (~1.5 weeks)

### Exact design spec (from `kol.jsx`)

**Layout**: `maxWidth: 1320`, `padding: 24px 28px 80px`. Responsive
breakpoint at 1100px (detail card drops below list).

**Header bar** (`paddingBottom: 14, borderBottom: 1px solid rule`):
- Left: kicker `KÊNH THAM CHIẾU · NGÁCH {niche}` (mono 10px uc, ink-4) +
  H1 `fontSize: clamp(28px, 3.2vw, 40px), fontWeight 600`. Copy switches
  by tab: pinned → `3 kênh bạn đang <em>theo dõi sát</em>` / discover →
  `Khám phá <em>kênh mới</em> trong ngách`. `<em>` in accent italic.
- Right: two-button tab toggle — `border: 1px solid ink, borderRadius: 6,
  overflow: hidden`. Pinned tab: `[bookmark] Đang theo dõi {count}` /
  discover: `[sparkle] Khám phá {count}`. Active: `background: ink, color:
  canvas`. Each button: `padding: 10px 16px, fontSize: 13`. Count badge:
  mono 10px, `padding: 2px 6px, borderRadius: 4`, background switches with
  active state.

**Filter ribbon** (`padding: 8px 0 18px`):
- Left: `LỌC THEO` label (mono 9px uc, ink-4) + pill chips: niche (active
  state = `chip-accent`) + follower range + region + growth + `+ Thêm điều
  kiện`. Pill = `className="chip"`.
- Right: `SearchInput placeholder="Tìm @handle…"` + context button:
  pinned tab → `[plus] Ghim kênh` (btn), discover tab →
  `[sparkle] Gợi ý cho ngách của tôi` (btn).

**Two-column grid**: `1fr 380px`, gap 28.

**Left — sortable table**:
- Header row: `grid-template-columns: 40px 2fr 100px 100px 100px 80px`,
  `padding: 10px 18px, borderBottom: 1px solid ink`. Columns: `# / CREATOR
  / FOLLOW / VIEW TB / TĂNG 30D / MATCH` (mono 9px uc, ink-4).
- Each row: same grid template, `padding: 14px 18px, borderBottom: 1px
  solid rule`. Active row: `background: paper`. Hover → cursor pointer.
- `#` col: mono 11px, ink-4 (01, 02…)
- `CREATOR` col: avatar (36×36 circle, color cycle `[accent, #3D2F4A,
  #2A3A5C, #1F3A5C, #4A2A5C, #5C2A3A]`, first letter) + name (13px) with
  optional `GHIM` badge (mono 8px uc, `background: accent-soft, color:
  accent-deep`) when `isPinned && tab === 'discover'` + handle·tone (mono
  10px, ink-4).
- `FOLLOW / VIEW TB`: mono 12px.
- `TĂNG 30D`: mono 12px, `color: pos-deep, fontWeight: 600`.
- `MATCH`: progress bar (`flex: 1, height: 4, borderRadius: 999, background:
  rule, overflow: hidden`) + fill (`width: {match}%, background: accent`) +
  score label (mono 10px, `width: 22`).

**Right — sticky detail card** (`position: sticky, top: 86`):
- `className="card"`, `padding: 22`.
- Header: avatar 56×56 (accent bg) + name (tight 22px) + handle (mono 11px,
  ink-3).
- Stats 2×2 grid (`background: canvas-2, borderRadius: 8, padding: 14,
  gridTemplateColumns: 1fr 1fr, gap: 14`): NGÁCH / FOLLOW / VIEW TB /
  TĂNG 30D. Each: label mono 9px uc ink-4 + value 13px (growth: pos-deep).
- Match score: `ĐỘ KHỚP NGÁCH BẠN` label + big `{match}/100` (tight 36px,
  accent; `/100` in 16px ink-4) + description 11px ink-3.
- Three CTAs (flex col, gap 8):
  1. `[eye] Phân tích kênh đầy đủ` (btn) → routes to `/channel`
  2. `[bookmark] Bỏ ghim khỏi theo dõi` / `Ghim để theo dõi` (btn-ghost)
     — text switches on pin state
  3. `[script] Học hook từ kênh này` (btn-ghost) → routes to `/script`

### Data model

**Table `CREATORS` fields mapped to API**:
`handle, name, niche, followers, avg_views, growth_30d_pct, match_score,
tone` — matches `creator_velocity` + `starter_creators` + computed match.

**Match score formula** (rule-based, weights from B.0.2):

```
match = 0.40 × niche_match
      + 0.30 × follower_range_overlap
      + 0.20 × growth_percentile
      + 0.10 × reference_channel_overlap
```

Each component 0–1; result × 100 = displayed score. Cached per
`(user_id, handle)`. Invalidated on `primary_niche` or
`reference_channel_handles` change.

**No `creator_pins` table** (resolved in B.0.3). Pin list is
`profiles.reference_channel_handles TEXT[]`, cap 10. "Đang theo dõi" tab
reads this column directly. "Khám phá" tab reads `starter_creators` filtered
by `niche_id = user.primary_niche`.

New Supabase RPC (migration in B.2.1):

```sql
CREATE OR REPLACE FUNCTION toggle_reference_channel(p_handle TEXT)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  IF p_handle = ANY(
    SELECT reference_channel_handles FROM profiles WHERE id = auth.uid()
  ) THEN
    UPDATE profiles SET reference_channel_handles =
      array_remove(reference_channel_handles, p_handle)
    WHERE id = auth.uid();
  ELSE
    UPDATE profiles SET reference_channel_handles =
      array_append(reference_channel_handles, p_handle)
    WHERE id = auth.uid()
      AND cardinality(reference_channel_handles) < 10;
  END IF;
END;
$$;
```

### Endpoints

- `GET /kol/browse?niche_id&tab=pinned|discover&page` — returns table rows
  with match_score. Pinned: filter `creator_velocity` by handles in
  `profiles.reference_channel_handles`. Discover: `starter_creators` filtered
  by niche.
- `POST /kol/toggle-pin` — body `{handle}`. Calls
  `toggle_reference_channel` RPC via service client.

### Frontend: `/app/kol` route

- Route: `src/routes/_app/kol/route.tsx`
- New primitives: `FilterChipRow` (reuses `Chip`), `SortableTableHeader`
  (column headers, sort state), `MatchBar` (progress bar + score).
- Sticky detail card: `position: sticky, top: 86px` — CSS, not JS.
- Tab state in URL search param `?tab=pinned|discover` for deep-linking.
- Pin/unpin: optimistic update via TanStack `useMutation`.

### Milestones

1. **B.2.1** (2d) — `toggle_reference_channel` RPC migration + match score
   computation + `/kol/browse` + `/kol/toggle-pin` endpoints + tests
2. **B.2.2** (4d) — `/app/kol` full screen: table + filter ribbon + sticky
   detail card + tab switching + toggle-pin mutation
3. **B.2.3** (1d) — retire `find_creators` / `creator_search` chat CTA;
   "Tìm KOL" quick-action routes to `/app/kol`
4. **B.2.4** (0.5d) — design-audit pass against `kol.jsx` reference

---

## B.3 — `/channel` Phân Tích Kênh (~2.5 weeks)

### Exact design spec (from `channel.jsx`)

**Layout**: `maxWidth: 1280`, `padding: 24px 28px 80px`. Responsive at 900px
(hero 2-col → 1-col, bottom grid → 1-col).

**Back button**: `← Về Studio` btn-ghost, `marginBottom: 18`.

**Hero card** (`background: paper, border: 1px solid rule, borderRadius: 12,
padding: 28px 32px, gridTemplateColumns: 1fr 1fr, gap: 32, marginBottom: 28`):
- Left: kicker `HỒ SƠ KÊNH · {niche}` (mono 9.5px uc, ink-4) + avatar
  circle (64×64, accent bg, first letter, fontSize 22) + name (tight 38px) +
  handle·followers (mono 12px, ink-3) + italic bio (tight 18px, fontStyle
  italic, ink-2, maxWidth 460, lineHeight 1.4) + chips row: `Đăng
  {postingCadence}` (chip) + `Engagement {rate}` (chip-accent) +
  `{totalVideos} video` (chip).
- Right: 2×2 KPI grid (`border: 1px solid rule, borderRadius: 10, overflow:
  hidden`). Each cell `padding: 18, background: canvas`. Borders: right on
  col 0, bottom on rows 0-1. Four cells: `VIEW TRUNG BÌNH / {avgViews} /
  ↑ 12% MoM` | `HOOK CHỦ ĐẠO / "{topHook}" / 62% video dùng` | `ĐỘ DÀI TỐI
  ƯU / 42–58s / từ {n} video gần` | `THỜI GIAN POST / 7:30 sáng / reach
  +28%`. Label mono 9px uc ink-4 + value tight 22px + delta mono 10px
  pos-deep.

**Formula bar** (`SectionMini` kicker `CÔNG THỨC PHÁT HIỆN`, title
`"{name} Formula" — 4 bước lặp đi lặp lại`):
- `height: 80, borderRadius: 8, overflow: hidden, border: 1px solid ink`
- 4 segments as `flex: {pct}` divs. Colors: `[accent, ink-2, ink-3,
  accent-deep]`. Each: `padding: 12, color: white, flex-direction: column,
  justifyContent: space-between`. Top: `{step} · {pct}%` (mono 10px uc,
  opacity 0.9). Bottom: `{detail}` (11px, lineHeight 1.3).
- Data fixture: `formula: [{step: 'Hook', detail: '0–3s: câu hỏi POV',
  pct: 22}, {step: 'Setup', detail: '3–8s: vấn đề cụ thể', pct: 18},
  {step: 'Body', detail: '8–35s: 3 ý chính, b-roll dày', pct: 45},
  {step: 'Payoff', detail: '35–45s: tóm tắt + CTA', pct: 15}]`

**Two-col grid** (`1fr 1fr`, gap 32, `className="ch-grid"`):
- Left (`SectionMini` kicker `VIDEO ĐỈNH`, title `Top 4 video gây tiếng
  vang`): 2-col video grid (`1fr 1fr`, gap 12). Each tile: `9/16` aspect
  div with colored bg + views overlay (mono 10px, white, bottom-left) +
  title below (11px, ink-3). Clicking routes to `/video`.
- Right (`SectionMini` kicker `ĐIỀU NÊN COPY`, title `Học gì từ kênh này`):
  4 lesson cards (`className="card"`, `padding: 14, gap: 12`). Each: number
  `mono 12px accent-deep fontWeight 600` + title `13px fontWeight 500` +
  body `12px ink-3`. Below: full-width `[script] Tạo kịch bản theo công
  thức này` btn-accent → routes to `/script` with formula pre-loaded.

### Data model

**`CHANNEL_DETAIL` fields mapped to API**:
`handle, name, bio, followers, totalVideos, avgViews, engagement,
postingCadence ({day} · {time}), topHook, formula [{step, detail, pct}]`

**New table: `channel_formulas`**:
```sql
CREATE TABLE channel_formulas (
  handle         TEXT PRIMARY KEY,
  niche_id       INTEGER REFERENCES niche_taxonomy(id),
  formula        JSONB NOT NULL,    -- [{step, detail, pct}] × 4
  lessons        JSONB NOT NULL DEFAULT '[]',  -- [{title, body}] × 4
  top_hook       TEXT,
  optimal_length TEXT,             -- e.g. "42–58s"
  posting_time   TEXT,             -- e.g. "7:30 sáng"
  posting_cadence TEXT,            -- e.g. "Hàng ngày"
  avg_views      BIGINT,
  engagement_pct NUMERIC(10,4),
  total_videos   INTEGER,
  computed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```
TTL: recompute only if `computed_at < now() - interval '7 days'`.

**Claim-tier gate for formula generation**: a `channel_formulas` row is only
computed when the creator has **≥ 10 videos** in `video_corpus` for the
requested `niche_id` (reuses `CLAIM_TIERS["pattern_spread"] = 10` from
`claim_tiers.py`). Fewer than 10 videos → `/channel/analyze` returns
`{"formula": null, "formula_gate": "thin_corpus"}`. Frontend renders the
Formula bar as a "Chưa đủ video để dựng công thức" empty state (mono 11px,
ink-4, centered inside the `height: 80` bar container) instead of a
half-computed bar.

**Posting cadence**: aggregate `created_at` distribution across creator's
`video_corpus` rows → best weekday + hour bucket. (Note: uses `created_at`
= ingest time, not TikTok `posted_at` — acceptable 24h lag.)

### Endpoints

- `GET /channel/analyze?handle=X` — reads `channel_formulas` cache. If
  stale or missing AND creator has ≥ 10 corpus videos: fetch top 20 videos
  → Gemini call (formula + lessons, pydantic schema) → compute KPIs →
  upsert `channel_formulas` → return. If < 10 videos → return thin_corpus
  gate response. Auth-required, credit deducted via `decrement_credit()` RPC
  (only on cache miss that triggers Gemini, not on cached reads or gate hits).

### Frontend: `/app/channel` route

- Route: `src/routes/_app/channel/route.tsx?handle=X`
- New primitive: `FormulaBar` — `height: 80` flex bar, 4 color-keyed
  segments, text inside each. Exact colors: `[accent, ink-2, ink-3,
  accent-deep]`.
- Reuses: `KpiGrid` (from B.1), `SectionMini`, video tile grid shape from
  Win mode.
- Navigation: KOL detail card "Phân tích kênh đầy đủ" → `/channel?handle=X`.

### Milestones

1. **B.3.1** (3d) — `channel_formulas` migration + claim-tier gate (≥ 10
   videos check) + Gemini schema + formula aggregation + `/channel/analyze`
   endpoint + tests
2. **B.3.2** (2d) — posting cadence computation + KPI aggregation from
   `video_corpus` + cache TTL logic
3. **B.3.3** (4d) — `/app/channel` full screen + `FormulaBar` primitive +
   thin-corpus empty state + data wiring
4. **B.3.4** (2d) — retire `competitor_profile` + `own_channel` chat CTAs;
   "Soi Kênh" quick-action routes to `/channel`
5. **B.3.5** (1d) — design-audit pass against `channel.jsx` reference

---

## B.4 — `/script` Xưởng Viết (~3 weeks)

### Exact design spec (from `script.jsx`)

**Layout**: `maxWidth: 1380`, `padding: 24px 28px 80px`. Three-column
`300px 1fr 300px`, responsive: ≤1240px → `280px 1fr` (right col wraps
below, flex-row overflow-x auto); ≤880px → single col.

**Header** (`paddingBottom: 16, borderBottom: 2px solid ink`):
- Left: kicker `XƯỞNG VIẾT · KỊCH BẢN SỐ {n}` (mono 10px uc, accent,
  fontWeight 600) + H1 `{topic}` (serif, `clamp(26px, 3vw, 36px)`,
  fontWeight 500, letterSpacing -0.02em).
- Right: `[copy] Copy` + `[download] PDF` (btn-ghost) +
  `[film] Chế độ quay` (btn).

**LEFT col** — 5 `CardInput` panels (border 1px rule, background paper,
padding 14):

1. `CHỦ ĐỀ`: textarea (serif font, 2 rows, transparent bg, 16px).
2. `MẪU HOOK · XẾP THEO RETENTION`: list of 4 hook buttons. Each:
   `padding: 8px 10px, borderRadius: 4`. Active: `background: ink, color:
   canvas, border: 1px solid ink`. Inactive: `background: canvas-2, color:
   ink-2, border: 1px solid rule`. Left: `"{pattern}"` (tight 13px). Right:
   `▲{delta}` (mono 10px, rgb(0,159,250)).
3. `HOOK RƠI LÚC {n}s`: range slider (min 400, max 3000, step 100) +
   `HookTimingMeter` (14px tall bar with sweet-spot band 0.8–1.4s marked
   in `rgba(0,159,250,0.22)` + dashed borders + cursor line in blue/accent).
   Below: text note — winners land at `0.8–1.4s`, after 1.4s retention
   drops 38%.
4. `ĐỘ DÀI · {n}s`: range slider (15–90) + `DurationInsight` — 4 text
   states by range: <22s ink-4 / 22–40s blue "★ Vùng vàng" /
   41–60s ink-4 / >60s accent "⚠".
5. `GIỌNG ĐIỆU`: chip row — `Hài / Chuyên gia / Tâm sự / Năng lượng /
   Mỉa mai`. Active chip: `chip-accent`. Below panels: `[sparkle] Tạo lại
   với AI` btn-accent (full-width) + `CitationTag` (dashed border, mono
   10px, "✻ Gợi ý dựa trên {n} video trong ngách {niche} · 7 ngày gần nhất").

**MIDDLE col** — `PacingRibbon` + shot rows + `ForecastBar`:

**`PacingRibbon`** (`border: 1px solid ink, background: paper, padding: 14`):
- Header: kicker `NHỊP ĐỘ · PACING RIBBON` + subtext (13px ink-2) +
  legend dots (yours=accent, niche=blue).
- Shot bar group: `height: 38`, gap 2. Each shot button: `flex: {width}`.
  Two sub-bars per shot: "yours" at left 20% (width 25%, height proportional
  to duration, accent or accent if slow) + "niche" at left 55% (width 25%,
  height proportional, blue 50% opacity). Slow = `duration > winnerAvg × 1.2`.
  Active shot: `background: accent-soft`. Shot number top-left (mono 9px).
- Timeline: `height: 16`, timestamps at each shot boundary (mono 9px ink-4).

**`ShotRow`** (6 rows): `grid-template-columns: 90px 100px 1fr 1fr`.
Border: `1px solid rule` (inactive) / `1px solid ink` (active).
Box-shadow on active: `3px 3px 0 var(--ink)`.
- Col 1 (time): `padding: 12`. Active: `background: ink, color: canvas`.
  Shot 1 inactive: `background: accent, color: white`. Others: `canvas-2,
  ink-2`. Shows `SHOT 0{n}` (mono 10px) + `{t0}–{t1}s` (mono 12px
  fontWeight 600) + duration (mono 9px).
- Col 2 (camera viz): color `[#3A4A5C, #2A3A5C, #3D2F4A, #4A2A3D, #2A4A5C,
  #5C2A3A][idx%6]` bg. Camera label white mono 11px, bottom-left.
- Col 3 (voice, `borderRight: 1px solid rule`): kicker `LỜI THOẠI` + quoted
  voice text (serif 13.5px, lineHeight 1.35).
- Col 4 (visual): kicker `HÌNH ẢNH · {overlay}` + description (12px ink-3)
  + pacing badge: slow → accent-soft bg, accent-deep text, "⚠ {n}s · ngách
  {winner}s"; ok → blue 12% bg, blue text, "✓ {n}s · ngách {winner}s".

**`ForecastBar`** (`marginTop: 16, padding: 16px 20px, background: ink,
color: canvas`): kicker `DỰ KIẾN HIỆU SUẤT` (mono 9.5px uc, opacity 0.5) +
prediction (serif 28px fontWeight 500 for view count + inline retention % in
blue + hook score in accent/10) + `Lưu vào lịch quay →` btn-accent.
Formula: `hookDelay ≤ 1400 → hookScore 8.4`, ≤2000 → 6.2, else 4.1.
`goodLen = duration ≥ 22 && ≤ 40`. View: `goodLen ? 62K : 34K`. Retention:
`goodLen ? 72% : 54%`.

**RIGHT col** — `SceneIntelligence` for active shot (4 stacked cards):

1. **Tip card** (`border: 1px solid ink, background: ink, color: canvas,
   padding: 16`): kicker `SHOT 0{n} · PHÂN TÍCH CẤU TRÚC` (mono 10px uc,
   opacity 0.6) + tip text (serif 18px, fontWeight 500, lineHeight 1.25).
2. **Shot length diagnostic** (`border: 1px solid rule, background: paper,
   padding: 14`): kicker `ĐỘ DÀI SHOT` + big duration (serif 28px fontWeight
   500) + status (mono 11px — slow: accent `▲ dài hơn {n}s` / ok: blue
   `✓ đúng nhịp ngách`) + `MiniBarCompare` (3 bars: Của bạn/Ngách TB/Winner)
   + legend text (11px ink-4).
3. **Text overlay library** (`border: 1px solid rule, background: paper,
   padding: 14`): kicker `TEXT OVERLAY · THƯ VIỆN` + description (12px ink-3)
   citing winner style. If `overlay !== 'NONE'`: 3 chip buttons from
   `OVERLAY_SAMPLES[overlay]` — each `chip`, `padding: 7px 10px, fontSize: 11,
   justifyContent: space-between` + plus icon right.
4. **Reference clips** (`border: 1px solid rule, background: paper,
   padding: 14`): kicker `CLIP THAM KHẢO` + 3 clip thumbnails inline
   `overflowX: auto`. Each: `width: 80, aspectRatio: 9/13`, bg color per
   index, handle + label + duration badge. Clicking routes to `/video`.
   Below: "3 scene cùng mục đích từ video thắng tuần này."

### Data model

**Two independent backend concerns:**

**1 — Pacing ribbon** (pre-shoot, deterministic from draft times):
The user types shot time markers (`t0, t1` per shot). The ribbon renders
"your draft tempo vs niche-winner tempo" — no API call needed. All data
is derived client-side from the shot list + niche benchmark loaded once:
- `winnerAvg` per scene type → from `scene_intelligence` (loaded at
  screen open, cached 6h)
- `corpusAvg` per scene type → same source
- Slow flag: `(t1 − t0) > winnerAvg × 1.2` — computed in the component

**2 — Scene intelligence panel** (on-hover reference, separate concern):
Activated when user clicks a shot row. Fetches (or reads from cache) the
`scene_intelligence` row for `(niche_id, scene_type_of_active_shot)`.
Returns: tip, shot-length diagnostic, overlay library, 3 reference clips.
This is a read-only reference panel — it does not affect the draft or pacing
ribbon. No write path.

**Shot state** (local only, no DB in v1):
- `t0, t1` — user input
- `cam, voice, viz, overlay` — user-authored
- `corpusAvg, winnerAvg` — from `scene_intelligence` loaded at screen open
- `overlayWinner` — from `scene_intelligence.winner_overlay_style`
- `tip` — from `scene_intelligence.tip`
- `OVERLAY_SAMPLES[overlay]` — from `scene_intelligence.overlay_samples` JSONB

**New table: `scene_intelligence`**:
```sql
CREATE TABLE scene_intelligence (
  niche_id            INTEGER NOT NULL REFERENCES niche_taxonomy(id),
  scene_type          TEXT NOT NULL,  -- 'HOOK'|'PROMISE'|'BODY'|'CTA' etc.
  corpus_avg_duration NUMERIC(6,2),
  winner_avg_duration NUMERIC(6,2),
  winner_overlay_style TEXT,
  overlay_samples     JSONB NOT NULL DEFAULT '[]',  -- [string] × 5
  tip                 TEXT,
  reference_video_ids TEXT[] NOT NULL DEFAULT '{}', -- top 3 video_ids
  sample_size         INTEGER NOT NULL DEFAULT 0,
  computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (niche_id, scene_type)
);
```
Nightly batch job refreshes niches with `sample_size ≥ 30` winners per scene type.

**Hook patterns** (from `hook_effectiveness` table, already exists):
`hook_type, avg_views, avg_engagement_rate, sample_size, trend_direction`.
Mapped to `HOOKS` fixture: `{pattern, delta, uses, avg}`.

**`OVERLAY_SAMPLES`** lookup — materialized from `scene_intelligence
.overlay_samples` by scene_type. Client fetches once per niche, caches.

### Endpoints

- `POST /script/generate` — body `{hook, hook_delay_ms, duration, tone,
  niche_id}`. Returns shot list + pacing data + forecast. Auth-required,
  credit deducted.
- `GET /script/scene-intelligence?niche_id=X` — all scene types for the
  niche. Cached; refreshed nightly.
- `GET /script/hook-patterns?niche_id=X` — from `hook_effectiveness`,
  sorted by `avg_views` desc.

### Frontend: `/app/script` route

- Route: `src/routes/_app/script/route.tsx`
- URL param: `?hook=...&niche_id=...` for morning-ritual prefill and
  channel-formula prefill.
- New primitives: `PacingRibbon`, `HookTimingMeter`, `DurationInsight`,
  `ShotRow`, `SceneIntelligence`, `ForecastBar`, `MiniBarCompare`,
  `CitationTag`, `CardInput`. All defined in `script.jsx` — implement 1:1.
- Overlay samples and scene intelligence: single TanStack Query per niche,
  `staleTime: 1000 * 60 * 60 * 6` (6h).
- Shot rows: local state only (`useState`). No DB persistence in v1.

### Milestones

1. **B.4.1** (3d) — `scene_intelligence` migration + nightly batch job +
   aggregation from `video_corpus.analysis_json.scenes[]` + tests
2. **B.4.2** (2d) — `/script/scene-intelligence` endpoint + forecast formula
   + `/script/hook-patterns` endpoint
3. **B.4.3** (5d) — 3-col layout + pacing ribbon (deterministic, no API) +
   shot row editor + scene intelligence panel (on-hover, reads cached
   `scene_intelligence`) + overlay library
4. **B.4.4** (2d) — morning-ritual → `/script` prefill (hook + niche)
5. **B.4.5** (2d) — `/channel` → `/script` formula prefill; retire
   `shot_list` chat CTA
6. **B.4.6** (1d) — design-audit pass against `script.jsx` reference

---

## Cross-cutting

### Things retired when Phase B lands

`/app/chat` quick-action CTAs for: `video_diagnosis`, `creator_search`,
`competitor_profile`, `own_channel`, `shot_list`. Chat stays for `follow_up`
/ general Q&A only.

### Deliberately deferred to Phase C

- `/answer` — threaded research session with classifier-driven turns,
  idea directions, style guide, stop-doing list
- `/history` full restyle (currently on purple tokens)
- `/chat` retirement (stays as generic fallback)
- Landing page refit

### Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| EnsembleData has no retention curve | Medium | Resolved in B.0.1. Fallback: modeled sigmoid, labeled `ĐƯỜNG ƯỚC TÍNH` in UI. |
| Scene intelligence sparse (<30 winners/scene in small niches) | High | Claim-tier gate: hide `SceneIntelligence` right rail if `sample_size < 30`. Show "corpus too thin" empty state. |
| Channel formula thin corpus (<10 creator videos) | High | Resolved via claim-tier gate in B.3.1. Formula bar shows empty state, no Gemini call, no credit deducted. |
| Channel formula Gemini cost at scale | Medium | `computed_at` TTL gate (7 days). Nightly batch for pinned creators only. |
| B.4 shot state not persisted | Low | Acceptable for v1. Add `draft_scripts` table in Phase C. |
| `api-types.ts` drift between screens | Low | Single file created B.1.1 day 1. All four screens share it. |
| B.1 checkpoint gate fails | Medium | Pause B.2, revisit entry-point design. B.0.3 simplified pin model reduces this risk. |

### Chat middle-state UX

While B.1–B.4 are in flight, quick-action cards pointing to unreleased screens
show a mono `TUẦN X` countdown chip instead of "Sắp có". Drop when the screen
ships.

| Quick-action | Chip shows while | Drop when |
|---|---|---|
| Soi Video | B.1 in progress | B.1.6 merges |
| Tìm KOL / Creator | B.2 in progress | B.2.3 merges |
| Soi Kênh Đối Thủ | B.3 in progress | B.3.4 merges |
| Lên Kịch Bản Quay | B.4 in progress | B.4.5 merges |

Add optional `countdown?: string` to the `QUICK_ACTIONS` config. Home screen
renders it as a `mono uc` chip in `ink-4` at top-right of the card.

### Measurement

One event per screen. Log to `anonymous_usage` (existing table) via a
`logUsage(action, metadata)` wrapper — fire-and-forget, no await in UI path.

| Screen | Gate metric | Event | Instrument |
|---|---|---|---|
| `/video` | ≥ 30% flop sessions → "Áp vào kịch bản" click | `flop_cta_click` | row count vs `video_screen_load` |
| `/kol` | ≥ 20% sessions → pin or channel click | `kol_pin` / `kol_to_channel` | row count |
| `/channel` | ≥ 25% sessions → "Tạo kịch bản" click | `channel_to_script` | row count |
| `/script` | ≥ 15% scripts → "Lưu vào lịch quay" click | `script_save` | row count |

No new instrumentation dependency — `anonymous_usage` table exists.

### Testing strategy

Per screen: pytest ≥ 80% branch coverage on new backend aggregators, vitest
smoke for the route component, shell smoke in `artifacts/qa-reports/`.

| Screen | pytest target | vitest smoke | shell smoke |
|---|---|---|---|
| `/video` | `video_structural.py` — all four functions | Win + Flop modes render | `smoke-video.sh` |
| `/kol` | match score, `toggle_reference_channel` | pinned + discover tabs render | `smoke-kol.sh` |
| `/channel` | formula aggregation, thin-corpus gate | full card + empty FormulaBar | `smoke-channel.sh` |
| `/script` | `scene_intelligence` batch aggregator, slow flag | 3-col layout, PacingRibbon, ForecastBar | `smoke-script.sh` |

Shell smokes follow the existing pattern in `artifacts/qa-reports/` — curl
the Cloud Run endpoint, assert HTTP 200 and key JSON fields present.

### Revised timeline

| Screen | Previous | Revised | Reason |
|---|---|---|---|
| B.0 spike | — | **1w** | Retention curve + match score + pins data-model |
| B.1 `/video` | 2.5w | **3w** | Design-audit milestone + checkpoint period |
| B.2 `/kol` | 1w | **1.5w** | Design-audit + simplified pin model |
| B.3 `/channel` | 2w | **2.5w** | Claim-tier gate + design-audit |
| B.4 `/script` | 2.5w | **3w** | Pacing/intelligence split + design-audit |
| Buffer | — | **1w** | Design-audit round-trips per screen |
| **Total** | **~8w** | **~12w** | |
