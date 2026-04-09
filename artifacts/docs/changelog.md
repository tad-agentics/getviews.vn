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

## Resolved

| Feature | What changed | Resolved | Commit |
|---|---|---|---|
