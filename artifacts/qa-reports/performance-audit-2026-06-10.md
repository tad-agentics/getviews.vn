# Performance Audit — GetViews.vn (2026-06-10)

Speed/latency audit across three surfaces: client bundle + render, frontend
data-fetch waterfalls, and Cloud Run backend latency. Plus production DB
performance advisors. Every load-bearing claim re-verified against build
artifacts / live schema before acting; agent claims that didn't survive
verification are called out. **FIXED** = applied this pass.

## Measured baseline (build artifacts, not estimates)

| Surface | Number |
|---|---|
| Landing first-load JS (prerendered `/`) | **236 KB gzip across 19 chunks** + 28 KB gzip CSS |
| Largest single chunk | `entry.client` 96 KB gz |
| `motion` chunk preloaded on landing | 40 KB gz (landing never renders motion — see FE-P1) |
| Largest lazy route chunk | `AnswerScreen` 234 KB raw / 57 KB gz |
| `supabase` chunk | 48 KB gz — **NOT** on the landing path (verified: 0 refs in index.html) |
| Root CSS | 182 KB raw / 28 KB gz (single file, all routes) |

## FIXED this pass

### DB-P1 · Missing FK index on `video_corpus` (the big nightly-written table) — FIXED
Advisor flagged `video_corpus.inferred_creator_niche_id` FK with no covering
index. Added partial index (migration `20260910000000`, applied to prod). Same
for `corpus_ingest_queue.niche_id` (the table added earlier today).

### DB-P2 · Two dead GIN indexes = pure write-amplification on nightly ingest — FIXED
`idx_corpus_topics` (2.5 MB) and `idx_corpus_hashtags` (536 KB) on `video_corpus`
had `idx_scan=0` AND — verified by grep — **no query uses an array-containment
operator** (`@>`, `.cs()`, `.ov()`) on those columns; the only reader selects
`hashtags` as a payload column filtered by the separately-indexed
`content_class_id`. GIN maintenance ran on every row of every nightly bulk
upsert for nothing. Dropped (applied to prod). The `answer_sessions` trgm
*search* indexes were deliberately KEPT — they're `idx_scan=0` only because
history search is unused in prod so far, but `search_history_union` needs them.

### DB-P3 · RLS per-row re-evaluation on a hot authenticated table — FIXED
`content_class_hook_effectiveness` (read on pattern-report builds) re-evaluated
`auth.uid()` per row. Wrapped as `(select auth.uid())` so Postgres evaluates it
once per query — identical behaviour, scales with (classes × hooks). Applied.

### BE-P1 · SSE hello frame moved before the lock RPC → ~30-50 ms faster first byte — FIXED
`POST /answer/sessions/{id}/turns` emitted its `hello` frame *after* the
`begin_processing` lock round-trip. The hello carries no state, so it now fires
first — the client sees "connected" ~30-50 ms sooner, and gets a real
`stream_id` for replay-resume before any DB work. A subsequent
`already_processing`/`stream_failed` is just the next frame (already handled).
`POST /channel/diagnose` already did this correctly (no change). Tests green.

## Recalibrated DOWN after verification (agent overstated)

- **"Split providers off the landing, save 41 KB"** (agent: Critical): **mostly
  wrong.** The big `supabase` chunk (48 KB) is **not** on the landing path
  (verified 0 refs). Only `tanstack` (10 KB) + tiny `auth` are — ~11 KB, not 41.
  And CLAUDE.md documents that the `QueryClientProvider`→`AuthProvider` order in
  `root.tsx` is **load-bearing for the Vercel prerender** (splitting it throws at
  build). Not worth the risk for ~11 KB. **Not done.**
- **append_turn "3 serial DB calls, parallelize" (Critical, ~40 ms)**: real but
  the two reads live inside a 960-line sync function run in a worker thread;
  restructuring the credit-deduction-critical path for ~40 ms isn't worth the
  risk right now. Backlog.
- **channel_diagnose "hello after cache lookup"**: **wrong** — it already emits
  hello before the cache fetch (`video.py:862` before `:866`).

## Real findings, documented as backlog (honest severity)

### FE-P1 · `motion` (40 KB gz) preloaded on the landing critical path — ✅ FIXED (follow-up pass, same day)
Root cause turned out deeper than a chunk-graph hint: **Rolldown's merge pass
ignored `manualChunks` return values and folded `react/jsx-runtime` INTO the
`motion` chunk** (and React core into `icons`) — so *every component chunk*
statically imported `motion`, including `Btn`, `tanstack`, and the landing
route. Verified by reading the built chunk (jsx-runtime's
`Symbol.for("react.transitional.element")` implementation sat at the top of
`motion-*.js`).

Fix: migrated chunking to Rolldown-native `output.advancedChunks` with
priority-enforced groups — the exact migration the old config comment had
deferred. Measured result:
- **Landing first-load: 236 KB → 196 KB gzip (−40 KB, −17%)**; `motion` has
  0 references in the landing preload graph.
- Bonus: `react-vendor` (59 KB gz) and `react-router` (40 KB gz) now emit as
  real chunks → long-term-cacheable independently of app code (the caching win
  the old comment deferred "until we migrate to advancedChunks").
- Full vitest suite + typecheck + build green; per-route chunks intact.

### FE-P2 · `AnswerScreen` bundles all six report formats together (57 KB gz)
A user viewing a pattern report still downloads the video-diagnosis renderer
(frame grids, evidence embeds). Per-format `React.lazy` would trim ~20-30 KB per
session. Real, but "nice to have" — not broken.

### FE-P3 · No `React.memo` on streaming report subtrees
Every SSE token does `setState({...s, text})`; without memo on the large grids
(`PatternCellGrid`, `EvidenceGrid`) and the steps list, they re-render per
token. Adding `memo` is the single biggest *perceived* streaming-smoothness win
(~200-500 ms of reflow over a stream). Verified no memo present. Backlog —
medium effort, medium risk (need to confirm prop stability).

### FE-P4 · No list virtualization (ExploreScreen / HistoryScreen)
Corpus browse can render 50-100+ `VideoThumbnail` tiles — mobile-scroll jank on
low-end Android (common in VN). Backlog: `@tanstack/react-virtual` on the grid
(medium). CORRECTION to the agent claim: HistoryScreen's `groupByDate` is
**already memoized** (`HistoryScreen.tsx:116`) — no fix needed there. Also
fixed in the follow-up pass: `Btn` size `md` now has `min-h-[44px]` (FE-L1)
and the stale "90s" replay-TTL comment in AnswerScreen (FE-L3; the sseResume.ts
comment flagged by the agent was already correct — it documents the historical
bug, not a live one).

### BE-P2 · Pattern-report corpus + hook-effectiveness fetches are serial
`load_pattern_inputs` fetches the corpus window (limit 2500) then hook
effectiveness sequentially. `asyncio.gather` would save ~200-400 ms on the most
common report type. Backlog (needs care — both are sync supabase calls inside a
threaded builder).

### BE-P3 · Live-search supplement blocks the SSE generator
`report_pattern.py` spins a `new_event_loop().run_until_complete(fetch_live_supplement())`
inside the sync builder — blocks the stream ~200-500 ms when triggered (fresh
query / thin corpus). Backlog.

### DB-P4 · ~43 remaining unused indexes + 6 small-table policy hints — documented, NOT auto-applied
Most flagged "unused" indexes are on features that may not be live yet (douyin,
competitor_tracking, push_events) or are write-only-table pkeys (`usage_events`)
— `idx_scan=0` there is normal, not a drop signal. The 3 duplicate-permissive-
policy + remaining init-plan warnings are on tiny reference tables
(`content_class_ingest_targets` ~43 rows, `hashtag_class_map`,
`content_class_trend_velocity`) where per-row auth re-eval is negligible.
Rewriting RLS role-scoping or dropping indexes there for marginal gain is the
classic "perf fix that causes an outage" — left for a human with feature
context. The two GIN drops above were the only *verified-dead, hot-table* ones.

## Already fast / well-done (verified)
- **HomeScreen** fires its 4 queries in parallel (only a 2-level profile→scope
  waterfall) — a textbook TanStack pipeline.
- **Executor sized to 40 threads** (fixed in the cloud-run audit) — paid
  concurrency no longer capped at 5.
- **SSE replay buffer (TD-4)**, **idempotency guards**, **7-day channel cache**,
  **profile realtime + 4 s poll** — all sound.
- **Image loading**: `VideoThumbnail` lazy-loads with an R2→CDN→placeholder
  fallback chain and deduped failure telemetry.
- **Fonts**: preconnect + `font-display: swap`, no FOUT; **PWA** uses
  `registerType: "prompt"` (no SW cost on the landing TTI).

## Bottom line
Perceived speed is **good already** — warm pod, parallel home queries, SSE with
an early ack. The cheap wins are banked (DB indexes/policy, dead-GIN write-amp,
earlier hello). The biggest remaining lever is **FE-P1 (40 KB motion off
landing)** for conversion, then **FE-P3 (memo) / BE-P2 (parallel corpus fetch)**
for the core analysis loop — all worth a dedicated, measured follow-up rather
than a rushed change.
