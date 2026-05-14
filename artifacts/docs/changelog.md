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
| Northstar v1.3 update | **Explore screen added** (§11): visual browse grid + R2 inline video playback + Video detail modal + Videos to Copy sidebar. Free for all tiers (0 credits). This is a new screen not in the current screen-specs — requires Phase 2 amendment before /phase4. | YES — new screen | No | — |
| Northstar v1.3 update | **Batch cost corrected**: $55/mo → $42/mo due to 720p/30s proxy optimization. Proxy step: 1.8GB/day → 1.0GB/day. R2 now stores full 720p/30s video clips. `video_corpus` gains `video_url` column. | NO — infra only | No | — |
| Northstar v1.3 update | **Wave 2 scope** renamed "Intelligence + Explore": Explore page promoted to Wave 2 deliverable. Rate limiting scope updated to include Explore (100/day). | NO — planning only | No | — |
| Figma phase | **ExploreScreen added** (`/app/explore`): 2-column video grid with niche/date/sort filters + VideoDetailModal (inline player, similar videos, "Phân tích" CTA). Implements northstar §11. Free (0 credits). Screen spec added. | NO — new screen, Wave 1 | No | — |
| Figma phase | **LearnMoreScreen added** (`/app/learn-more`): static resources + legal hub (About, Docs, Changelog, Creator Academy, Terms, Privacy, Refund). Accessible from SettingsScreen + sidebar. Screen spec added. | NO — new screen, low complexity | No | — |

## Resolved

| Feature | What changed | Resolved | Commit |
|---|---|---|---|
| Explore / Trends | **Trending This Week retired**: removed `TrendingSection`, `useTrendingCards`, `trending_cards.py`, and the `corpus_ingest` weekly hook. `trending_cards` table + Monday Edge digest unchanged. | 2026-04 | — |
| Figma phase | **OnboardingScreen dropped**: niche selection moved inline to ChatScreen first session. `/onboarding` route redirects to `/app`. No frontend work needed for this screen. | 2026-04 (Figma phase) | — |
| Phase 4 audit | **ChatMessage TypeScript interface consolidated**: removed individual `diagnosis_rows`, `hook_rankings`, etc. fields; replaced with `structured_output: StructuredOutput \| null` typed union to match DB schema. Added `ThumbnailItem` interface. | 2026-04-09 | — |
| Phase 4 audit | **TrendScreen data hooks added** to Section 9: `useNicheIntelligence`, `useTrendVelocity`, `useHookEffectiveness`, `useFormatLifecycle`. | 2026-04-09 | — |
| Phase 4 audit | **SSEToken interface added** to Section 4 (stream_id + seq + delta + done + error). | 2026-04-09 | — |
| Phase 4 audit | **NicheTaxonomy, NicheIntelligence, TrendVelocity, HookEffectiveness, FormatLifecycle TypeScript interfaces added** to Section 4. | 2026-04-09 | — |
| Phase 4 audit | **BillingPeriod type expanded**: added `overage_10 \| overage_30 \| overage_50` to match DB CHECK constraint. | 2026-04-09 | — |
| Phase 4 audit | **IntentType enum expanded**: added `format_lifecycle` to match Figma Make session intent label. | 2026-04-09 | — |
| Phase 4 audit | **niche_intelligence schema expanded**: added `video_count_7d` and `trending_keywords` columns for TrendScreen. | 2026-04-09 | — |
| Phase 4 audit | **TD-5 added**: documents upfront credit grant model (PayOS one-time → credits deposited at PAID webhook, no monthly top-up cron). | 2026-04-09 | — |
| Phase 4 audit | **Overage pack 30 credits added** (350,000đ / 11,700đ per credit). | 2026-04-09 | — |
| Phase 4 audit | **Overage 50-credit price corrected**: 600,000đ → 550,000đ. | 2026-04-09 | — |
| Phase 4 audit | **ZaloPay noted in screen-specs**: Figma Make PaymentMethodRow includes ZaloPay. Confirm PayOS supports before launch. | 2026-04-09 | — |
| Phase 4 audit | **seed.sql trend_velocity extended**: added niches 8 (Gym/Fitness) and 17 (Gaming). | 2026-04-09 | — |
| Two-axis niche refactor | **`profiles.primary_niche` dropped** (PR6 applied 2026-05-13). Cloud Run + FE migrated to `creator_niche_id`. `legacyNicheIdForCreatorNiche()` resolver in `src/lib/profileNiches.ts` and `profile_niches.py` bridges corpus queries. Retain mapping until 2026-06-13. | 2026-05-13 | — |
| v5 pipeline refactor | **Two-Core Architecture shipped**: `run_extraction_core` (static pixel analysis, immutable, 1 Gemini call) + `run_video_diagnosis_core` (cohort-comparative narrative, 1h TTL, 2 Gemini calls). Replaces single monolithic pipeline. `video_diagnostics` table now caches diagnosis layer separately from `video_corpus`. | 2026-05-13 | — |
| v5 pipeline refactor | **`_schema_version: "v5"` marker added** to backend response. Frontend `isV5Report()` uses this as primary signal; sentence-count heuristic is fallback only. | 2026-05-13 | — |
| v5 pipeline refactor | **`admin_flush_video_diagnostics_cache` RPC added** (migration `20260513070000_*`). Admin-only, accepts TikTok URL, deletes matching `video_diagnostics` rows. Used by acceptance tests to force fresh analysis. | 2026-05-13 | — |
| v5 UI layout audit | **VideoBody layout changes**: "Vấn đề chính" → "Vấn đề cốt lõi"; error rows numbered 1/2/3 (replaces severity label + timestamp); "Fix" chip → "Sửa:" inline label; "Cần làm gì khác" prose → `NextStepsSection` bullet list; "Lỗi cấu trúc" section header removed (self-labelled by numbers); `ChannelProofBlock` rewritten to show `@handle` title + 2-cell FormatRangeCell (best vs analyzed format). | 2026-05-13 | 461ad56 |
| v5 UI layout audit | **`CreatorComparisonUnavailable` empty state removed**: no longer renders the dashed "not enough data" box when `creator_comparison` is null — `ChannelProofBlock` already covers channel data. | 2026-05-14 | 767cc4c |
| v5 prompt engineering | **Channel-first diagnosis voice**: `van_de_chinh` now opens with the creator's own channel data (top_videos / per_format_views) as sentence 1, then contrasts what this specific video does differently. `loi_chinh_narrative.narrative` sentence 2 now requires channel data comparison. Voice guide updated with CHANNEL-FIRST mandatory principle + audit-form anti-patterns + channel-first few-shot examples. | 2026-05-14 | a3255b3 |
| v5 prompt engineering | **Error titles and fix instructions sharpened**: title ≤10 words (was ≤5), em-dash allowed for contrast; fix must have 2 parts — specific action at timestamp + quoted concrete example. | 2026-05-13 | — |
| Playwright acceptance | **Phase 4.5 v5 acceptance test added** (`tests/v5-acceptance.spec.ts`, 10 criteria, `v5-acceptance` project in `playwright.config.ts`). C2 updated for "Vấn đề cốt lõi" label; C5 updated for "Sửa:" vs legacy "Fix". | 2026-05-13 | 461ad56 |
