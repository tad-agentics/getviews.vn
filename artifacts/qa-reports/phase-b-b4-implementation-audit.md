# Phase B · B.4 — implementation audit (post-push)

**Date:** 2026-04-19 (updated)  
**Git:** `main` includes `POST /script/generate`, analytics patches, and doc alignment for B.4 gaps.

This pass checks **deliverables vs** `artifacts/plans/phase-b-plan.md` §B.4 (data model, endpoints, frontend, milestones B.4.1–B.4.6).

---

## Summary

| Area | Status | Notes |
|------|--------|--------|
| DB + migration `scene_intelligence` | **OK** | `supabase/migrations/20260428120000_scene_intelligence.sql` |
| Nightly / batch refresh | **OK** | `POST /batch/scene-intelligence`, `scene_intelligence_refresh.py`; overlay samples capped across events (regression test). |
| GET script read APIs | **OK** | `/script/scene-intelligence`, `/script/hook-patterns` in `cloud-run/main.py`; `script_data.py`. |
| POST `/script/generate` | **OK (v1)** | `cloud-run/getviews_pipeline/script_generate.py` — deterministic 6-shot scaffold, **one credit** via `decrement_credit`; `niche_id` must match caller `primary_niche`. Client: `useScriptGenerate` + **Tạo lại với AI** applies response + re-merges `scene_intelligence`. |
| `/app/script` route | **OK** | `src/routes.ts` → `app/script`; lazy `ScriptScreen`. |
| TanStack Query 6h stale | **OK** | `useScriptHookPatterns`, `useScriptSceneIntelligence` use `staleTime: 1000 * 60 * 60 * 6`. |
| v2 primitives | **OK** | Pacing ribbon, shot row, hook meter, duration insight, forecast bar, scene panel, mini bars, citation, card input under `src/components/v2/`. |
| B.4.4 Morning ritual → script | **OK** | `scriptPrefill.ts` + ritual surfaces when `primary_niche` set. |
| B.4.5 Channel / video / quick action | **OK** | Channel formula CTA, video win CTA, chat quick action, home quick grid → `/app/script`. |
| Retire `shot_list` **chat CTA** | **OK** | No `kich-ban` modal; typed `shot_list` via `intent-router` unchanged (plan allows). |
| Shell **Kịch Bản** | **OK** | `AppLayout` → `/app/script`; `ScriptScreen` `active="script"`. |
| B.4.6 design audit | **OK** | `phase-b-design-audit-script.md` + token fixes. |
| **Analytics (gap patch)** | **OK** | `logUsage`: `script_screen_load`, `script_generate`, `channel_to_script`, `video_to_script` (see `src/lib/logUsage.ts`). |
| **`script_save`** | **Deferred** | “Lưu vào lịch quay” still disabled until persistence (Phase C / follow-up). |

---

## Milestone checklist (plan §B.4 milestones)

| ID | Milestone | Evidence |
|----|-----------|----------|
| B.4.1 | `scene_intelligence` + batch + tests | Migration; `test_scene_intelligence.py`. |
| B.4.2 | GET endpoints + api-types | `main.py`; `test_script_generate.py` + `script_generate.py`. |
| B.4.3 | 3-col studio + merge logic | `ScriptScreen.tsx`, `scriptEditorMerge.ts` + tests. |
| B.4.4 | Ritual prefill | `scriptPrefillFromRitual`. |
| B.4.5 | Channel + retire shot_list CTA | `scriptPrefillFromChannel`; Playwright quick-actions. |
| B.4.6 | Audit artifact + must-fix | `phase-b-design-audit-script.md`. |

---

## Gaps — status (2026-04-19)

| Gap | Status |
|-----|--------|
| `POST /script/generate` | **Closed (v1)** — deterministic scaffold; Gemini-rich copy can replace `build_script_shots` later without changing the HTTP contract. |
| Doc drift (channel supplementary) | **Closed** — CTA row + deferred section updated. |
| `phase-b-plan.md` quick-action / measurement rows | **Closed** — Lên Kịch Bản Quay marked shipped; measurement table lists `script_*` and `video_to_script`. |
| `script_save` / persistence | **Open** — intentional deferral. |

---

## Commands

```bash
npx tsc --noEmit && npx vitest run
cd cloud-run && python3 -m pytest tests/test_script_generate.py tests/test_scene_intelligence.py -q
```

---

## Verdict

**B.4 implementation gaps from the prior audit are patched:** generate endpoint + UI wiring, product analytics for script/channel/video entry points, and plan/supplementary doc alignment. **`script_save`** remains the only listed measurement event not yet instrumented, pending a real save flow.
