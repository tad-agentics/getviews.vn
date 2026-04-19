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

> **Design source**: `artifacts/uiux-reference/screens/video.jsx`
> + `artifacts/uiux-reference/styles.css` (tokens)
> + `artifacts/uiux-reference/data.js` (fixture shapes that drive the API contract)
>
> Every px / kicker / token must trace back to one of these files.

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

### Fixture mapping (design → backend)

Source fixture: `VIDEOS[10]` + inline literals in `video.jsx`.
**The fixtures are the contract; the backend serves them. Not the other way around.**

| Design field (fixture / JSX literal) | `/video/analyze` response field | Source |
|---|---|---|
| `v.title` | `meta.title` | `video_corpus.title` |
| `v.creator` | `meta.creator_handle` | `video_corpus.creator_handle` |
| `v.dur` | `meta.duration_sec` (formatted client-side "M:SS") | `analysis_json.duration_seconds` |
| `v.views` ("234K") | `meta.views` (raw int, formatted client-side) | `video_corpus.views` |
| `v.bg` | `meta.thumbnail_url` (bg color fallback derived client-side from `niche_id` color map) | `video_corpus.thumbnail_url` |
| `v.breakout` badge | `meta.is_breakout` bool (`breakout_multiplier ≥ 3`) | computed from `video_corpus.breakout_multiplier` |
| "Đăng 18.04 · 234K view · 6.8K save · 4.2K share" | `meta.date_posted`, `meta.views`, `meta.saves`, `meta.shares` | `video_corpus.*` |
| `{ label:'VIEW', value:'234K', delta:'12× kênh' }` | `kpis[0]: {label, value, delta}` — delta computed as `views / niche_avg_views` | `video_corpus.views` + `niche_intelligence.avg_views` |
| `{ label:'GIỮ CHÂN', value:'78%', delta:'top 5%' }` | `kpis[1]: {label, value, delta}` — retention % + percentile rank | `retention_curve` last point + niche distribution |
| `{ label:'SAVE RATE', value:'2.9%', delta:'rất cao' }` | `kpis[2]: {label, value, delta}` — `saves/views`, delta label is client-side tier ('rất cao' if > 2%) | `video_corpus.saves / views` |
| `{ label:'SHARE', value:'4.2K', delta:'lan ra Threads' }` | `kpis[3]: {label, value, delta}` — `meta.shares`; delta text is **LLM-generated** bounded string, cached | `video_corpus.shares` + Gemini |
| Timeline `segs[]` `{name, pct, color}` (8 segments) | `segments[]: {name, pct, color_key}` — color_key maps to CSS var client-side | `video_diagnostics.segments` ← `decompose_segments(analysis_json.scenes[])` |
| Hook phase cards `{t, label, body}` × 3 | `hook_phases[]: {t_range, label, body}` | `video_diagnostics.hook_phases` ← `extract_hook_phases` (deterministic `t_range`/`label` + bounded LLM `body`) |
| Lessons `[title, body]` × 3 | `lessons[]: {title, body}` | `video_diagnostics.lessons` ← Gemini win-mode, cached |
| Analysis headline ("Tại sao … lại nổ?") | `analysis_headline` | `video_diagnostics.analysis_headline` ← Gemini |
| Analysis subtext (15px ink-3) | `analysis_subtext` | `video_diagnostics.analysis_subtext` ← Gemini |
| Retention curve SVG paths | `retention_curve[]: {t, pct}` × 20 | `video_diagnostics.retention_curve` ← B.0.1 decision |
| Niche benchmark dashed curve | `niche_benchmark_curve[]: {t, pct}` × 20 | `video_diagnostics.niche_benchmark_curve` ← `niche_intelligence` |
| "Ngách Tech TB: 42K · 58% ret · 3.4% CTR" | `niche_meta: {avg_views, avg_retention, avg_ctr, sample_size}` | `niche_intelligence` |
| Flop issues `{sev, t, end, title, detail, fix}` × N | `flop_issues[]: {sev, t, end, title, detail, fix}` | `video_diagnostics.flop_issues` ← Gemini pydantic schema |
| Flop summary headline + projected views ("~34K") | `analysis_headline` + `projected_views` | `video_diagnostics.analysis_headline` ← Gemini; `projected_views` computed deterministically from fix count × niche median |
| "BÁO CÁO PHÂN TÍCH · TECH" kicker niche label | `meta.niche_label` | `niche_taxonomy.label` joined via `video_corpus.niche_id` |

**Client-side only (no backend field needed):**
- `v.bg` color fallback when `thumbnail_url` is null → `NICHE_COLOR_MAP[niche_id]`
- "M:SS" duration format from `meta.duration_sec`
- `12× kênh` delta label formatted from `meta.views / niche_meta.avg_views`
- `top 5%` percentile label derived from niche retention distribution (front-end bucket)
- `rất cao` / tier labels for save rate (static threshold table, client-side)
- Segment `color` CSS variable resolved from `color_key` via a static map in `Timeline.tsx`
- `BREAKOUT` badge visibility from `meta.is_breakout`

**TODO flagged for spike (B.0.1):**
- `retention_curve[]` exact shape: real API vs modeled sigmoid. Decision record determines field population strategy. UI label (`ĐƯỜNG GIỮ CHÂN` vs `ĐƯỜNG ƯỚC TÍNH`) toggles based on `meta.retention_source: "real"|"modeled"`.

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
- `extract_hook_phases(analysis_json)` → 3 `{t_range, label, body}` cards:
  `t_range` + `label` from structured `hook_analysis` + `scenes[0]`
  (deterministic); **`body`** is the only LLM-filled slot here (bounded
  Vietnamese blurbs, same `video_diagnostics` write path as win copy).
- `model_retention_curve(views, breakout_multiplier, niche_benchmark)` →
  20-point curve. Parameterized sigmoid anchored to known drop-off zones.
- `diagnose_flop(video_data, niche_benchmark)` → Gemini call with pydantic
  schema. Only fires when flop threshold met.
- `generate_win_analysis(video_data, corpus_context)` → Gemini call for
  **analysis headline + subtext + 3 lesson rows only** — not hook phase
  cards (those are `extract_hook_phases`). Cached in `video_diagnostics`.

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
- New primitives needed (names align with `### New design primitives`):
  - `RetentionCurve` — two curves + annotations; `viewBox="0 0 400 80"`,
    height 80px.
  - `Timeline` — 8-segment flex bar, `color_key` → CSS var, timestamps below.
  - `HookPhaseCard` — win mode 3-card hook grid (composed from `Card`).
  - `IssueCard` — flop mode issue row, grid `80px 1fr auto`, severity border.
  - `KpiGrid` — `repeat(auto-fit, minmax(140px, 1fr))`, shared with
    later screens.
  - `SectionMini` — already in `video.jsx`: kicker + title +
    `borderBottom: 1px solid ink`. Implement once, export from
    `src/components/SectionMini.tsx`.
- Reuses: `Btn`, `Card`, existing icon set.

### New design primitives

New files under `src/components/v2/` — build these during the
backend-finishing overlap (B.1.1–B.1.3) so B.1.4 frontend work is never
blocked on primitives.

| Component | Description | Source |
|---|---|---|
| `RetentionCurve` | SVG: `viewBox="0 0 400 80"`, rendered height 80px — area fill + polyline (video) + dashed overlay (niche benchmark), matching `video.jsx` `FlopDiagnostic`. | `video.jsx` `FlopDiagnostic` |
| `Timeline` | 8-segment horizontal flex bar, `color_key` → CSS var map, pct labels per segment, timestamp axis below. | `video.jsx` `WinAnalysis` |
| `HookPhaseCard` | 3-card grid (0–0.8s / 0.8–1.8s / 1.8–3s), each card: `t_range` kicker + label + body text. | `video.jsx` |
| `KpiGrid` | 2×2 grid, ink-filled or paper per design token. Shared with B.3. | `video.jsx` |

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
6. **B.1.6** ✅ (1d) — retire `video_diagnosis` chat CTA; "Soi video"
   quick-action routes to `/app/video` *(audit: `artifacts/qa-reports/phase-b-design-audit-video.md` §B.1.6)*.
7. **B.1.7** ✅ (1d) — **Design audit** — compare shipped `/app/video` against
   `video.jsx` section-by-section: primitives, tokens, kickers, spacing,
   copy, responsive behaviour (900px breakpoint). Produce
   `artifacts/qa-reports/phase-b-design-audit-video.md` with `must-fix /
   should-fix / consider` tiers. Ship all must-fix items before closing B.1.
   - **Token check**: zero raw hex codes in JSX; zero purple-era tokens
     (`--ink-soft`, `--purple`, `--border-active`, or any `--gv-purple-*`)
     in new screen files. Every color reference must resolve to a
     `var(--gv-*)` token. Grep new files for `#[0-9a-fA-F]{3,6}` and the
     banned token list as part of the audit — any hit is a `must-fix`.
   **Non-negotiable: B.1 cannot close without a green audit report.**  
   *Shipped 2026-04-19: report green; must-fix parity items in same commit (padding, flop high border, win BREAKOUT pill).*

### B.1 checkpoint (measure for 2 weeks post-ship)

Gate metric: **≥ 30% of `/app/video` Flop-mode sessions end with an
"Áp vào kịch bản" CTA click** (operationalized as `flop_cta_click` /
`video_screen_load` where `metadata.mode = 'flop'` in `usage_events`; see
`artifacts/sql/b1-checkpoint-flop-cta.sql`).

Narrative cross-check (optional): a `chat_sessions` row with
`intent_type = 'shot_list'` opened within **10 min** of the same user’s flop
`video_screen_load` — second query in the same SQL file.

Instrument: SPA `logUsage()` → **`usage_events`** (`video_screen_load` on
analysis render, `flop_cta_click` on flop handoff CTAs). Migration:
`supabase/migrations/20260419120000_usage_events_b1_checkpoint.sql`.

If gate fails after 2 weeks: pause B.2, revisit whether the deterministic-slot
thesis holds or whether users need a different entry point.

---

## B.2 — `/kol` Kênh Tham Chiếu (~1.5 weeks)

> **Design source**: `artifacts/uiux-reference/screens/kol.jsx`
> + `artifacts/uiux-reference/styles.css` (tokens)
> + `artifacts/uiux-reference/data.js` (fixture shapes that drive the API contract)
>
> Every px / kicker / token must trace back to one of these files.

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

### Fixture mapping (design → backend)

Source fixture: `CREATORS[]` in `data.js` + inline literals in `kol.jsx`.
**The fixtures are the contract; the backend serves them. Not the other way around.**

| Design field (fixture / JSX literal) | `/kol/browse` response field | Source |
|---|---|---|
| `c.handle` | `handle` | `creator_velocity.handle` / `starter_creators.handle` |
| `c.name` | `name` | `creator_velocity.name` / `starter_creators.name` |
| `c.niche` | `niche_label` | `niche_taxonomy.label` joined via `niche_id` |
| `c.followers` ("412K") | `followers` (raw int, formatted client-side) | `creator_velocity.followers` |
| `c.avg` ("89K") | `avg_views` (raw int, formatted client-side) | `creator_velocity.avg_views` |
| `c.growth` ("+12%") | `growth_30d_pct` (numeric, formatted client-side with sign) | `creator_velocity.growth_30d_pct` |
| `c.match` (94) | `match_score` (0–100 int) | computed per B.0.2 formula, cached per `(user_id, handle)` |
| `c.tone` ("Giải thích — chậm, rõ") | `tone` | `starter_creators.tone` / `creator_velocity.tone` |
| `# 01 02 …` row index | sequence number — client-side from array index | n/a |
| Avatar circle letter + color | first letter of `name`; color from `AVATAR_COLOR_CYCLE[idx % 6]` | client-side |
| `GHIM` badge (when `isPinned && tab === 'discover'`) | `is_pinned: bool` — derived client-side from `profiles.reference_channel_handles.includes(handle)` | `profiles.reference_channel_handles` loaded once at screen open |
| Detail card stats 2×2: NGÁCH / FOLLOW / VIEW TB / TĂNG 30D | same fields as table row | same sources |
| `ĐỘ KHỚP NGÁCH BẠN {match}/100` | `match_score` | computed per B.0.2 |
| Match score description (11px ink-3) | `match_description` — **LLM-generated** 1-sentence string, cached per `(user_id, handle)` in B.2 spike if time allows; otherwise static template client-side | computed or static |
| Filter chip options (niche / follower range / region / growth) | filter params passed as query string to `/kol/browse` | `niche_taxonomy`, hardcoded ranges |
| `{count}` badge in tab toggle | count of pinned handles / count of discover results | `profiles.reference_channel_handles.length` / query total |

**Client-side only (no backend field needed):**
- Avatar color from `AVATAR_COLOR_CYCLE[idx % 6]` static array
- `#01 02 …` row index from array position
- `GHIM` badge visibility: `profiles.reference_channel_handles` fetched once, set compared client-side
- `{match}/100` typography split (tight 36px + 16px ink-4 "/100") — formatting only
- Tab count badges formatted from response metadata

**TODO flagged for spike:**
- `match_description` — decide static template vs Gemini in B.2.1. If Gemini: bounded to 1 sentence, cached per `(user_id, handle)`, no credit deducted.

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

### New design primitives

New files under `src/components/v2/` — build during B.2.1 backend work so
the B.2.2 frontend milestone is unblocked.

| Component | Description | Source |
|---|---|---|
| `FilterChipRow` | Horizontally scrollable pill row: `LỌC THEO` label (mono 9px uc, ink-4) + `Chip` / `chip-accent` pills. Wraps existing `Chip`. | `kol.jsx` filter ribbon |
| `SortableTable` | `grid-template-columns: 40px 2fr 100px 100px 100px 80px`, sortable column headers (mono 9px uc, ink-4), active row `background: paper`. | `kol.jsx` left column |
| `StickyDetailCard` | `position: sticky, top: 86px`, 2×2 stats grid (`background: canvas-2, borderRadius: 8`), match score display, 3-CTA column. | `kol.jsx` right column |
| `MatchScoreBar` | Progress bar `height: 4, borderRadius: 999, background: rule`, fill `width: {match}%, background: accent`, score label mono 10px. | `kol.jsx` MATCH column |

### Milestones

1. **B.2.1** (2d) — `toggle_reference_channel` RPC migration + match score
   computation + `/kol/browse` + `/kol/toggle-pin` endpoints + tests
2. **B.2.2** (4d) — `/app/kol` full screen: table + filter ribbon + sticky
   detail card + tab switching + toggle-pin mutation
3. **B.2.3** (1d) — retire `find_creators` / `creator_search` chat CTA;
   "Tìm KOL" quick-action routes to `/app/kol`
4. **B.2.4** (1d) — **Design audit** — compare shipped `/app/kol` against
   `kol.jsx` section-by-section: primitives, tokens, kickers, spacing, copy,
   responsive behaviour (1100px breakpoint). Produce
   `artifacts/qa-reports/phase-b-design-audit-kol.md` with `must-fix /
   should-fix / consider` tiers. Ship all must-fix items before closing B.2.
   - **Token check**: zero raw hex codes in JSX; zero purple-era tokens
     (`--ink-soft`, `--purple`, `--border-active`, or any `--gv-purple-*`)
     in new screen files. Every color reference must resolve to a
     `var(--gv-*)` token. Grep new files for `#[0-9a-fA-F]{3,6}` and the
     banned token list as part of the audit — any hit is a `must-fix`.
   **Non-negotiable: B.2 cannot close without a green audit report.**

---

## B.3 — `/channel` Phân Tích Kênh (~2.5 weeks)

> **Design source**: `artifacts/uiux-reference/screens/channel.jsx`
> + `artifacts/uiux-reference/styles.css` (tokens)
> + `artifacts/uiux-reference/data.js` (fixture shapes that drive the API contract)
>
> Every px / kicker / token must trace back to one of these files.

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

### Fixture mapping (design → backend)

Source fixture: `CHANNEL_DETAIL` in `data.js` + inline literals in `channel.jsx`.
**The fixtures are the contract; the backend serves them. Not the other way around.**

| Design field (fixture / JSX literal) | `/channel/analyze` response field | Source |
|---|---|---|
| `CHANNEL_DETAIL.handle` | `handle` | `channel_formulas.handle` |
| `CHANNEL_DETAIL.name` | `name` | `creator_velocity.name` / `starter_creators.name` |
| `CHANNEL_DETAIL.bio` | `bio` | `creator_velocity.bio` (if available) — **LLM-generated fallback** 1-sentence string, cached |
| `CHANNEL_DETAIL.followers` ("412K") | `followers` (raw int, formatted client-side) | `creator_velocity.followers` |
| `CHANNEL_DETAIL.totalVideos` (248) | `total_videos` | `channel_formulas.total_videos` ← count from `video_corpus` |
| `CHANNEL_DETAIL.avgViews` ("89K") | `avg_views` (raw int, formatted client-side) | `channel_formulas.avg_views` |
| `CHANNEL_DETAIL.engagement` ("6.4%") | `engagement_pct` (numeric, formatted client-side) | `channel_formulas.engagement_pct` |
| `CHANNEL_DETAIL.postingCadence` ("Hàng ngày · 7:30 sáng") | `posting_cadence` + `posting_time` (joined client-side with ` · `) | `channel_formulas.posting_cadence` + `.posting_time` |
| `CHANNEL_DETAIL.topHook` ("Khi bạn ___") | `top_hook` | `channel_formulas.top_hook` ← most frequent `hook_type` in creator's `video_corpus` |
| `CHANNEL_DETAIL.formula[{step, detail, pct}]` × 4 | `formula[]: {step, detail, pct}` | `channel_formulas.formula` JSONB ← Gemini pydantic schema |
| KPI cell "VIEW TRUNG BÌNH / {avgViews} / ↑ 12% MoM" | `kpis[0]: {label, value, delta}` — delta MoM computed from 30-day window | `channel_formulas.avg_views` + windowed aggregation |
| KPI cell "HOOK CHỦ ĐẠO / "{topHook}" / 62% video dùng" | `kpis[1]: {label, value, delta}` — pct computed as `count(top_hook) / total_videos` | `channel_formulas.top_hook` + `video_corpus` count |
| KPI cell "ĐỘ DÀI TỐI ƯU / 42–58s / từ {n} video gần" | `kpis[2]: {label, value, delta}` — `optimal_length` string + `sample_size` | `channel_formulas.optimal_length` + count |
| KPI cell "THỜI GIAN POST / 7:30 sáng / reach +28%" | `kpis[3]: {label, value, delta}` — posting_time + reach delta **computed deterministically** from engagement quartile vs off-peak baseline | `channel_formulas.posting_time` + engagement aggregation |
| Formula bar segments `{step, detail, pct}` × 4 | same as `formula[]` above — rendered as `flex: {pct}` | `channel_formulas.formula` |
| `formula_gate: "thin_corpus"` empty state | `formula_gate` field (`null` or `"thin_corpus"`) | `/channel/analyze` gating logic |
| Top 4 video tiles (bg color, views, title) | `top_videos[]: {video_id, title, views, bg_color, thumbnail_url}` | top 4 by views from `video_corpus` for this `handle` |
| 4 lesson cards `{number, title, body}` | `lessons[]: {title, body}` | `channel_formulas.lessons` JSONB ← Gemini |
| Hero kicker `HỒ SƠ KÊNH · {niche}` | `niche_label` | `niche_taxonomy.label` |
| Chips: `Đăng {postingCadence}` + `Engagement {rate}` + `{n} video` | derived client-side from `posting_cadence`, `engagement_pct`, `total_videos` | same fields above |

**Client-side only (no backend field needed):**
- Avatar circle first letter + accent bg — from `name[0]`
- "M:SS" duration format, follower/view "K" abbreviation — formatting
- Hero chip text assembled client-side from `posting_cadence` + `engagement_pct` + `total_videos`
- Formula bar `flex: {pct}` widths from `formula[].pct`; color map is static `[accent, ink-2, ink-3, accent-deep]`
- FormulaBar empty state shown when `formula_gate === "thin_corpus"`
- "← Về Studio" back button — router navigation, no data

**TODO flagged for spike (B.3.1):**
- `bio` field — confirm if `creator_velocity` stores bio; if not, decide: scrape-at-ingest or 1-sentence Gemini summary from top videos.
- KPI "reach +28%" for posting time — verify derivable from existing engagement data before committing to the delta string.

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

### New design primitives

New files under `src/components/v2/` — build during B.3.1–B.3.2 backend
overlap.

| Component | Description | Source |
|---|---|---|
| `FormulaBar` | `height: 80`, `border: 1px solid ink`, 4 flex segments (`flex: {pct}`), colors `[accent, ink-2, ink-3, accent-deep]`. Each segment: `padding: 12`, top `{step} · {pct}%` (mono 10px uc, opacity 0.9), bottom `{detail}` (11px). Empty state: "Chưa đủ video" mono 11px centered. | `channel.jsx` formula bar |
| `PostingHeatmap` | *(deferred from v1 scope but spec here for B.3 reference)* Day×hour grid derived from `video_corpus.created_at` distribution. Only implement if time allows; otherwise reuse chip display of `postingCadence` string. | `channel.jsx` |

Reuses from B.1: `KpiGrid`, `SectionMini`.

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
5. **B.3.5** (1d) — **Design audit** — compare shipped `/app/channel` against
   `channel.jsx` section-by-section: primitives, tokens, kickers, spacing,
   copy, responsive behaviour (900px breakpoint). Produce
   `artifacts/qa-reports/phase-b-design-audit-channel.md` with `must-fix /
   should-fix / consider` tiers. Ship all must-fix items before closing B.3.
   - **Token check**: zero raw hex codes in JSX; zero purple-era tokens
     (`--ink-soft`, `--purple`, `--border-active`, or any `--gv-purple-*`)
     in new screen files. Every color reference must resolve to a
     `var(--gv-*)` token. Grep new files for `#[0-9a-fA-F]{3,6}` and the
     banned token list as part of the audit — any hit is a `must-fix`.
   **Non-negotiable: B.3 cannot close without a green audit report.**

---

## B.4 — `/script` Xưởng Viết (~3 weeks)

> **Design source**: `artifacts/uiux-reference/screens/script.jsx`
> + `artifacts/uiux-reference/styles.css` (tokens)
> + `artifacts/uiux-reference/data.js` (fixture shapes that drive the API contract)
>
> Every px / kicker / token must trace back to one of these files.

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

### Fixture mapping (design → backend)

Source fixtures: `HOOKS[]` in `data.js` + inline literals in `script.jsx`.
**The fixtures are the contract; the backend serves them. Not the other way around.**

**Left panel inputs → `/script/generate` request body:**

| Design field (JSX literal) | Request body field | Notes |
|---|---|---|
| Topic textarea value | `topic` (string) | User-authored, no backend source |
| Selected hook button `{pattern}` | `hook` (string) | User-selected from `HOOKS[]` list |
| Hook delay slider value (ms) | `hook_delay_ms` (int, 400–3000) | User input |
| Duration slider value (s) | `duration` (int, 15–90) | User input |
| Selected tone chip | `tone` (string: 'Hài'|'Chuyên gia'|'Tâm sự'|'Năng lượng'|'Mỉa mai') | User input |
| `niche_id` | `niche_id` | From `profiles.primary_niche` loaded at screen open |

**`HOOKS[]` fixture → `/script/hook-patterns` response:**

| Design field | Response field | Source |
|---|---|---|
| `HOOKS[i].pattern` ("Khi bạn ___") | `hook_patterns[i].pattern` | `hook_effectiveness.hook_type` |
| `HOOKS[i].delta` ("+248%") | `hook_patterns[i].delta` (computed: `(avg_views / niche_avg) - 1`, formatted with sign) | `hook_effectiveness.avg_views` vs `niche_intelligence.avg_views` |
| `HOOKS[i].uses` (1240) | `hook_patterns[i].uses` | `hook_effectiveness.sample_size` |
| `HOOKS[i].avg` ("128K") | `hook_patterns[i].avg_views` (raw int, formatted client-side) | `hook_effectiveness.avg_views` |

**`CitationTag` ("✻ Gợi ý dựa trên {n} video…") → from hook-patterns metadata:**

| Design field | Response field | Source |
|---|---|---|
| `{n} video trong ngách {niche}` | `citation: {sample_size, niche_label, window_days}` | `hook_effectiveness.sample_size` + `niche_taxonomy.label` |

**`/script/generate` response → shot list (middle col):**

| Design field (JSX) | Response field | Source |
|---|---|---|
| `ShotRow` `{t0, t1}` per shot | `shots[i].t0`, `shots[i].t1` (seconds) | Gemini structured output via pydantic schema |
| `ShotRow` camera label | `shots[i].cam` (string) | Gemini |
| `ShotRow` voice text | `shots[i].voice` (string) | Gemini |
| `ShotRow` visual description | `shots[i].viz` (string) | Gemini |
| `ShotRow` overlay type | `shots[i].overlay` (string key: 'NONE'|'TEXT\_TITLE'|…) | Gemini |
| Pacing badge "⚠ {n}s · ngách {winner}s" / "✓" | `shots[i].corpus_avg`, `shots[i].winner_avg` — slow flag `(t1-t0) > winner_avg × 1.2` computed client-side | `scene_intelligence.corpus_avg_duration` + `.winner_avg_duration` loaded at screen open |

**`scene_intelligence` → right panel (SceneIntelligencePanel):**

| Design field | Response field | Source |
|---|---|---|
| Tip card text | `tip` | `scene_intelligence.tip` |
| Shot length diagnostic duration + status | `corpus_avg_duration`, `winner_avg_duration` | `scene_intelligence.*` |
| MiniBarCompare bars | `corpus_avg_duration`, `winner_avg_duration` + `(t1-t0)` from local shot state | `scene_intelligence.*` + client-side |
| OverlaySample chips × 3 | `overlay_samples[]` (string) | `scene_intelligence.overlay_samples` JSONB |
| Reference clips × 3 (thumbnail, handle, label, duration) | `reference_clips[]: {video_id, thumbnail_url, handle, label, duration_sec}` | `scene_intelligence.reference_video_ids` → joined to `video_corpus` |

**`ForecastBar` → deterministic formula, no backend call:**

| Design field | Derivation | Source |
|---|---|---|
| View forecast ("62K" / "34K") | `goodLen = duration ≥ 22 && ≤ 40; goodLen ? 62K : 34K` | Static formula from `script.jsx` — client-side only |
| Retention % ("72%" / "54%") | `goodLen ? 72% : 54%` | Static formula — client-side only |
| Hook score ("/10") | `hookDelay ≤ 1400 → 8.4; ≤ 2000 → 6.2; else 4.1` | Static formula — client-side only |

**Client-side only (no backend field needed):**
- `KỊCH BẢN SỐ {n}` header counter — incremented per session in `useState`
- `{topic}` H1 updated live from textarea
- Shot row `active` state — `useState` local
- `DurationInsight` tier labels (<22s / 22–40s / 41–60s / >60s) — static threshold table
- All forecast bar values — static formula as above
- Overlay chip `+` icon — opens text-insert flow, no API

**TODO flagged for spike (B.4.1):**
- `shots[].overlay` key mapping to `OVERLAY_SAMPLES[overlay]` — confirm enum values match between Gemini output and `scene_intelligence.overlay_samples` keys before building the lookup.
- `reference_clips` thumbnail availability — confirm `video_corpus.thumbnail_url` is populated for the top-3 reference videos before committing to the panel design.

### Endpoints

- `POST /script/generate` — body `{topic, hook, hook_delay_ms, duration,
  tone, niche_id}`. Returns shot list + pacing inputs (`shots[]` with
  `t0`/`t1`/`cam`/`voice`/`viz`/`overlay`); **ForecastBar numbers stay
  client-only** (see Fixture mapping). Auth-required, credit deducted.
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

### New design primitives

New files under `src/components/v2/` — build during B.4.1–B.4.2 backend
overlap so B.4.3 (the largest frontend milestone) is fully unblocked.

| Component | Description | Source |
|---|---|---|
| `PacingRibbon` | `border: 1px solid ink, background: paper, padding: 14`. Shot bar group `height: 38`. Two sub-bars per shot (yours at 20% left, niche at 55% left), `flex: {width}`. Slow shots: accent; ok: blue 50% opacity. Timeline row `height: 16`. | `script.jsx` middle col |
| `ShotRow` | `grid-template-columns: 90px 100px 1fr 1fr`. 4-col grid: time cell (active=`background: ink`), camera viz (color-keyed bg), voice text (serif 13.5px), visual + pacing badge. Active box-shadow `3px 3px 0 var(--ink)`. | `script.jsx` |
| `HookTimingMeter` | 14px tall bar, sweet-spot band 0.8–1.4s in `rgba(0,159,250,0.22)` with dashed borders, cursor line in accent. Sits below range slider. | `script.jsx` left col panel 3 |
| `MiniBarCompare` | 3 vertical bars (Của bạn / Ngách TB / Winner), fixed height, labeled below (mono 9px ink-4). | `script.jsx` right col card 2 |
| `OverlaySample` | Chip button `padding: 7px 10px, fontSize: 11`, text left + plus icon right. Rendered 3× from `OVERLAY_SAMPLES[overlay]`. | `script.jsx` right col card 3 |
| `SceneIntelligencePanel` | Stacked 4-card right column: tip card (ink bg), shot-length diagnostic + `MiniBarCompare`, overlay library + `OverlaySample` chips, reference clips `width: 80, aspectRatio: 9/13`. | `script.jsx` right col |
| `ForecastBar` | `background: ink, color: canvas, padding: 16px 20px`. Kicker + serif 28px view forecast + inline retention % (blue) + hook score (accent/10). | `script.jsx` middle col |

Reuses from B.1: `KpiGrid`. Reuses from B.2: `FilterChipRow` (chip row for tone picker).

### Milestones

1. **B.4.1** (3d) — `scene_intelligence` migration + nightly batch job +
   aggregation from `video_corpus.analysis_json.scenes[]` + tests
2. **B.4.2** (2d) — `/script/scene-intelligence` + `/script/hook-patterns`
   endpoints; document ForecastBar math in `api-types.ts` (client-only —
   no forecast API)
3. **B.4.3** (5d) — 3-col layout + pacing ribbon (deterministic, no API) +
   shot row editor + scene intelligence panel (on-hover, reads cached
   `scene_intelligence`) + overlay library
4. **B.4.4** (2d) — morning-ritual → `/script` prefill (hook + niche)
5. **B.4.5** (2d) — `/channel` → `/script` formula prefill; retire
   `shot_list` chat CTA
6. **B.4.6** (1d) — **Design audit** — compare shipped `/app/script` against
   `script.jsx` section-by-section: primitives, tokens, kickers, spacing,
   copy, responsive behaviour (1240px and 880px breakpoints). Produce
   `artifacts/qa-reports/phase-b-design-audit-script.md` with `must-fix /
   should-fix / consider` tiers. Ship all must-fix items before closing B.4.
   - **Token check**: zero raw hex codes in JSX; zero purple-era tokens
     (`--ink-soft`, `--purple`, `--border-active`, or any `--gv-purple-*`)
     in new screen files. Every color reference must resolve to a
     `var(--gv-*)` token. Grep new files for `#[0-9a-fA-F]{3,6}` and the
     banned token list as part of the audit — any hit is a `must-fix`.
   **Non-negotiable: B.4 cannot close without a green audit report.**

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
| Soi Video | — | B.1.6 ✅ (routes `/app/video`) |
| Tìm KOL / Creator | B.2 in progress | B.2.3 merges |
| Soi Kênh Đối Thủ | B.3 in progress | B.3.4 merges |
| Lên Kịch Bản Quay | B.4 in progress | B.4.5 merges |

Add optional `countdown?: string` to the `QUICK_ACTIONS` config. Home screen
renders it as a `mono uc` chip in `ink-4` at top-right of the card.

### Measurement

Product events: **`usage_events`** (auth users) via `src/lib/logUsage.ts` —
fire-and-forget `insert`, no `await` on the UI hot path. B.1 ships the table +
RLS + `/app/video` logging; later screens add their own `action` names.

| Screen | Gate metric | Event | Instrument |
|---|---|---|---|
| `/video` | ≥ 30% flop sessions → "Áp vào kịch bản" click | `flop_cta_click` | row count vs `video_screen_load` (`metadata.mode = flop`) |
| `/kol` | ≥ 20% sessions → pin or channel click | `kol_pin` / `kol_to_channel` | row count |
| `/channel` | ≥ 25% sessions → "Tạo kịch bản" click | `channel_to_script` | row count |
| `/script` | ≥ 15% scripts → "Lưu vào lịch quay" click | `script_save` | row count |

*Note:* `anonymous_usage` remains IP-scoped for the landing free Soi Kênh trial;
it is **not** used for in-app screen analytics.

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

**Responsive breakpoints (all four screens, non-negotiable).**
Every new screen must respect the reference stylesheet's breakpoints before
the design audit closes. QA at all four viewport widths:

| Breakpoint | Behaviour | Reference |
|---|---|---|
| ≤ 1100px | `.hide-narrow` elements hidden (e.g. live-data chip in KOL header) | `styles.css` `.hide-narrow` |
| ≤ 900px | Multi-column grids collapse to 1 column (video 2-col, channel hero, channel bottom grid) | `video.jsx`, `channel.jsx` |
| ≤ 640px | H1 `font-size` shrinks to 30px | `styles.css` |
| ≤ 560px | Big-number / `.bignum` font-size shrinks to 34px | `styles.css` |

Manual QA: resize browser to each width and verify against the reference JSX.
Any layout break at a listed breakpoint is a `must-fix` in the audit report.

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
