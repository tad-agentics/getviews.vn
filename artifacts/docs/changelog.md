# Changelog — GetViews.vn

## How to use

- Add one row per deviation discovered during build — takes 30 seconds
- Do NOT edit specs mid-build — log the deviation here instead
- BLOCKING = can't continue the current feature without resolving this → fix before marking the feature complete
- NON-BLOCKING = log and continue → batch-fix before pre-handoff review (after all features pass QA)
- Move to RESOLVED when fixed, including the commit hash

## Active

| Feature | What changed | Blocking? | Fixed? | Commit |
|---|---|---|---|---|
| Northstar v1.3 update | **Explore screen added** (§11): visual browse grid + R2 inline video playback + Trending This Week + Video detail modal + Videos to Copy sidebar. Free for all tiers (0 credits). This is a new screen not in the current screen-specs — requires Phase 2 amendment before /phase4. | YES — new screen | No | — |
| Northstar v1.3 update | **Batch cost corrected**: $55/mo → $42/mo due to 720p/30s proxy optimization. Proxy step: 1.8GB/day → 1.0GB/day. R2 now stores full 720p/30s video clips. `video_corpus` gains `video_url` column. | NO — infra only | No | — |
| Northstar v1.3 update | **Wave 2 scope** renamed "Intelligence + Explore": Explore page promoted to Wave 2 deliverable. Rate limiting scope updated to include Explore (100/day). | NO — planning only | No | — |
| Figma phase | **OnboardingScreen dropped**: niche selection moved inline to ChatScreen first session. `/onboarding` route redirects to `/app`. No frontend work needed for this screen. | NO — simplification | Yes (Figma phase) | — |
| Figma phase | **ExploreScreen added** (`/app/explore`): 2-column video grid with niche/date/sort filters + VideoDetailModal (inline player, similar videos, "Phân tích" CTA). Implements northstar §11. Free (0 credits). Screen spec added. | NO — new screen, Wave 1 | No | — |
| Figma phase | **LearnMoreScreen added** (`/app/learn-more`): static resources + legal hub (About, Docs, Changelog, Creator Academy, Terms, Privacy, Refund). Accessible from SettingsScreen + sidebar. Screen spec added. | NO — new screen, low complexity | No | — |

| Phase 4 audit | **ChatMessage TypeScript interface consolidated**: removed individual `diagnosis_rows`, `hook_rankings`, etc. fields; replaced with `structured_output: StructuredOutput \| null` typed union to match DB schema. Added `ThumbnailItem` interface. `thumbnails` field name matches Figma Make. | NO | Yes (2026-04-09) | — |
| Phase 4 audit | **TrendScreen data hooks added** to Section 9: `useNicheIntelligence`, `useTrendVelocity`, `useHookEffectiveness`, `useFormatLifecycle`. These were missing, leaving TrendScreen without a data contract. | NO | Yes (2026-04-09) | — |
| Phase 4 audit | **SSEToken interface added** to Section 4 (stream_id + seq + delta + done + error). | NO | Yes (2026-04-09) | — |
| Phase 4 audit | **NicheTaxonomy, NicheIntelligence, TrendVelocity, HookEffectiveness, FormatLifecycle TypeScript interfaces added** to Section 4. These were used by Section 9 hooks but not defined. | NO | Yes (2026-04-09) | — |
| Phase 4 audit | **BillingPeriod type expanded**: added `overage_10 \| overage_30 \| overage_50` to match DB CHECK constraint. | NO | Yes (2026-04-09) | — |
| Phase 4 audit | **IntentType enum expanded**: added `format_lifecycle` to match Figma Make session intent label. | NO | Yes (2026-04-09) | — |
| Phase 4 audit | **niche_intelligence schema expanded**: added `video_count_7d` (integer) and `trending_keywords` (jsonb) columns that TrendScreen references but were missing from the materialized view definition. | NO | Yes (2026-04-09) | — |
| Phase 4 audit | **TD-5 added**: documents upfront credit grant model (PayOS one-time → credits deposited at PAID webhook, no monthly top-up cron). | NO | Yes (2026-04-09) | — |
| Phase 4 audit | **Overage pack 30 credits added** (350,000đ / 11,700đ per credit). Figma Make PricingScreen has 3 packs (10/30/50); screen-specs and tech-spec previously only had 10/50. | NO | Yes (2026-04-09) | — |
| Phase 4 audit | **Overage 50-credit price corrected**: 600,000đ → 550,000đ to match Figma Make. Per-credit drops from 12,000đ to 11,000đ. | NO | Yes (2026-04-09) | — |
| Phase 4 audit | **ZaloPay noted in screen-specs**: Figma Make PaymentMethodRow includes ZaloPay. Confirm PayOS integration supports it before launch. | NO | Yes (2026-04-09) | — |
| Phase 4 audit | **seed.sql trend_velocity extended**: added niches 8 (Gym/Fitness) and 17 (Gaming) rows for TrendScreen dev testing beyond niches 1 and 2. | NO | Yes (2026-04-09) | — |

## Resolved

| Feature | What changed | Resolved | Commit |
|---|---|---|---|
