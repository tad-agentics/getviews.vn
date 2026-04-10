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
| email-cron (expiry reminders + cron jobs) | 2 | — | — | — | — |

## Post-Build

- [ ] Visual fidelity audit (Product Designer — staging URL vs Make code)
- [ ] Pre-handoff code review (QA Agent — /review skill)

## Issues

See `artifacts/issues/`
BLOCKING: 0 | NON-BLOCKING: 0
