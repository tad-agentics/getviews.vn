# Phase B · B.4 — supplementary design parity (`/app/script`)

**Date:** 2026-04-19
**Parent audits:** `phase-b-design-audit-script.md` (B.4.6), `phase-b-b4-implementation-audit.md` (post-push checklist).
**Scope:** Second-pass drift check against `artifacts/uiux-reference/screens/script.jsx` after B.4.1–B.4.6 closed on `main` (latest: `e3cf69b` analytics/gap patches + `064e345` PWA/build fix).

---

## Token & banned-pattern sweep (re-verified)

`grep -nE '#[0-9a-fA-F]{3,8}\b|--ink-soft|--purple|--border-active|--gv-purple|text-white|bg-black|rgba\(|rgb\('`

| Scope | Hits |
|---|---|
| `src/routes/_app/script/**/*.tsx` | **0** |
| `src/components/v2/{Script*, Scene*, Mini*, HookTiming*, DurationInsight, CardInput, CitationTag}*.tsx` | **0** |

`var(--gv-chart-benchmark)` is defined in `src/app.css` as `rgb(0, 159, 250)` — the token-catalog equivalent of the reference's raw `rgb(0,159,250)` literal. Consistent with the B.3 backend-palette precedent.

---

## Remaining drifts vs `script.jsx` (after primary audit)

### must-fix

| ID | Item | Reference | Shipped | Fix |
|----|------|-----------|---------|-----|
| M-1 | **Content max-width capped at 1280px** — the outer `<main className="gv-route-main gv-route-main--1280">` resolves to `max-width: 1280px` (see `src/app.css:511-521`). The inner `<div className="mx-auto max-w-[1380px] …">` can never exceed its parent's 1280px; the 1380px ceiling is a no-op. | `maxWidth: 1380` (`script.jsx:31`) | Inner wants 1380; outer caps at 1280. Primary audit recorded the intent but missed the parent cap. | In `ScriptScreen.tsx:261`, drop the `gv-route-main--1280` modifier (keep bare `gv-route-main` which is 1320px, closer to the 1380 target), **or** add a new `.gv-route-main--1380` utility in `app.css` and apply it here. |
| M-2 | Hook-pattern delta missing leading `▲` glyph. Reference: `<span>▲{h.delta}</span>` renders `▲+248%`. Shipped: `<span>{h.delta}</span>` renders `+248%`. | `script.jsx:78` | `ScriptScreen.tsx:347` | Prepend `▲` to the `{h.delta}` span. Keep the existing `gv-chart-benchmark` color. One-character change. |

### should-fix

| ID | Item | Note | Suggested fix |
|----|------|------|---------------|
| S-1 | **Sharp-corner cards became soft-corner cards.** Reference applies `border: 1px solid var(--rule)` with **no border-radius** to `CardInput`, `PacingRibbon`, and all three right-rail cards (tip, độ dài shot, overlay library, reference clips). Shipped adds `rounded-[var(--gv-radius-sm)]` to every one of them via `CardInput.tsx:13`, `ScriptPacingRibbon.tsx:23`, `SceneIntelligencePanel.tsx:45/49/56/77/103`. Cumulative visual softening vs the editorial-sharp reference aesthetic. | Design intent is hard corners throughout the script studio; softness reads as "product-y" vs "publication-y". | Either (a) remove the radius from all five call-sites, or (b) introduce a `--gv-radius-none` override for the script route and apply locally. (a) is simpler. |
| S-2 | **Tip-card typography tighter than reference.** Shipped `SceneIntelligencePanel.tsx:53` uses `tracking-tight` (= `-0.025em`) and `leading-snug` (= `1.375`); reference `script.jsx:311` uses `letterSpacing: -0.01em` and `lineHeight: 1.25`. The serif 18px tip is the hero line in the right rail; too-tight tracking + too-loose leading makes it feel wrong on long tips. | Minor but visible on hero copy. | Swap `tracking-tight` → `tracking-[-0.01em]`; swap `leading-snug` → `leading-[1.25]`. |
| S-3 | **Overlay library dropped the "47 video" social-proof anchor.** Reference: `Trong 47 video thắng, scene loại này dùng:` (`script.jsx:338`). Shipped: `Trong các video thắng, scene loại này hay dùng:` (`SceneIntelligencePanel.tsx:82`). The `47` is meaningful context — reinforces that overlays are corpus-backed. | Possibly dropped because `47` was hardcoded and a real count needs an API hookup — but the scene's `sample_size` is already plumbed through `sceneSampleSize` prop and `activeIntel.sample_size` is available. | Interpolate `activeIntel.sample_size ?? citation.sample_size`: `Trong {N} video thắng, scene loại này dùng:` when N > 0; keep the generic copy as fallback. |

### consider

| ID | Item | Note |
|----|------|------|
| C-1 | **Camera-swatch palette: pastel avatars vs navy/plum reference.** `ScriptShotRow.tsx:3-10` cycles `--gv-avatar-2..6`; reference `script.jsx:273` cycles `['#3A4A5C','#2A3A5C','#3D2F4A','#4A2A3D','#2A4A5C','#5C2A3A']` — moody navy/plum hexes that read as "film editor" rather than "brand avatar". Primary audit parked this as "OK — token-native analogue"; call it out as a larger visual delta than sub-pixel padding. | If the design team wants the cinematic palette back, add a `--gv-shot-cam-1..6` token catalog with the reference hexes. |
| C-2 | **Top padding `pt-2` (8px) vs ref `24px`.** Compensated by `TopBar` + back row height, so visual breathing room is roughly equivalent; primary audit parked as Consider. Flag only if `TopBar` is ever removed from this route. | Leave. |
| C-3 | **`script_no` is frozen at `14` via `useState(() => 14)`.** Reference has the same literal, but the shipped state shape implies future persistence; either wire it to a real counter or mark as `const`. | Minor tech-debt. |
| C-4 | **Disabled header buttons leak the "Sắp có" tooltip to end users.** The reference shows enabled buttons with no handler (same behavior, different UX). Either keep the tooltip (clear signal) or change copy to "Sắp ra mắt — Q2 2026" style. | Leave, re-visit when persistence ships. |

---

## Backend parity check (not in primary audit)

| Area | Status |
|------|--------|
| `POST /script/generate` body validation | `ScriptGenerateBody` pydantic: topic 1-500, hook 1-200, hook_delay_ms 400-3000, duration 15-90, tone literal, niche_id ≥1. Matches left-rail ranges exactly. |
| Caller niche guard | `main.py:1417-1421` enforces `body.niche_id == _resolve_caller_niche_id(token)` → 400 on mismatch. Good — prevents cross-niche credit burn. |
| Credit gate | `_decrement_credit_or_raise` before `build_script_shots` → 402 on `InsufficientCreditsError`. |
| Deterministic shot count | `_WEIGHTS = (3,5,8,8,6,2)` always yields 6 shots summing to `duration`. Rescale works for 15s..90s. |
| `scene_intelligence` RLS | `authenticated` SELECT only; `service_role` upserts nightly via `scene_intelligence_refresh.py`. `MIN_VIDEOS_PER_SCENE_TYPE = 30` gates row emission. |
| `overlay_samples` cap | Tested by `test_scene_intelligence.py::test_overlay_samples_capped_at_five_across_winner_events` — confirms the `break`-across-events guard. |

**Gap:** `/script/generate` v1 returns a deterministic **scaffold** (no LLM). Primary audit OKs this. Gemini upgrade should keep the same HTTP contract (`ScriptShot` shape is stable).

---

## Test coverage

**Backend** (`cloud-run/tests/`):

| File | Tests | Covers |
|------|-------|--------|
| `test_script_generate.py` | 2 | `_segment_lengths` (4 totals), `build_script_shots` shape + topic interpolation. |
| `test_script_data.py` | 3 | `_fmt_delta_pct` signs, `_pattern_label` Vietnamese label, `latest_hook_effectiveness_rows` dedupe by `computed_at`. |
| `test_scene_intelligence.py` | 4 | Parsing video row → events, threshold skip (<30), threshold emit, overlay-sample cap across events. |

**Frontend** (`src/lib/`):

| File | Tests | Covers |
|------|-------|--------|
| `scriptPrefill.test.ts` | 3 | Ritual / channel / video prefill → URL query. Includes 500-char topic truncation. |
| `scriptEditorMerge.test.ts` | 2 | API → editor mapping; `scene_intelligence` overlay merge. |

**Gaps:** No `ScriptScreen.test.tsx`, no unit tests for `ScriptPacingRibbon` / `SceneIntelligencePanel` / `MiniBarCompare` / `HookTimingMeter` / `DurationInsight` / `ScriptForecastBar`. All but the screen-level test are cheap renders (deterministic pure inputs). **Recommended follow-up** (not a must-fix): one render test per primitive asserting key geometry + empty-state branch.

---

## Deferred / aligned-with-plan

- **`script_save` / "Lưu vào lịch quay"** — persistence deferred to Phase C. Disabled with `title="Sắp có"`.
- **Copy / PDF / Chế độ quay** — same deferral.
- **LLM shot generation** — v1 is deterministic template. HTTP contract frozen so Gemini can drop in without client changes.
- **`script_save` analytics event** — intentionally not wired until the save flow lands; `script_screen_load`, `script_generate`, `channel_to_script`, `video_to_script` are live.

---

## Verdict

**Yellow** — primary B.4.6 verdict was green after M-1 (token literals) and S-1/S-2 (benchmark blue) closed. Two supplementary **must-fix** remain (width cap, `▲` delta), three **should-fix** (radius, tip typography, overlay citation count), and one larger **consider** (camera palette). Backend + tests are solid.

Next: fold M-1 + M-2 into a small polish commit. After that, B.4 is structurally complete; Phase C unlocks `script_save` + LLM upgrade.

---

## Traceability

| B.4 milestone | Commit |
|---------------|--------|
| B.4.1 `scene_intelligence` migration + batch + tests | `b25bba9` |
| B.4.2 GET endpoints + api-types | `b25bba9` |
| B.4.3 3-col studio + merge logic + `ScriptScreen` v1 | `b25bba9` |
| B.4.4 Morning ritual prefill | `57f22ea` |
| B.4.5 Channel / video / quick-action prefill + retire `kich-ban` modal | `57f22ea` |
| B.4.6 design audit + token fixes | `57f22ea` |
| `POST /script/generate` + analytics + doc patches | `e3cf69b` |
| PWA workbox glob + Rolldown hook expr build fix | `064e345` |
