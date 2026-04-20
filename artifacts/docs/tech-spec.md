# Tech Spec — GetViews.vn
**Version:** 1.0
**Last updated:** 2026-04-09

---

## 1. Overview

GetViews.vn is a Vietnamese-language TikTok creative intelligence platform for Vietnamese creators and agencies. Users paste a TikTok URL or ask a question in chat — GetViews analyzes the video frame-by-frame using Gemini vision and compares it against a pre-indexed corpus of 46,000+ analyzed Vietnamese TikTok videos, returning a specific diagnosis, hook effectiveness rankings, and actionable fixes in Vietnamese within 20-30 seconds. The primary user is Minh (24, Shopee affiliate creator earning 10-20M VND/mo) who needs to know why his video flopped and exactly what to film next; the secondary user is Linh (28, agency Creative Lead) who needs creator discovery and production-ready KOL briefs.

---

## FE-BE Connection — Quick Reference

| Concern | Where to look |
|---|---|
| Functional requirements (what the app does) | Section 2 — Functional Requirements |
| Non-functional requirements (performance, scale) | Section 3 — Non-Functional Requirements |
| Shared TypeScript types | Section 4 — Shared TypeScript Interfaces → `src/lib/api-types.ts` |
| External integration patterns and SDK usage | Section 5 — External Integrations |
| Client-side data hooks and query functions | Section 9 — Data Access Layer → `src/hooks/` and `src/lib/data/` |
| Edge Function contracts (webhooks, cron, email) | Section 10 — API Contracts |
| Standard error handling shape | Section 10 — Standard Error Response Shape |
| Auth flow | Section 11 — Auth & Security Model |
| Per-screen data mappings | Screen spec metadata in `screen-specs-getviews-vn-v1.md` |
| Env vars frontend can access vs Edge Function secrets | Section 12 — Environment Variables (`VITE_` = client-safe) |
| Shared hooks (useAuth, useProfile, etc.) | Built in Foundation — see `src/hooks/` |
| SEO metadata, OG images, PWA manifest, service worker | Section 18 — SEO & PWA Infrastructure |
| Install prompt hook (useInstallPrompt) | Section 18 → `src/hooks/useInstallPrompt.ts` |

---

## 2. Functional Requirements

### Auth

| # | As a [user] | I can... | Acceptance signal |
|---|---|---|---|
| FR-01 | anonymous visitor | paste a TikTok URL on the landing page and receive one free Soi Kênh analysis without signing up | Diagnosis renders in ChatScreen without auth prompt |
| FR-02 | anonymous visitor | sign up via Facebook OAuth (primary) or Google OAuth (secondary) | Account created, free tier (10 deep credits) activated, redirected to ChatScreen |
| FR-03 | authenticated user | remain logged in across sessions | Supabase session persists; navigating to `/app` does not redirect to login |
| FR-04 | authenticated user | log out | Session cleared, redirected to `/login` |

### Core Chat Loop — 7 Intents

| # | As a [user] | I can... | Acceptance signal |
|---|---|---|---|
| FR-05 | authenticated user | paste a TikTok video URL and receive a frame-by-frame diagnosis (Intent ①) | DiagnosisRows render with ✕/✓ markers, benchmark data, fix recommendations, CorpusCite, ThumbnailStrip |
| FR-06 | authenticated user | paste a TikTok carousel URL and receive slide-by-slide analysis (Intent ① carousel) | Carousel diagnosis renders with per-slide visual type, text overlays, story arc, swipe incentive |
| FR-07 | authenticated user | ask "Gì đang hot trong [niche]?" and receive 3 corpus-backed content directions (Intent ②) | 3 structural patterns returned with Vietnamese reference video thumbnails and CorpusCite |
| FR-08 | authenticated user | paste a creator handle and receive their repeatable formula from 3 recent videos (Intent ③) | Competitor profile rendered with hook patterns, pacing, format, emerging creator flag if applicable |
| FR-09 | authenticated user | ask GetViews to analyse my own channel (Intent ④ Soi Kênh) | Pattern analysis across user's videos; top vs bottom by ER returned |
| FR-10 | authenticated user | request a production-ready KOL brief (Intent ⑤) | Brief block rendered: hook script, format, pacing, reference videos, recommended KOL tier + cost range |
| FR-11 | authenticated user | ask for this week's trends in my niche (Intent ⑥) | Velocity-weighted trend analysis rendered with hook type shifts, format lifecycle signals, trending sounds |
| FR-12 | authenticated user | search for KOLs by niche, follower range, and bio keywords (Intent ⑦) | Creator cards returned with handle, follower count, likes, bio contact info, optional corpus profile |
| FR-13 | authenticated user | send follow-up questions within a session at no credit cost | Follow-up messages processed without decrementing `deep_credits_remaining` |
| FR-14 | authenticated user | see streaming tokens appear in real-time as GetViews analyses | Chat bubble renders incrementally during SSE stream |
| FR-15 | authenticated user | see my current deep credit balance at all times | CreditBar visible and accurate on all `/app/*` screens |
| FR-16 | authenticated user | be prompted to upgrade when I have 0 credits | CreditBar turns purple with "Hết credit. Mua thêm →" when `deep_credits_remaining = 0` |

### Explore

| # | As a [user] | I can... | Acceptance signal |
|---|---|---|---|
| FR-17 | authenticated user | browse the pre-indexed video corpus in a 2-column grid filtered by niche, date, sort | ExploreGrid renders with VideoCards; filter chips update grid |
| FR-18 | authenticated user | tap a video thumbnail to open a VideoDetailModal with inline playback | Modal opens with `<video>` player loading from R2 URL; mute/unmute works |
| FR-19 | authenticated user | tap "Phân tích video này" in the modal to navigate to ChatScreen with URL pre-loaded | ChatScreen input pre-filled with the video URL |

### History

| # | As a [user] | I can... | Acceptance signal |
|---|---|---|---|
| FR-20 | authenticated user | view my past chat sessions sorted by recency | SessionList renders with intent badge, first message excerpt, date, credits used |
| FR-21 | authenticated user | search my history by query text | Filtered SessionList updates as user types |
| FR-22 | authenticated user | tap a past session to resume it in ChatScreen | ChatScreen loads with the session's message history |

### Billing

| # | As a [user] | I can... | Acceptance signal |
|---|---|---|---|
| FR-23 | authenticated user | view subscription plans and pricing with billing period toggle (monthly / 6-month / annual) | PricingScreen renders with correct prices per period; annual pre-selected |
| FR-24 | authenticated user | purchase a subscription pack or overage pack via MoMo, VNPay, bank transfer, or Visa/Mastercard | PayOS QR or bank details rendered; webhook confirms payment; credits updated |
| FR-25 | authenticated user | see updated credit balance after successful payment | PaymentSuccessScreen shows new credit count; CreditBar updates |
| FR-26 | authenticated user | receive expiry reminder emails 7 days, 3 days, and 1 day before pack expires | Emails sent by cron Edge Function at scheduled times |

### Settings & Content

| # | As a [user] | I can... | Acceptance signal |
|---|---|---|---|
| FR-27 | authenticated user | view my profile, subscription tier, credit balance, and reset date | SettingsScreen renders with real data from `profiles` and `subscriptions` tables |
| FR-28 | authenticated user | change my primary niche inline | NicheInput appears; saves to `profiles.primary_niche`; ChatScreen NicheBadge updates |
| FR-29 | authenticated user | browse resources, docs, and legal links | LearnMoreScreen renders all 3 sections with external links |

---

## 3. Non-Functional Requirements

| Category | Requirement | Target |
|---|---|---|
| Performance | Initial page load (LCP) | < 2.5s on 4G (Vietnamese mobile) |
| Performance | Time to interactive (TTI) | < 3.5s on 4G |
| Performance | Chat response first token (streaming start) | < 3s for text intents; < 5s for video intents (SSE begins streaming while Cloud Run processes) |
| Performance | Video diagnosis end-to-end | < 30s (20s target) |
| Scale | Concurrent users (v1) | Up to 500 (Wood ED plan headroom = 16% at 500 users) |
| Scale | video_corpus rows (Month 6) | ~46,000; Month 12 ~92,000 |
| Scale | chat_messages rows (2,000 users × 50/week) | Prune at 100 per user; archive older to `chat_messages_archive` |
| Availability | Uptime target | 99.9% (Vercel SLA) |
| Error handling | Unhandled server errors | Logged; user sees Vietnamese error banner |
| Accessibility | WCAG compliance | AA |
| Security | All user data routes | Enforced via Supabase RLS; `auth.uid() = user_id` |
| Security | Secrets | Never in client bundle; never in version control; Edge Function secrets only |
| Security | Rate limiting (⑥⑦ intents) | 100 free queries/day per account via `profiles.daily_free_query_count` |
| Mobile | Viewport | 360–393px baseline; one-handed use; 44×44px minimum touch targets |

---

## 4. Shared TypeScript Interfaces

All shared types live in `src/lib/api-types.ts`.

```typescript
// src/lib/api-types.ts

// ─── Enums ────────────────────────────────────────────────────────────────────

export type IntentType =
  | 'video_diagnosis'
  | 'content_directions'
  | 'competitor_profile'
  | 'soi_kenh'
  | 'brief_generation'
  | 'trend_spike'
  | 'find_creators'
  | 'follow_up'
  | 'format_lifecycle'   // Figma Make uses this as a session intent label for ⑥ format sub-intent

export type SubscriptionTier = 'free' | 'starter' | 'pro' | 'agency'

export type BillingPeriod = 'monthly' | 'biannual' | 'annual' | 'overage_10' | 'overage_30' | 'overage_50'

export type ContentType = 'video' | 'carousel'

export type LifecycleStage = 'emerging' | 'peaking' | 'declining'

export type TrendDirection = 'rising' | 'stable' | 'declining'

export type MessageRole = 'user' | 'assistant'

// ─── Database entities ────────────────────────────────────────────────────────

export interface Profile {
  id: string                          // = auth.users.id
  created_at: string
  updated_at: string
  display_name: string
  email: string
  avatar_url: string | null
  primary_niche: string | null        // maps to niche_taxonomy niche name
  niche_id: number | null             // FK → niche_taxonomy.id
  tiktok_handle: string | null
  subscription_tier: SubscriptionTier
  deep_credits_remaining: number
  lifetime_credits_used: number
  credits_reset_at: string | null     // ISO timestamp
  daily_free_query_count: number      // resets daily by cron
  daily_free_query_reset_at: string | null
  is_processing: boolean              // concurrent request guard
}

export interface ChatSession {
  id: string
  created_at: string
  updated_at: string
  user_id: string
  title: string | null
  first_message: string
  intent_type: IntentType | null
  credits_used: number
  is_pinned: boolean
  deleted_at: string | null
}

// Typed union for the structured_output JSONB column in chat_messages.
// Matches the DB schema exactly — one column, typed at the application layer.
export type StructuredOutput =
  | { type: 'diagnosis';   diagnosis_rows: DiagnosisRow[]; corpus_cite: CorpusCite | null; thumbnails: ThumbnailItem[] }  // thumbnails matches Figma Make field name
  | { type: 'hook_ranking'; hook_rankings: HookRanking[]; corpus_cite: CorpusCite | null }
  | { type: 'creators';    creator_cards: CreatorCard[] }
  | { type: 'brief';       brief_block: BriefBlock }

export interface ThumbnailItem {
  handle: string
  views: string           // display string e.g. "1,2M" — matches Figma Make thumbnails[]
  url: string             // TikTok URL for external link
}

export interface ChatMessage {
  id: string
  created_at: string
  session_id: string
  user_id: string
  role: MessageRole
  content: string | null              // null for structured assistant responses
  intent_type: IntentType | null
  credits_used: number                // 0 or 1
  is_free: boolean
  structured_output: StructuredOutput | null   // single JSONB column; typed union above
  stream_id: string | null            // for SSE reconnection
}

export interface Subscription {
  id: string
  created_at: string
  user_id: string
  tier: SubscriptionTier
  billing_period: BillingPeriod
  amount_vnd: number
  deep_credits_granted: number
  starts_at: string
  expires_at: string
  payos_order_code: string
  payos_payment_id: string | null
  status: 'pending' | 'active' | 'expired' | 'cancelled'
}

export interface CreditTransaction {
  id: string
  created_at: string
  user_id: string
  delta: number                       // negative = debit, positive = credit
  balance_after: number
  reason: 'purchase' | 'query' | 'refund' | 'admin_grant' | 'expiry_reset'
  session_id: string | null
  subscription_id: string | null
}

export interface VideoCorpus {
  id: string
  created_at: string
  video_id: string                    // TikTok aweme_id
  content_type: ContentType
  niche_id: number
  creator_handle: string
  tiktok_url: string
  thumbnail_url: string | null        // R2 WebP URL
  video_url: string | null            // R2 mp4 URL (720p/30s) for Explore playback
  frame_urls: string[]
  analysis_json: VideoAnalysis | CarouselAnalysis
  views: number
  likes: number
  comments: number
  shares: number
  engagement_rate: number             // computed: (likes+comments+shares)/views
  indexed_at: string
}

export interface AnonymousUsage {
  id: string
  created_at: string
  ip_hash: string                     // hashed for privacy
  has_used_free_soikenh: boolean
}

// ─── Analysis JSON shapes (stored in video_corpus.analysis_json) ──────────────

export interface VideoAnalysis {
  hook_type: string
  face_appears_at: number | null      // seconds
  first_frame_type: string
  text_overlays: TextOverlay[]
  scene_transitions_per_second: number
  audio_transcript_excerpt: string | null
  hook_classification: string
  duration_seconds: number
}

export interface CarouselAnalysis {
  slide_count: number
  hook_slide: number                  // index of hook slide
  slides: CarouselSlide[]
  story_arc: string
  swipe_incentive: string | null
}

export interface CarouselSlide {
  index: number
  visual_type: string
  text_overlays: TextOverlay[]
}

export interface TextOverlay {
  text: string
  appears_at_seconds: number | null
}

// ─── Inline chat output component types ──────────────────────────────────────

export interface DiagnosisRow {
  type: 'pass' | 'fail'
  finding: string
  benchmark: string | null
  fix: string | null
}

export interface HookRanking {
  hook_type: string
  multiplier: number                  // e.g. 3.2 = 3.2x views vs baseline
  bar_percent: number                 // 0-100 for animated bar width
}

export interface CreatorCard {
  handle: string
  display_name: string | null
  followers: number
  total_likes: number
  bio_contact: string | null          // email / Zalo / phone from bio
  dominant_hook_type: string | null   // from corpus if available
  posting_frequency_per_week: number | null
  has_corpus_data: boolean
}

export interface BriefBlock {
  title: string
  hook_script: string
  format: string
  pacing_notes: string
  kol_tier: string
  estimated_cost_vnd: string
  affiliate_note: string | null
  reference_video_urls: string[]
}

export interface CorpusCite {
  count: number
  niche: string
  timeframe: string                   // e.g. "7 ngày"
  updated_hours_ago: number
}

// ─── API request / response shapes ───────────────────────────────────────────

export interface ChatRequest {
  session_id: string
  message: string
  intent_type_hint: IntentType | null  // from client-side rule-based detection
}

export interface CreatePaymentRequest {
  tier: SubscriptionTier
  billing_period: BillingPeriod
  is_overage: boolean
  overage_pack_size: 10 | 30 | 50 | null
}

export interface CreatePaymentResponse {
  order_code: string
  payment_url: string                 // PayOS checkout URL
  qr_code_url: string | null
  bank_details: BankTransferDetails | null
  amount_vnd: number
  expires_at: string
}

export interface BankTransferDetails {
  bank_name: string
  account_number: string
  account_name: string
  reference_code: string
}

// ─── SSE stream token shape (Cloud Run → client, never stored in DB) ─────────

export interface SSEToken {
  stream_id: string       // ties all tokens to one response
  seq: number             // monotonically increasing; client stores last_seq for reconnect
  delta: string           // partial text token
  done: boolean           // true on final token
  error?: string          // set on stream error
}

// ─── Niche taxonomy ───────────────────────────────────────────────────────────

export interface NicheTaxonomy {
  id: number
  name_vn: string         // e.g. "Review đồ Shopee / Gia dụng"
  name_en: string
  signal_hashtags: string[]
  created_at: string
}

// ─── Client-safe view types ───────────────────────────────────────────────────

export interface ProfileSummary {
  id: string
  display_name: string
  avatar_url: string | null
  primary_niche: string | null
  subscription_tier: SubscriptionTier
  deep_credits_remaining: number
  credits_reset_at: string | null
}

export interface SessionSummary {
  id: string
  created_at: string
  first_message: string
  intent_type: IntentType | null
  credits_used: number
  is_pinned: boolean
}

export interface NicheIntelligence {
  niche_id: number
  avg_face_appears_at: number | null
  hook_type_distribution: Record<string, number>
  avg_transitions_per_second: number | null
  avg_video_length_seconds: number | null
  median_engagement_rate: number | null
  sample_size: number
  video_count_7d: number
  trending_keywords: Array<{ keyword: string; usage_count: number }>
  computed_at: string
}

export interface TrendVelocity {
  id: string
  niche_id: number
  week_start: string
  hook_type_shifts: Record<string, { prev_pct: number; curr_pct: number; delta: number }>
  format_changes: Record<string, unknown>
  new_hashtags: string[]
  sound_trends: { trending_sounds: Array<{ sound_id: string; name: string; niche_count: number }> }
}

export interface HookEffectiveness {
  id: string
  niche_id: number
  hook_type: string
  avg_views: number
  avg_engagement_rate: number
  avg_completion_rate: number | null
  sample_size: number
  trend_direction: TrendDirection
  computed_at: string
}

export interface FormatLifecycle {
  id: string
  niche_id: number
  format_type: string
  lifecycle_stage: LifecycleStage
  volume_trend: number | null
  engagement_trend: number | null
  weeks_in_stage: number | null
  computed_at: string
}

export interface VideoCorpusSummary {
  id: string
  video_id: string
  creator_handle: string
  tiktok_url: string
  thumbnail_url: string | null
  video_url: string | null
  views: number
  engagement_rate: number
  niche_id: number
  indexed_at: string
  hook_type: string | null            // extracted from analysis_json for display
}
```

---

## 5. External Integrations

| Service | Purpose | SDK / Method | Auth |
|---|---|---|---|
| Supabase | Auth + DB + RLS + Edge Functions + Storage | `@supabase/supabase-js` | publishable key (client) / service role key (Edge Functions) |
| Google Gemini API | Video extraction + synthesis | `@google/generative-ai` | `GEMINI_API_KEY` (Edge Function secret) |
| EnsembleData | TikTok metadata + CDN video URLs | REST API via `fetch` | `ENSEMBLE_DATA_API_KEY` (Edge Function secret) |
| PayOS | Vietnamese payment aggregator (MoMo, VNPay, bank, card) | REST API via `fetch` | `PAYOS_API_KEY`, `PAYOS_CLIENT_ID`, `PAYOS_CHECKSUM_KEY` (secrets) |
| Cloudflare R2 | Frame thumbnails (WebP) + video clips (720p/30s mp4) | `@aws-sdk/client-s3` (S3-compatible) | `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` (secrets) |
| Resend | Transactional email (expiry reminders, Monday plans) | `resend` | `RESEND_API_KEY` (secret) |
| Cloud Run | Video analysis pipeline (avoids Vercel 60s timeout) | Direct HTTP + SSE | Supabase JWT validated via `SUPABASE_JWT_SECRET` |

### Supabase
**SDK:** `@supabase/supabase-js`
**Initialized in:** `src/lib/supabase.ts` (client-safe, publishable key only)
**Key operations:**
- `supabase.auth.signInWithOAuth({ provider: 'facebook' | 'google' })` — auth
- `supabase.from('profiles').select()` — profile data
- `supabase.from('chat_sessions').select()` — session history
- `supabase.from('video_corpus').select()` — Explore browse
- `supabase.rpc('decrement_credit')` — atomic credit deduction (see TD-1)
- `supabase.functions.invoke('create-payment')` — payment initiation

### Google Gemini API
**SDK:** `@google/generative-ai`
**Initialized in:** Cloud Run service only (server-side Python — not a frontend concern). Frontend triggers via SSE to Cloud Run endpoint.
**Models:**
- `gemini-3.1-flash-lite-preview` — video extraction + knowledge answers + batch indexing
- `gemini-3-flash-preview` — Vietnamese synthesis output
**Fallback chains:**
- Extraction: Flash-Lite → Flash
- Synthesis: Flash → Flash-Lite
**Note:** Never reference Gemini 2.5 (shutdown June 17, 2026) or Gemini 2.0 (shutdown March 31, 2026).

### EnsembleData
**SDK:** `fetch` (REST)
**Initialized in:** Cloud Run service (Python). Edge Functions do NOT call EnsembleData.
**Key operations:**
- `GET /tt/keyword/search` — niche batch crawl
- `GET /tt/hashtag/posts` — hashtag crawl
- `POST /tt/user/posts` — fetch creator videos (Intent ③)
- `POST /tt/post/info` — fetch single video metadata (Intents ①③④)
- `GET /tt/user/search` + `GET /tt/user/info` — Find Creators (Intent ⑦)

### PayOS
**SDK:** `fetch` (REST API at api.payos.vn)
**Initialized in:** `supabase/functions/create-payment/` (Edge Function)
**Key operations:**
- `POST /v2/payment-requests` — create payment order, returns QR + bank details
- Webhook: `POST supabase/functions/v1/payos-webhook` — payment confirmation
**Webhook events handled:**
| Event | Handler | What it does |
|---|---|---|
| `PAID` | `supabase/functions/payos-webhook` | Validates checksum, marks subscription active, credits user account, sends receipt email |
| `CANCELLED` | `supabase/functions/payos-webhook` | Marks subscription cancelled, no credits granted |

### Cloudflare R2
**SDK:** `@aws-sdk/client-s3` (S3-compatible)
**Initialized in:** Cloud Run service (batch job writes frames/videos). Edge Functions use R2 only for pre-signed read URLs if needed.
**Buckets:**
- `getviews-frames` — WebP key frames. Public bucket. URL: `https://frames.getviews.vn/{video_id}/{frame_n}.webp`
- `getviews-videos` — 720p/30s mp4 clips. Public bucket. URL: `https://media.getviews.vn/videos/{video_id}.mp4`
- No signed URLs — frames and videos are thumbnails of public TikTok content, no access control needed. Public = permanent URLs.

### Resend
**SDK:** `resend`
**Initialized in:** `supabase/functions/send-email/` — all email sends go through this Edge Function.
**Key operations:** `resend.emails.send()` — triggered by cron + webhook

---

## 6. Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Framework | React Router v7 (Vite) | SPA mode; pre-rendered landing page at `/` for SEO |
| Styling | Tailwind CSS v4 + Make design tokens | Figma Make output; `--purple`, `--ink`, `--surface` tokens |
| Data Fetching | TanStack React Query | Caching, dedup, stale-while-revalidate, mutation invalidation |
| Backend / DB | Supabase (DB + Auth + RLS + Edge Functions) | Sole backend — no server runtime in frontend |
| Auth | Supabase Auth (Facebook OAuth + Google OAuth) | Facebook non-negotiable for Vietnamese market |
| Server logic | Supabase Edge Functions | Webhooks, cron, email, PayOS, service_role operations |
| AI — extraction | Gemini 3.1 Flash-Lite (`gemini-3.1-flash-lite-preview`) | Video extraction — 84.8% Video-MMMU, 50% cheaper than Flash |
| AI — synthesis | Gemini 3 Flash (`gemini-3-flash-preview`) | Vietnamese synthesis — stronger reasoning |
| Video processing | Google Cloud Run (Python) | Avoids Vercel 60s timeout for video analysis; handles SSE streaming |
| Deployment | Vercel | SPA + pre-rendered landing page |
| Payments | PayOS (payos.vn) | Vietnamese aggregator — MoMo, VNPay, bank transfer, Visa/Mastercard |
| Email | Resend | Vietnamese transactional emails |
| Media storage | Cloudflare R2 | Frames (WebP) + video clips (mp4). Zero egress fees — enables Explore |
| Animation | motion (Framer Motion v11) | D1–D6 dopamine moments per EDS §6; CreditBar, HookRankingBars, streaming |
| UI primitives | shadcn/Radix UI (from Figma Make output) | Accordion, Dialog, RadioGroup, Tabs, Select |

---

## 7. Architecture Overview

**Data flow:** React SPA (`src/routes/`) → Supabase (`supabase-js` publishable key + JWT) → Postgres (RLS-enforced). Text intents (⑤⑥⑦ + follow-ups) go via Vercel Edge Runtime → Gemini API. Video intents (①③④) bypass Vercel — client opens SSE directly to Cloud Run endpoint.

**SDK rule:** Every external SDK is initialized through a single wrapper file in `src/lib/`. No component or hook imports a third-party SDK directly. Server-only SDKs (Gemini, EnsembleData, PayOS, Resend, R2) are accessed only via Cloud Run or Supabase Edge Functions, never in the frontend bundle.

**Routing split:**
- Vercel: SPA host + pre-rendered `/` + text intent routing (`/api/chat` for ⑤⑥⑦) via Edge Runtime
- Cloud Run (`getviews-pipeline`, Singapore, `min-instances: 1`): same service serves SSE `/stream`, authenticated JSON routes, and `POST /batch/*` corpus jobs. **Capacity (see `cloud-run/deploy.sh`):** `4Gi` RAM, `2` vCPU, **3600s** max request time — needed so multi-niche corpus ingest (parallel video pulls + Gemini) does not OOM or hit a 300s wall.

**Streaming:** Client connects directly to Cloud Run SSE with Supabase JWT. Cloud Run validates JWT via `jsonwebtoken.verify()` against `SUPABASE_JWT_SECRET` — no Supabase call on hot path. Vercel never proxies video analysis.

---

## 7b. Technical Decisions

### TD-1: Atomic credit deduction

**Context:** When a user sends a deep query, their credit balance must decrease by exactly 1. Multiple browser tabs or rapid double-taps could cause concurrent decrements.
**Complexity signal:** Credit balance that can be spent (race condition in balance updates)
**Options considered:**
- A) Read balance, check > 0, then update — two-step, susceptible to race condition
- B) Atomic SQL: `UPDATE profiles SET deep_credits_remaining = deep_credits_remaining - 1 WHERE user_id = $1 AND deep_credits_remaining > 0 RETURNING deep_credits_remaining` — single operation, fails safely

**Decision:** Option B via Supabase RPC function `decrement_credit(user_id uuid)`. Returns the new balance. If 0 rows returned → insufficient credits.
**Research basis:** Architecture skill — "Race condition in balance updates" anti-pattern; northstar §13 architecture decision.
**Risks:** Supabase RPC add latency (~50ms). Acceptable — credit check happens before routing to Cloud Run.
**Revisit trigger:** If credit granularity changes (fractional credits).

### TD-2: PayOS webhook idempotency

**Context:** PayOS may retry webhooks on network failure. A retry must not credit the user twice.
**Complexity signal:** Idempotent webhooks
**Options considered:**
- A) Check `subscriptions` table for existing `payos_payment_id` before processing
- B) Maintain `processed_webhook_events` table with unique `(payos_order_code, event_type)`

**Decision:** Option B — `processed_webhook_events` table with UNIQUE constraint. `INSERT ... ON CONFLICT DO NOTHING` at the start of webhook handler. If inserted 0 rows → duplicate, return 200 immediately.
**Research basis:** Architecture skill schema anti-pattern checklist — "Idempotent webhooks."
**Risks:** Table grows unbounded. Prune events older than 30 days via weekly cron.
**Revisit trigger:** If PayOS adds native idempotency headers.

### TD-3: Concurrent request guard

**Context:** Users on slow Vietnamese mobile connections may double-tap send, or have multiple tabs open, causing duplicate credit charges and duplicate Cloud Run requests.
**Decision:** Set `profiles.is_processing = true` when a deep request starts; clear on completion or error. Vercel API route rejects messages while `is_processing = true`. Returns "Đang phân tích, vui lòng chờ..." error.
**Research basis:** Northstar §13 best practices — "Concurrent request guard."
**Risks:** If Cloud Run crashes without clearing flag, user is stuck. Mitigation: cron resets stale `is_processing = true` flags older than 5 minutes.

### TD-5: Subscription credit grant model — upfront, not monthly top-up

**Context:** Subscriptions grant a fixed number of deep credits per billing period. PayOS is one-time (no recurring billing). Credits need to be available immediately after payment confirmation.
**Decision:** Credits are granted **once upfront** on the PAID webhook — the full period's allotment (e.g., Starter monthly = 30 credits deposited immediately). There is no monthly top-up cron. When a subscription expires (`cron-expiry-check`), unused credits are cleared and the profile is downgraded to free.
**Implication for seed.sql:** `deep_credits_granted = 30` for Starter monthly is correct — this is the one-time grant for the month. Linh's Pro annual grant of 80 is also correct — the annual pack gives 80 credits upfront (not 80×12). Annual users pay upfront for access, not for monthly allotments.
**Revisit trigger:** If recurring billing is added (Wave 2), this becomes a monthly cron top-up.

### TD-4: SSE reconnection for Vietnamese mobile

**Context:** Vietnamese mobile connections (4G) are prone to blips. If an SSE stream disconnects mid-response, the user loses partial output.
**Decision:** Cloud Run sends `stream_id` + incremental `seq` number with each token. Client stores last `seq`. On disconnect: reconnect with `stream_id` + `last_seq` → Cloud Run replays from in-memory buffer (60s TTL).
**Research basis:** Northstar §13 — "SSE reconnection."

---

## 8a. Data Invariants

| Entity | Invariant | Enforcement |
|---|---|---|
| Profile credits | `deep_credits_remaining` never goes negative | Atomic `WHERE deep_credits_remaining > 0` in RPC; CHECK constraint `deep_credits_remaining >= 0` |
| Profile credits | Every credit change has a corresponding `credit_transactions` row | Edge Function writes both atomically; RLS prevents direct balance update |
| Subscription | A PayOS payment must be idempotent — retries do not double-credit | `processed_webhook_events` table with UNIQUE; RPC grants credits only once |
| Subscription | A user can only have one `active` subscription at a time | CHECK constraint; webhook handler expires previous before activating new |
| ChatSession | A session belongs to exactly one user | FK `user_id` + RLS `auth.uid() = user_id`; NOT NULL |
| VideoCorpus | Each TikTok video is indexed at most once | UNIQUE constraint on `video_id`; batch uses `INSERT ... ON CONFLICT DO NOTHING` |
| Profile free queries | Daily free query count resets once per day | Cron Edge Function resets `daily_free_query_count = 0` nightly |
| Anonymous usage | Each IP gets at most one free Soi Kênh | `anonymous_usage.has_used_free_soikenh` boolean; unique by `ip_hash` |

---

## 8b. Database Schema

### profiles
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK, references auth.users(id) ON DELETE CASCADE | |
| created_at | timestamptz | default now() | |
| updated_at | timestamptz | default now() | updated by trigger |
| display_name | text | NOT NULL, default '' | from OAuth provider |
| email | text | NOT NULL | from OAuth provider |
| avatar_url | text | | from OAuth provider |
| primary_niche | text | | user's self-reported niche label |
| niche_id | integer | FK → niche_taxonomy(id) | resolved from primary_niche text |
| tiktok_handle | text | | optional |
| subscription_tier | text | NOT NULL, default 'free', CHECK IN ('free','starter','pro','agency') | |
| deep_credits_remaining | integer | NOT NULL, default 10, CHECK >= 0 | |
| lifetime_credits_used | integer | NOT NULL, default 0 | |
| credits_reset_at | timestamptz | | when current pack expires |
| daily_free_query_count | integer | NOT NULL, default 0 | for ⑥⑦ rate limiting |
| daily_free_query_reset_at | timestamptz | | reset by cron |
| is_processing | boolean | NOT NULL, default false | concurrent request guard |

RLS:
- SELECT: `auth.uid() = id`
- INSERT: denied (profiles created by `handle_new_user` trigger via service role)
- UPDATE: `auth.uid() = id` (only permitted columns via column-level security or CHECK)
- DELETE: denied

Indexes:
- `CREATE UNIQUE INDEX idx_profiles_id ON profiles(id);` (implicit PK)
- `CREATE INDEX idx_profiles_niche_id ON profiles(niche_id);`

### niche_taxonomy
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | integer | PK, serial | |
| name_vn | text | NOT NULL, UNIQUE | e.g. "Review đồ Shopee / Gia dụng" |
| name_en | text | NOT NULL | |
| signal_hashtags | text[] | NOT NULL, default '{}' | |
| created_at | timestamptz | default now() | |

RLS: SELECT public (no auth required for niche list). No INSERT/UPDATE/DELETE via client.

### chat_sessions
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK, default gen_random_uuid() | |
| created_at | timestamptz | default now() | |
| updated_at | timestamptz | default now() | |
| user_id | uuid | NOT NULL, FK → auth.users(id) ON DELETE CASCADE | |
| title | text | | user-editable |
| first_message | text | NOT NULL | first user message text |
| intent_type | text | CHECK IN (intent values) | set on first intent detection |
| credits_used | integer | NOT NULL, default 0 | total for session |
| is_pinned | boolean | NOT NULL, default false | |
| deleted_at | timestamptz | | soft delete |

RLS:
- SELECT: `auth.uid() = user_id AND deleted_at IS NULL`
- INSERT: `auth.uid() = user_id`
- UPDATE: `auth.uid() = user_id`
- DELETE: denied (use `deleted_at`)

Indexes:
- `CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);`
- `CREATE INDEX idx_chat_sessions_user_created ON chat_sessions(user_id, created_at DESC);`
- `CREATE INDEX idx_chat_sessions_deleted ON chat_sessions(deleted_at) WHERE deleted_at IS NULL;`

### chat_messages
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK, default gen_random_uuid() | |
| created_at | timestamptz | default now() | |
| session_id | uuid | NOT NULL, FK → chat_sessions(id) ON DELETE CASCADE | |
| user_id | uuid | NOT NULL, FK → auth.users(id) | denormalized for RLS |
| role | text | NOT NULL, CHECK IN ('user','assistant') | |
| content | text | | null for structured assistant messages |
| intent_type | text | | |
| credits_used | integer | NOT NULL, default 0 | |
| is_free | boolean | NOT NULL, default true | |
| structured_output | jsonb | | DiagnosisRows, HookRankings, etc. |
| stream_id | text | | for SSE reconnection |

RLS:
- SELECT: `auth.uid() = user_id`
- INSERT: `auth.uid() = user_id`
- UPDATE: denied (messages are immutable)
- DELETE: denied (cascades from session delete)

Indexes:
- `CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);`
- `CREATE INDEX idx_chat_messages_user_id ON chat_messages(user_id);`
- `CREATE INDEX idx_chat_messages_session_created ON chat_messages(session_id, created_at ASC);`

### subscriptions
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK, default gen_random_uuid() | |
| created_at | timestamptz | default now() | |
| user_id | uuid | NOT NULL, FK → auth.users(id) | |
| tier | text | NOT NULL, CHECK IN tier values | |
| billing_period | text | NOT NULL, CHECK IN ('monthly','biannual','annual','overage_10','overage_30','overage_50') | |
| amount_vnd | integer | NOT NULL | |
| deep_credits_granted | integer | NOT NULL | |
| starts_at | timestamptz | NOT NULL | |
| expires_at | timestamptz | NOT NULL | |
| payos_order_code | text | NOT NULL, UNIQUE | |
| payos_payment_id | text | | set on PAID webhook |
| status | text | NOT NULL, default 'pending', CHECK IN ('pending','active','expired','cancelled') | |

RLS:
- SELECT: `auth.uid() = user_id`
- INSERT: denied (created by Edge Function service role)
- UPDATE: denied (updated by Edge Function service role)
- DELETE: denied

Indexes:
- `CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);`
- `CREATE INDEX idx_subscriptions_user_status ON subscriptions(user_id, status);`
- `CREATE UNIQUE INDEX idx_subscriptions_payos_order ON subscriptions(payos_order_code);`

### credit_transactions
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK, default gen_random_uuid() | |
| created_at | timestamptz | default now() | |
| user_id | uuid | NOT NULL, FK → auth.users(id) | |
| delta | integer | NOT NULL | negative = debit |
| balance_after | integer | NOT NULL | snapshot for audit |
| reason | text | NOT NULL, CHECK IN ('purchase','query','refund','admin_grant','expiry_reset') | |
| session_id | uuid | FK → chat_sessions(id) ON DELETE SET NULL | |
| subscription_id | uuid | FK → subscriptions(id) ON DELETE SET NULL | |

RLS:
- SELECT: `auth.uid() = user_id`
- INSERT: denied (written only by Edge Functions and RPC)
- UPDATE: denied
- DELETE: denied

Indexes:
- `CREATE INDEX idx_credit_transactions_user_id ON credit_transactions(user_id);`
- `CREATE INDEX idx_credit_transactions_user_created ON credit_transactions(user_id, created_at DESC);`

### processed_webhook_events
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK, default gen_random_uuid() | |
| created_at | timestamptz | default now() | |
| payos_order_code | text | NOT NULL | |
| event_type | text | NOT NULL | e.g. 'PAID', 'CANCELLED' |

RLS: No client access (service role only).

Indexes:
- `CREATE UNIQUE INDEX idx_processed_events_order_event ON processed_webhook_events(payos_order_code, event_type);`

### video_corpus
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK, default gen_random_uuid() | |
| created_at | timestamptz | default now() | |
| video_id | text | NOT NULL, UNIQUE | TikTok aweme_id |
| content_type | text | NOT NULL, CHECK IN ('video','carousel') | |
| niche_id | integer | NOT NULL, FK → niche_taxonomy(id) | |
| creator_handle | text | NOT NULL | |
| tiktok_url | text | NOT NULL | |
| thumbnail_url | text | | R2 WebP frame URL |
| video_url | text | | R2 mp4 URL (720p/30s) |
| frame_urls | text[] | NOT NULL, default '{}' | R2 frame URLs |
| analysis_json | jsonb | NOT NULL | VideoAnalysis or CarouselAnalysis |
| views | bigint | NOT NULL, default 0 | |
| likes | bigint | NOT NULL, default 0 | |
| comments | bigint | NOT NULL, default 0 | |
| shares | bigint | NOT NULL, default 0 | |
| engagement_rate | numeric(10,4) | NOT NULL, default 0 | |
| indexed_at | timestamptz | NOT NULL, default now() | |

RLS:
- SELECT: authenticated users only (`auth.uid() IS NOT NULL`)
- INSERT: denied (batch job uses service role)
- UPDATE: denied
- DELETE: denied

Indexes:
- `CREATE INDEX idx_corpus_niche_date ON video_corpus(niche_id, indexed_at DESC);`
- `CREATE INDEX idx_corpus_niche_er ON video_corpus(niche_id, engagement_rate DESC);`
- `CREATE INDEX idx_corpus_content_type ON video_corpus(content_type);`
- `CREATE UNIQUE INDEX idx_corpus_video_id ON video_corpus(video_id);`

### niche_intelligence (materialized view)
Refreshed weekly (Sunday night). Computed from `video_corpus`, `hook_effectiveness`, `format_lifecycle`, `trend_velocity`.
| Column | Type | Notes |
|---|---|---|
| niche_id | integer | |
| avg_face_appears_at | numeric | seconds |
| hook_type_distribution | jsonb | `{hook_type: count}` |
| avg_transitions_per_second | numeric | |
| avg_video_length_seconds | numeric | |
| median_engagement_rate | numeric | |
| sample_size | integer | videos in last 30 days |
| video_count_7d | integer | videos indexed in last 7 days — TrendScreen corpus cite |
| trending_keywords | jsonb | `[{keyword: string, usage_count: number}]` — TrendScreen TrendingKeywordSection |
| computed_at | timestamptz | |

### trend_velocity
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| created_at | timestamptz | default now() | |
| niche_id | integer | FK → niche_taxonomy(id) | |
| week_start | date | NOT NULL | |
| hook_type_shifts | jsonb | | `{hook_type: {prev_pct, curr_pct, delta}}` |
| format_changes | jsonb | | |
| engagement_changes | jsonb | | |
| new_hashtags | text[] | | |
| sound_trends | jsonb | | |

RLS: SELECT authenticated only.
Index: `CREATE INDEX idx_trend_velocity_niche_week ON trend_velocity(niche_id, week_start DESC);`

### hook_effectiveness
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| niche_id | integer | FK → niche_taxonomy(id) | |
| hook_type | text | NOT NULL | |
| avg_views | bigint | | |
| avg_engagement_rate | numeric | | |
| avg_completion_rate | numeric | | |
| sample_size | integer | | |
| trend_direction | text | CHECK IN ('rising','stable','declining') | |
| computed_at | timestamptz | | |

RLS: SELECT authenticated only.
Index: `CREATE INDEX idx_hook_effectiveness_niche ON hook_effectiveness(niche_id, computed_at DESC);`

### format_lifecycle
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| niche_id | integer | FK → niche_taxonomy(id) | |
| format_type | text | NOT NULL | |
| lifecycle_stage | text | CHECK IN ('emerging','peaking','declining') | |
| volume_trend | numeric | | week-over-week change |
| engagement_trend | numeric | | |
| weeks_in_stage | integer | | |
| computed_at | timestamptz | | |

RLS: SELECT authenticated only.

### creator_velocity
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| creator_handle | text | NOT NULL | |
| niche_id | integer | FK → niche_taxonomy(id) | |
| follower_trajectory | jsonb | | `[{week, count}]` |
| engagement_trend | text | CHECK IN ('rising','stable','declining') | |
| dominant_hook_type | text | | |
| dominant_format | text | | |
| posting_frequency_per_week | numeric | | |
| velocity_score | numeric | | computed composite |
| computed_at | timestamptz | | |

RLS: SELECT authenticated only.

### batch_failures
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| created_at | timestamptz | default now() | |
| video_id | text | NOT NULL | |
| error_type | text | NOT NULL | |
| failure_count | integer | NOT NULL, default 1 | incremented on retry |
| last_failed_at | timestamptz | | |
| excluded_permanently | boolean | NOT NULL, default false | set after 3 consecutive failures |

RLS: No client access.

### anonymous_usage
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| created_at | timestamptz | default now() | |
| ip_hash | text | NOT NULL, UNIQUE | SHA-256 of IP |
| has_used_free_soikenh | boolean | NOT NULL, default false | |

RLS: No client access (service role only).

### Storage Buckets (Cloudflare R2, not Supabase Storage)
- `getviews-frames` — WebP key frames. Public. Path: `{video_id}/{frame_n}.webp`. Max 200KB per frame.
- `getviews-videos` — 720p/30s mp4. Public. Path: `videos/{video_id}.mp4`. Max ~4MB per file.
Note: R2 buckets are managed outside Supabase — no Supabase Storage RLS needed. Access via AWS S3 SDK in Cloud Run.

---

## 9. Data Access Layer

| Function / Hook | File | Returns | Used by screen(s) |
|---|---|---|---|
| `useProfile()` | `src/hooks/useProfile.ts` | `{ data: ProfileSummary, loading, error }` | All `/app/*` screens (CreditBar, SettingsScreen) |
| `useChatSession(sessionId)` | `src/hooks/useChatSession.ts` | `{ data: ChatMessage[], loading, error }` | ChatScreen |
| `useChatSessions()` | `src/hooks/useChatSessions.ts` | `{ data: SessionSummary[], loading, error }` | HistoryScreen, sidebar |
| `useVideoCorpus(filters)` | `src/hooks/useVideoCorpus.ts` | `{ data: VideoCorpusSummary[], loading, error, fetchNextPage }` | ExploreScreen |
| `useVideoDetail(videoId)` | `src/hooks/useVideoDetail.ts` | `{ data: VideoCorpusSummary \| null, loading, error }` | ExploreScreen VideoDetailModal |
| `useSubscription()` | `src/hooks/useSubscription.ts` | `{ data: Subscription \| null, loading, error }` | SettingsScreen, PricingScreen |
| `useNicheTaxonomy()` | `src/hooks/useNicheTaxonomy.ts` | `{ data: NicheTaxonomy[], loading, error }` | ExploreScreen filter chips, SettingsScreen niche selector, TrendScreen niche chips |
| `useNicheIntelligence(nicheId)` | `src/hooks/useNicheIntelligence.ts` | `{ data: NicheIntelligence \| null, loading, error }` | TrendScreen (hook rankings, format lifecycle, trending keywords, corpus cite) |
| `useTrendVelocity(nicheId)` | `src/hooks/useTrendVelocity.ts` | `{ data: TrendVelocity \| null, loading, error }` | TrendScreen (hook type shifts, sound trends) |
| `useHookEffectiveness(nicheId)` | `src/hooks/useHookEffectiveness.ts` | `{ data: HookEffectiveness[], loading, error }` | TrendScreen HookRankingSection |
| `useFormatLifecycle(nicheId)` | `src/hooks/useFormatLifecycle.ts` | `{ data: FormatLifecycle[], loading, error }` | TrendScreen FormatLifecycleSection |
| `getRelatedVideos(videoId, nicheId)` | `src/lib/data/corpus.ts` | `Promise<VideoCorpusSummary[]>` | ExploreScreen VideoDetailModal "Similar Videos" |
| `searchSessions(query)` | `src/lib/data/sessions.ts` | `Promise<SessionSummary[]>` | HistoryScreen search |
| `updateProfile(patch)` | `src/lib/data/profile.ts` | `Promise<void>` | SettingsScreen niche change |
| `pinSession(sessionId, pinned)` | `src/lib/data/sessions.ts` | `Promise<void>` | ChatScreen / HistoryScreen |
| `renameSession(sessionId, title)` | `src/lib/data/sessions.ts` | `Promise<void>` | ChatScreen / HistoryScreen |
| `deleteSession(sessionId)` | `src/lib/data/sessions.ts` | `Promise<void>` | HistoryScreen |

**Realtime (Supabase channel):**
- `useProfile()` subscribes to `profiles` row changes for the current user — CreditBar updates live after payment webhook credits the account.

---

## 10. API Contracts

**Routing decision:**
- **Direct client → Supabase (RLS):** Profile reads, session/message reads and inserts, video_corpus queries, niche_taxonomy reads
- **Vercel Edge Runtime (`/api/chat`):** Text-only intents ⑤⑥⑦ + follow-ups — Gemini API call, stream via Vercel Edge
- **Cloud Run SSE (`/stream`):** Video intents ①③④ — video download, Gemini extraction + synthesis, SSE stream to client
- **Supabase Edge Functions:** PayOS webhook, payment creation, email sending, cron jobs

---

### supabase/functions/create-payment
**Trigger:** Client call via `supabase.functions.invoke('create-payment', { body })`
**Auth:** Supabase JWT (authenticated user)
**Validation:**
```typescript
{ tier: z.enum(['starter','pro','agency']), billing_period: z.enum(['monthly','biannual','annual']), is_overage: z.boolean(), overage_pack_size: z.union([z.literal(10), z.literal(30), z.literal(50), z.null()]) }
```
**Request body:**
```json
{ "tier": "starter", "billing_period": "annual", "is_overage": false, "overage_pack_size": null }
```
**Response (200):**
```json
{ "order_code": "GV-123456", "payment_url": "https://pay.payos.vn/web/...", "qr_code_url": "...", "bank_details": { "bank_name": "Vietcombank", "account_number": "...", "account_name": "CONG TY GETVIEWS", "reference_code": "GV-123456" }, "amount_vnd": 2388000, "expires_at": "2026-04-09T12:30:00Z" }
```
**Error cases:** 401 (not authenticated), 422 (invalid tier/period combination), 500 (PayOS API failure)

---

### supabase/functions/payos-webhook
**Trigger:** PayOS HTTP POST on payment status change
**Auth:** PayOS HMAC checksum signature (`PAYOS_CHECKSUM_KEY`)
**Validation:** Verify `x-payos-signature` header against request body HMAC-SHA256
**Request body:**
```json
{ "code": "00", "desc": "success", "data": { "orderCode": "GV-123456", "amount": 2388000, "description": "GV-123456", "accountNumber": "...", "reference": "...", "transactionDateTime": "2026-04-09T...", "paymentLinkId": "...", "code": "00", "desc": "Thành công", "counterAccountBankId": null, "counterAccountBankName": null, "counterAccountName": null, "counterAccountNumber": null, "virtualAccountName": null, "virtualAccountNumber": null, "currency": "VND" }, "signature": "..." }
```
**Processing (PAID event):**
1. Insert into `processed_webhook_events` — if conflict, return 200 (duplicate)
2. Validate checksum
3. Find `subscriptions` row by `payos_order_code`
4. Mark subscription `status = 'active'`, set `payos_payment_id`
5. Call `decrement_and_grant_credits` RPC: grant `deep_credits_granted`, insert `credit_transactions` row
6. Update `profiles.subscription_tier`, `credits_reset_at`, `deep_credits_remaining`
7. Invoke `send-email` with `receipt` template
**Response (200):** `{ "success": true }`
**Error cases:** 400 (invalid signature), 500 (DB error)

---

### supabase/functions/send-email
**Trigger:** Internal call from webhook + cron Edge Functions
**Auth:** Service role key only — not callable by clients
**Request body:**
```json
{ "template": "receipt", "to": "minh@example.com", "data": { "display_name": "Nguyễn Minh", "tier": "Starter", "credits": 30, "expires_at": "2027-04-09" } }
```
**Response (200):** `{ "message_id": "..." }`
**Error cases:** 422 (unknown template), 500 (Resend API failure)

---

### supabase/functions/cron-expiry-check
**Trigger:** pg_cron daily at 09:00 ICT (02:00 UTC)
**Auth:** Service role
**What it does:**
1. Find all subscriptions where `expires_at <= now() + 7 days` and status = 'active' and expiry reminder not yet sent
2. Send expiry reminder emails (7-day, 3-day, 1-day windows)
3. Find subscriptions where `expires_at < now()` and status = 'active'
4. Mark them `status = 'expired'`
5. Downgrade profiles to `subscription_tier = 'free'`
6. Reset `daily_free_query_count = 0` for all users whose `daily_free_query_reset_at < now()`

---

### supabase/functions/cron-reset-free-queries
**Trigger:** pg_cron daily at 00:00 ICT (17:00 UTC previous day)
**Auth:** Service role
**What it does:** `UPDATE profiles SET daily_free_query_count = 0, daily_free_query_reset_at = now() WHERE daily_free_query_reset_at < now() - interval '23 hours'`

---

### supabase/functions/cron-prune-webhooks
**Trigger:** pg_cron weekly Sunday 03:00 ICT
**Auth:** Service role
**What it does:** `DELETE FROM processed_webhook_events WHERE created_at < now() - interval '30 days'`

---

### supabase/functions/decrement-credit (RPC, not HTTP Edge Function)
**Type:** Postgres RPC function called via `supabase.rpc('decrement_credit', { p_user_id })`
**SQL:**
```sql
CREATE OR REPLACE FUNCTION decrement_credit(p_user_id uuid)
RETURNS integer AS $$
DECLARE v_balance integer;
BEGIN
  UPDATE profiles
  SET deep_credits_remaining = deep_credits_remaining - 1,
      lifetime_credits_used = lifetime_credits_used + 1
  WHERE id = p_user_id AND deep_credits_remaining > 0
  RETURNING deep_credits_remaining INTO v_balance;
  -- Returns null if no rows updated (insufficient credits)
  RETURN v_balance;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

### Standard Error Response Shape

```json
{
  "error": {
    "code": "INSUFFICIENT_CREDITS",
    "message": "Bạn đã hết deep credits. Mua thêm để tiếp tục phân tích."
  }
}
```

Common codes: `UNAUTHORIZED`, `NOT_FOUND`, `VALIDATION_ERROR`, `RATE_LIMITED`, `INSUFFICIENT_CREDITS`, `VIDEO_DOWNLOAD_FAILED`, `SERVER_ERROR`

---

## 11. Auth & Security Model

- **Auth provider:** Supabase Auth
- **Auth methods:** Facebook OAuth (primary — non-negotiable for Vietnamese market) + Google OAuth (secondary). Both via Supabase built-in OAuth providers. Facebook OAuth requires Supabase OAuth setup (App ID + Secret). Both are native Supabase Auth — no custom OAuth implementation needed.
- **Why these methods:** Vietnamese creators primarily log into everything via Facebook. Google OAuth as fallback for users without Facebook or on iOS with Google-first preference.
- **Anonymous access:** Landing page (`/`). One free Soi Kênh analysis available without account (IP-tracked via `anonymous_usage` table with hashed IP). All other intents require sign-up.
- **Account creation trigger:** After anonymous free Soi Kênh result display, or on first non-Soi-Kênh query attempt → sign-up modal → free tier (10 deep credits + unlimited browse) activated.
- **Auth UI approach:** Custom screens (`LoginScreen.tsx` from Figma Make). No Supabase Auth UI — consumer product requires branded experience.
- **Session handling:** Supabase session persists in localStorage. JWT refreshed automatically by `@supabase/supabase-js`. No manual session expiry.
- **Profile data stored:** `display_name`, `email`, `avatar_url` (from OAuth), `primary_niche`, `niche_id`, `tiktok_handle` (optional), `subscription_tier`, `deep_credits_remaining`, `credits_reset_at`
- **New user trigger:** Supabase `handle_new_user` trigger on `auth.users` INSERT → creates `profiles` row via service role (no client insert).
- **RLS enforcement:** All tables enforce RLS. `user_id = auth.uid()` on all user data tables. `video_corpus`, `niche_taxonomy`, `trend_velocity`, `hook_effectiveness`, `format_lifecycle`, `creator_velocity` — SELECT for authenticated users; no client writes.
- **Cloud Run JWT validation:** Cloud Run validates Supabase JWT via `jsonwebtoken.verify(token, SUPABASE_JWT_SECRET)`. Stateless — no Supabase call on hot path.
- **Service role usage:** Edge Functions (PayOS webhook, cron, email, new user trigger). Never in frontend bundle.

---

## 12. Environment Variables

### Vercel (client-safe, `VITE_` prefix)

| Variable | Description | Where to get it |
|---|---|---|
| `VITE_SUPABASE_URL` | Supabase project URL | Supabase → Project Settings → API |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Supabase anon key | Supabase → Project Settings → API |
| `VITE_CLOUD_RUN_API_URL` | Cloud Run user-facing service URL | GCP → Cloud Run → service URL |

### Supabase Edge Function secrets (`supabase secrets set`)

| Variable | Description | Where to get it |
|---|---|---|
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | Supabase → Project Settings → API |
| `SUPABASE_JWT_SECRET` | JWT secret for Cloud Run validation | Supabase → Project Settings → API → JWT Settings |
| `PAYOS_API_KEY` | PayOS API key | payos.vn → Developer → API Keys |
| `PAYOS_CLIENT_ID` | PayOS client ID | payos.vn → Developer |
| `PAYOS_CHECKSUM_KEY` | PayOS webhook HMAC key | payos.vn → Developer |
| `RESEND_API_KEY` | Resend email API key | resend.com → API Keys |

### Cloud Run environment (set in GCP service config)

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key |
| `ENSEMBLE_DATA_API_KEY` | EnsembleData API key |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 access key |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 secret |
| `R2_ACCOUNT_ID` | Cloudflare account ID |
| `SUPABASE_URL` | Supabase project URL (for batch DB writes) |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key for batch inserts |
| `SUPABASE_JWT_SECRET` | For validating user JWTs on SSE endpoint |
| `PROXY_PROVIDER_URL` | Residential proxy endpoint |
| `PROXY_USERNAME` | Proxy auth |
| `PROXY_PASSWORD` | Proxy auth |

---

## 13. LLM Usage Decisions

| Feature | LLM Used? | Rationale | Model | Est. calls/month |
|---|---|---|---|---|
| Video extraction (frames → JSON) | Yes | Unstructured visual analysis cannot be templated | Gemini 3.1 Flash-Lite | ~255/day batch + per user query |
| Vietnamese synthesis output | Yes | NLP reasoning over corpus context → Vietnamese strategist voice | Gemini 3 Flash | ~30-80 per user/mo |
| Intent classification (ambiguous) | Yes | Natural language classification when rules fail | Gemini 3.1 Flash-Lite | < 5% of queries |
| Follow-up text responses | Yes | Conversational context requires LLM | Gemini 3.1 Flash-Lite | ~50/user/mo |
| Pricing display | No | Static data | — | — |
| Niche aggregate computation | No | SQL aggregates | — | — |
| Session search | No | Postgres text search | — | — |

**Monthly cost ceiling:** $70/month (Gemini API across all intents + batch job)
**Default rule:** SQL and templates for deterministic logic. LLM only for unstructured NLP (video analysis, Vietnamese synthesis, intent classification).

---

## 14. AI Module Inventory

| Capability | Type | Source | Build impact |
|---|---|---|---|
| Video frame extraction → structured JSON | BUILD | Cloud Run Python service (forked from GetReels global) | Fork existing pipeline; add Vietnamese niche taxonomy context |
| Carousel slide analysis | BUILD | Cloud Run Python service | Extend extraction pipeline with carousel branch |
| Vietnamese synthesis prompts | BUILD | Cloud Run (system prompt + knowledge base injection) | Native Vietnamese rewrite of synthesis persona + few-shot examples |
| Intent classifier | BUILD | Vercel Edge Runtime — rule-based first, Gemini Flash-Lite fallback | Rule definitions + Flash-Lite call spec |
| Niche inference resolver | BUILD | `src/lib/niche-resolver.ts` — maps free-text niche → `niche_taxonomy.id` | 4-level resolution: explicit match → keyword match → hashtag match → default |

**Module boundary rule:** All AI modules in Cloud Run receive niche, corpus data, and user context as function arguments — never import app-specific config. Enables extraction to separate service later without modification.

---

## 15. Scheduled Tasks / Cron Jobs

| Job | Schedule | Edge Function | What it does | Auth |
|---|---|---|---|---|
| Daily corpus batch ingest | `0 2 * * *` · `Asia/Ho_Chi_Minh` (02:00 ICT; ≈ prior-day 19:00 UTC) | Cloud Scheduler → `getviews-pipeline` · `POST /batch/ingest` | Crawl all niches (~21), download+analyze up to cap/niche, update `video_corpus` + refresh `niche_intelligence`; optional R2 frame/video | `X-Batch-Secret` = Cloud Run `BATCH_SECRET` + service env |
| Weekly intelligence layer recompute | `0 16 * * 0` UTC (Sunday 11 PM ICT) | Cloud Run batch | Refresh niche_intelligence materialized view, recompute trend_velocity, hook_effectiveness, format_lifecycle, creator_velocity | Service role |
| Daily expiry check + reminders | `0 2 * * *` UTC (9 AM ICT) | `supabase/functions/cron-expiry-check` | Send expiry emails (7d/3d/1d windows), expire subscriptions, downgrade tiers | Service role |
| Daily free query reset | `0 17 * * *` UTC (midnight ICT) | `supabase/functions/cron-reset-free-queries` | Reset `daily_free_query_count = 0` for all users | Service role |
| Weekly webhook event prune | `0 20 * * 0` UTC (Sunday 3 AM ICT) | `supabase/functions/cron-prune-webhooks` | Delete `processed_webhook_events` older than 30 days | Service role |
| Stale processing guard reset | `*/5 * * * *` UTC (every 5 min) | `supabase/functions/cron-reset-processing` | Set `is_processing = false` on profiles where `is_processing = true AND updated_at < now() - 5 minutes` | Service role |

**Cloud Scheduler → Cloud Run:** For `POST /batch/ingest`, set HTTP `attempt-deadline` to **30m** (GCP maximum for Scheduler) and keep Cloud Run **request timeout ≥ that** (`deploy.sh` uses **3600s**). Shorter deadlines cut long batches off mid-flight.

---

## 16. Email / Notification Flows

**Wrapper:** `supabase/functions/send-email/index.ts` — all email sends go through this Edge Function.

| Trigger | Template | To | Subject |
|---|---|---|---|
| PayOS PAID webhook | `receipt` | user email | "Thanh toán thành công — GetViews [Tier]" |
| 7 days before expiry | `expiry_reminder_7d` | user email | "Gói GetViews của bạn hết hạn trong 7 ngày" |
| 3 days before expiry | `expiry_reminder_3d` | user email | "Gói GetViews của bạn hết hạn trong 3 ngày" |
| 1 day before expiry | `expiry_reminder_1d` | user email | "Gói GetViews của bạn hết hạn ngày mai" |
| Weekly (Monday 8 AM ICT) — Wave 2 | `monday_plan` | Starter+ users | "Xu hướng tuần này trong [niche] của bạn" |

### receipt
**Trigger:** PayOS PAID webhook confirmed
**Data:**
```typescript
{ display_name: string; tier: string; credits_granted: number; expires_at: string; amount_vnd: number }
```

### expiry_reminder_*
**Trigger:** cron-expiry-check
**Data:**
```typescript
{ display_name: string; tier: string; expires_at: string; renewal_url: string }
```

---

## 17. Not Building

The following features are explicitly excluded from v1.

- **English-language support** — Vietnamese-only product; global users use GetReels
- **MCP server access** — Vietnamese developer market too small; cut for v1
- **Multi-platform (Reels, Shorts)** — TikTok only; Vietnamese creator economy is TikTok-dominant
- **Creator marketplace / talent management** — GetViews finds creators (Intent ⑦) but does not manage contracts, payments, or ongoing relationships
- **Video editing tools** — GetViews diagnoses, not edits (CapCut territory)
- **Scheduling / posting** — different category
- **Shopee analytics / affiliate dashboard** — GetViews includes affiliate commission rates as context in recommendations but does NOT build a dashboard for tracking Shopee/TikTok Shop earnings, orders, or commission payouts (Kalodata territory)
- **Notification management screen** — email-based renewal reminders only; no in-app notification preferences
- **Admin dashboard** — use Supabase Dashboard directly
- **Competitor tracking dashboard screen** — managed as chat sessions; Wave 2 feature
- **Monday weekly email** — Wave 2 (cron + template built, but content generation deferred)
- **Recurring subscription billing** — PayOS is one-time; packs expire and renew manually
- **Zalo notifications** — Wave 2
- **Douyin trend forecasting** — Wave 2
- **Full livestream analysis** — Wave 3+ (hours-long content, no hook structure)
- **OnboardingScreen** — dropped in Figma phase; niche set inline on first ChatScreen session

**Known shortcuts (deliberate trade-offs — not bugs):**
- No pagination on ExploreScreen — infinite scroll with 20-item pages is sufficient for v1
- No full-text search on `video_corpus` — niche + date filters cover 95% of browse patterns
- `monday_plan` email template created but content generation (Wave 2 LLM call) deferred
- Analysis cache (same-video deduplication across users) — scoped to Wave 1 but deprioritised; batch UNIQUE constraint handles corpus-side dedup

---

## 18. SEO & PWA Infrastructure

### Landing Page Pre-rendering

The landing page at `/` is pre-rendered at build time via `react-router.config.ts` (`prerender: ['/']`). Route: `src/routes/_index/route.tsx`. Exports `meta` function with:

- `title`: "GetViews.vn — Phân tích TikTok bằng Data Thực"
- `description`: "Dán link TikTok vào. 1 phút sau biết lỗi ở đâu, hook nào đang chạy trong niche của bạn, và nên fix gì. Dựa trên hàng ngàn video TikTok Việt Nam đã phân tích."
- `og:title`, `og:description`, `og:image` (`/og-image.png`), `og:type: "website"`, `og:locale: "vi_VN"`
- `html lang="vi"` set in `src/root.tsx`

### Open Graph Image

**Default OG image:** Static PNG at `public/og-image.png` (1200×630px). Shows GetViews wordmark + Vietnamese headline + sample diagnosis UI. Font: TikTok Sans (self-hosted, supports Vietnamese diacritics).

### SEO Static Files

| File | Location | Content |
|---|---|---|
| Sitemap | `public/sitemap.xml` | `/` (priority 1.0). No `/app/*` routes (auth-gated). |
| Robots | `public/robots.txt` | Allow `/`, disallow `/app/` |
| Manifest | `public/manifest.json` | PWA manifest (see below) |

### JSON-LD Structured Data

| Schema | Page | Purpose |
|---|---|---|
| `WebApplication` | Landing page | App name: "GetViews.vn", applicationCategory: "BusinessApplication", offers: free |
| `FAQPage` | Landing page | FAQ items from §15: ChatGPT vs GetViews, khóa học vs GetViews, Kalodata vs GetViews, hiệu quả |

Rendered as `<script type="application/ld+json">` in landing page component. Escape `<` as `\u003c`.

### PWA Manifest (`public/manifest.json`)

```json
{
  "name": "GetViews.vn",
  "short_name": "GetViews",
  "description": "Phân tích TikTok bằng data thực cho creator Việt Nam",
  "start_url": "/app",
  "display": "standalone",
  "background_color": "#EDEDEE",
  "theme_color": "#7C3AED",
  "orientation": "portrait",
  "lang": "vi",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-192-maskable.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ],
  "screenshots": [
    { "src": "/screenshots/chat-mobile.png", "sizes": "390x844", "type": "image/png", "form_factor": "narrow" }
  ]
}
```

### Service Worker

**Library:** `vite-plugin-pwa` (Workbox) — configured in `vite.config.ts`
- `registerType: "autoUpdate"`
- `manifest: false` (using static `public/manifest.json`)
- `navigateFallback: "/index.html"` with allowlist `[/^\/app/]`
- Runtime caching: cache-first for static assets; network-first for Supabase API
- Disabled in development

### Install Prompt

**Hook:** `src/hooks/useInstallPrompt.ts`
- Captures `beforeinstallprompt` (Chromium)
- Defers until user scrolls past hero or taps CTA
- Detects `display-mode: standalone` to hide when already installed
- iOS fallback: detect iOS + show "Thêm vào Màn hình chính" instruction banner

### Core Web Vitals Budget

| Metric | Target | How |
|---|---|---|
| LCP | ≤ 2.5s on 4G | Hero with `loading="eager"`, TikTok Sans `font-display: swap`, pre-rendered HTML |
| CLS | ≤ 0.1 | Reserved heights on skeleton loaders, `size-adjust` in `@font-face` |
| INP | ≤ 200ms | No render-blocking JS; Vite code splitting; route-level `React.lazy()` for all `/app/*` screens |

### Font Loading

Self-hosted in `public/fonts/`:
- `TikTokSans-Variable.woff2` — variable font (100-900 weight range)
- `TikTokSans16pt-Regular/Medium/SemiBold/Bold.woff2` — static fallbacks
- JetBrains Mono — data/numbers display
All declared via `@font-face` in `src/app.css` with `font-display: swap`. Vietnamese glyphs fully covered by TikTok Sans.

### Vietnamese SEO Requirements

- `html lang="vi"` in `src/root.tsx`
- Title and description in Vietnamese with full diacritics
- Target both diacritic and non-diacritic keyword variants in metadata
- Primary keyword targets: "phân tích tiktok", "tool tiktok việt nam", "hook tiktok", "soi video tiktok"
- Domain: `getviews.vn` (`.vn` TLD for local ranking benefit)

### Social Sharing Validation (pre-launch checklist)

| Tool | URL | Purpose |
|---|---|---|
| Facebook Sharing Debugger | `developers.facebook.com/tools/debug/` | Validate OG tags, clear FB cache |
| Zalo Debug Tool | `developers.zalo.me/tools/debug-sharing` | Validate OG tags, clear Zalo cache ("Thu thập lại") |
| OpenGraph.io | `opengraph.io/link-preview` | Cross-platform preview |
| Google Rich Results Test | `search.google.com/test/rich-results` | Validate JSON-LD structured data |
