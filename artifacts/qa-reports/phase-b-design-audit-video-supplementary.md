# Phase B · B.1 — supplementary design parity (resolved)

**Date:** 2026-04-19  
**Scope:** Single polish commit closing drifts vs `artifacts/uiux-reference/screens/video.jsx`, `phase-b-plan.md`, and `retention-curve-decision.md`.

**Automated checks (acceptance):** `cloud-run/tests/test_video_analyze.py` — existing cases left intact (fixtures unchanged); added **`test_run_pipeline_respects_mode_override`** only for POST `mode` on a heuristically-win corpus. `src/components/v2/retentionCurveMath.test.ts` — 5 vitest cases for `retentionDropAnnotations`.

| ID | Item | Resolution | Status |
|----|------|------------|--------|
| M-1 | Shell `TopBar` kicker/title | `kicker="BÁO CÁO"`, `title="Phân Tích Video"`; right slot unchanged. | ✅ Shipped |
| M-2 | `meta.niche_label` missing on `/video/analyze` | `_resolve_niche_label()` + field on every response (cache + fresh). | ✅ Shipped |
| M-3 | `meta.retention_source` hardcoded | Wired from `build_niche_benchmark_payload` → `retention_source`. | ✅ Shipped |
| M-4 | Win/flop report kickers | Win: `BÁO CÁO PHÂN TÍCH · {niche_label}`. Flop: `CHẨN ĐOÁN · N ĐIỂM LỖI CẤU TRÚC`; strip duplicate kicker. | ✅ Shipped |
| M-5 | Retention block vs B.0.1 + reference | `RetentionCurve`: `retentionSource` prop, modeled vs real kicker, `p-[18px]`, benchmark stroke `var(--gv-chart-benchmark)`; up to two drop labels from `retentionDropAnnotations`. | ✅ Shipped |
| M-6 | Win/Flop client path + flop typography | `VideoScreen`: `Segmented` + `?mode=` + `useVideoAnalysis` POST `mode`; Cloud Run `VideoAnalyzeRequest.mode` bypasses heuristic + 1h cache when set. Flop H1: `gv-serif-italic` + `var(--gv-accent)` on view accent, `var(--gv-pos)` on prediction. `IssueCard` title: `var(--gv-font-serif)` at 18px. | ✅ Shipped |
| S-1 | Stale clients without `retention_source` | `useVideoAnalysis` `select` defaults `meta.retention_source` to `"modeled"`. | ✅ Shipped |

Also: lessons title `3 điều bạn có thể copy`; retention drop annotation `drop −…% @ …s`; `retentionCurveMath` + tests updated for API shape.

---

## Shipped in commit (per M-item)

| M-ID | Shipped in commit | Notes |
|------|-------------------|--------|
| M-1 | `7820de0` | `VideoScreen` `TopBar` kicker/title parity (`fix(B.1): close supplementary video design parity`). |
| M-2 | `7820de0` | `_resolve_niche_label()` + `meta.niche_label` on `/video/analyze` responses (same commit). |
| M-3 | `7820de0` | `meta.retention_source` from `build_niche_benchmark_payload` / pipeline (same commit). |
| M-4 | `7820de0` | Win vs flop header kickers + duplicate kicker strip (same commit). |
| M-5 | `822d40b`, `05caf2b`, `7820de0` | `822d40b` — `RetentionCurve` + `p-[18px]` + benchmark stroke token on first `/app/video` ship; `05caf2b` — dual steep-drop annotations on the chart; `7820de0` — `retentionSource` kicker wiring / parity batch. |
| M-6 | `6611af0`, `6f0d458`, `6023fcb` | `6611af0` — structured flop `analysis_headline` (**FlopHeadline** JSON in existing `TEXT` column, no migration). `6f0d458` — flop H1 + `IssueCard` title serif. `6023fcb` — client `Segmented` + `?mode=`, `useVideoAnalysis` POST `mode`, `VideoAnalyzeRequest.mode` + pipeline cache bypass when set, `test_run_pipeline_respects_mode_override`. |

**S-1** (stale `retention_source` client default): shipped in `8c52625` — `useVideoAnalysis` `select` sets `meta.retention_source` to `"modeled"` when absent (same change as `winners_sample_size` normalization).
