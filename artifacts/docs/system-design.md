# System Design — GetViews.vn

**Last updated:** 2026-05-20 (`6a69ab3`)  
**Status:** Living document. Update in the same commit as any architectural change.

**Surface inventory (routes, endpoints, synthesis paths, shipping status):** [`feature-map.md`](feature-map.md) — per-route source of truth. **Orchestration / invariants:** this file. **Corpus Gemini field utilization:** [`corpus-gemini-utilization-audit.md`](corpus-gemini-utilization-audit.md). Update docs and bump `main @ <sha>` / **Last updated** in the same commit when routes or pipelines change.

---

## 1. Component Map

```
┌─────────────────────────────────────────────────────────────────────┐
│  USER BROWSER (PWA)                                                  │
│  React SPA · Vite · React Router v7 · TanStack Query               │
│  Hosted on Vercel (CDN + Edge network)                              │
└──────────┬───────────────┬────────────────────────────────────────┘
           │               │
           │ POST /api/*   │ SSE (direct HTTP, Supabase JWT)
           ▼               ▼
┌──────────────┐   ┌──────────────────────────────────────────────────┐
│ Vercel Edge  │   │  Cloud Run · asia-southeast1                      │
│ /api/chat    │   │                                                    │
│ /api/        │   │  getviews-pipeline-USER                           │
│ landing-stats│   │  (min:1, 2Gi, 600s timeout)                       │
│              │   │  Routers: /intent /video /script                  │
│ Auth:        │   │           /home /answer /douyin                   │
│ Supabase JWT │   │           /health /batch_proxy                    │
│              │   │                                                    │
│ Calls:       │   │  getviews-pipeline-BATCH                          │
│ Gemini API   │   │  (min:0, 4Gi, 3600s timeout)                      │
└──────┬───────┘   │  Routers: /batch/* /admin/* /health               │
       │           │                                                    │
       │           │  Auth: Supabase JWKS (asymmetric, stateless)       │
       └─────────┬─┴──────────────────────┬─────────────────────────┘
                 │                         │
                 ▼                         ▼
        ┌─────────────────┐      ┌─────────────────────┐
        │  Gemini API     │      │  EnsembleData API   │
        │  (Google Cloud) │      │  (TikTok metadata)  │
        │  gemini-3.x     │      │  Wood plan          │
        │  flash-lite /   │      │  1,500 units/day    │
        │  flash-preview  │      └─────────────────────┘
        └─────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  Supabase · Project: lzhiqnxfveqttsujebiv                          │
│                                                                     │
│  Postgres (RLS on every table)                                     │
│  Auth (Google OAuth + Facebook OAuth — FB non-negotiable for VN)   │
│  Edge Functions (Deno) — webhooks + cron                           │
│  Storage — not used (R2 handles frames/thumbnails/videos/shots)    │
│  pg_cron — schedules HTTP calls to Cloud Run batch pod             │
└────────────────────────────────────────────────────────────────────┘
                 │
                 ▼
        ┌──────────────────────────────────────┐
        │  Cloudflare R2 — single public bucket │
        │  getviews-frames (R2_BUCKET_NAME)     │
        │  Namespaces:                          │
        │   frames/{id}/{0,1,2}.png             │
        │   thumbnails/{id}.png or .jpg         │
        │   videos/{id}.mp4                     │
        │   video_shots/{id}/{n}.jpg            │
        │  No signed URLs — all public CDN      │
        └──────────────────────────────────────┘
```

**Key boundaries:**
- `GEMINI_API_KEY` is server-only. Never in client bundle (`VITE_` prefix forbidden).
- RLS is the only authorization boundary for DB access. No middleware layer.
- Cloud Run user pod validates JWT via Supabase JWKS — no round-trip to Supabase Auth.
- Vercel Edge validates JWT by passing it to the Supabase client (anon key + JWT = scoped session).

---

## 2. Frontend Routes

All routes declared in `src/routes.ts` (explicit, not file-based).

| Path | Surface | Notes |
|------|---------|-------|
| `/` | Landing | Pre-rendered for SEO. Eager-loaded. |
| `/login` `/signup` | Auth | Supabase OAuth redirect. |
| `/auth/callback` | Auth | OAuth callback handler. |
| `/app` | App shell | Auth-guarded by `_app/layout.tsx`. `?session=` → `/app/history/chat/:id`. No niche → `/app/onboarding`. |
| `/app/onboarding` | Onboarding | Single-niche picker (`profiles.creator_niche_id`). |
| `/app/answer` | Answer | **Primary** structured video report + Q&A turns (`ReportV1`). Replaces deleted `/app/video`. |
| `/app/history` | History | Session list via `history_union` RPC. |
| `/app/history/chat/:sessionId` | History | Read-only legacy chat transcript. |
| `/app/trends` | Trends | Niche intelligence + hook effectiveness. |
| `/app/douyin` | Douyin | Douyin trend analysis. |
| `/app/compare` | Compare | Two URLs → `POST /stream` `compare_videos`. |
| `/app/channel` | Channel | Channel deep-dive (`POST /channel/diagnose`). |
| `/app/script` | Script | Script generation. |
| `/app/script/shoot/:draftId` | Script | Shoot-mode for a draft. |
| `/app/settings` | Settings | Profile + niche edit. |
| `/app/learn-more` | Learn more | Support / refund copy (PayOS). |
| `/app/pricing` `/app/checkout` `/app/payment-success` | Billing | PayOS **one-time** credit packs (`create-payment` Edge Function). |
| `/app/admin` | Admin | Gated by `profiles.is_admin`. Observability + manual batch triggers. |

**Deleted:** `/app/video` (2026-04-28) — `VideoBody` renders inside `/app/answer` sessions only.

Every `/app/*` leaf route is code-split with `React.lazy` + `Suspense`.  
Do not use React Router `clientLoader` — TanStack Query is the data layer.

---

## 3. Intent Routing

`src/routes/_app/intent-router.ts` — `detectIntent(query)` classifies input; `resolveDestination()` maps intent → **screen** (`answer:video`, `answer:pattern`, `/app/compare`, `/app/channel`, …). **Transport** (which HTTP endpoint) is chosen separately by the screen/hook — see §4.

```
User message
     │
     ├─ Two TikTok URLs?
     │      └─ YES → compare_videos → /app/compare → POST /stream
     │
     ├─ One TikTok URL?
     │      └─ YES → video_diagnosis → /app/answer → POST /answer/sessions/{id}/turns
     │                 (answer_turn SSE — NOT POST /video; route deleted)
     │
     ├─ Contains @handle?
     │      └─ YES → channel → /app/channel → POST /channel/diagnose
     │
     ├─ Explicit keyword (trends / douyin / script / …)?
     │      └─ YES → specialized intent → answer:* shelf or dedicated screen
     │
     └─ Text-only follow-up
              ├─ answer session continuation → POST /answer/sessions/{id}/turns (kind ≠ primary)
              └─ legacy chat / free text → POST /api/chat (Vercel Edge)
```

**Rule:** Never reinvent routing inside screen components. Extend `detectIntent()`, `resolveDestination()`, and `intent-router.test.ts`.

### Dual SSE transport (FE: `useSessionStream`)

| Mode | Endpoint | Typical surfaces |
|------|----------|------------------|
| `answer_turn` | `POST /answer/sessions/{id}/turns` | `/app/answer` (video + structured follow-ups) |
| default (`chat`) | `POST /stream` (`intent.py:265`) | `/app/compare`, legacy chat-era `video_diagnosis` |
| chat → Vercel | `POST /api/chat` | Free/cheap text intents ⑤⑥⑦ |

Both Cloud Run SSE paths use `stream_id` + `seq` and a **60s** in-memory replay buffer (TD-4). Answer turns also emit **heartbeat** frames every 10s during long Gemini work to avoid client idle timeout.

---

## 4. Video Analysis Flow (user-facing SSE)

The product has **two** user-facing video diagnosis transports. Do not conflate them.

### 4.1 Primary — Answer turn (Studio → `/app/answer`)

This is the default path when a creator pastes a TikTok URL in Home or Answer.

```
1. FE: detectIntent → video_diagnosis → navigate /app/answer
2. FE: createAnswerSession() → POST /answer/sessions (optional Idempotency-Key)
3. FE: useSessionStream({ mode: "answer_turn" })
        → POST /answer/sessions/{session_id}/turns (Supabase JWT)
4. Cloud Run: answer_append_turn → append_turn() (answer_session.py)
   ├─ primary kind: decrement_credit() ×1 via user JWT (TD-1)
   ├─ script kind: decrement_credit() ×3
   └─ other kinds: often free (see append_turn builder matrix)

5. append_turn → build_video_report() (report_video.py)
   ├─ A) Corpus hit: run_video_analyze_pipeline()
   │      └─ reads video_corpus + video_diagnostics; may short-circuit narrative cache
   └─ B) Corpus miss: run_video_analyze_on_demand()
          ├─ EnsembleData fetch + extraction (async_run_extraction_core / analyze_video)
          ├─ v4 hardening on extraction path
          └─ writes/updates video_diagnostics (source=on_demand)

6. finalize_video_narrative_layer() (video_analyze.py) — mutates response in place
   ├─ Cache hit with narrative_vi.van_de_chinh: skip Gemini synthesis; may run embed-tile repair (§4.3)
   └─ Miss: select_synthesis_references_for_video → synthesize_diagnosis_v2()
          (v6 section pool when GETVIEWS_DIAGNOSIS_SECTION_MODE=1)
          ├─ narrative_vi + diagnosis_vi.sections[].embedded_tiles
          ├─ format_cards, performance_tier, channel_context, reference_videos
          └─ posting context folded into distribution/diagnosis (no separate Timing report on answer)

7. SSE to browser: hello (seq 0) → step events → terminal ReportV1 payload
   └─ Chunks cached in session_store for TD-4 replay (no re-bill on successful resume)

8. Persist answer_turns.payload (ReportV1); video_diagnostics row holds on-demand cache
9. Optional: promote_on_demand_to_corpus() when quality_tier eligible (ingest_source write-once)
```

**Cold:** ~20–30s. **Warm** (diagnostics + narrative cache): ~2s.  
**Not used on this path:** `POST /video`, `pipelines.run_video_diagnosis()` as the top-level orchestrator.

### 4.2 Secondary — `/stream` (compare + legacy chat video)

```
1. FE: useSessionStream() default mode → POST /stream (intent.py)
2. intent normalized:
   ├─ compare_videos → run_compare_pipeline() → run_video_diagnosis() per URL + delta
   └─ video_diagnosis → run_video_diagnosis() directly (chat session_store context)
3. Uses pipelines.py orchestration + run_video_diagnosis_core inside the diagnosis stack
4. TD-3: profiles.is_processing guard on /stream path
5. Compare single-side failure → FE redirects to /app/answer with prefillUrl
```

`/app/compare` is the main live caller. New Studio work should stay on §4.1 unless explicitly adding a `/stream` consumer.

### 4.3 Embedded reference tiles (answer path)

**Canonical UI contract:** `narrative_vi.diagnosis_vi.sections[].embedded_tiles[]` joined to `reference_videos` by `aweme_id` in `DiagnosisSectionRenderer.tsx`.

**Poisoned-cache problem (2026-05):** Rows could cache `reference_videos` but zero `embedded_tiles` on all sections. Fixes:

| Mechanism | Where |
|-----------|--------|
| `EMBED_CONTRACT_VERSION` + `repair_diagnosis_vi_embedded_tiles()` | `gemini.py` |
| `finalize-lite` on corpus/on-demand cache hits | `finalize_video_narrative_layer`, `_try_on_demand_cache_hit` |
| `ON_DEMAND_RESPONSE_SCHEMA_VERSION = 3` | `video_analyze.py` — stale `cached_response` below min version re-synthesizes |
| FE fallback | `embeddedTilesFromEvidenceAnchors` when `evidence_anchors` carry `aweme_id` |

Channel diagnosis uses a **different** embed shape (`section_start.embedded_tiles` on SSE — §16); do not reuse video answer repair logic there.

### 4.4 Shared pipeline internals (both paths)

Extraction + diagnosis cores (§12) apply inside `run_video_analyze_*` and `run_video_diagnosis`:

- `async_run_extraction_core` / `run_extraction_core` → `ExtractionResult`
- `run_video_diagnosis_core` → `DiagnosisResult` (error extraction + structural parse)
- `finalize_video_narrative_layer` + `synthesize_diagnosis_v2` for the **answer** report shape
- Default model: **`gemini-3.1-flash-lite`** (override `GEMINI_SYNTHESIS_MODEL`)

---

## 5. Text Query Flow (Vercel Edge + answer follow-ups)

### 5.1 Vercel Edge (`/api/chat`)

```
1. Browser: detectIntent → follow_up_* (or format_lifecycle, creator_search in FREE_INTENTS)
2. Browser: POST /api/chat (Vercel Edge, Supabase JWT)
3. Edge: validate JWT, optional free-intent daily cap (100/day)
4. Edge: TD-1 decrement_credit() when intent is billable
5. Edge: stream Gemini (gemini-3.1-flash-lite default)
6. Writes chat_sessions + chat_messages (immutable)
```

No Cloud Run. Typical latency ~2–5s.

### 5.2 Answer-session text follow-ups

Structured follow-ups inside an existing `/app/answer` session use **`answer_turn`** SSE (§4.1) with `kind` ≠ `primary` and intent-specific `run_*` builders in `append_turn` — not `/api/chat`.

---

## 6. Cache Layers

| Layer | Storage | TTL | Key | Cost of miss |
|-------|---------|-----|-----|-------------|
| Video diagnosis | `video_diagnostics` (Supabase) | ~1h (application) | normalized `tiktok_url` / `video_id`; `cached_response.response_schema_version` + `embed_contract_version` gate stale blobs | ~30s + synthesis on miss |
| Channel diagnosis | `channel_diagnoses` | **7 days** | `(handle, video_url, niche_id)` | full re-diagnose |
| Corpus rows | `video_corpus` (Supabase) | permanent | `aweme_id` | full re-ingest |
| Channel snapshot | In-process (Cloud Run user pod) | 24h, 500 entries | `creator_handle` (normalized) | 1 EnsembleData query |
| TanStack Query | Browser memory | varies by hook | per query key | 1 Supabase query |

**URL normalization is mandatory** before cache lookups. `normalize_tiktok_url()` in Python; must stay in sync with `TIKTOK_URL_GLOBAL_RE` in `intent-router.ts`.

---

## 7. Billing & Credit Flow

```
1. User: /app/pricing → select pack
2. Browser: call create-payment Edge Function
3. Edge Function: POST to PayOS API → returns payment link
4. User: pays on PayOS page
5. PayOS: POST to payos-webhook Edge Function
6. Edge Function:
   ├─ Verify PayOS signature (PAYOS_CHECKSUM_KEY)
   ├─ Idempotency check: INSERT into processed_webhook_events (UNIQUE constraint) — TD-2
   └─ Grant credits: UPDATE profiles SET credits = credits + pack_size (upfront) — TD-5
7. User: credits visible immediately in app
8. Per analysis: decrement_credit() RPC — atomic, WHERE credits > 0 guard — TD-1
```

**PayOS is one-time payment, not subscription.** No recurring billing, no monthly top-up cron.

---

## 8. Background Jobs

### Supabase Edge Functions (Deno) — called by pg_cron or directly

| Function | Trigger | What it does |
|----------|---------|-------------|
| `cron-expiry-check` | Daily 02:00 UTC | Expires packs past their end date |
| `cron-reset-free-queries` | Daily 17:00 UTC | Resets free query count |
| `cron-reset-processing` | Every 5 min | Clears `is_processing` flags older than 5min (TD-3 safety net) |
| `cron-prune-webhooks` | Weekly Sunday 20:00 UTC | Prunes old `processed_webhook_events` rows |
| `cron-chat-archival` | Nightly 03:00 UTC | Archives old chat sessions |
| `cron-daily-health-digest` | Daily | Ops email (Resend) — corpus growth + Gemini cost |
| `payos-webhook` | PayOS HTTP POST | Payment confirmation → credit grant |
| `create-payment` | Browser call | Creates PayOS payment link |
| `send-email` | Internal | Resend transactional email (expiry reminders etc.) |

### pg_cron → Cloud Run batch pod (via Supabase Vault URL)

| Job | Schedule (UTC) | ICT | What it does |
|-----|---------------|-----|-------------|
| `cron-batch-morning-ritual` | Daily 15:00 | 22:00 | Generates 3-script bundle per user |
| `cron-batch-scene-intelligence` | Daily 21:30 | 04:30+1 | Scene-level corpus analysis |
| `cron-batch-ingest` | Daily 20:00 | 03:00+1 | Nightly EnsembleData TikTok ingest |
| `cron-batch-analytics` | Weekly Sunday 21:00 | Mon 04:00 | Weekly analytics roll-up |
| `cron-batch-sound-aggregate` | Weekly Monday 21:30 | Tue 04:30 | Sound trending aggregate |
| `cron-batch-trend-velocity` | Weekly Monday 22:30 | Tue 05:30 | Trend velocity refresh |
| `cron-pg-net-batch-http-4xx-watch` | Hourly | — | Monitors for 4xx responses to batch pod (Vault misconfiguration alert) |

**HI-13 (optional):** When `CORPUS_INGEST_USE_GEMINI_BATCH=true` on the batch pod, corpus **video** extraction is submitted as one Gemini **Batch API** job per niche shard using a **JSONL file** input ([batch file docs](https://ai.google.dev/gemini-api/docs/batch-api)). Carousel posts stay on the synchronous path. Failed or missing batch lines fall back to the existing `analyze_video` sync flow. `gemini_calls.is_batch` tags batch-tier cost (~50% standard for the same model, per pricing page).

**Vault dependency:** `cloud_run_api_url` and `cloud_run_batch_secret` in Supabase Vault must be kept in sync with the batch pod's actual URL and `BATCH_SECRET`. Rotation without updating both breaks all pg_cron jobs silently.

---

## 9. Data Model (Key Tables)

### Two parallel session data models (NOT legacy — both live)

GetViews runs **two coexisting session models**. Do not confuse them or try to consolidate:

| Model | Tables | Used by | Write path |
|-------|--------|---------|------------|
| **Chat model** (older) | `chat_sessions` + `chat_messages` | Text intents ⑤⑥⑦ (Vercel `/api/chat`), `/stream` Cloud Run path, history drawer, `session_store.py` context reconstruction | Cloud Run `intent.py` + Vercel Edge |
| **Answer sessions model** (newer) | `answer_sessions` + `answer_turns` | Structured video diagnosis (Intents ①③④), channel diagnosis, follow-up turns | Cloud Run `answer.py` + `answer_session.py` |

`history_union` + `search_history_union` SQL RPCs surface both models in one unified history drawer.
`chat_messages` is **immutable** — no UPDATE ever (see TD chat-immutable). `answer_turns` payload is append-only.
`gemini_calls` is logged from Cloud Run for both models; `user_id` may be null for answer-session calls (service-role path).

**Do not delete `chat_sessions` / `chat_messages`** — they hold all legacy text-intent history and are still written for every new text intent session.

| Table | Owner | Write path | Notes |
|-------|-------|-----------|-------|
| `profiles` | Supabase | Client (RLS), Edge Functions | `creator_niche_id` FK, `credits`, `is_processing`, `is_admin` |
| `creator_niches` | Supabase | Migrations only | **16 active** UX-facing buckets (taxonomy v2: `comedy` 5, `art_craft` 17; retired: `pets_home`) |
| `content_classifications` | Supabase | Migrations only | **82** analysis-facing categories (77 video + 5 carousel HI-16; class 82 AI) |
| `video_corpus` | Cloud Run batch | Service role only | 46K+ analyzed TikTok videos; `ingest_source` is write-once |
| `video_diagnostics` | Cloud Run user | Service role | On-demand diagnosis cache (1h TTL); `cached_response.response_schema_version` (bump invalidates stale rows when `meta.caption` / refs change) |
| `chat_sessions` | Supabase | Client + Cloud Run | Chat model — title, niche, soft-delete via `deleted_at` |
| `chat_messages` | Supabase | Cloud Run only | Chat model — immutable (no UPDATE); text intent transcripts |
| `answer_sessions` | Supabase | Client + Cloud Run | Answer model — session format, intent type |
| `answer_turns` | Supabase | Cloud Run (service role) | Answer model — append-only; `payload` is validated `ReportV1` JSON |
| `processed_webhook_events` | Supabase | Edge Function | UNIQUE constraint for PayOS idempotency |
| `niche_intelligence` | Supabase | Cloud Run batch | Materialized niche stats for TrendScreen |
| `vietnamese_asr_cache` | Supabase | Cloud Run (service role) | **HI-14:** Deduped GCP Speech-to-Text `vi-VN` segments per `video_id`; video paths only (carousels skip STT — HI-17) |

### Niche model (two-axis, since 2026-05-13)

- **`creator_niches`** (**16 active** buckets) — UX-facing. `profiles.creator_niche_id` FK. Taxonomy v2: `comedy` (5) and `art_craft` (17) active; retired: `pets_home` → `lifestyle`.
- **`content_classifications`** (**82** categories: 77 video + 5 carousel) — analysis-facing. `video_corpus.content_class_id`.
- **`creator_niche_content_classes`** — M:N junction with `is_primary` tie-break at ingest only (FE loads full junction).
- **Phase C (2026-05-21):** `video_corpus.niche_id` **dropped**. Cohort = `(content_class_id, creator_tier)`. Legacy bridge `legacyNicheIdForCreatorNiche()` for ingest loop only.
- **HI-11:** Production `NICHE_RESOLVER_MODE=route` on batch + user pods. Rollback: `shadow` — see [`two-axis-niche-cutover-runbook.md`](two-axis-niche-cutover-runbook.md).
- **Corpus browse:** `VITE_CORPUS_BROWSE_CLASS_FIRST` + `VITE_CORPUS_BROWSE_CLASS_ONLY` default on. Filter `content_class_id IN (...)` only. **Thin banner:** sum `content_class_intelligence.sample_size` across junction — **no** `niche_intelligence` fallback. Canonical: [`two-axis-niche-model.md`](two-axis-niche-model.md) §10.
- **Content-class pivot flags:** `CORPUS_SCORE_COHORT=class`, `CORPUS_INGEST_LOOP=class`, `LIVE_COHORT_CLASS_FIRST=true`, `CORPUS_WRITE_NICHE_ID=false`, `REFRESH_NICHE_INTELLIGENCE_MV=false`.
- **MV catalog (3):** `content_class_intelligence` (+ velocity/`lifecycle_stage` Wave 3a), `content_class_tier_intelligence`, `creator_niche_content_class_stats` (Wave 3c). Nightly refresh chain §8.1 in [`two-axis-niche-model.md`](two-axis-niche-model.md) §9 — ingest 03:00 ICT → class MV 04:00 → tier 04:15 → stats 04:30 → ritual read 22:00.
- **Intelligence → surface:** Morning Signal strip (Max-2-Card) via `useClassMorningSignals`; spec [`class-intelligence-ui-spec.md`](class-intelligence-ui-spec.md). Phase 2: `peer_percentile` diagnosis when BE returns label.

---

## 10. Critical Invariants

These are production guards. Breaking any of them silently loses money or data.

| ID | Guard | Where |
|----|-------|-------|
| **TD-1** | Credit deduction: `decrement_credit()` RPC with `WHERE credits > 0` — never two-step read-then-write | Supabase RPC |
| **TD-2** | PayOS webhook idempotency: `processed_webhook_events` UNIQUE constraint — retries safe | Supabase table |
| **TD-3** | Concurrent analysis guard: `profiles.is_processing` boolean — `cron-reset-processing` clears stale flags after 5min | Supabase + cron |
| **TD-4** | SSE reconnection: Cloud Run emits `stream_id` + `seq` per token, replays from 60s in-memory buffer | Cloud Run |
| **TD-5** | Credits granted upfront at PAID webhook — no subscription, no monthly top-up | Edge Function |
| **TD-6** | **Junction parity for `route` mode:** When `NICHE_RESOLVER_MODE=route`, a promoted `content_class_id` may only be written when junction lookup succeeds (`junction_has_pair` / `content_class_id_for_creator_niche_format`). Otherwise ingest falls back to the hashtag ladder. Seed data (`JUNCTION_NICHE_FORMAT_PAIRS` + migrations) must stay aligned — CI pins `test_hi9_junction_seed.py`. | `corpus_ingest.py` + taxonomy migrations |
| **TD-7** | **Extraction parity (live vs batch):** On-demand SSE and batch corpus ingest must share the same Vietnamese extraction prompts and HI-9 `niche_classification` contract so shadow telemetry, corpus rows, and user diagnoses stay comparable. **`build_tiktok_caption_extraction_prefix`** + tagline-vs-rhetorical-hook rules must ship on every path through `analyze_video` / batch JSONL (not ASR-only). **`user_stats.caption`** in synthesis = TikTok `desc`, never `meta.title` / `hook_phrase`. | `analysis_core.py`, `corpus_ingest.py`, `prompts.py`, `video_analyze.py` |

---

## 11. Auth Boundaries

| Layer | Mechanism | Validated by |
|-------|-----------|-------------|
| Browser → Supabase | Supabase JWT (anon key + user JWT) | Supabase RLS |
| Browser → Cloud Run | `Authorization: Bearer <supabase_jwt>` | Cloud Run JWKS validation (stateless) |
| Browser → Vercel Edge | `Authorization: Bearer <supabase_jwt>` | Supabase client (anon key + JWT) |
| pg_cron → Cloud Run batch | `X-Batch-Secret` header | Cloud Run env `BATCH_SECRET` |
| Cloud Run batch → Supabase | `SUPABASE_SERVICE_ROLE_KEY` | Supabase (bypasses RLS) |
| Edge Function → Supabase | `SUPABASE_SERVICE_ROLE_KEY` | Supabase (bypasses RLS) |

**RLS is the only authorization boundary for all client-side DB access.**

---

## 12. Cloud Run Pipeline Architecture

*These principles came out of the 2026-05-13 tactical refactor. They are binding for all pipeline work in `cloud-run/getviews_pipeline/`.*

### Service layer (mandatory)

All business logic lives in `services/`. `pipelines.py` and `video_analyze.py` are **thin orchestrators** — they sequence calls; they contain no logic of their own.

| Module | Owns |
|--------|------|
| `services/extraction.py` | `run_extraction_core`, `async_run_extraction_core`, Gemini frame analysis |
| `services/diagnosis.py` | `run_video_diagnosis_core`, error extraction, retention modeling |
| `services/synthesis.py` | `synthesize_core`, narrative generation, format cards |
| `services/channel.py` | `fetch_channel_context_sync` (24h in-process cache), creator comparison |
| `services/performance.py` | Performance tier classification, KPI enrichment |
| `services/references.py` | `select_synthesis_references_for_video` — corpus pool → proximity → content-targeted ED merge → `_reference_evidence_lines` (stream + finalize parity) |
| `services/corpus_quality.py` | `promote_on_demand_to_corpus`, `quality_tier`, cohort eligibility |
| `services/asr_vietnamese.py` | **HI-14:** `sync_prepare_vietnamese_asr_supplement` — GCP STT `vi-VN`, reads/writes `vietnamese_asr_cache` (**video file paths only**; carousels skip) |

### Supplemental ASR and hook-window video sampling (HI-14, HI-15)

- **HI-14:** Before the main Gemini vision pass on **videos**, the pipeline may fetch a short Vietnamese transcript via Google Cloud Speech-to-Text (`vi-VN`), formatted into the extraction user turn. Results are cached per `video_id` in `vietnamese_asr_cache` so later calls reuse one ASR pass. **Carousels do not invoke this path** (image-only `analyze_carousel`).
- **HI-15:** `analyze_video` may send **two** `Part` payloads: full clip at `GEMINI_VIDEO_BASE_FPS` and the first `GEMINI_HOOK_WINDOW_END_SEC` at clamped `GEMINI_HOOK_WINDOW_FPS` (3–5), so hook timing sees sharper frames without raising cost on the whole file. `GEMINI_HOOK_WINDOW_DUAL_PART=false` restores single-Part behaviour.

### Caption TikTok vs hook in-video

| Field | Source | UI / synthesis |
|-------|--------|----------------|
| `video_corpus.caption` | `aweme.desc` at ingest | Unchanged semantics |
| `hook_analysis.hook_phrase` | Gemini vision (+ caption prefix rules) | Hook section / copy handoff |
| `VideoAnalyzeMeta.caption` | TikTok `desc` on response | Phone overlay (`line-clamp`) |
| `VideoAnalyzeMeta.hook_phrase` | Extraction `hook_phrase` | Script handoff when set |
| `VideoAnalyzeMeta.title` | **Legacy** — first line of `desc` | Backward compat only; do not assign vision hook here |

Extraction prepends `CAPTION_TIKTOK` via `build_tiktok_caption_extraction_prefix` (merged with HI-14 ASR block). When caption opens with a rhetorical hook and 0–3s overlay is only a marketing tagline (“coming soon”, launch date, collection name), model should set `hook_phrase` from caption and record overlay in `hook_timeline` / overlays — **batch + on-demand** share the same prefix (TD-7).

### Live on-demand niche ladder

Distinct from batch loop niche: `resolve_live_niche_id` in `live_niche.py` — (1) `CREATOR_NICHE_OVERRIDE` (e.g. `curnon.official` → fashion/jewelry `niche_id=3`), (2) `classify_from_hashtags`, (3) `find_niche_match` on `desc` + `challenges[].title`, (4) `answer_sessions.niche_id` via `build_video_report(session_niche_id=…)`, (5) `profiles.creator_niche_id` → `legacy_niche_id_for_creator_niche`. `finalize_video_narrative_layer` re-resolves empty `meta.niche_label`, refreshes benchmark, then runs `select_synthesis_references_for_video`.

### Reference parity (answer / on-demand finalize)

**Answer path** (`build_video_report` → `run_video_analyze_*` → `finalize_video_narrative_layer`) and **`/stream`** (`pipelines.run_video_diagnosis`) both end in `finalize_video_narrative_layer` or an equivalent synthesis step that calls `select_synthesis_references_for_video`: corpus pool (≥`REF_N` or sparse/live fallback) → `_select_by_proximity_then_er` → `_maybe_merge_content_targeted_refs_async` → `_reference_evidence_lines` passed to `synthesize_diagnosis_v2(..., reference_evidence_block=…)`. Embed-tile repair (§4.3) applies on the answer finalize path only.

### Two cores — one extraction, one diagnosis

```
run_extraction_core(video_path) -> ExtractionResult
  • Download video (R2 / temp)
  • Optional HI-14 ASR supplement (video only) → cached transcript hint
  • Optional `CAPTION_TIKTOK` prefix (`build_tiktok_caption_extraction_prefix`) — same on carousel limit note
  • Gemini vision (e.g. `gemini-3.1-flash-lite`) — frame / video Parts per HI-15
  • apply_timestamp_guards  ← v4 hardening
  • validate_transcript      ← v4 hardening
  • score_entry_cost         ← v4 hardening
  Returns: ExtractionResult (Pydantic + matching TS interface)

run_video_diagnosis_core(DiagnosisInput) -> DiagnosisResult
  • extract_video_errors (Gemini) — 1 Gemini call
  • apply_rule_based_video_errors ← v4 hardening
  • structural parsing (retention curve, hook phases, segments)
  Returns: DiagnosisResult (Pydantic)
```

### Corpus extraction utilization

Nightly ingest runs **one Gemini extraction call per video** (carousel: image path). Output lands in `video_corpus.analysis_json` plus ~25 promoted columns. **~50–65%** of extracted fields have a clear batch or aggregate consumer; most HI-9 semantic fields activate on **user diagnosis** when the same `video_id` is analyzed (Tier B signals). Field-level tier map: [`corpus-gemini-utilization-audit.md`](corpus-gemini-utilization-audit.md).

**Invariants (enforced by CI):**
- **Batch never calls `run_video_diagnosis_core`.** Batch (`corpus_ingest`, `douyin_ingest`) calls `async_run_extraction_core` only. Diagnosis is user-facing SSE only.
- **`finalize_video_narrative_layer` is never called from batch.** It owns the 2-Gemini-call synthesis + narrative.
- At 20K corpus videos/day: 1 Gemini call/video = ~$3/day. Diagnosis layer would cost ~$9/day — wrong order of magnitude.
- **Diagnosis-first v6 (flagged):** When `GETVIEWS_DIAGNOSIS_SECTION_MODE=1`, synthesis runs `build_signal_manifest` + `select_sections_to_emit` (`diagnose_sections.py`). The pool includes `metadata` (§1 safe zone, business/V-pop heuristic), `editing` (§5 color grade + overlay readability), and `douyin_origin` (§8 — `douyin_match.py` may enrich `analysis` from `douyin_video_corpus` before `synthesize_diagnosis_v2` when `GETVIEWS_DOUYIN_ORIGIN_MATCH` is on) among others; matching fields on `VideoAnalysis` are extracted in `prompts.py` / Gemini JSON (§8 reserved null on extract). **`signals/performance.py` (§12)** adds `commerce_performance_conversion_override` (salience 1.0) when `user_stats.commerce_conversion` / `shop_order_count` from Shop/API contradicts a view-only flop/average read — populate server-side only; do not extract orders via Gemini. Default env keeps legacy monolithic path until cutover. **Douyin daily ingest cron / TikHub cost gate** remains a separate DevOps decision.

CI enforcement: `tests/test_two_core_audit.py`.

### v4 hardening — non-negotiable

These four guards apply to **every extraction path** without exception:

1. `apply_timestamp_guards` — strips impossible timestamps from error events
2. `validate_transcript` — discards hallucinated transcripts
3. `score_entry_cost` — scores entry cost based on hook timing
4. `apply_rule_based_video_errors` — adds rule-based structural errors

They live in `run_extraction_core` so all callers (batch + on-demand) receive them. Adding a new extraction path that doesn't route through `run_extraction_core` silently skips all four. CI check: `test_v4_hardening_uniform.py`.

### Schema contract CI

`tests/test_schema_contract.py` auto-generates JSON Schema from Pydantic models and compares against TypeScript interfaces in `src/lib/api-types.ts`.

**Rule:** any new Pydantic model that crosses the FE/BE boundary must have a matching TypeScript interface AND pass the schema contract test before merging.

Models covered (input + output): `ExtractionResult`, `VideoDiagnosisV5`, `VideoErrorsExtractionInput`, `DiagnosisSynthesisInput`.

### Gemini call contract — HYBRID pattern

Every Gemini call uses a typed Pydantic model for its structured data input. The prompt is assembled as:

```
[Vietnamese rubric — natural-language system instructions]
[JSON block — typed structured data: json.dumps(input_model, ensure_ascii=False)]
[Vietnamese format/output spec]
```

**No hand-built f-string prompts for structured data.** The data block is always `model.model_dump_json(indent=2)` wrapped in a `json` code fence. This makes regressions detectable without running Gemini: if the prompt changes a field name, the schema contract CI fails before the change ships.

- **Tier B (small structured inputs):** pure JSON block — `VideoErrorsExtractionInput`
- **Tier C (narrative synthesis):** HYBRID — Vietnamese instructions + JSON sub-block for arrays — `DiagnosisSynthesisInput`

### Pydantic Settings — no `os.environ.get` in logic

All env vars are read once at import time via `getviews_pipeline/settings.py` (`pydantic.BaseSettings`). Business logic modules import from `settings`, never from `os.environ`. Fails fast at boot on misconfiguration.

### No per-instance state

Cloud Run can run multiple replicas. No mutable module-level state is allowed **except:**

- `services/channel.py` in-process cache (`_channel_cache`): **explicitly acceptable** because `min-instances=1` keeps a warm instance, cache is bounded (500 entries, 24h TTL), and the worst case on cache miss is a redundant Supabase query, not a crash.

Everything else must be stateless and safe to reconstruct on each request.

### 12.1 Corpus ingest selection (live)

Nightly `/batch/ingest` ranks EnsembleData pool candidates with **`instructiveness_score`** (breakout-relative + recency + ER + sound momentum), not raw `play_count`. Canonical thresholds: [`corpus-ingest-criteria-v1.md`](corpus-ingest-criteria-v1.md).

| Mode | Behavior |
|------|----------|
| `legacy` | Flat view floor; sort `play_count`; VPN≈30 |
| `shadow` | Compute purity stack + `[corpus_shadow]` logs; legacy selection ships |
| `purity` | Tier 0–2 gates, R1/R2/R3, VPN=15, post-extract Tier 3 |

**Modules:** `corpus_instructiveness.py` (score + select), `corpus_boost_suspect.py` (§4.7 M1 proxy). Batch-start prefetch: niche p50/p75 views, boost percentiles, `trend_velocity` sound buckets. When `CORPUS_SCORE_COHORT=class_shadow|class`, also prefetch class-keyed p50/p75; `score_cohort_mismatch` flags loop vs stored class.

**Class ingest loop (Phase 3, default on):** `CORPUS_INGEST_LOOP=class` (production) uses `content_class_ingest_targets`; dedup allows re-upsert when `content_class_id` changes. **ACQE** (`class_quality_engine.py`) runs post-MV refresh; cold-start nights 1–3 per pipeline §10. Rollback: `CORPUS_INGEST_LOOP=niche`.

**TD-8:** Ingest selection changes must not fork TD-7 extraction contract (same `async_run_extraction_core` / prompts).

**Post-extract (Tier 3):** hard failures block upsert when `CORPUS_POSTEXTRACT_HARD_REJECT=true` (non-VN caption, uninstructive structure, hook–content mismatch). Hook-type soft cap (`CORPUS_POSTEXTRACT_HOOK_CAP_ENFORCE`) is env-gated when shadow metrics pass; breakout ≥3.0 bypass.

**Columns:** `boost_attribution`, `reference_eligible`, `ingest_relaxation_tier` (migration `20260520000000_corpus_ingest_criteria_columns.sql`).

**Consumers (Phase 4):** `morning_ritual` grounding pool sorts `breakout_multiplier`; ref pool (`corpus_context`) sorts breakout + optional `reference_eligible` filter; `hook_effectiveness_compute` weights by breakout; Trends virals rail min `breakout_multiplier ≥ 2`.

**Phase 5b (optional):** top-niche ED comment fetch → `comment_radar` when `ED_BATCH_COMMENT_FETCH_ENABLED=true` (gated by shadow overlap metrics in v1 spec §13).

### COALESCE provenance on UPSERT

`video_corpus.ingest_source` records how a row was first created: `batch_nightly`, `user_diagnosis`, `douyin_batch`, or **`reference_live_search`** (high-view refs enqueued from live diagnosis and drained by the batch pod). This column is **write-once** — the first writer sets it; subsequent UPSERTs must not overwrite it.

**`corpus_ingest_queue`** — lightweight Supabase table: user pod upserts aweme IDs + metadata after live reference discovery; **`POST /batch/process-ingest-queue`** pulls pending rows and runs `run_reingest_video_items` (full analysis + `video_corpus` upsert). Thumbnails are mirrored to R2 best-effort on enqueue (`download_and_upload_thumbnail`, multiple CDN URLs). **pg_cron** job `cron-batch-process-ingest-queue` calls that endpoint daily at **01:30 UTC** (`limit=50`, `timeout_milliseconds` 3600000) — migration `20260723000000_cron_batch_process_ingest_queue.sql`.

Mechanism: `upsert_video_corpus_batch` uses:
```sql
ON CONFLICT (video_id) DO UPDATE SET
  ingest_source = COALESCE(video_corpus.ingest_source, EXCLUDED.ingest_source)
```

Without this clause, the most-frequent writer (usually a cron) silently overwrites user-discovered provenance — breaking the `corpus_growth_via_users` metric.

### Structured logging + OTel

Every critical event emits a structured JSON log via `observability.py`. Every external I/O boundary is wrapped in a `telemetry.span()`:

- Gemini API calls
- HTTP calls to EnsembleData, R2
- Supabase queries (diagnosis cache hit/miss)

OTel exports to Cloud Trace via OTLP gRPC. Set `OTEL_DISABLED=true` in test environments (`tests/conftest.py`).

Key metrics emitted:

| Metric | Event field | Emitted by |
|--------|-------------|------------|
| Cache hit rate | `cache_hit` / `cache_write` | `log_cache_event` in `video_analyze.py` |
| Gemini cost saved | `gemini_cost_saved_usd` | `log_diagnosis_event` in `pipelines.py` |
| Corpus growth via users | `corpus_growth` | `log_corpus_growth_event` in `corpus_quality.py` |
| Channel cache hit | `channel_cache_hit` / `channel_cache_miss` | `log_channel_cache_event` in `services/channel.py` |
| URL normalize collision | `url_normalize` | `log_url_normalize_event` in `video_analyze.py` |

### Adding a new pipeline

When adding a new pipeline (e.g., `instagram_ingest.py`):

1. Call `async_run_extraction_core` or `run_extraction_core`. Never call `gemini.analyze_video` directly.
2. Write to a separate corpus table unless the data is TikTok and belongs in `video_corpus`.
3. Add a `services/your_service.py` for any significant logic.
4. Add new env vars to `settings.py`, not `os.environ.get`.
5. Wrap every external I/O call in an OTel span.
6. Add a matching TS interface for any FE-bound Pydantic model and extend the schema contract test.
7. Add an audit test to `test_two_core_audit.py` confirming the new module doesn't import diagnosis-layer symbols.

---

## 13. Answer Sessions

### Tables

| Table | Purpose |
|-------|---------|
| `answer_sessions` | One row per research session. `format ∈ 'pattern' | 'ideas' | 'timing' | 'generic' | 'video_diagnosis'` |
| `answer_turns` | Append-only. `payload` is a validated `ReportV1` JSON inserted with service role (bypasses RLS). Authenticated users SELECT only. |

### Credit rules (`append_turn`)

- **Primary turn** (`kind = 'primary'`): 1 credit via `decrement_credit()` before work starts. Insufficient balance → `insufficient_credits`, no turn row.
- **Script turn** (`builder_fmt == "script"`): **3 credits** (B.4 parity with script workshop).
- **Most other follow-up kinds** (`timing`, `creators`, `generic`, …): 0 credits on that turn.
- Channel diagnosis (`/channel/diagnose`) bills separately (3 credits) — not via answer turns; wallet column `profiles.credits_remaining`.

### SSE replay

Same `stream_id` + `seq` buffer as video analysis. TTL: **60s** (`session_store.py:_STREAM_REPLAY_TTL_SEC`). Client resumes with `?resume_from_seq=<n>`. Buffer is per-instance — reconnect to a different Cloud Run pod may miss replay (acceptable; replays are best-effort).

### Idempotency

`POST /answer/sessions` accepts `Idempotency-Key: <uuid>`. Server caches 120s on `(user_id, key)` — replays return the same `session_id`.

---

## 14. Home Screen Endpoints

All JWT-gated via `require_user`. Niche resolved from `profiles.creator_niche_id`. If the user hasn't completed onboarding, returns 404 with `"chưa chọn ngách"` — frontend should route to onboarding.

Implementations: `cloud-run/getviews_pipeline/routers/home.py`, `pulse.py`, `ticker.py`, `morning_ritual.py`.

### `GET /home/pulse`

Feeds the PulseCard (big views stat + delta + supporting stats). Key response fields:

| Field | Description |
|-------|-------------|
| `views_this_week` / `views_last_week` | Sum of `video_corpus.views` for 7-day window |
| `views_delta_pct` | Float, 1dp. `0.0` when `views_last_week == 0` — UI renders "—" |
| `viral_count_this_week` | Videos with `breakout_multiplier ≥ 3.0` |
| `top_hook_name` | Pattern with highest `weekly_instance_count` in niche |
| `adequacy` | Claim tier: `none \| reference_pool \| basic_citation \| niche_norms \| hook_effectiveness \| trend_delta`. Drives soft state when corpus is thin. |

When `adequacy == "none"`, hide deltas and show empty-corpus state.

### `GET /home/ticker`

Feeds the marquee ticker. Five buckets, ≤2 items each, 7-day window, round-robin-interleaved:

| Bucket key | Label | Source |
|------------|-------|--------|
| `breakout` | BREAKOUT | Top 2 `video_corpus` rows by `breakout_multiplier ≥ 2.0` |
| `hook_mới` | HOOK MỚI | Top 2 `video_patterns` that entered the niche this week |
| `cảnh_báo` | CẢNH BÁO | Patterns where `weekly_instance_count` dropped ≥40% vs prev week |
| `kol_nổi` | KOL NỔI | Creators with in-niche `breakout_multiplier ≥ 2.0` this week |
| `âm_thanh` | ÂM THANH | Top 2 `trending_sounds` from most recent `week_of` in niche |

**Fail-open contract:** each bucket runs in an isolated executor task. An exception in one leaves the other four intact. Worst case: empty `items` array — UI hides the ticker when `items.length < 3`.

`target_kind` maps to routes: `video` → video-diagnosis, `creator` → channel analysis, `pattern` → Explore patterns, `sound` → trending-sounds view.

### `GET /home/starter-creators`

Feeds onboarding step 2 — 10 reference creators per niche, ranked by follower count. Seeded by `seed_starter_creators()` RPC from `video_corpus`; rows flagged `is_curated = TRUE` are never overwritten by re-seeding.

User writes back directly via Supabase client update to `profiles.reference_channel_handles TEXT[]` (CHECK: length ≤ 3, GIN-indexed).

### `GET /home/daily-ritual`

Returns today's morning ritual for the caller's niche. 404 with `"ritual_no_row"` or `"ritual_niche_stale"` when missing.

**Schema:** `daily_ritual (user_id, generated_for_date DATE, niche_id, scripts JSONB, adequacy, grounded_video_ids, generated_at)` — PK is `(user_id, generated_for_date, niche_id)`.

**Generation:** one 3-script bundle per user per niche (single niche per user since two-axis migration 2026-05-13 — the old multi-niche-up-to-3 model is retired). Triggered by `POST /batch/morning-ritual` (pg_cron, daily 15:00 UTC / 22:00 ICT). Gemini call: one synthesis per user.

**Batch endpoints:**

| Endpoint | Auth | Body | Use |
|----------|------|------|-----|
| `POST /batch/morning-ritual` | `X-Batch-Secret` | `{}` or `{"user_ids": ["<uuid>"]}` | pg_cron / manual |
| `POST /admin/trigger/morning_ritual` | User JWT + `is_admin` | same | Admin panel trigger |

Response includes: `generated`, `skipped_thin` (< 10 grounding videos), `failed_schema`, `failed_gemini`, `users_no_niche`.

---

## §15 R2 Storage

### Bucket topology

Single bucket (`getviews-frames`) configured via `R2_BUCKET_NAME` env var. All objects are public — no signed URLs. Two CDN domain env vars are supported (optional custom domains; falls back to the Cloudflare `pub-*.r2.dev` URL pattern when unset):

| Env var | Default | Purpose |
|---|---|---|
| `R2_PUBLIC_URL` | (r2.dev URL) | Frames + thumbnails CDN origin |
| `R2_VIDEO_PUBLIC_URL` | (falls back to R2_PUBLIC_URL) | Video clip CDN origin |

### Key namespaces

| Namespace | Pattern | Written by | Consumers |
|---|---|---|---|
| `frames/` | `frames/{video_id}/{0,1,2}.png` | `extract_and_upload()` during corpus ingest | Gemini vision analysis |
| `thumbnails/` | `thumbnails/{video_id}.png` or `.jpg` | `copy_first_frame_to_thumbnail()` (.png) or `upload_thumbnail_bytes()` (.jpg) or `download_and_upload_thumbnail()` (.jpg) | `video_corpus.thumbnail_url` → FE card screens |
| `videos/` | `videos/{video_id}.mp4` | `download_and_upload_video()` | Trends / Pattern cards in FE |
| `video_shots/` | `video_shots/{video_id}/{n}.jpg` | `extract_and_upload_scene_frames()` | Script screen scene reference |

### Thumbnail derivation rules

**For video posts:**
1. Primary (preferred): `copy_first_frame_to_thumbnail()` — R2 server-side copy from `frames/{id}/0.png` → `thumbnails/{id}.png`. Zero CDN bytes, one R2 op. Only available when frame extraction succeeded.
2. Fallback: `download_and_upload_thumbnail(cdn_url, video_id)` — download from TikTok CDN, write `thumbnails/{id}.jpg`.

**For carousel posts:**
1. Primary: `upload_thumbnail_bytes(video_id, slide_bytes[0], mime)` — called from `_analyze_carousel()` immediately after Gemini analysis while slide images are still in memory. Writes `thumbnails/{id}.jpg`.
2. Lazy backfill: `refresh_stale_thumbnails()` — fetches fresh slide URL via EnsembleData multi-info, calls `download_and_upload_thumbnail()` on-read. Triggered any time a carousel row is cited in an answer session.
3. Corpus ingest fallback: if R2 not configured, `_build_corpus_row()` stores the first TikTok CDN slide URL as `thumbnail_url` (expires; temporary).

**Dedup invariant:** at most one extension per `video_id` under `thumbnails/`. Both write helpers (`copy_first_frame_to_thumbnail` and `upload_thumbnail_bytes`) delete the opposite-extension key after a successful write via `_delete_thumbnail_other_ext()`. Failure is non-fatal (logged at debug).

### `_is_r2_url()` — stale-URL detection

```python
def _is_r2_url(url) -> bool:
    # Check configured custom domains first (R2_PUBLIC_URL + R2_VIDEO_PUBLIC_URL)
    # then fall back to the default https://pub-*.r2.dev prefix.
```

Used by `refresh_stale_thumbnails()` to decide whether to skip (already R2) or repair (still TikTok CDN). A URL is R2 if it starts with `R2_PUBLIC_URL + "/"`, `R2_VIDEO_PUBLIC_URL + "/"`, or `"https://pub-"`. The `+ "/"` suffix prevents subdomain prefix collision (e.g. `media.getviews.vn.evil.com`).

### R2 Janitor

`r2_janitor.py` reconciles R2 objects against `video_corpus.video_id`. Objects whose video_id is not in the live corpus are considered orphaned and deleted in batches (S3 DeleteObjects, 1000-key cap).

**Schedule:** pg_cron `cron-batch-r2-janitor` fires Sundays 18:00 UTC (01:00 ICT Monday). Uses `vault.cloud_run_api_url` (must point to batch pod) + `vault.cloud_run_batch_secret`.

**Before applying migration or enabling schedule:** run a dry-run first:
```bash
curl -s -X POST "$BATCH_URL/batch/r2-janitor?dry_run=true" \
  -H "X-Batch-Secret: $BATCH_SECRET" | jq .per_prefix
```
If any prefix shows unexpectedly high orphan ratio (>20%), investigate key-pattern drift before enabling the destructive pass.

**Rollback:**
```sql
SELECT cron.unschedule('cron-batch-r2-janitor');
```

### Thumbnail failure observability

`VideoThumbnail.tsx` fires `navigator.sendBeacon` to the `track-thumbnail-failure` Edge Function on every image load error. De-duplicated per `video_id` per page load (module-level `Set<string>`). Failures are persisted to the `thumbnail_failures` table (service_role insert via Edge Function).

Admin panel tile (`/app/admin`) shows 7-day failure count + top-10 video_ids. Spike in count = potential R2 outage or bulk CDN expiry in corpus.

---

## §16 Channel Diagnosis (Lightreel Narrative)

`POST /channel/diagnose` — Cloud Run user pod. Accepts `handle`, `niche_id`, and optional `video_url`. Returns Server-Sent Events in the TD-4 envelope (`stream_id + seq + done`). Costs **3 credits** on cache miss; cache hit replays the stored result for free.

### Data sources

| Source | Usage |
|---|---|
| EnsembleData | Live fetch of the 30 most-recent videos for the handle (`fetch_user_posts`) |
| `video_corpus` | **Corpus-first peer creators** (`select_niche_peer_creators`) — content_class → niche_only → thin; follower enrichment via EnsembleData (never surface `0` as real count). |
| `video_corpus` + `map_legacy_corpus_to_content_class` | **Channel persona** — dominant content class + label (`derive_channel_persona`). |
| `niche_channel_benchmarks` RPC | Percentile band (P25/P50/P75) + median posts/week for score card + prompts |
| Gemini | Vietnamese narrative only (synthesis model, ~`gemini-3-flash-preview`). Structured blocks (score card, hashtags, peer table, next-video skeleton) are **template-generated**. |

### Trajectory classification

Backend classifies the channel into one of 6 `TrajectoryShape` values before LLM synthesis:

| Shape | Heuristic |
|---|---|
| `new_account` | < 5 videos posted |
| `breakout` | recent 30-day avg > 3× baseline (excluding recent window) |
| `decline_from_peak` | peak-30-day avg > 2× current, inflection point detected |
| `steady_growth` | ≥4 consecutive quarters with ≥1.2× growth |
| `bursty` | stdev/mean views > 1.5 |
| `stagnant` | default fallback |

### SSE event shape

Emitted in order (cache replay must mirror the same fields):
1. `hello` — handshake
2. `cache_hit` — only on 7-day cache replay (no re-billing)
3. `trajectory` — `{ trajectory: TrajectoryShape }`
4. `score_card` — `{ data: metrics, captions?: Record<string,string> }` — deterministic TLDR + educative captions (template)
5. `step_start` / `step_done` — pipeline step progress
6. `section_start` — `{ section_id, title, embedded_tiles?, embedded_creators?, hashtag_insights?, next_video? }`
7. `text_chunk` — `{ content: string }` — streaming prose chunks
8. `section_done` — `{ section_id }`
9. `recommendation_item` — `{ index, title, body, kind?: "hero"|"regular"|"anti" }`
10. `payload` — full `ChannelDiagnosisPayload` JSON (v2 fields on fresh + replay)
11. `done: true` — terminal frame

Mandatory LLM sections: **verdict** + **recommendations** — fallback to raw prose if LLM omits them. `next_video` may be injected from a deterministic seed. `hashtag_insights` is synthetic (not from Gemini).

### Cache contract

- **Table**: `channel_diagnoses` PK `(handle, video_url, niche_id)`. `video_url` = empty string when no target video.
- **TTL**: 7 days (application-enforced via `computed_at >= now() - 7 days` filter).
- **Writes**: service_role only (RLS blocks authenticated writes).
- **V2 columns**: `score_card`, `verdict_tiles`, `hashtag_insights`, `next_video`, `channel_persona`, `peer_source` (`NULL` = legacy row — do not label as “thin”).
- **Cache hit**: emits `cache_hit` + `trajectory` + **`score_card`** + sections with **`verdict_tiles` / `hashtag_insights` / `next_video`** on `section_start`, then **`payload`** parity with fresh runs.

### Tile selection (trajectory-aware)

**Verdict evidence** — `verdict_tiles`: peak + 2 most recent public videos, deduped by `video_id`.

| Trajectory | Top tiles | Bottom tiles |
|---|---|---|
| `breakout` | Quarterly breakout videos | — |
| `new_account` | Niche peer videos from corpus | — |
| `decline_from_peak` / `stagnant` / `bursty` | Top-2 per top-2 format archetypes | Worst recent performers |
| `steady_growth` | Top-2 per format | Latest quarter top videos |

**Peer creators** (competitive landscape): **`select_niche_peer_creators`** (`video_corpus`). **Hashtags**: `compute_hashtag_insights` + captions. **Next video**: `derive_next_video_concept` + optional Gemini narrative in `next_video` section.

### Frontend

- **Hook**: `useChannelDiagnose` — handles `score_card` SSE; exposes `scoreCard`, `channelPersona`, `peerSource`; merges terminal `payload` for replay completeness.
- **Components**: `ScoreCard`, `HashtagInsightsBlock`, `NextVideoCard`, `SectionRenderer`, `VideoTileRow`, `CreatorTileRow`, `NumberedRecommendation` (hero / anti grouping), `StepProgress`, `ProvenanceLine` under `src/routes/_app/channel/components/`.
- **Screen**: `ChannelScreen.tsx` — score card skeleton until `score_card` arrives; thin-corpus disclaimer when `peer_source === "thin"` (or legacy `niche_thin` in old payloads).

### Phase 2 cleanup — **DONE** (2026-07-15)

Removed in migration `20260715000001_drop_channel_formulas.sql` + codebase cleanup:

- ~~`channel_analyze.py` + `/channel/analyze`~~ — deleted
- ~~`useChannelAnalyze.ts` + `ChannelAnalyzeResponse`~~ — deleted
- ~~`ConnectChannelCard.tsx` + home `Channel*Block` components~~ — deleted
- `DROP TABLE channel_formulas` + `DROP FUNCTION channel_corpus_stats` — applied

**Kept:** `niche_channel_benchmarks` RPC + `content_class_channel_benchmarks` — used by `channel_diagnose`.

---

## §17 Cost Budget & Guardrails

### Monthly target

| Service | Monthly ceiling | Notes |
|---|---|---|
| Gemini API (all models) | **~$80–90** | `gemini-3.1-flash-lite` at $0.25/$1.50 per 1M. Includes batch ingest + live diagnoses + text intents. |
| GCP Speech-to-Text (HI-14) | ~$5–10 | `vi-VN` on video paths only; carousels skip |
| EnsembleData API | per plan | Monitor via `ensemble_calls` table |

### Gemini daily hard ceiling

A **$15/day** cap is enforced on the **batch pod** via `GEMINI_DAILY_USD_MAX=15` + `GEMINI_DAILY_USD_ENFORCE=true` (set 2026-05-17). At the current run rate (~$1.50/day ingest + live traffic) this is a 10× safety margin. If the cap is hit, `check_gemini_daily_budget()` raises `GeminiDailyBudgetExceeded` and the call site logs + skips.

The **user-facing pod** does not enforce `GEMINI_DAILY_USD_MAX` — it serves live SSE requests and a hard stop mid-stream would break the UX. Rate-limiting is instead handled at the credit-deduction layer (TD-1).

### Monitoring

- Daily cost by `call_site`: `SELECT call_site, sum(cost_usd) FROM gemini_calls WHERE created_at >= current_date GROUP BY 1 ORDER BY 2 DESC`
- MTD projection: `SELECT round(sum(cost_usd)/extract(day FROM now())*30, 2) AS projected_30d FROM gemini_calls WHERE created_at >= date_trunc('month', now())`
- EnsembleData calls: `SELECT endpoint, count(*) FROM ensemble_calls WHERE created_at >= current_date GROUP BY 1`

### HI-13 status (Gemini Batch API)

Disabled as of 2026-05-17 (`CORPUS_INGEST_USE_GEMINI_BATCH=false` on batch pod). `gemini-3.1-flash-lite` returns HTTP 400 on `batchGenerateContent` — model does not currently support the JSONL Batch API. Re-enable when confirmed supported; expected ~50% cost reduction on nightly extraction.

### HI-14 status (GCP Speech-to-Text)

Disabled as of 2026-05-17 (`GCP_STT_VI_ENABLED=false` on both batch + user pods). Two blockers: (1) API returned 403 `SERVICE_DISABLED` initially; (2) after enabling, returned 400 `Inline audio exceeds duration limit` — the current code sends audio inline rather than via a GCS URI, which is required for clips over ~60s. Re-enable requires implementing a GCS upload step before the STT call. Guard: `GCP_STT_VI_ENABLED=false` skips the entire ASR path gracefully.

---

## Update Protocol

When any of the following changes, update this file in the same commit:

- New route added or removed
- New Cloud Run router or endpoint
- New Supabase Edge Function or pg_cron job
- Change to auth flow or JWT validation
- New cache layer or TTL change
- New critical invariant (TD-N)
- Billing / credit flow change
- New external service dependency
- Corpus ingest **selection criteria** change (pre-Gemini rank/gates) — update §12.1 + [`corpus-ingest-criteria-v1.md`](corpus-ingest-criteria-v1.md)
- Corpus ingest **pre/post-Gemini gate** change (Tier 3 reject, boost-suspect, hook cap)
