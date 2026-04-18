# KOL Finder — seller-first output spec

Status: **proposed** · Owner: pending · Targets: next PR after `claude/fix-niche-inference-uM2wP` merges

## Problem

Today's `creator_search` returns a 3-creator shortlist with `{handle, avatar_video_id, followers≈total_views, er, reason}`. That's enough to confirm a creator exists — not enough for a seller to decide "I will pay this person $X to post about my product this week."

Sellers reading the output have to open TikTok, eyeball each creator's profile, guess at audience, guess at rates, and guess at brand safety. Every one of those steps should be answered by the card.

## Seller decision model (4 pillars)

The output has to let a seller answer each of these in under 10 seconds per card:

1. **Fit** — will their audience buy my product? (niche match, audience demo, past purchases via commerce signals)
2. **Reach** — does the cost-per-view math work? (real followers, post cadence, consistent views)
3. **Performance quality** — is the engagement real? (ER from followers not views, comment/view ratio, trend direction)
4. **Commerce + risk** — safe to partner with? (sponsored history, competitor conflicts, red flags, contact info)

Plus one synthesis field: **"why *this* creator for *my* product"** — the 2-3 reasons tied to the persona slots we already extract (`audience_age`, `pain_points`, `geography`).

## Output JSON shape

The Cloud Run pipeline returns a `creator_search` intent with this shape. Frontend reads from `structured_output`.

```ts
type CoverageMeta = {
  niche_id: number | null;
  niche_label: string;
  corpus_count: number;
  reference_count: number;
  source: "corpus" | "live_aggregate" | "live_search";
  freshness_days: number;
};

type CreatorTier = "nano" | "micro" | "macro" | "mega";
// nano   < 10K   · micro 10K-100K · macro 100K-1M · mega 1M+

type EngagementTrend = "rising" | "stable" | "declining";

type CommerceSignal = {
  shop_linked: boolean;              // tiktok_shop or shopee affiliate detected
  recent_sponsored_count: number;    // last 90d
  competitor_conflicts: string[];    // normalised brand names found in recent sponsored posts
};

type RedFlag =
  | "engagement_anomaly"   // likes/views ratio falls outside creator's own baseline
  | "post_gap"             // no post in > 14 days
  | "declining_views"      // 30-day median < 60-day median
  | "competitor_conflict"; // actively promoting a competitor

type CreatorCard = {
  // Identity
  handle: string;                    // "@thaotranbeauty"
  display_name: string | null;       // "Thảo Trần"
  verified: boolean;
  avatar_url: string | null;
  bio_excerpt: string | null;        // first 140 chars

  // Reach
  followers: number;                 // REAL count from fetch_user_search
  tier: CreatorTier;                 // derived from followers
  posting_frequency_per_week: number;
  days_since_last_post: number;

  // Fit
  niche_match: {
    primary_niche: string;           // "skincare / làm đẹp"
    confidence: number;              // 0..1 — share of last-20 posts in target niche
    secondary_niches: string[];      // e.g. ["lifestyle", "K-beauty"]
  };
  audience: {
    // Where EnsembleData provides it; else null and card shows "—".
    top_age_bucket: string | null;   // "18-24"
    gender_skew: "female" | "male" | "balanced" | null;
    top_region: string | null;       // "Vietnam" | "Hanoi" | "HCMC"
  };

  // Performance
  engagement_rate_followers: number; // real ER = engagements / followers (%)
  comment_rate: number;              // comments / views (%)
  median_views: number;              // 30d median, not mean — resistant to breakout hits
  engagement_trend: EngagementTrend;

  // Best reference
  best_video: {
    video_id: string;
    thumbnail_url: string | null;
    tiktok_url: string;
    views: number;
    why_it_worked: string;           // 1 sentence — hook + formula
  } | null;

  // Commerce + risk
  commerce: CommerceSignal;
  red_flags: RedFlag[];
  contact: {
    email: string | null;
    zalo: string | null;
    management: string | null;       // agency / MCN from bio if mentioned
  };

  // Rationale + rate hint
  reason: string;                    // 2-3 sentences, persona-aware
  rate_ballpark: {
    currency: "VND";
    low: number;
    high: number;
    confidence: "observed" | "tier_estimate";   // observed if we've seen past sponsored posts
  } | null;

  // UI hooks
  actions: Array<
    | { type: "brief"; prompt: string }         // "Tạo brief cho @handle"
    | { type: "deep_dive"; prompt: string }     // "Phân tích chi tiết @handle" → competitor_profile
    | { type: "sponsored_history"; prompt: string }
    | { type: "similar"; prompt: string }
  >;
};

type CreatorSearchResponse = {
  intent: "creator_search";
  niche: string;                      // raw user input
  synthesis: string;                  // short markdown intro (1-2 sentences)
  creators: CreatorCard[];            // length 3-5
  coverage: CoverageMeta;
  follow_ups: string[];               // chip suggestions (existing contract)
};
```

## Per-field data source

| Field | Source | Cost |
|---|---|---|
| handle, display_name, verified, avatar_url, followers | `ensemble.fetch_user_search(keyword)` or `fetch_user_info` by handle | 1 EnsembleData unit per creator (batched) |
| bio_excerpt | `fetch_user_search` response `user.signature` | included |
| tier | derive from `followers` client-side | 0 |
| posting_frequency_per_week, engagement_trend, dominant_format | `creator_velocity` table (existing) | 0 — cached batch output |
| days_since_last_post | `fetch_user_posts(username, depth=1)` first result timestamp | 1 EnsembleData unit |
| niche_match | classify each of their last 20 posts via `hashtag_niche_map.classify_from_hashtags` — % matching target niche_id | 0 (in-memory map lookups) |
| audience.top_age_bucket / gender_skew / top_region | EnsembleData `/user/info` if the field is populated (often empty for VN); else infer from comment-language ratio (Vietnamese vs other) and comment author profile samples | 0–1 unit |
| engagement_rate_followers | Σ(engagements on last 20 posts) ÷ (followers × 20) | derived |
| comment_rate | Σ(comments) ÷ Σ(views) | derived |
| median_views | median of last-20 posts' views | derived |
| best_video + why_it_worked | Top-ER post from the last 20; 1-sentence Gemini reason using existing `analysis_json` if the post is in `video_corpus`, else short live call | 0–1 Gemini call |
| commerce.shop_linked | regex scan of bio + last-20 captions for `shopee.vn`, `tiktok.shop`, `bit.ly/[skincare\|beauty]` | 0 |
| commerce.recent_sponsored_count | keyword scan of last-20 captions (`#hợp tác \| #ad \| #sponsored \| [Brand name]`) | 0 |
| commerce.competitor_conflicts | caller passes optional `competitor_brands` list; we match against caption text | 0 |
| red_flags | derived from the fields above (rule-based) | 0 |
| contact.email / zalo / management | regex scan of bio text | 0 |
| reason | Gemini call that receives persona slots + card facts + this creator's `why_it_worked` | 1 cheap call per creator |
| rate_ballpark | existing industry rules per tier: nano 300-800K, micro 1-4M, macro 5-15M, mega 20M+; override with "observed" when we see past sponsored post pricing leaked in bio/caption | 0 |

**Total Gemini + API cost per creator**: ~2-3 EnsembleData units + 1-2 Gemini calls. For 3 creators that's ~10 units + 6 calls — similar order of magnitude to `run_kol_search` today (~6 Gemini calls) but buys much richer output.

## Scope phasing

### Phase 1 (MVP — ship next PR)
Everything not requiring new EnsembleData endpoints or ML:
- Real followers, tier, verified, avatar, bio
- Posting cadence, days_since_last_post (from `creator_velocity` + last-post fetch)
- Niche match confidence (from `hashtag_niche_map`)
- Median views, real ER, comment rate
- Engagement trend (from `creator_velocity.engagement_trend`)
- Best video + why_it_worked (cached from `video_corpus`)
- Commerce shop_linked + sponsored count (regex)
- Contact extraction (regex — §18 risk already budgeted)
- Red flags derived from in-hand signals
- Persona-aware reason (Gemini — persona slots already extracted)
- Rate ballpark (rule-based per tier)
- Action chips (brief / deep_dive / similar)
- **Product-context follow-up prompt** injected into `follow_ups[]` when the
  current query has no product/price/competitor slots — re-fires
  `creator_search` with the enriched context on the second turn.
- Frontend card hides rows whose data is null (no "—" placeholders).

### Phase 2
- Audience demographics (EnsembleData user-info endpoint — wire + fall back to comment-language inference)
- Competitor conflict detection (caller passes brand list; card surfaces matches)
- Sponsored-history chip → renders a second card listing past sponsored posts with engagement per post

### Phase 3
- Observed rate learning — when we see a price leak ("giá book $500"), store it in a `creator_rate_samples` table and upgrade `rate_ballpark.confidence` to `observed`
- Batch refresh job — update creator_velocity + real follower counts nightly so first-call latency drops

## Card layout (frontend)

```
┌────────────────────────────────────────────────────────────────┐
│ [avatar]  @thaotranbeauty  ✓                            [Tier] │
│           Thảo Trần · 47K followers · Hà Nội                   │
│                                                                │
│ ► Niche match: 92% — đăng skincare 4-5 lần/tuần                │
│ ► Audience: 68% nữ 18-24, 62% Việt Nam (VN-first)              │
│ ► Engagement: 7.4% ER thật · 1.2% comment rate · đang rising ↑ │
│ ► Post gần nhất: 2 ngày trước · Median 18K views               │
│                                                                │
│ ┌──────────────────────┐                                       │
│ │ [best-video thumb]   │ Tại sao chạy: hook "3 sai lầm da dầu" │
│ │ 180K views · 14 ngày │ + before/after, CTA trong 5s đầu      │
│ └──────────────────────┘                                       │
│                                                                │
│ 🛒 Commerce: TikTok Shop linked · 3 post sponsored (90 ngày)   │
│ ⚠ Red flags: (none)                                            │
│ ✉  Email: thao@mail.com · 📱 Zalo: 0912...                     │
│                                                                │
│ **Vì sao hợp với bạn:**                                        │
│ Cô ấy nói riêng tới da dầu 18-25 — sản phẩm K-beauty của bạn   │
│ khớp với 3 video gần nhất. Đã review 2 serum Hàn Quốc, ER cao. │
│                                                                │
│ Giá ước (micro tier): 1.5-4 triệu / post                       │
│                                                                │
│ [Tạo brief]  [Phân tích sâu]  [Xem sponsored history]          │
└────────────────────────────────────────────────────────────────┘
```

A seller reading this knows in 10 seconds: fits product, reachable audience, engagement is real, contact exists, rough budget, concrete "why."

## Migration from today's pipelines

- **`run_kol_search` deleted** — it analysed a video pool rather than creators. The "deep" signal it produced (per-video Gemini extraction) is already available in `video_corpus.analysis_json` for cached videos; any non-cached video falls back to "why_it_worked" sourced from the top post metadata only.
- **`run_creator_search` is the single entry point** — extended to return the `CreatorCard[]` shape above.
- **`find_creators` / `kol_search` / `kol_finder` aliases** resolved to `creator_search` in `_normalize_intent_name`. Old shapes stop being emitted.
- **`is_free_intent` in `main.py:85`** updated: `creator_search` joins the free list so the Cloud Run check matches `FREE_INTENTS` in `api/chat.ts`.

## Open questions — **resolved**

1. **Product context** — not collected in the modal. Instead, the assistant surfaces it as a follow-up in the output after the first 3 cards render: *"Nếu bạn cho mình biết sản phẩm + giá + đối thủ, mình sẽ lọc lại danh sách phù hợp hơn."* This keeps the first response fast and the interaction conversational. The answer re-fires `creator_search` with the extra context passed in `questions[]` so the rationale + competitor-conflict check sharpen on the second turn.
2. **Rate ballpark** — ship with the tier bands below; tune after we see real quotes.
3. **Missing audience data** — **hide the row entirely** when the field is null. No "—" placeholders. Fewer UI cells is cleaner than empty-looking ones.

## Action

Approve the Phase-1 scope above and I'll open a new branch `claude/kol-finder-seller-output` that:
1. Updates `run_creator_search` to return the new shape (backward-compat: old keys remain populated).
2. Deletes `run_kol_search` + the two aliases.
3. Extends `ChatScreen.tsx` to render the new `CreatorCard` layout instead of the minimal 2-line card today.
4. Ships the regex + rule-based helpers as pure functions with unit tests.
