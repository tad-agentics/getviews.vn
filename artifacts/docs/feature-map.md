# Feature Map (main @ baa3af1)

*Comprehensive full-stack inventory of user-facing surfaces, backend endpoints, synthesis paths, and database tables. Status reflects shipping state on 2026-05-20.*

*Verified against codebase 2026-05-20. Route + endpoint claims spot-checked: routes.ts mounts, `/stream` dispatch (intent.py:265), all 9 `async def run_*` pipelines, `/channel/diagnose` (video.py:736), `/home/*` quartet (home.py:31/49/67/87), `/answer/sessions[/{id}/turns]` (answer.py:62/94/260/280/291/306), `/script/*` 9-endpoint set (script.py:37–192), `/admin/*` (admin.py:771–1453), `/batch/*` (batch.py:23–1257), edge functions `api/chat.ts` + `api/landing-stats.ts`, and the `signals/` module set.*

---

## 1. Landing & Authentication

### /) Landing page
- **FE:** `src/routes/_index/route.tsx` (line 18), `src/routes/_index/LandingPage.tsx`
- **BE endpoints:**
  - GET `/api/landing-stats` (Vercel Edge, `api/landing-stats.ts`) → fetches aggregated hook statistics + thumbnail IDs for hero carousel
- **DB tables:** `hook_effectiveness` (read for hooks list), R2 (frame0 thumbnails)
- **Status:** shipped & live
- **Evidence:** Route mounted `src/routes.ts:5`. Landing stats loader at line 20.

### /login
- **FE:** `src/routes/_auth/login/route.tsx`
- **BE:** Supabase Auth (OAuth: Google, Facebook; email/password)
- **Status:** shipped & live
- **Evidence:** `routes.ts:8`, OAuth flows at lines 157–160

### /signup, /auth/callback
- **FE:** `src/routes/_auth/signup/route.tsx`, `src/routes/_auth/callback/route.tsx`
- **BE:** Supabase Auth
- **Status:** shipped & live
- **Evidence:** `routes.ts:9–10`

---

## 2. /app Shell & Home Screen

### /app (index)
- **FE:** `src/routes/_app/route.tsx` → HomeScreen
- **Routing logic:**
  - If no niche in profile → redirect to `/app/onboarding`
  - Otherwise render HomeScreen (lazy)
- **Query:** `useProfile()` → checks `profileHasNiche()` at line 44
- **Status:** shipped & live
- **Evidence:** `routes.ts:14`, redirect logic at lines 44–46

### /app/home (implicit via HomeScreen)
- **FE:** `src/routes/_app/home/HomeScreen.tsx`
- **Sub-surfaces:**
  1. **Ticker marquee** — `TickerMarquee` component, pulls from `/home/ticker`
  2. **Daily ritual widget** — `HomeSuggestionsToday` tier rendering, pulls `/home/daily-ritual` + `/home/pulse`
  3. **Starter creators** — contextual creator card widget, `/home/starter-creators`
  4. **Pulse data** — niche vitals, calls `/home/pulse` (line 115)
  5. **Query composer** — text input for video URL / niche questions (lines 66–67)
- **BE endpoints:**
  - GET `/home/pulse` → `cloud-run/routers/home.py:32` — returns niche health (as_of timestamp, pulse data) + daily ritual regen status
  - GET `/home/ticker` → `cloud-run/routers/home.py:50` — hot hooks (3 per niche)
  - GET `/home/starter-creators` → `cloud-run/routers/home.py:68` — 3 trending creators
  - GET `/home/daily-ritual` → `cloud-run/routers/home.py:88` — user's daily ritual suggestions (3 tiers: 01 scripts, 02 channel analysis, 03 trend insight)
  - GET `/answer/sessions` → queries past sessions for user (implied via `answerSessionKeys.listsForUser()`)
- **Synthesis paths invoked:**
  - Daily ritual synthesis (pattern_decks, brief_generation, creator_search pipelines called nightly via `/batch/morning-ritual`)
  - Pulse aggregation (daily corpus snapshot)
- **DB tables:** `daily_ritual`, `starter_creators`, `niche_insights`, `answer_sessions`, `answer_turns`
- **Status:** shipped & live
- **Evidence:** HomeScreen lines 115–126 (pulse + ticker), daily ritual suggestions rendering at line 200+, routes.ts:14

---

## 3. /app/answer — Video Diagnosis + Q&A Research

**Central surface for video analysis, follow-up Q&A, and multi-turn research synthesis.**

- **FE:** `src/routes/_app/answer/AnswerScreen.tsx` (lazy route at `routes.ts:15`)
- **Entry points:** 
  - Direct `/app/answer` (fresh session) or `/app/answer?session=<id>` (resume)
  - Seeded from home composer (`?q=<query>`), OR from /app/channel diagnostics deep link
- **Primary query params:** `?session=`, `?q=`, `?session_id=`

### ① **Sub-surface: Primary turn (video diagnosis)**
- **FE flow:** QueryComposer accepts TikTok URL or text question → `createAnswerSession()` → SSE stream
- **Intent router logic:** `src/routes/_app/intent-router.ts` classifies input (video URL → `video_diagnosis`, text → `follow_up_unclassifiable` or specific intent)
- **BE endpoints:**
  - POST `/answer/sessions` (Cloud Run, `routers/answer.py:62`) — idempotency-keyed, creates blank session row
  - POST `/answer/sessions/{session_id}/turns` (Cloud Run SSE, `routers/answer.py:94`) — streams diagnosis; supports resume_stream_id + resume_from_seq replay
- **Synthesis pipeline:**
  - For video URL: `run_video_diagnosis()` calls `diagnosis_synthesis_v6_section_pool` (prompts.py) → Gemini extracts hook, commerce, story arc, etc.
  - Signals evaluated: `hook_type`, `hook_effectiveness`, `creator_velocity`, `video_patterns`, `niche_insights` (lookups)
  - Output: ReportV1 (diagnosis payload) with sections: hook ranking, patterns, commerce hooks, ideas
- **DB tables:** `answer_sessions`, `answer_turns`, `video_diagnostics`, `video_corpus`, `hook_effectiveness`, `content_classifications`, `signal_grades`
- **Status:** shipped & live
- **Evidence:** AnswerScreen.tsx line 143 (useAnswerSessionDetail), POST /answer/sessions at answerApi.ts:52, playback loop at lines 255–295

### ② **Sub-surface: Follow-up turns (Q&A)**
- **FE:** ContinuationTurn component + FollowUpComposer, manual query input
- **Intent router:** Classifies follow-up intent from text (trend_spike, creator_search, timing, script, generic, etc.)
- **BE:** POST `/answer/sessions/{session_id}/turns` → same stream endpoint but different kind ("timing", "creators", "script", "generic")
- **Synthesis:** Intent-specific pipeline (e.g., `run_trend_spike()` for niche trend data, `run_creator_search()` for creator finder, `run_shot_list()` for script suggestions)
- **Status:** shipped & live
- **Evidence:** ContinuationTurn component usage in AnswerScreen, follow-up composer at lines 330+

### ③ **Sub-surface: Chat history**
- **FE display:** TimelineRail shows turn breadcrumb, click to jump to a turn
- **Query:** GET `/answer/sessions/{session_id}` → fetches full session detail (header + all turns)
- **DB:** answer_sessions.title, answer_turns array
- **Status:** shipped & live

**Core answer-session error codes:** insufficient_credits, daily_free_limit, stream_failed, stream_timeout, session_not_found, idempotency_conflict (AnswerScreen.tsx:53–70)

---

## 4. /app/history — Session Archive

- **FE:** `src/routes/_app/history/route.tsx` → HistoryScreen
- **Sub-views:**
  - List of sessions (with filter ribbon: niche, intent type, date range)
  - Click → `/app/history/chat/:sessionId` (ChatSessionReadScreen)
- **BE endpoints:**
  - GET `/answer/sessions` (Cloud Run, `routers/answer.py`) — paginated list for user
  - GET `/answer/sessions/{session_id}` → full detail with turns
- **DB tables:** `answer_sessions`, `answer_turns`
- **Status:** shipped & live
- **Evidence:** `routes.ts:16–18`, HistoryScreen.tsx filter ribbon

---

## 5. /app/channel — Channel Deep-Dive Analysis

- **FE:** `src/routes/_app/channel/ChannelScreen.tsx` (lazy route at `routes.ts:27`)
- **Entry:** `/app/channel?handle=<@handle>` (optional `?creator_niche_id=<id>`, `?force_refresh=true`, `?video_url=<...>`)
- **Flow:** User enters TikTok handle → calls `useChannelDiagnose()` → SSE diagnosis
- **BE endpoints:**
  - GET `/channel/user-search` (Cloud Run, `routers/video.py:100`) — autocomplete handle lookup
  - POST `/channel/diagnose` (Cloud Run SSE, `routers/video.py:736`) — streams channel diagnosis with sections (growth trajectory, content directions, niche fit, competitor benchmarks, top patterns)
  - POST `/channel/refresh-mine` (Cloud Run, `routers/video.py:143`) — refresh current user's own channel cache
- **Synthesis paths:**
  - `run_own_channel()` / `run_competitor_profile()` pipelines → calls `channel_diagnose_prompts.py` Gemini synthesis
  - Sections rendered: GrowthCard (trajectory), ScoreCard (niche fit), CommentRadarTile, PatternSpreadStrip (hot hooks in channel)
  - Signals: `channel_diagnoses` row, `video_patterns`, `hook_effectiveness`, `creator_velocity`
- **DB tables:** `channel_diagnoses` (cached, keyed by handle), `video_patterns`, `creator_velocity`, `hook_effectiveness`, `niche_insights`
- **Credit cost:** 3 deep_credits per diagnosis (ChannelScreen.tsx:22)
- **Status:** shipped & live
- **Evidence:** Channel diagnosis endpoint at video.py:736, SectionRenderer at ChannelScreen.tsx:17, scorecard at line 18

---

## 6. /app/trends — Niche Intelligence & Pattern Explorer

- **FE:** `src/routes/_app/trends/route.tsx` → ExploreScreen
- **Param:** `?niche=<id>` (else defaults to user's primary niche)
- **Sub-views:**
  - Top patterns (hook gallery, sorted by trend velocity)
  - Filter/sort UI
- **BE endpoints:**
  - GET `/home/pulse` (reused) — niche vitals
  - GET `/script/hook-patterns` (Cloud Run, implied from ScriptScreen data dependency) — hooks + recent usage
- **Signals:** `trend_velocity` table (updated nightly), hook recency
- **DB tables:** `video_patterns`, `trend_velocity`, `hook_effectiveness`, `niche_taxonomy`
- **Status:** shipped & live
- **Evidence:** `routes.ts:19`, ExploreScreen lazy load

---

## 7. /app/script — Content Script Workshop

- **FE:** `src/routes/_app/script/route.tsx` → ScriptScreen
- **Params:** `?hook=`, `?niche_id=`, `?topic=`, `?duration=`
- **Features:**
  - Hook pattern explorer (top hooks for niche + filter)
  - Scene intelligence (if enabled)
  - Shot list generation (idea references)
  - Save draft script
- **BE endpoints:**
  - GET `/script/scene-intelligence` (`routers/script.py:37`) — scene type classifier (depends on batch `/batch/scene-intelligence` job)
  - GET `/script/idea-references` (`routers/script.py:58`) — idea suggestions keyed to hook
  - GET `/script/hook-patterns` (`routers/script.py:84`) — top hooks for niche + metadata
  - POST `/script/generate` (`routers/script.py:105`) — synchronous script generation given hook + niche
  - POST `/script/save` (`routers/script.py:138`) — legacy save path
  - POST `/script/drafts` (`routers/script.py:147`) — save new draft
  - GET `/script/drafts` (`routers/script.py:156`) — user's saved scripts
  - GET `/script/drafts/{draft_id}` (`routers/script.py:173`) — single draft detail
  - POST `/script/drafts/{draft_id}/export` (`routers/script.py:192`) — export draft
- **Sub-route:** `/app/script/shoot/:draftId` (AnswerScreen with draft hydration) — renders script sections + video guidance
- **Synthesis paths:**
  - `run_shot_list()` pipeline — Gemini generates shot list given hook + niche
  - Scene intelligence → batch job classifies video frames into scene types
- **DB tables:** `draft_scripts`, `public.video_shots`, `scene_intelligence`, `hook_effectiveness`, `content_format_reclassify`
- **Status:** shipped & live (core) / WIP (scene intelligence batch integration)
- **Evidence:** `routes.ts:28–29`, script.py router, draft_scripts schema in migrations

---

## 8. /app/douyin — Douyin Corpus & Analytics

- **FE:** `src/routes/_app/douyin/route.tsx` → DouyinScreen
- **Features:**
  - Douyin niche selector (16+ Chinese niches)
  - Pattern feed (hot hooks in Douyin)
  - Trend explorer
- **BE endpoints:**
  - GET `/douyin/feed` (Cloud Run, `routers/douyin.py`) — paginated hot videos
  - GET `/douyin/patterns` → hot Douyin-specific patterns
  - (Implied) Batch `/batch/douyin-ingest`, `/batch/douyin-patterns`, `/batch/douyin-synth` (nightly corpus refresh)
- **DB tables:** `douyin_video_corpus`, `douyin_video_shots`, `douyin_niche_taxonomy`, `douyin_patterns`
- **Status:** shipped & live (read surfaces) / WIP (corpus sync + pattern synthesis)
- **Evidence:** `routes.ts:20`, douyin.py router, Douyin corpus migrations (20260603000000_*, 20260603000002_*)

---

## 9. /app/compare — Two-Video Comparison

- **FE:** `src/routes/_app/compare/route.tsx` → CompareScreen
- **Entry:** `/app/compare?url_a=<url>&url_b=<url>` (from intent router)
- **Flow:** Two video URLs → POST `/stream` with intent `compare_videos` → parallel diagnoses + delta synthesis
- **BE endpoints:**
  - POST `/stream` (Cloud Run, `routers/intent.py:265`) — orchestrates `run_compare_pipeline()` (report_compare.py) which parallelizes diagnoses then diffs them
- **Output:** ComparePayload (delta report showing differences in hooks, patterns, commerce effectiveness)
- **DB tables:** video_corpus, video_diagnostics, video_patterns (both videos)
- **Status:** shipped & live
- **Evidence:** `routes.ts:26`, compare.py route comment at lines 10–15, report_compare import in intent.py

---

## 10. /app/onboarding

- **FE:** `src/routes/_app/onboarding/route.tsx`
- **Purpose:** Single-niche setup for new users (niche_taxonomy picker)
- **BE:** Writes creator_niches → profiles.creator_niche_id
- **Status:** shipped & live
- **Evidence:** `routes.ts:17`, profile redirect logic in /app route

---

## 11. /app/settings, /app/learn-more, /app/pricing, /app/checkout, /app/payment-success

- **FE:** Lazy-loaded screens (`src/routes/_app/<feature>/route.tsx`)
- **/app/settings:**
  - Niche/profile editor, subscription management, API key management (if admin)
  - POST → updates profiles table
- **/app/pricing:** Static pricing display (no BE integration)
- **/app/checkout:** Lemon Squeezy integration (subscription)
- **/app/payment-success:** Post-checkout redirect
- **Status:** shipping / live
- **Evidence:** `routes.ts:30–34`

---

## 12. /app/admin — Operator Dashboard

- **FE:** `src/routes/_app/admin/route.tsx` → AdminScreen + sub-panels (EnsembleCreditsPanel, FunnelPanel, CorpusHealthPanel, TriggersPanel, ThumbnailFailuresPanel, LogsPanel, ActionLogPanel, Layer0Panel)
- **BE endpoints (Cloud Run `routers/admin.py`):**
  - **Observability:**
    - GET `/admin/corpus-health` (line 771) — corpus recency, niche distribution, ingest queue status
    - GET `/admin/ensemble-credits` (line 861) — Gemini usage (call count, spend, burndown)
    - GET `/admin/ensemble-call-sites` (line 880) — breakdown by synthesis path
    - GET `/admin/ensemble-history` (line 908) — 7-day Gemini usage trend
    - GET `/admin/alert-fires` (line 983) — recent alerts (ensemble runway, corpus staleness, trigger failures)
    - GET `/admin/logs` (line 997) — structured logs tail
    - GET `/admin/action-log` (line 1038) — audit log of operator triggers
    - GET `/admin/funnel` (line 1052) — user funnel (signup → first diagnosis → subscription)
    - GET `/admin/layer0-health` (implied) — video extraction queue status
  - **Triggers (manual batch jobs)** — all in `routers/admin.py`:
    - POST `/admin/trigger/ingest` (1228) → corpus ingest with optional niche filter
    - POST `/admin/trigger/analytics` (1259) → batch analytics recalc
    - POST `/admin/trigger/scene_intelligence` (1267) → batch scene classification
    - POST `/admin/trigger/thumbnail_backfill` (1275) → re-extract thumbnails from R2 fallback
    - POST `/admin/trigger/backfill_classification` (1312) → re-run content-format classifier
    - POST `/admin/trigger/refresh` (1330) → re-diagnose channels / refresh feeds
    - POST `/admin/trigger/reclassify_format` (1346) → re-classify content format
    - POST `/admin/trigger/r2_janitor` (1357) → cleanup orphaned R2 assets
    - POST `/admin/trigger/layer0` (1371) → reprocess failed video extractions
    - POST `/admin/trigger/enrich_shots_top500` (1382) → enrich shot metadata for top corpus
    - POST `/admin/trigger/viral_score_backtest` (1394) → eval viral-score model on historical corpus
    - **Note:** there is NO `/admin/trigger/morning-ritual` — morning ritual is regenerated via `POST /home/regenerate-ritual` (`home.py:181`) for users or `POST /batch/morning-ritual` (`batch.py:1031`) for the cron.
- **Alert rules:** Ensemble runway low, corpus stale, trigger error spike, pg_net batch HTTP 4xx
- **DB tables:** `ensemble_calls`, `admin_alert_rules`, `admin_alert_fires`, `admin_action_log`, `batch_job_runs`, `batch_http_log`
- **Status:** shipped & live
- **Evidence:** Admin router line 771+, AdminScreen.tsx structure with sub-panels

---

## 13. Vercel Edge Functions

### `api/chat.ts`
- **Endpoint:** POST `/api/chat` (Vercel Edge)
- **Purpose:** Message streaming from a React Query + SSE integration (implied dual-mode streaming for replay buffering)
- **Status:** shipped & live (infrastructure)
- **Evidence:** `api/chat.ts:20`

### `api/landing-stats.ts`
- **Endpoint:** GET `/api/landing-stats`
- **Purpose:** Lightweight aggregated stats for landing page (hook list + frame thumbnails)
- **Status:** shipped & live
- **Evidence:** Landing route loader (src/routes/_index/route.tsx:20)

---

## 14. Background Jobs (Cloud Run + pg_cron)

All `/batch/*` endpoints live in `cloud-run/getviews_pipeline/routers/batch.py` (require `BATCH_SECRET`).

| Job | Endpoint (batch.py line) | Synthesis | DB write | Status |
|---|---|---|---|---|
| Corpus ingest | `/batch/ingest` (95) | `corpus_ingest.py` extracts hooks/scenes/transcript via Gemini per video | `video_corpus`, `video_shots`, `video_patterns`, `content_classifications`, `signal_grades` | live |
| Post-processing | `/batch/post-processing` (160) | analytics + signal recomputes after ingest | `niche_insights`, `signal_grades` | live |
| Re-ingest videos | `/batch/reingest-videos` (278) | re-extract a list of video IDs | `video_corpus`, `video_shots` | live |
| Ingest queue drain | `/batch/process-ingest-queue` (313) — daily pg_cron | drains `corpus_ingest_queue` (new 2026-05-19) | `corpus_ingest_queue`, `video_corpus` | live |
| Channel/feed refresh | `/batch/refresh` (376) | re-diagnose channels + feed snapshots | `channel_diagnoses` | live |
| Reclassify format | `/batch/reclassify-format` (405) | re-runs content-format classifier on existing corpus | `content_classifications` | live |
| Classification backfill | `/batch/backfill-classification` (445) | re-classify content + hook type | `content_classifications`, `signal_grades` | live |
| Sound aggregate | `/batch/sound-aggregate` (481) | trending sounds rollup | `trending_sounds` | live |
| Trend velocity | `/batch/trend-velocity` (518) — weekly | hook recency + velocity scoring | `trend_velocity` | live |
| R2 janitor | `/batch/r2-janitor` (568) | delete orphaned R2 assets | (R2 only) | live |
| Thumbnail backfill | `/batch/backfill-thumbnails` (633) | re-extract frame0 + frame analysis | `video_shots` (frame metadata) | live |
| Analytics | `/batch/analytics` (896) | corpus stats + niche insights rollup | `niche_insights` | live |
| Layer0 reprocess | `/batch/layer0` (979) | reprocess failed extractions | `video_corpus` | live |
| Morning ritual | `/batch/morning-ritual` (1031) — daily | calls `run_brief_generation` / `run_competitor_profile` / `run_creator_search` per active user-niche | `daily_ritual`, `starter_creators` | live |
| Pattern decks | `/batch/pattern-decks` (1064) — daily | aggregates `hook_effectiveness`, `video_patterns`, `trend_velocity` per niche | `video_patterns` (upsert) | live |
| Douyin synth | `/batch/douyin-synth` (1139) — D3b daily | grades `douyin_video_corpus` rows for adapt-level | `douyin_video_corpus` | live |
| Scene intelligence | `/batch/scene-intelligence` (1202) | frame scene-type classification | `scene_intelligence` | WIP |
| Douyin patterns | `/batch/douyin-patterns` (1257) — D5c weekly | synthesize 3 pattern signals per active niche | `douyin_patterns` | live |
| Douyin ingest | `/batch/douyin-ingest` (215) — nightly | extracts Douyin video metadata + thumbnails | `douyin_video_corpus`, `douyin_video_shots` | live |

**Other periodic tasks (pg_cron-driven, not in batch.py):**
- Channel diagnoses prune — `channel_diagnoses` rows older than 7d (weekly)
- Starter creators reseed — weekly
- Daily health digest — Monday email
- pg_net batch HTTP 4xx watcher — hourly

**User-facing trigger:** `POST /home/regenerate-ritual` (`home.py:181`) for on-demand morning-ritual regeneration; polls back via `/home/daily-ritual`.

---

## 15. Cross-Feature Observations

### Synthesis path orchestration
- **Single entry point:** POST `/stream` (intent.py) classifies intent from text/URL, then dispatches to:
  - `run_video_diagnosis()` → video_diagnosis intent
  - `run_competitor_profile()` → channel deep-dive
  - `run_creator_search()` → creator finder
  - `run_trend_spike()` → trend explorer
  - `run_shot_list()` → script generator
  - `run_compare_pipeline()` → two-video comparison
- **Synthesis engine:** All paths invoke Gemini via `gemini_text_only()` (genai SDK) + LLM cache for prompt deduplication
- **Signals layer:** All diagnoses read from `hook_effectiveness`, `video_patterns`, `signal_grades`, `niche_insights` (precomputed by batch jobs)

### Niche taxonomy dual-mode
- **Legacy:** `niche_taxonomy` (TikTok Vietnam niches, 1–21)
- **New:** `creator_niches` (16+ multi-platform niches: music, real estate, fashion, etc.)
- **User assignment:** profiles.creator_niche_id (single niche per user post-2026-05-05 refactor)
- **Backward compat:** Surfaces still read niche_taxonomy for hook signals + pattern lookups

### Unused/dormant code paths
- `/app/video` route deleted (2026-04-28) — video diagnosis now lands in `/app/answer` sessions
- `chat_messages`, `chat_sessions` (legacy chat-era tables) — schema exists but no active FE queries
- `METADATA_ONLY` intent (historical) — folded into `follow_up_unclassifiable` (intent.py:84)
- `format_lifecycle` table — populated but not actively read by any FE surface (WIP lifecycle modeling)

### Data freshness signals
- **Pulse (home widget):** `as_of` timestamp from corpus snapshot (daily)
- **Ticker (hot hooks):** 3-day recency window, updated nightly
- **Trends (pattern explorer):** `trend_velocity` updated nightly (velocity = instance count change week-over-week)
- **Channel diagnoses:** Cached for 30 days (force_refresh=true invalidates)

### Error recovery
- **SSE replay buffer:** `/answer/sessions/{id}/turns` supports `?resume_stream_id=<>&resume_from_seq=<>` (90s TTL in `session_store.get_stream_chunks()`)
- **Idempotency:** `/answer/sessions` POST accepts Idempotency-Key header (120s server cache via `answer_session_idempotency` table)
- **Credit rollback:** On stream failure, credits returned to user_id (dependency: `credit_transactions` audit trail)

---

## Shipping Status Summary

| Surface | FE Route | Status | Notes |
|---|---|---|---|
| Landing page | / | ✓ live | Pre-rendered, SEO tags |
| Auth (OAuth + email) | /login, /signup, /auth/callback | ✓ live | Supabase Auth |
| Home + widgets | /app | ✓ live | Daily ritual, ticker, starter creators |
| Answer/diagnosis | /app/answer | ✓ live | Video URL + Q&A, 5+ intent types |
| History | /app/history | ✓ live | Session archive + filtering |
| Channel deep-dive | /app/channel | ✓ live | Handle analysis + benchmarks |
| Trends explorer | /app/trends | ✓ live | Niche pattern feed |
| Script workshop | /app/script | ✓ live (core) | Hook patterns + draft saved; scene intel WIP |
| Video comparison | /app/compare | ✓ live | Parallel diagnosis + delta |
| Douyin corpus | /app/douyin | ✓ live (read) | Ingest + pattern synth live but streaming UI TBD |
| Onboarding | /app/onboarding | ✓ live | Single-niche picker |
| Settings | /app/settings | ✓ live | Niche edit, API keys (admin) |
| Pricing | /app/pricing | ✓ live | Static display |
| Checkout | /app/checkout | ✓ live | Lemon Squeezy integration |
| Admin panel | /app/admin | ✓ live | Full operator dashboard |

---

## API Client Patterns

- **React Query:** `useQuery()` for GET endpoints (with polling/refetch for real-time data)
- **SSE (Server-Sent Events):** `fetchEventSource()` for streaming `/stream` and `/answer/sessions/{id}/turns` (with replay buffer via `useSessionStream()` hook)
- **Manual fetch:** Edge functions (`api/chat.ts`, `api/landing-stats.ts`) + legacy endpoints
- **Auth:** Supabase JWT in `Authorization: Bearer <token>` header (validated by `require_user` FastAPI dependency)

---

## Key Infrastructure Files

- **Routes:** `src/routes.ts` (mounted tree)
- **Intent router:** `src/routes/_app/intent-router.ts` (input classification logic)
- **Cloud Run:** `cloud-run/getviews_pipeline/routers/` (answer.py, video.py, intent.py, home.py, script.py, admin.py, batch_proxy.py, douyin.py)
- **Synthesis pipelines:** `cloud-run/getviews_pipeline/pipelines.py` (run_* functions)
- **Prompts:** `cloud-run/getviews_pipeline/prompts.py`, `diagnose_prompts.py`, `channel_diagnose_prompts.py`
- **Corpus logic:** `corpus_ingest.py`, `corpus_context.py`, `channel_diagnose.py`
- **DB schema:** `supabase/migrations/` (200+ DDL migrations)
- **Signals layer:** `cloud-run/getviews_pipeline/signals/` — `base.py`, `channel.py`, `commerce.py`, `compliance.py`, `context_signals.py`, `distribution.py`, `douyin.py`, `editing.py`, plus `engagement.py`, `hook.py`, `performance.py`, `script.py` etc. Consumed by `pipelines.py::run_video_diagnosis` and others.

