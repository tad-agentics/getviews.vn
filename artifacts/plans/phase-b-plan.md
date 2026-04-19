# Phase B — Deterministic analysis screens

Four screens that take the creator beyond the Home/morning-ritual loop into
the per-video, per-channel, per-KOL, per-script workflows. Every screen is
deterministic-first: backend emits structured fields, frontend slots them
into a fixed layout, LLM is confined to bounded text.

**Scope source of truth**: `artifacts/uiux-reference/screens/` (`video.jsx`,
`channel.jsx`, `kol.jsx`, `script.jsx`) + `data.js` fixtures for
`CHANNEL_DETAIL`, `VIDEOS`, `CREATORS`, `HOOKS`.

## Guiding principles

- **One screen at a time.** Each sub-phase lands an atomic PR with its own
  backend aggregations + migration + tests + docs. Partial screens don't
  ship.
- **Claim tiers gate visibility, not disclaim inline.** A thin-corpus
  niche renders fewer cards, not a 42%-disclaimer caption.
- **Slots beat prompts.** If a number is computable from corpus, compute
  it. Gemini stays for TL;DR paragraphs and "why it works" blurbs.
- **Retire chat fallbacks as each screen ships.** `/app/chat` loses its
  corresponding quick-action CTA once the dedicated screen is live.

## Recommended order

| # | Screen | Rationale |
|---|---|---|
| B.1 | `/video` Phân Tích Video | Highest-traffic intent (the "Soi video" quick action). Validates the whole deterministic-slot pattern. Medium complexity. |
| B.2 | `/kol` Kênh Tham Chiếu | Lowest-risk — mostly table queries + detail card. Builds on `profiles.reference_channel_handles` from Phase A. Confidence builder after B.1. |
| B.3 | `/channel` Phân Tích Kênh | Extends B.1's structural decomposition from single video → creator scale. |
| B.4 | `/script` Xưởng Viết | Most generative + most complex. Closes the morning-ritual loop (hook card → full shot list). Save for last. |

Estimated 7 weeks at steady pace (one engineer, full-time).

---

## B.1 — `/video` Phân Tích Video (~2 weeks)

### What the creator sees

- Win/Flop segmented toggle at top
- **Win mode**: phone preview (9:16) + KPI 2×2 + Timeline (8 segments
  HOOK/PROMISE/APP1-5/CTA with pct) + Hook phase 3-card breakdown
  (0-0.8s / 0.8-1.8s / 1.8-3s) + 3 numbered "Lessons" with
  "Áp dụng" CTAs
- **Flop mode**: URL input → big serif headline ("Video dừng ở 8.4K view
  vì hook rơi muộn…") + retention curve SVG (yours vs niche benchmark)
  + issue list (4 cards: severity / timestamp / title / detail /
  "Áp vào kịch bản") + dark summary bar ("Dự đoán ~34K view · giữ chân 56%")

### Backend

New module `cloud-run/getviews_pipeline/video_structural.py`:

- **Segment decomposition**: maps `analysis_json.scenes[]` → named
  segments (HOOK 0-3s / PROMISE 3-8s / APPEAL 8-N / CTA end) with
  per-segment `duration_pct`. Mostly deterministic from scene
  timestamps; Gemini only names the segment's content in 3-5 words.
- **Hook phase breakdown**: 3 cards describing what happens in each
  slice of the first 3s (visual / text / sound). Derived from
  `analysis_json.first_frame_type`, `face_appears_at`, and scene[0].
- **Retention curve**: not in current data. Need to derive or fake.
  *Option A* (simpler): estimate from breakout_multiplier + niche
  median. *Option B* (correct): parse TikTok's per-video retention
  curve if ensembledata exposes it — check their API docs first.
  Decision needed.
- **Flop diagnostic**: Gemini call with strict schema returning
  `[{severity: "high"|"mid"|"low", time_range, title, detail, fix}]`.
  Only fires when user's video is < niche-median retention.

New table: `video_diagnostics` caching derivations keyed by `video_id`
(so re-analyzing is free).

New fields on `niche_intelligence` materialized view: `retention_curve`
(JSONB array of 20 points, median across niche).

### Endpoints

- `POST /video/analyze` — body `{video_id?, tiktok_url?}`. Returns:
  segments, hook phases, retention_curve + niche_benchmark_curve, and
  (conditional on underperformance) flop_diagnostic.
- `GET /video/niche-benchmark?niche_id=X` — cached.

### Frontend

- New route `/app/video`
- Layout uses existing v2 primitives: `TopBar` + `Card` + `Segmented` +
  `Btn`. New primitive: `RetentionCurve` SVG component.
- URL input flow for flop mode reuses the existing `prefillUrl` pattern
  from ChatScreen.

### Milestones

1. **B.1.1** (3d) backend — `video_structural.py` segment + hook phase
   + `video_diagnostics` migration + unit tests
2. **B.1.2** (3d) backend — retention curve (decide A vs B first) +
   niche benchmark caching in `niche_intelligence`
3. **B.1.3** (2d) backend — flop diagnostic Gemini endpoint + pydantic
   schema + tests
4. **B.1.4** (4d) frontend — `/app/video` Win mode + wiring
5. **B.1.5** (2d) frontend — Flop mode + URL input
6. **B.1.6** (1d) retire `video_diagnosis` chat intent CTA; Soi video
   card routes to `/app/video`

### Decisions to lock before starting

- Retention curve: derive/fake (A) or fetch real data (B)?
- Cache diagnostics in `video_diagnostics` or recompute on each view?
- Flop threshold: absolute retention < X% or relative-to-niche-median?

---

## B.2 — `/kol` Kênh Tham Chiếu (~1 week)

### What the creator sees

- Top bar: "3 kênh bạn đang theo dõi sát" vs "Khám phá kênh mới"
- Segmented: "Đang theo dõi" / "Khám phá" (counts)
- Filter ribbon: niche chips + follower range + growth rate + search
- 2-col: sortable table (#/CREATOR/FOLLOW/VIEW TB/TĂNG 30D/MATCH) +
  sticky detail card (avatar + 2×2 stats + big MATCH score + 3 CTAs:
  Phân tích kênh đầy đủ / Ghim-Bỏ ghim / Học hook)

### Backend

- **Match score (0-100)**: combines niche overlap + follower range
  overlap with creator-user + tone similarity (embedding distance or
  categorical). Derivable live per (user, creator) pair; cache in
  `creator_match_score` if cost matters.
- **Creator pins**: new table `creator_pins (user_id, handle, pinned_at,
  PRIMARY KEY (user_id, handle))`. The "Đang theo dõi" tab seeds from
  `profiles.reference_channel_handles` and lets the creator pin more.

### Endpoints

- `GET /kol/browse?niche_id&pinned_only&filters` — returns table rows.
  Service-role (RLS-limited to pin ownership).
- `POST /kol/pin` / `DELETE /kol/pin` — user-scoped.

### Frontend

- New route `/app/kol`
- New primitives: `FilterChipRow` (reuses `Chip`), `SortableTable`,
  `StickyDetailCard`
- Clicking "Phân tích kênh đầy đủ" routes to `/app/channel?handle=X`
  (B.3)

### Milestones

1. **B.2.1** (2d) backend — match score derivation + `creator_pins`
   migration + endpoints + tests
2. **B.2.2** (4d) frontend — `/app/kol` screen + table + detail card
3. **B.2.3** (1d) auto-populate "Đang theo dõi" from
   `reference_channel_handles`; drop `creator_search` chat CTA

---

## B.3 — `/channel` Phân Tích Kênh (~2 weeks)

### What the creator sees

- Back button → hero card (profile + bio + stats + 2×2 KPI grid)
- **Formula bar**: 4 weighted segments (HOOK / SETUP / BODY / PAYOFF)
  with pct + detail text
- 2-col: top 4 videos + "Điều nên copy" 4 numbered lesson cards
- Full-width "Tạo kịch bản theo công thức này" CTA → `/app/script`
  with the channel's formula pre-loaded

### Backend

- **Channel formula**: Gemini call with creator's top videos →
  `[{step: "HOOK", detail, pct}, {step: "SETUP", ...}, ...]`. Cached
  per `creator_handle` in `channel_formulas` table. Refresh weekly.
- **Posting cadence**: aggregate `posted_at` distribution across the
  creator's videos → best weekday + hour bucket.
- **Creator KPIs**: avg views / engagement / posting frequency from
  `video_corpus` rows.

### Endpoints

- `GET /channel/analyze?handle=X` — paid (credit decrement). Returns
  hero + formula + top 4 + lessons.

### Frontend

- New route `/app/channel?handle=X`
- New primitive: `FormulaBar` (4-segment weighted bar with labels)
- Reuses Win-mode layout shape from `/video` for the top videos grid

### Milestones

1. **B.3.1** (3d) backend — `channel_formulas` aggregation + migration
   + Gemini schema + cache
2. **B.3.2** (2d) backend — posting cadence + creator KPIs + endpoint
3. **B.3.3** (4d) frontend — `/app/channel` + data wiring
4. **B.3.4** (2d) retire `competitor_profile` + `own_channel` chat
   CTAs; route Soi kênh card to `/app/channel`

---

## B.4 — `/script` Xưởng Viết (~2 weeks)

### What the creator sees

- 3-col layout
- **Left**: inputs (topic textarea + hook-template picker + hook-
  timing slider with sweet-spot band + duration slider with banded
  feedback + tone chips + "Tạo lại với AI" button + citation tag)
- **Middle**: **PacingRibbon** (your tempo vs niche winners) → shot
  rows (6 shots, each with time/cam/voice/visual+overlay/slow-or-on-
  beat) → **ForecastBar** ("Dự đoán ~62K view · retention 72%")
- **Right**: **SceneIntelligence** for active shot — tip card +
  MiniBarCompare (you vs niche avg vs winner) + overlay library
  samples + 3 reference clips

### Backend

- **Scene intelligence**: per-scene-type aggregation across niche top
  videos — corpus-avg duration, winner-avg duration, winner overlay
  style description, 3 reference clips. Stored in
  `scene_intelligence (niche_id, scene_type, PRIMARY KEY (niche_id,
  scene_type))`. Refreshed nightly for niches with sufficient corpus.
- **Pacing ribbon data**: tempo curve for user's draft (derived from
  shot times) + niche-winner curve + niche-average curve.
- **Hook sweet-spot**: per-niche `(min_sec, max_sec)` band where
  retention is highest in niche (from top-performing videos' hook
  landing times).
- **Overlay library**: keyed by scene type, sourced from
  `analysis_json.text_overlays` across winning videos.
- **Forecast formula**: hook_score × duration_band_goodness × niche
  median. Deterministic.

### Endpoints

- `POST /script/generate` — body `{hook, niche_id, tone}`. Returns
  shot list + pacing + forecast. Paid.
- `GET /script/scene-intelligence?niche_id=X&scene_type=Y` — cached.

### Frontend

- New route `/app/script`
- New primitives: `PacingRibbon`, `MiniBarCompare`, `HookTimingMeter`
  (slider with sweet-spot band overlay), `ShotRow`
- Morning-ritual card "Mở kịch bản →" prefills the script with the
  ritual's hook

### Milestones

1. **B.4.1** (3d) backend — `scene_intelligence` aggregation + nightly
   cron + migration
2. **B.4.2** (2d) backend — pacing ribbon data + forecast formula +
   endpoints
3. **B.4.3** (5d) frontend — 3-col layout + shot row editor + scene
   intelligence panel
4. **B.4.4** (2d) integrate morning-ritual → `/app/script` prefill;
   retire `shot_list` chat CTA
5. **B.4.5** (2d) integrate `/channel` → `/app/script` formula
   prefill

---

## Cross-cutting

### Deliberately deferred to Phase C

- `/answer` — threaded research session with classifier-driven turns,
  idea directions, style guide, stop-doing list
- `/history` full restyle (currently on purple tokens)
- `/chat` retirement (it stays around as the generic fallback)
- Landing page refit

### Things that get retired when Phase B lands

- `/app/chat` quick-action CTAs for: `video_diagnosis`, `creator_search`,
  `competitor_profile`, `own_channel`, `shot_list`. Chat stays for
  `follow_up` / general Q&A only.

### Risks to monitor

- **Retention curve data**: if ensembledata doesn't expose per-video
  retention, the flop diagnostic is weaker. Spike in B.1.2.
- **Scene intelligence sparsity**: niches with <30 winners per scene
  type won't cluster meaningfully. Claim-tier gates handle this but
  the UI needs a graceful empty state.
- **Channel formula cost**: one Gemini call per creator per week. For
  every creator in `creator_pins` + `starter_creators` across all
  niches, this scales. Cache and batch.
- **B.4 overlaps with Phase C `/answer`**: the forecast + idea
  direction concepts want to live in `/answer` too. Before starting
  B.4, draw a clear line.

### Before kickoff

Lock these:
1. Retention curve: derived from breakout_multiplier (A) or real data
   from ensembledata (B)?
2. Match score: embedding-based (costly, accurate) or rule-based
   (cheap, directional)?
3. Channel formula refresh: nightly per-creator or on-demand +
   time-to-live cache?
4. Scene intelligence: nightly job or recompute on open?

My defaults: A / rule-based / TTL cache / nightly. All lean toward
"cheap and shippable first, optimize later".
