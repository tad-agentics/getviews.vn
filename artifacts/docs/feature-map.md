# Feature Map (main @ da76f96)

*Comprehensive full-stack inventory of user-facing surfaces, backend endpoints, synthesis paths, and database tables. **Source of truth** for what ships where — update this file in the same commit as any route, endpoint, or orchestration change.*

*User value / JTBD / gap analysis:* [`product-value-audit.md`](product-value-audit.md) (value → data, doc-only).  
*V1 product vision (chỉ phạm vi ship GTM V1):* [`feature-map-v1.md`](feature-map-v1.md) — **không** liệt kê tính năng ngoài V1; xem **§ Post-V1 backlog** bên dưới.

*Verified against codebase **2026-05-22** (Wave 0 incremental — channel 3× credit + F8 verify). Spot-checked: two-axis browse (`corpusNicheFilter.ts`, `useTopBreakouts`, `useCrossNicheBreakouts`); Home tier I–III (`MorningSignalStrip`, `HooksTable`, `BreakoutGrid`); Trends Explore (`CrossNicheBreakoutLane`, `TrendsRail`, class MV thin banner); taxonomy v2 (16 active niches, 82 classes); dual SSE + answer path unchanged from prior audit.*

*Pivot SSOT:* Production ingest/browse defaults — [`system-design.md`](system-design.md) §9 · taxonomy tables — [`two-axis-niche-model.md`](two-axis-niche-model.md).*

*Incremental V1 path:* [`incremental-v1-roadmap.md`](../plans/incremental-v1-roadmap.md) · Wave 0 ops checklist — [`wave0-cron-sla-checklist.md`](wave0-cron-sla-checklist.md).*

---

## Post-V1 backlog (không trong product vision V1)

*Tổng hợp từ [`feature-map-v1.md`](feature-map-v1.md) — code as-built có thể vẫn tồn tại; V1 **không** marketing, nav, billing, hay QA GTM.*

| Item | As-built / route | Ghi chú |
|------|------------------|---------|
| **So sánh 2 video (F3)** | `/app/compare`, `CompareScreen.tsx`, `report_compare.py` | POST `/stream` `compare_videos`; 1 credit; ẩn khỏi V1 UX. Wave 2 / agency |
| **Watchlist đối thủ + push alert** | — | Wave 2 |
| **Douyin trend forecast** (lead-time productized) | — | Wave 2; V1 chỉ `TrendsDouyinCard` optional trên `/app/trends` |
| **Passive FYP mirror / push feed** | — | Wave 2+ |
| **Legacy `/channel/analyze`** | *(removed)* | Dropped migration `20260715000001`; V1+ uses **`POST /channel/diagnose`** only |
| **Legacy chat sessions mới** | `chat_sessions`, `/api/chat` | V1: chỉ maintain `history_union` cho rows cũ |
| **Answer follow-up (turn 2+)** | `POST /answer/sessions/{id}/turns`, `append_turn` | Sau `video_diagnosis`: pattern, timing, ideas, generic, creators, script…; TimelineRail |
| **Composer — câu hỏi text** | `intent-router.ts`, `/api/chat` | Intents ⑤⑥⑦ + research Q&A; V1 composer = URL/@handle theo pill only |
| **Script — thư viện câu searchable** | — | v1.1 |
| **Auto-post / scheduler** | — | Out of product |
| **Viral alignment score** | — | Deferred (ρ &lt; 0.35) |
| **Shopee / affiliate product ranking** | — | Kalodata territory |
| **TikTok OAuth / Ads API** (boost attribution) | — | V1: inference ED + corpus only |
| **User self-report “đã chạy ads”** | — | V1: tự động only |
| **English UI, native apps, recurring subscription** | — | Project rules |
| **Đổi route `/app/trends` → `/app/xu-huong`** | Open product (D4 in vision doc) | SEO/i18n |
| **Xu hướng — segment TikTok \| Douyin (cấp 1)** | — | V1 freeze: một trang Explore; `TrendsDouyinCard` optional |
| **Xu hướng — block “Hôm nay” / ritual duplicate** | — | Ritual chỉ Studio `HomeSuggestionsToday` tier I |
| **Cross-niche breakout lane (Wave 3b)** | — | **Shipped** on `/app/trends` — `CrossNicheBreakoutLane`; distinct from Home tier III (within-niche) |
| **F6 full UX reshape** | — | V1: giữ Công thức + Kho video; chỉ handoff §4.10 |

**Maintenance:** Khi defer hoặc cut một tính năng khỏi V1, **xóa** khỏi `feature-map-v1.md` và **thêm một dòng** vào bảng này trong cùng PR doc.

---

## 1. Landing & Authentication

### /) Landing page
- **FE:** `src/routes/_index/route.tsx` (line 18), `src/routes/_index/LandingPage.tsx`
- **BE endpoints:**
  - GET `/api/landing-stats` (Vercel Edge, `api/landing-stats.ts`) → aggregated hook statistics + thumbnail IDs for hero carousel
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
  - `?session=<id>` → redirect to `/app/history/chat/<id>` (legacy chat URLs)
  - If no niche in profile → redirect to `/app/onboarding`
  - Otherwise render HomeScreen (lazy)
- **Query:** `useProfile()` → checks `profileHasNiche()` at line 44
- **Status:** shipped & live
- **Evidence:** `routes.ts:14`, redirect logic at lines 27–46

### /app/home (implicit via HomeScreen)
- **FE:** `src/routes/_app/home/HomeScreen.tsx`
- **Sub-surfaces:**
  1. **Ticker marquee** — `TickerMarquee`, pulls `/home/ticker`
  2. **Gợi ý hôm nay (3 tầng)** — `HomeSuggestionsToday.tsx`:
     - **Tier I — Hôm nay quay ngay:** `MorningSignalStrip` (`useClassMorningSignals` → `content_class_intelligence` MV, primary junction only, energy toggle `productionFriction.ts`) + `StudioHero` (`GET /home/daily-ritual` — 3 ranked ritual scripts)
     - **Tier II — Công thức nền:** `HooksTable` embedded (`useTopPatterns` → `video_patterns` / pattern scope from legacy niche + junction)
     - **Tier III — Cảm hứng:** `BreakoutGrid` (`useTopBreakouts` → `video_corpus`, **within** user's junction `content_class_id`; cap 3; rotating window; copy: breakout trong ngách từ creator khác) → link `/app/trends`
  3. **Starter creators** — `/home/starter-creators`
  4. **Pulse data** — `DataFreshnessPill` + `/home/pulse`
  5. **Query composer** — 4 pills + Cơ bản/Chuyên sâu → intent router → `/app/answer` | `/app/channel` | `/app/script`
  6. **Niche picker** — session-scoped browse anchor (`studioNicheSession.ts`); profile `creator_niche_id` is SSOT
- **FE hooks (browse filter):** `fetchContentClassIdsForCreatorNiche`, `applyVideoCorpusNicheFilter` (`src/lib/corpusNicheFilter.ts`)
- **BE endpoints:**
  - GET `/home/pulse` → `cloud-run/getviews_pipeline/routers/home.py:31`
  - GET `/home/ticker` → `home.py:49` — hot hooks (3 per niche)
  - GET `/home/starter-creators` → `home.py:67`
  - GET `/home/daily-ritual` → `home.py:87` — 3-tier ritual (scripts / channel / trend)
  - POST `/home/regenerate-ritual` → `home.py:181` — on-demand ritual regen (202)
- **Synthesis paths invoked (batch/cron):**
  - Daily ritual: `/batch/morning-ritual` or `POST /admin/trigger/morning_ritual`
  - Pulse aggregation (daily corpus snapshot)
  - Class MV refresh chain (post-ingest): `content_class_intelligence` → tier → `creator_niche_content_class_stats` (see [`two-axis-niche-model.md`](two-axis-niche-model.md) §9)
- **DB tables / MVs:** `daily_ritual`, `starter_creators`, `answer_sessions`, `answer_turns`, `video_corpus`, `creator_niche_content_classes`, `content_class_intelligence` (MV), `creator_niche_content_class_stats` (MV), `video_patterns`
- **Status:** shipped & live

---

## 3. /app/answer — Video Diagnosis + Q&A Research

**Central surface for structured video reports (Win/Flop). Replaces deleted `/app/video` (2026-04-28).**

**V1 product:** **single turn** per video session — no follow-up Q&A in Answer UI ([`feature-map-v1.md`](feature-map-v1.md) §4.10.1). As-built still supports turn 2+ (see ② below) — Post-V1.

- **FE:** `src/routes/_app/answer/AnswerScreen.tsx` (`routes.ts:15`)
- **Entry points:**
  - `/app/answer` (fresh) or `/app/answer?session=<id>` (resume; alias `session_id`)
  - Home composer `?q=<query>`; channel deep link; compare single-side fallback → `/app/answer` + `state.prefillUrl`
- **Query params:** `?session=` | `?session_id=`, `?q=`

### FE streaming contract
- **`useSessionStream({ mode: "answer_turn" })`** → `POST /answer/sessions/{id}/turns` (not `/stream`)
- **`createAnswerSession()`** → `POST /answer/sessions` with optional `Idempotency-Key`
- **Intent router:** `intent-router.ts` maps `video_diagnosis` → `answer:video`; other intents → `answer:pattern` | `answer:timing` | `answer:generic` | etc.
- **Session safety:** banner when `?q=` URL disagrees with loaded session video (`AnswerScreen.tsx`)

### ① Primary turn (video URL → structured diagnosis)
- **BE endpoints:**
  - POST `/answer/sessions` (`answer.py:62`) — create session row
  - POST `/answer/sessions/{session_id}/turns` (`answer.py:94`) — SSE `ReportV1`; TD-4 replay via `resume_stream_id` + `resume_from_seq`
- **Server orchestration:** `append_turn()` (`answer_session.py`) → **`build_video_report()`** (`report_video.py:405`):
  1. Corpus path: `run_video_analyze_pipeline()` (`video_analyze.py`)
  2. Else on-demand: `run_video_analyze_on_demand()`
  3. Narrative layer: `finalize_video_narrative_layer()` → **`synthesize_diagnosis_v2()`** (v6 section pool in `gemini.py`)
  4. Persist: `video_diagnostics` (`source` corpus | on_demand), `answer_turns` payload
- **Embedded reference tiles (2026-05):**
  - Canonical: `narrative_vi.diagnosis_vi.sections[].embedded_tiles` joined to `reference_videos` in `DiagnosisSectionRenderer.tsx`
  - Cache repair: `embed_contract_version` + `repair_diagnosis_vi_embedded_tiles()` on corpus/on-demand cache hits (`finalize-lite`); `ON_DEMAND_RESPONSE_SCHEMA_VERSION = 3`
  - FE fallback: `embeddedTilesFromEvidenceAnchors` when anchors carry `aweme_id` (`VideoBody.tsx`)
- **Signals (read-only lookups):** `hook_effectiveness`, `video_patterns`, `content_class_intelligence`, `signal_grades`, corpus peers; **`peer_percentile` / `peer_percentile_label`** on diagnosis payload → `FlopDiagnosisStrip` (`VideoBody.tsx`)
- **DB tables:** `answer_sessions`, `answer_turns`, `video_diagnostics`, `video_corpus`, `content_classifications`
- **Status:** shipped & live

### ② Follow-up turns (Q&A) — not in V1 GTM

**V1:** hidden — see [Post-V1 backlog](#post-v1-backlog-không-trong-product-vision-v1).
- Same POST `/answer/sessions/{id}/turns` with turn `kind` from `appendTurnKindForQuery()` (timing, creators, script, generic, …)
- **Synthesis:** intent-specific `run_*` in `pipelines.py` (e.g. `run_trend_spike`, `run_creator_search`, `run_shot_list`)
- Text-only free intents may also use Vercel **`POST /api/chat`** when routed to chat mode (see §13)
- **Status:** shipped & live

### ③ In-session timeline + session CRUD
- **TimelineRail** — jump between turns; GET `/answer/sessions/{session_id}` (`answer.py:280`)
- **PATCH** `/answer/sessions/{session_id}` (`answer.py:291`) — title / metadata
- **DELETE** `/answer/sessions/{session_id}` (`answer.py:306`) — soft-delete session
- **List:** GET `/answer/sessions` (`answer.py:260`)

**Answer error codes (FE):** `insufficient_credits`, `daily_free_limit`, `stream_failed`, `stream_timeout`, `session_not_found`, `idempotency_conflict` (`AnswerScreen.tsx`)

---

## 4. /app/history — Session Archive

- **FE:** `src/routes/_app/history/route.tsx` → HistoryScreen; detail at `/app/history/chat/:sessionId`
- **BE:**
  - **Primary list:** Supabase RPC **`history_union`** (+ **`search_history_union`** when searching) — merges `answer_sessions` and legacy `chat_sessions` (`useHistoryUnion.ts`)
  - GET `/answer/sessions` — answer-only paginated list (also used elsewhere)
  - GET `/answer/sessions/{session_id}` — full answer session + turns
- **Filters:** niche, intent type, date range (client-side on union rows)
- **DB tables:** `answer_sessions`, `answer_turns`, `chat_sessions`, `chat_messages` (legacy rows still listed)
- **Status:** shipped & live
- **Evidence:** `HistoryScreen.tsx` (union RPC), `routes.ts:16–17`

---

## 5. /app/channel — Channel Deep-Dive Analysis

- **FE:** `src/routes/_app/channel/ChannelScreen.tsx` (`routes.ts:27`)
- **Entry:** `/app/channel?handle=<@handle>` (+ optional `creator_niche_id`, `force_refresh=true`, `video_url`)
- **BE endpoints:**
  - GET `/channel/user-search` (`video.py:100`) — handle autocomplete
  - POST `/channel/diagnose` (`video.py:736`) — SSE narrative channel diagnosis (Lightreel-style v2)
  - POST `/channel/refresh-mine` (`video.py:143`) — refresh signed-in user's channel
- **Cache:** `channel_diagnoses` row, **`max_age_days=7`** default (`_fetch_channel_diagnoses_cache`, `video.py:291`); `force_refresh=true` bypasses
- **Synthesis:** `channel_diagnose.py` + `channel_diagnose_prompts.py`; corpus-first peers + live EnsembleData hybrid
- **Credit cost:** **3** `credits_remaining` per cache-miss diagnosis — FE `ChannelScreen.tsx` `CREDIT_COST=3`; BE `channel_diagnose.CHANNEL_DIAGNOSE_CREDIT_COST=3` (pre-check balance ≥3, then 3× `decrement_credit` RPC). Cache hit free. No credit rollback on `stream_failed` (as-built).
- **DB tables:** `channel_diagnoses`, `video_patterns`, `hook_effectiveness`, `creator_velocity`, `niche_insights`
- **Status:** shipped & live

---

## 6. /app/trends — Niche Intelligence & Pattern Explorer

- **FE:** `src/routes/_app/trends/route.tsx` → `ExploreScreen.tsx` (lazy + `Suspense`)
- **Params:** `?niche=<legacy_niche_id>` (defaults to user's primary legacy niche via `profileFirstNicheId`)
- **Primary blocks (V1 freeze):**
  1. **Công thức từ video viral trong ngách** — `TrendsPatternThesisHero` + `TrendsPatternGrid` + `PatternModal` (`useTopPatterns`, `video_patterns`)
  2. **Kho video** (`II — KHO VIDEO`) — searchable `video_corpus` grid + `ExploreCorpusVideoModal`; filters via `applyVideoCorpusNicheFilter` (`content_class_id IN junction`)
- **Auxiliary blocks (shipped, not V1 gate):**
  - **`CrossNicheBreakoutLane`** — `useCrossNicheBreakouts`: cap 3 tiles, `content_class_id NOT IN` user's junction, `breakout_multiplier ≥ 1.5`, 14d window (**cross-format** inspiration — distinct from Home tier III within-niche breakouts)
  - **`TrendsRail`** (desktop, `lg+`) — `useTrendsRailVideos`: top 5 breakouts (30d, `ingest_loop_niche_id`) + top 5 virals; list layout with navigate-to-answer CTA
  - **`TrendsNichePills`**, **`TrendingSoundsSection`**, **`TrendsDouyinCard`**
- **Thin-corpus banner:** `useContentClassIntelligence` — sum junction `sample_size` from `content_class_intelligence` MV gates “dữ liệu chưa đầy đủ” copy
- **BE (direct Supabase reads):** `video_corpus`, `creator_niche_content_classes`, `content_classifications`, MVs `content_class_intelligence`, `content_class_tier_intelligence`, `creator_niche_content_class_stats`
- **BE (Cloud Run):** GET `/home/pulse` (shared hook); GET `/script/hook-patterns` (`script.py:84`)
- **Legacy tables still referenced in places:** `niche_taxonomy` (pill labels / legacy id bridge), `trend_velocity`, `hook_effectiveness`
- **Status:** shipped & live

---

## 7. /app/script — Content Script Workshop

- **FE:** `src/routes/_app/script/route.tsx` → ScriptScreen; shoot sub-route `app/script/shoot/:draftId`
- **BE endpoints** (`routers/script.py`):
  - GET `/script/scene-intelligence` (37)
  - GET `/script/idea-references` (58)
  - GET `/script/hook-patterns` (84)
  - POST `/script/generate` (105)
  - POST `/script/save` (138) — legacy
  - POST `/script/drafts` (147)
  - GET `/script/drafts` (156)
  - GET `/script/drafts/{draft_id}` (173)
  - POST `/script/drafts/{draft_id}/export` (192)
- **Synthesis:** `run_shot_list()`; scene intel via `/batch/scene-intelligence`
- **DB tables:** `draft_scripts`, `video_shots`, `scene_intelligence`, `hook_effectiveness`
- **Status:** shipped & live (core) / WIP (scene intelligence batch)

---

## 8. /app/douyin — Douyin Corpus & Analytics

- **FE:** `src/routes/_app/douyin/route.tsx` → DouyinScreen
- **BE endpoints** (`routers/douyin.py`):
  - GET `/douyin/feed` (28)
  - GET `/douyin/patterns` (50)
- **Batch:** `/batch/douyin-ingest` (215), `/batch/douyin-synth` (1139), `/batch/douyin-patterns` (1257)
- **DB tables:** `douyin_video_corpus`, `douyin_video_shots`, `douyin_niche_taxonomy`, `douyin_patterns`
- **Status:** shipped & live (read) / WIP (streaming diagnosis UI)

---

## 9. /app/compare — Two-Video Comparison

- **V1 product:** **không ship** — xem [Post-V1 backlog](#post-v1-backlog-không-trong-product-vision-v1). Route có thể giữ; ẩn nav GTM V1.
- **FE:** `src/routes/_app/compare/CompareScreen.tsx`
- **Entry:** `/app/compare?url_a=&url_b=`
- **Flow:** `useSessionStream()` (default **chat** mode) → POST **`/stream`** with `compare_videos` → `run_compare_pipeline()` (`report_compare.py`) parallelizes **`run_video_diagnosis()`** per URL, then delta
- **Single-side fallback:** surviving side returns `video_diagnosis` shape → navigate **`/app/answer`** with `prefillUrl` (not `/app/video`)
- **DB tables:** `video_corpus`, `video_diagnostics`, `video_patterns`
- **Status:** shipped in codebase · **not in V1 GTM**

---

## 10. /app/onboarding

- **FE:** `src/routes/_app/onboarding/route.tsx`
- **Purpose:** Single-niche picker — **16 active** `creator_niches` rows → `profiles.creator_niche_id` (includes restored `comedy`, new `art_craft`)
- **Status:** shipped & live

---

## 11. /app/settings, /app/learn-more, /app/pricing, /app/checkout, /app/payment-success

- **FE:** Lazy routes `routes.ts:30–34`
- **/app/settings:** profile + niche edit; admin API keys when applicable
- **/app/pricing:** static pack display (links to checkout)
- **/app/checkout:** **PayOS** one-time credit packs via Supabase Edge Function **`create-payment`**; payment methods MoMo / VietQR (`CheckoutScreen.tsx`). **Not** recurring subscription.
- **/app/payment-success:** return URL after PayOS redirect
- **/app/learn-more:** support copy references PayOS transaction IDs for refunds
- **Status:** shipped & live

---

## 12. /app/admin — Operator Dashboard

- **FE:** `src/routes/_app/admin/route.tsx` — CorpusHealth, EnsembleCredits, Funnel, Triggers, Layer0, Logs, etc.
- **Observability** (`routers/admin.py`):
  - GET `/admin/corpus-health` (771)
  - GET `/admin/ensemble-credits` (861)
  - GET `/admin/ensemble-call-sites` (880)
  - GET `/admin/ensemble-history` (908)
  - GET `/admin/alert-fires` (983)
  - GET `/admin/logs` (997)
  - GET `/admin/action-log` (1038)
  - GET `/admin/funnel` (1052)
  - GET `/admin/layer0-health` (1453)
- **Triggers:**
  - POST `/admin/trigger/ingest` (1228)
  - POST `/admin/trigger/morning_ritual` (1241) — same workload as `/batch/morning-ritual`
  - POST `/admin/trigger/analytics` (1259)
  - POST `/admin/trigger/scene_intelligence` (1267)
  - POST `/admin/trigger/thumbnail_backfill` (1275)
  - POST `/admin/trigger/backfill_classification` (1312)
  - POST `/admin/trigger/refresh` (1330)
  - POST `/admin/trigger/reclassify_format` (1346)
  - POST `/admin/trigger/r2_janitor` (1357)
  - POST `/admin/trigger/layer0` (1371)
  - POST `/admin/trigger/enrich_shots_top500` (1382)
  - POST `/admin/trigger/viral_score_backtest` (1394)
- **User/cron equivalents:** `POST /home/regenerate-ritual` (per user); `POST /batch/morning-ritual` (cron)
- **Status:** shipped & live

---

## 13. Vercel Edge Functions

### `api/chat.ts`
- **Endpoint:** POST `/api/chat` (Edge Runtime)
- **Purpose:** **Text intents ⑤⑥⑦ + follow-ups** — Gemini `gemini-3.1-flash-lite` (or `GEMINI_SYNTHESIS_MODEL`), free-intent daily cap, writes `chat_sessions` / `chat_messages`. Used when FE streams in **chat** mode (not `answer_turn`).
- **Evidence:** `api/chat.ts` header comment; `FREE_INTENTS` set lines 32–37

### `api/landing-stats.ts`
- **Endpoint:** GET `/api/landing-stats` — landing hero hooks + R2 thumbnails
- **Evidence:** `src/routes/_index/route.tsx` loader

---

## 14. Background Jobs (Cloud Run + pg_cron)

All `/batch/*` in `cloud-run/getviews_pipeline/routers/batch.py` (require `BATCH_SECRET`). Vault `cloud_run_api_url` must point at **batch** service.

| Job | Endpoint (line) | Synthesis | DB write | Status |
|---|---|---|---|---|
| Corpus ingest | `/batch/ingest` (95) | `corpus_ingest.py` — 1× Gemini extraction → `analysis_json` + ~25 promoted columns ([utilization audit](corpus-gemini-utilization-audit.md)). **Selection criteria redesign (instructiveness rank):** [`corpus-ingest-criteria-v1.md`](corpus-ingest-criteria-v1.md) | `video_corpus`, `video_shots`, `video_patterns`, `content_classifications`, `signal_grades` | live |
| Post-processing | `/batch/post-processing` (160) | analytics + signals | `niche_insights`, `signal_grades` | live |
| Douyin ingest | `/batch/douyin-ingest` (215) | Douyin metadata | `douyin_video_corpus`, `douyin_video_shots` | live |
| Re-ingest videos | `/batch/reingest-videos` (278) | re-extract IDs | `video_corpus`, `video_shots` | live |
| Ingest queue drain | `/batch/process-ingest-queue` (313) | drains queue | `corpus_ingest_queue`, `video_corpus` | live |
| Channel/feed refresh | `/batch/refresh` (376) | channel refresh | `channel_diagnoses` | live |
| Reclassify format | `/batch/reclassify-format` (405) | format classifier | `content_classifications` | live |
| Classification backfill | `/batch/backfill-classification` (445) | two-axis backfill | `content_classifications`, `signal_grades` | live |
| Sound aggregate | `/batch/sound-aggregate` (481) | sounds rollup | `trending_sounds` | live |
| Trend velocity | `/batch/trend-velocity` (518) | weekly velocity | `trend_velocity` | live |
| R2 janitor | `/batch/r2-janitor` (568) | orphan cleanup | R2 only | live |
| Thumbnail backfill | `/batch/backfill-thumbnails` (633) | frame0 repair | `video_shots` | live |
| Analytics | `/batch/analytics` (896) | niche rollup | `niche_insights` | live |
| Layer0 reprocess | `/batch/layer0` (979) | failed extractions | `video_corpus` | live |
| Morning ritual | `/batch/morning-ritual` (1031) | per-user ritual | `daily_ritual`, `starter_creators` | live |
| Pattern decks | `/batch/pattern-decks` (1064) | hook aggregates | `video_patterns` | live |
| Douyin synth | `/batch/douyin-synth` (1139) | adapt grading | `douyin_video_corpus` | live |
| Scene intelligence | `/batch/scene-intelligence` (1202) | scene types | `scene_intelligence` | WIP |
| Douyin patterns | `/batch/douyin-patterns` (1257) | pattern synth | `douyin_patterns` | live |

**pg_cron (not in batch.py):** channel_diagnoses prune (>7d), starter creators reseed, Monday health digest, pg_net batch HTTP 4xx watcher (hourly).

---

## 15. Cross-Feature Observations

### Dual SSE orchestration (do not conflate)

| Path | FE hook | Endpoint | Typical use |
|---|---|---|---|
| **Answer research** | `useSessionStream({ mode: "answer_turn" })` | `POST /answer/sessions/{id}/turns` | `/app/answer` video + Q&A turns, `ReportV1` |
| **Chat / compare / legacy stream** | `useSessionStream()` (default) | `POST /stream` (`intent.py:265`) | Compare, some chat-era intents, `run_video_diagnosis` compare arms |
| **Text intents Edge** | chat mode → Vercel | `POST /api/chat` | Free/cheap text follow-ups, format lifecycle |

**Video diagnosis synthesis (answer path):** `build_video_report` → `run_video_analyze_pipeline` | `run_video_analyze_on_demand` → `finalize_video_narrative_layer` → `synthesize_diagnosis_v2` — **not** a direct call to `run_video_diagnosis()` (that function serves `/stream` and compare internals).

**Gemini:** `gemini_text_only()` + prompt dedup cache across paths.

### Niche taxonomy (two-axis, taxonomy v2 2026-05-22)
- **UX axis:** `creator_niches` — **16 active** buckets (`comedy` id=5 restored; `art_craft` id=17 added; `pets_home` id=13 retired)
- **Content axis:** `content_classifications` — **82 classes** (77 video + 5 carousel); class **82** `ai_tool_workflow_tutorial` (primary `tech_gaming`, secondary `business`)
- **Junction:** `creator_niche_content_classes` — M:N map; browse filter = `content_class_id IN (...)` via `applyVideoCorpusNicheFilter` (Phase C: no `video_corpus.niche_id` FE fallback)
- **Legacy bridge:** `niche_taxonomy` + `ingest_loop_niche_id` on corpus rows; `legacyNicheIdForCreatorNiche()` / Python mirror for ingest loop + Trends rail
- **User:** `profiles.creator_niche_id` (single niche since 2026-05-05)
- **Class MVs (canonical browse benchmarks):** `content_class_intelligence`, `content_class_tier_intelligence`, `creator_niche_content_class_stats` — nightly refresh §9 [`two-axis-niche-model.md`](two-axis-niche-model.md); legacy `niche_intelligence` MV refresh **skipped** in prod (`REFRESH_NICHE_INTELLIGENCE_MV=false`)

### Dormant / legacy
- `/app/video` deleted 2026-04-28 — render `VideoBody` inside answer sessions only
- `chat_messages` / `chat_sessions` — still in `history_union`; no new product surface
- `format_lifecycle` table — batch-populated; FE uses `format_lifecycle_optimize` intent → `answer:lifecycle`
- `POST /channel/analyze` — **removed** (`20260715000001`); use `POST /channel/diagnose`

### Data freshness
- **Pulse:** daily `as_of`
- **Ticker:** ~3-day hook window, nightly refresh
- **Trend velocity:** nightly / weekly job
- **Channel diagnoses:** **7-day** DB cache (`max_age_days=7`); in-memory channel snapshot staleness gate ~18–24h for live ED refresh paths

### Error recovery (TD-1–TD-5)
- **SSE replay:** `resume_stream_id` + `resume_from_seq` on answer turns (60s server buffer, TD-4)
- **Idempotency:** `Idempotency-Key` on session create (~120s)
- **Credits:** atomic `decrement_credit()`; rollback on stream failure via `credit_transactions`

---

## Shipping Status Summary

| Surface | FE Route | Status | Notes |
|---|---|---|---|
| Landing | / | live | Pre-rendered SEO |
| Auth | /login, /signup, /auth/callback | live | Supabase; Facebook OAuth |
| Home | /app | live | 3-tier Gợi ý hôm nay + Morning Signal + within-niche breakouts |
| Answer | /app/answer | live (video 1-turn V1) | `answer_turn` SSE; `FlopDiagnosisStrip` peer percentile; follow-up turns Post-V1 |
| History | /app/history | live | `history_union` RPC |
| Channel | /app/channel | live | 3 credits FE+BE on cache miss (Wave 0) |
| Trends | /app/trends | live | Pattern grid + kho video + cross-niche lane + desktop rail |
| Script | /app/script | live (core) | Scene intel WIP |
| Compare | /app/compare | codebase only (not V1 GTM) | `/stream`; see Post-V1 backlog |
| Douyin | /app/douyin | live (read) | Batch ingest live |
| Onboarding | /app/onboarding | live | Single niche |
| Settings | /app/settings | live | Profile + niche |
| Pricing | /app/pricing | live | Static packs |
| Checkout | /app/checkout | live | **PayOS** one-time |
| Admin | /app/admin | live | Operator dashboard |

---

## API Client Patterns

- **React Query:** server state (profile, history union, session detail)
- **SSE:** `useSessionStream()` — **`answer_turn`** → `/answer/sessions/:id/turns`; default → Cloud Run `/stream` or Edge `/api/chat`
- **Replay:** TD-4 resume params; `savePendingAnswerStream` / `clearPendingAnswerStream` for tab recovery
- **Auth:** Supabase JWT `Authorization: Bearer` → Cloud Run `require_user`

---

## Key Infrastructure Files

| Area | Path |
|---|---|
| Routes | `src/routes.ts` |
| Intent routing | `src/routes/_app/intent-router.ts` |
| Browse / junction filter | `src/lib/corpusNicheFilter.ts`, `src/lib/profileNiches.ts` |
| Class intelligence hooks | `src/hooks/useContentClassIntelligence.ts`, `src/hooks/useClassMorningSignals.ts`, `src/hooks/useCrossNicheBreakouts.ts`, `src/hooks/useTopBreakouts.ts`, `src/hooks/useTrendsRailVideos.ts` |
| Answer API | `src/lib/answerApi.ts`, `src/hooks/useSessionStream.ts` |
| Video report | `cloud-run/getviews_pipeline/report_video.py`, `video_analyze.py` |
| Legacy stream diagnosis | `cloud-run/getviews_pipeline/pipelines.py` (`run_video_diagnosis`) |
| Compare | `cloud-run/getviews_pipeline/report_compare.py` |
| Routers | `cloud-run/getviews_pipeline/routers/{answer,video,intent,home,script,admin,batch,douyin}.py` |
| Prompts | `prompts.py`, `diagnose_prompts.py`, `channel_diagnose_prompts.py` |
| Embed repair | `gemini.py` (`repair_diagnosis_vi_embedded_tiles`, `EMBED_CONTRACT_VERSION`) |
| FE diagnosis render | `src/components/v2/answer/DiagnosisSectionRenderer.tsx`, `VideoBody.tsx` |
| DB | `supabase/migrations/` |
| Signals | `cloud-run/getviews_pipeline/signals/` — `base`, `registry`, `channel`, `commerce`, `compliance`, `context_signals`, `distribution`, `douyin`, `editing`, `engagement`, `hook`, `metadata`, `performance`, `persona`, `reference`, `salience`, `script`, `sound`, `triggers` |

**Maintenance rule:** When adding a route, endpoint, or changing orchestration, update this file **and** [`system-design.md`](system-design.md) §3–§4 in the **same commit**; bump both `main @ <short-sha>` headers.
