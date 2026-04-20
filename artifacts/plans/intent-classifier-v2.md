# Intent classifier v2 (Phase C.0.1) — decision record

**Date:** 2026-04-20  
**Source:** `artifacts/plans/phase-c-plan.md` §C.0.1, §A

## Summary

- **Client tier 1+2:** `detectIntent()` in [`src/routes/_app/intent-router.ts`](../../src/routes/_app/intent-router.ts) — structural URL/handle signals + keyword branches for all §A.2 report intents (timing, fatigue, format lifecycle, hook variants, content calendar, subniche, brief, trend, directions).
- **Server tier:** `classify_intent()` in [`cloud-run/getviews_pipeline/intents.py`](../../cloud-run/getviews_pipeline/intents.py) extended with parallel keyword branches; `QueryIntent` enum includes Phase C ids.
- **Destination matrix:** [`cloud-run/getviews_pipeline/intent_router.py`](../../cloud-run/getviews_pipeline/intent_router.py) — `INTENT_TO_DESTINATION` maps intent string → `video` | `channel` | `kol` | `script` | `answer:*`.
- **Budget guard:** `ClassifierDailyBudgetExceeded` in [`cloud-run/getviews_pipeline/ensemble.py`](../../cloud-run/getviews_pipeline/ensemble.py) (mirror `EnsembleDailyBudgetExceeded`). **`CLASSIFIER_GEMINI_DAILY_MAX`** (env, 0 = off) increments per UTC day before each `classify_intent_gemini` call; when exceeded, [`gemini.py`](../../cloud-run/getviews_pipeline/gemini.py) returns deterministic primary (`structural` or `follow_up`) without calling Gemini.
- **Gemini `destination_or_format`:** Deferred to **C.7** per plan — `classify_intent_gemini()` return shape extension lands with final Studio composer routing.

## Confidence tiers

| Tier | Client behaviour |
|------|------------------|
| high | URL / handle / strong keyword → route immediately |
| medium | Keyword match → confirm with Cloud Run classifier when wired |
| low | `follow_up` → Generic on `/answer` post–C.7 |

## Aliases

- SPA uses `creator_search`; Python enum `find_creators` — `intent_router` maps both to `kol`.
