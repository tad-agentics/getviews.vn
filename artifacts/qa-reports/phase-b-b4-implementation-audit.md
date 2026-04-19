# Phase B · B.4 — implementation audit (post-push)

**Date:** 2026-04-19  
**Git:** `57f22ea` on `origin/main` (feat(B.4): script prefill routes, shell nav, design audit fixes).

This pass checks **deliverables vs** `artifacts/plans/phase-b-plan.md` §B.4 (data model, endpoints, frontend, milestones B.4.1–B.4.6).

---

## Summary

| Area | Status | Notes |
|------|--------|--------|
| DB + migration `scene_intelligence` | **OK** | `supabase/migrations/20260428120000_scene_intelligence.sql` |
| Nightly / batch refresh | **OK** | `POST /batch/scene-intelligence`, `scene_intelligence_refresh.py`; overlay samples capped across events (regression test). |
| GET script read APIs | **OK** | `/script/scene-intelligence`, `/script/hook-patterns` in `cloud-run/main.py`; `script_data.py`. |
| POST `/script/generate` | **Not shipped** | No route in `main.py`; UI buttons still disabled with “Sắp có” tooltips — **matches plan deferral** for v1 shot persistence. |
| `/app/script` route | **OK** | `src/routes.ts` → `app/script`; lazy `ScriptScreen`. |
| TanStack Query 6h stale | **OK** | `useScriptHookPatterns`, `useScriptSceneIntelligence` use `staleTime: 1000 * 60 * 60 * 6`. |
| v2 primitives | **OK** | Pacing ribbon, shot row, hook meter, duration insight, forecast bar, scene panel, mini bars, citation, card input under `src/components/v2/`. |
| B.4.4 Morning ritual → script | **OK** | `scriptPrefill.ts` + `HomeMorningRitual`, `MorningRitualBanner`, `ChatScreen` empty states when `primary_niche` set. |
| B.4.5 Channel / video / quick action | **OK** | `ChannelScreen` formula CTA, `VideoScreen` win CTA, `EmptyStates` “Lên Kịch Bản Quay” → `/app/script`; `QuickActions` home script door. |
| Retire `shot_list` **chat CTA** | **OK** | No `kich-ban` modal; typed `shot_list` via `intent-router` unchanged (plan allows). |
| Shell **Kịch Bản** | **OK** | `AppLayout` navigates to `/app/script`; `BottomTabBar` `AppShellActive` includes `script`; `ScriptScreen` sets `active="script"`. |
| B.4.6 design audit | **OK** | `phase-b-design-audit-script.md` + token fixes in script primitives. |

---

## Milestone checklist (plan §B.4 milestones)

| ID | Milestone | Evidence |
|----|-----------|----------|
| B.4.1 | `scene_intelligence` + batch + tests | Migration file; `test_scene_intelligence.py` (4 tests, `python3 -m pytest` **pass**). |
| B.4.2 | GET endpoints + api-types / ForecastBar doc | `main.py` GET handlers; `api-types` ForecastBar comment; hooks call Cloud Run with JWT. |
| B.4.3 | 3-col studio + merge logic | `ScriptScreen.tsx`, `scriptEditorMerge.ts` + tests (Vitest suite **pass**). |
| B.4.4 | Ritual prefill | `scriptPrefillFromRitual`, URL `topic` / `hook` / `duration` / `niche_id`. |
| B.4.5 | Channel + retire shot_list CTA | `scriptPrefillFromChannel`; modal removed; Playwright `quick-actions.spec.ts` navigation case. |
| B.4.6 | Audit artifact + must-fix | `phase-b-design-audit-script.md`; white/black utilities removed from script v2 surfaces. |

---

## Gaps & follow-ups (non-blocking unless noted)

1. **`POST /script/generate`** — Backend + client mutation not implemented; “Tạo lại với AI” / persistence remain disabled. **Expected** for current slice.
2. **Doc drift:** `phase-b-design-audit-channel-supplementary.md` still states channel “Tạo kịch bản…” was disabled until B.4; behaviour is now live. Optional doc refresh.
3. **`phase-b-plan.md` measurement table** (Lên Kịch Bản Quay chip “B.4 in progress”) — optional editorial update to **B.4.5 done**.
4. **Analytics:** `channel_to_script` / `script_save` `logUsage` — verify separately if product wants gates from plan §Measurement.

---

## Commands run for this audit

```bash
npx tsc --noEmit && npx vitest run   # before commit: 93 passed
cd cloud-run && python3 -m pytest tests/test_scene_intelligence.py -q  # 4 passed
```

---

## Verdict

**B.4 is implementation-complete** for everything in scope **except** `POST /script/generate` and related “save / regenerate” affordances, which the plan already treats as a later ship. **Design audit (B.4.6)** is documented and must-fix token items are in `main`.
