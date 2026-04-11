# Project Plan — GetViews.vn

## Planning Phases

- [x] Phase 2 — Screen Specs + Figma Make Brief (commit a3c0ae1)
- [x] Figma Make — Human built prototype; code copied to `src/make-import/` (11 screens, 85 files)
- [x] Phase 4 — Tech Spec (2026-04-09) → `artifacts/docs/tech-spec.md`
- [x] Setup (2026-04-09) → `project.mdc` written, `build-plan.md` generated, `@payos/node` + `resend` installed

## Foundation

- [x] Backend foundation        commit: f83aa55
- [x] Frontend: Make import + component inventory + Tailwind config + landing page + auth screens commit: 81b99f2

## Feature Workstreams

| Feature | Wave | Backend | Frontend | QA | Commit |
|---|---|---|---|---|---|
| auth | 1 | ✅ 89dc2ca | ✅ fd2203f | ✅ a2661f6 | QA PASS 2026-04-08 |
| chat-core (ChatScreen — 7 intents, SSE, credit deduction) | 1 | ✅ 9b8bdd0 | ✅ df0b02c | ✅ 3e1da07 | QA PASS 2026-04-08 |
| history (HistoryScreen — session list, search, resume) | 1 | ✅ e8bc480 | ✅ c4cd6da | ✅ c30f2f3 | QA PASS 2026-04-08 |
| explore (ExploreScreen — corpus grid, VideoDetailModal, R2 playback) | 2 | ✅ 9f09947 | ✅ beff235 | ✅ 304f866 | QA PASS 2026-04-08 |
| trends (TrendScreen — hook rankings, format lifecycle, D2) | 2 | ✅ 58a6446 | ✅ b28a9a7 | ✅ ddaf839 | QA PASS 2026-04-10 |
| billing (PricingScreen + CheckoutScreen + PaymentSuccessScreen + PayOS) | 2 | ✅ f62ca14 | ✅ d706777 | ✅ 5b1c433 | QA PASS 2026-04-10 |
| settings (SettingsScreen + LearnMoreScreen) | 2 | ✅ 322649a | ✅ 09a81a8 | ✅ 8086be5 | QA PASS 2026-04-10 |
| email-cron (expiry reminders + cron jobs) | 2 | ✅ 31a2b70 | N/A | ✅ 54568ab | QA PASS 2026-04-10 |

## Post-Build

- [x] Visual fidelity audit (Product Designer — staging URL vs Make code) commit: 82c4c12
- [x] Pre-handoff code review (QA Agent — /review skill) commit: 2caeb1f

## Wave 3 — Output Quality

Full plan: `artifacts/plans/output-quality-plan.md`

| Feature | Priority | Backend | Frontend | QA | Status |
|---|---|---|---|---|---|
| P0-1: Corpus citations | P0 | ✅ | ✅ | 🔲 | Built — corpus_context.py + formatters.py + prompts.py wired |
| P0-3: Hook formula templates | P0 | ✅ | ✅ | 🔲 | Built — CopyableBlock.tsx + MarkdownRenderer hook detection |
| P0-5: "Chạy vì:" mechanism block | P0 | ✅ | — | 🔲 | Built — prompts.py instruction present |
| P0-2: Thumbnail reference cards | P0 | ✅ | ✅ | 🔲 | Built — VideoRefCard.tsx + VideoRefStrip.tsx + corpus-service.ts |
| P0-4: Recency tags + signal badges | P0 | ✅ | ✅ | 🔲 | Built — SignalBadge.tsx + formatters.ts |
| P0-6: Agentic Step Logger (SSE) | P0 | ✅ | ✅ | 🔲 | Built — step_events.py + AgentStepLogger.tsx + StepSpinner + StepThumbnails |
| P1-6: Trend Card UI | P1 | ✅ | ✅ | 🔲 | Built — TrendCard.tsx + trend_card schema in prompts.py |
| P1-7: Breakout multiplier | P1 | ✅ | — | 🔲 | Built — batch_analytics.py (creator_velocity + breakout_multiplier) |
| P1-8: Signal strength grading | P1 | ✅ | ✅ | 🔲 | Built — signal_classifier.py + SignalBadge.tsx |
| P1-9: Trending This Week (Explore) | P1 | ✅ | ✅ | 🔲 | Built — trending_cards migration + weekly batch + TrendingSection.tsx |
| P1-10: Meta-pattern Monday email | P1 | ✅ | — | 🔲 | Built — cron-monday-email Edge Function |
| P2-11: Cross-creator detection | P2 | ✅ | — | 🔲 | Built — cross_creator_patterns migration + weekly batch |
| P2-12: Video Đáng Học ranking | P2 | ✅ | ✅ | 🔲 | Built — video_dang_hoc migration + daily batch + VideoDangHocSidebar.tsx |
| P2-13: Creator network (stretch) | P2 | 🔲 | — | 🔲 | — |

## Issues

See `artifacts/issues/`
BLOCKING: 0 | NON-BLOCKING: 14
