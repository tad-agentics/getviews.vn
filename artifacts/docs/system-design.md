# System Design — GetViews.vn

**Last updated:** 2026-05-14  
**Status:** Living document. Update in the same commit as any architectural change.

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
│  Storage — not used for video (R2 handles frames/videos)           │
│  pg_cron — schedules HTTP calls to Cloud Run batch pod             │
└────────────────────────────────────────────────────────────────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  Cloudflare R2  │
        │  getviews-frames│
        │  getviews-videos│
        │  Public buckets │
        │  (no signed URL)│
        └─────────────────┘
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
| `/app` | App shell | Auth-guarded by `_app/layout.tsx`. |
| `/app/answer` | Answer | Video diagnosis + text Q&A. All session types land here. |
| `/app/history` | History | Session list. |
| `/app/history/chat/:sessionId` | History | Read-only legacy transcript. |
| `/app/trends` | Trends | Niche intelligence + hook effectiveness. |
| `/app/douyin` | Douyin | Douyin trend analysis. |
| `/app/compare` | Compare | Side-by-side creator comparison. |
| `/app/channel` | Channel | Channel deep-dive. |
| `/app/script` | Script | Script generation. |
| `/app/script/shoot/:draftId` | Script | Shoot-mode for a draft. |
| `/app/settings` | Settings | Profile + niche + subscription. |
| `/app/pricing` `/app/checkout` `/app/payment-success` | Billing | PayOS flow. |
| `/app/admin` | Admin | Gated by `profiles.is_admin`. Batch pod only. |

Every `/app/*` leaf route is code-split with `React.lazy` + `Suspense`.  
Do not use React Router `clientLoader` — TanStack Query is the data layer.

---

## 3. Intent Routing

`src/routes/_app/intent-router.ts` — `detectIntent(query)` classifies each user message before any network call.

```
User message
     │
     ├─ Contains TikTok URL?
     │      └─ YES → video_diagnosis → Cloud Run /video (SSE)
     │
     ├─ Contains @handle?
     │      └─ YES → channel_analyze → Cloud Run /channel or /app/channel shortcut
     │
     ├─ Explicit keyword match (trends / douyin / compare / script)?
     │      └─ YES → specialized intent → Cloud Run specialized router
     │
     └─ Everything else → follow_up_classifiable / follow_up_unclassifiable
              └─ → Vercel Edge /api/chat (Gemini text, no credits)
```

**Rule:** Never reinvent routing inside screen components. Extend `detectIntent()` and its tests (`intent-router.test.ts`).

---

## 4. Video Analysis Flow (user-facing SSE)

This is the most expensive and critical path. Every step has a cost and a guard.

```
1. Browser: detectIntent → video_diagnosis
2. Browser: POST /video to Cloud Run user pod (Supabase JWT in Authorization: Bearer)
3. Cloud Run: JWT validated via Supabase JWKS

4. Cache check (video_diagnostics table):
   ├─ HIT (< 1h old, has van_de_chinh): stream cached result → done (~2s, $0 Gemini)
   └─ MISS: continue

5. TD-3 guard: SET profiles.is_processing = true (atomic RPC)
   └─ Already processing? → return 429

6. run_extraction_core(video_path):
   ├─ Download video (EnsembleData → R2 / temp storage)
   ├─ Gemini vision analysis (gemini-3.1-flash-lite-preview)
   ├─ apply_timestamp_guards   ← v4 hardening, non-negotiable
   ├─ validate_transcript       ← v4 hardening
   ├─ score_entry_cost          ← v4 hardening
   └─ Returns: ExtractionResult (typed Pydantic + TS interface)

7. run_video_diagnosis_core(DiagnosisInput):
   ├─ extract_video_errors (gemini-3.1-flash-lite-preview)
   ├─ apply_rule_based_video_errors  ← v4 hardening
   ├─ retention curve parsing, hook phases, segments
   └─ Returns: DiagnosisResult

8. fetch_channel_context_sync(creator_handle):
   └─ 24h in-process cache → EnsembleData if miss

9. synthesize_diagnosis_v2(DiagnosisSynthesisInput):
   ├─ Gemini call 1: narrative_vi (van_de_chinh + loi_chinh_narrative + dinh_huong_chien_luoc)
   └─ Gemini call 2: format_cards

10. Stream SSE tokens to browser (stream_id + seq per token)
    └─ 60s in-memory replay buffer for reconnection (TD-4)

11. Write to video_diagnostics (1h TTL cache)
    └─ _schema_version: "v5" marker included

12. promote_on_demand_to_corpus() if quality_tier eligible
    └─ COALESCE ingest_source — first writer wins, batch never overwrites user provenance

13. SET profiles.is_processing = false
```

**Total time:** 20–30s cold. 2s warm (cache hit).  
**Gemini calls cold:** 3 (extraction + error + synthesis×2 counted as one call each).

---

## 5. Text Query Flow (Vercel Edge)

```
1. Browser: detectIntent → follow_up_*
2. Browser: POST /api/chat (Vercel Edge, Supabase JWT)
3. Edge: validate JWT via Supabase client, check credits
4. Edge: TD-1 guard — decrement_credit() RPC (WHERE credits > 0)
5. Edge: stream Gemini SSE (gemini-3.1-flash-lite-preview or flash-preview)
6. Browser: render streamed tokens
```

No Cloud Run involved. Fast path (~2–5s). Free for `follow_up` intents.

---

## 6. Cache Layers

| Layer | Storage | TTL | Key | Cost of miss |
|-------|---------|-----|-----|-------------|
| Video diagnosis | `video_diagnostics` (Supabase) | 1h | canonical `tiktok_url` | ~30s + 3 Gemini calls |
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

**Vault dependency:** `cloud_run_api_url` and `cloud_run_batch_secret` in Supabase Vault must be kept in sync with the batch pod's actual URL and `BATCH_SECRET`. Rotation without updating both breaks all pg_cron jobs silently.

---

## 9. Data Model (Key Tables)

| Table | Owner | Write path | Notes |
|-------|-------|-----------|-------|
| `profiles` | Supabase | Client (RLS), Edge Functions | `creator_niche_id` FK, `credits`, `is_processing`, `is_admin` |
| `creator_niches` | Supabase | Migrations only | 16 UX-facing buckets |
| `content_classifications` | Supabase | Migrations only | 74 analysis-facing categories |
| `video_corpus` | Cloud Run batch | Service role only | 46K+ analyzed TikTok videos; `ingest_source` is write-once |
| `video_diagnostics` | Cloud Run user | Service role | On-demand diagnosis cache (1h TTL); `_schema_version: "v5"` |
| `answer_sessions` | Supabase | Client + Cloud Run | Session format, intent type, credit spend |
| `chat_messages` | Supabase | Cloud Run only | Immutable — no UPDATE ever |
| `processed_webhook_events` | Supabase | Edge Function | UNIQUE constraint for PayOS idempotency |
| `niche_intelligence` | Supabase | Cloud Run batch | Materialized niche stats for TrendScreen |

### Niche model (two-axis, since 2026-05-13)

- **`creator_niches`** (16 buckets) — UX-facing. `profiles.creator_niche_id` FK. Single niche per user.
- **`content_classifications`** (74 categories) — analysis-facing. `video_corpus.content_class_id`.
- **`creator_niche_content_classes`** — M:N junction with `is_primary` flag.
- `niche_taxonomy` + `video_corpus.niche_id` are kept for backward compatibility. Downstream queries bridge via `legacy_niche_id_for_creator_niche()` (Python) / `legacyNicheIdForCreatorNiche()` (TypeScript) — both must stay in sync.

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
| `services/references.py` | Corpus reference video selection |
| `services/corpus_quality.py` | `promote_on_demand_to_corpus`, `quality_tier`, cohort eligibility |

### Two cores — one extraction, one diagnosis

```
run_extraction_core(video_path) -> ExtractionResult
  • Download video (R2 / temp)
  • Gemini vision (gemini-3.1-flash-lite-preview) — 1 Gemini call
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

**Invariants (enforced by CI):**
- **Batch never calls `run_video_diagnosis_core`.** Batch (`corpus_ingest`, `douyin_ingest`) calls `async_run_extraction_core` only. Diagnosis is user-facing SSE only.
- **`finalize_video_narrative_layer` is never called from batch.** It owns the 2-Gemini-call synthesis + narrative.
- At 20K corpus videos/day: 1 Gemini call/video = ~$3/day. Diagnosis layer would cost ~$9/day — wrong order of magnitude.

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

### COALESCE provenance on UPSERT

`video_corpus.ingest_source` records how a row was first created: `batch_nightly`, `user_diagnosis`, or `douyin_batch`. This column is **write-once** — the first writer sets it; subsequent UPSERTs must not overwrite it.

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

### Credit rules

- **Primary turn** (`kind = 'primary'`): 1 credit via `decrement_credit()` RPC **before** SSE stream starts. Insufficient balance → 402, no `answer_turns` row written.
- **Follow-up turns** (`timing`, `creators`, `script`): 0 credits — session already paid.
- **Generic fallback**: 0 credits.

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
