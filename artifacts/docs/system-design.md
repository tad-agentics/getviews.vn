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

See `pipeline-principles.md` for the full binding rules. Summary:

- **Service layer is mandatory:** all business logic in `services/`. `pipelines.py` and `video_analyze.py` are thin orchestrators only.
- **Two cores:** `run_extraction_core` (static, immutable, 1 Gemini call) and `run_video_diagnosis_core` (cohort-comparative, user-facing only). Batch never calls `run_video_diagnosis_core`.
- **v4 hardening guards** (`apply_timestamp_guards`, `validate_transcript`, `score_entry_cost`, `apply_rule_based_video_errors`) apply to every extraction path. Enforced by `test_v4_hardening_uniform.py`.
- **Schema contract CI:** Pydantic models ↔ TypeScript interfaces auto-diffed in `test_schema_contract.py`. Any FE/BE boundary model must have a matching TS interface.
- **No per-instance state** except `services/channel.py` in-process cache (explicitly documented, bounded, acceptable).

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
