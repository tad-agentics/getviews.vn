# Phase B · B.1 — supplementary design parity (resolved)

**Date:** 2026-04-19  
**Scope:** Single polish commit closing drifts vs `artifacts/uiux-reference/screens/video.jsx`, `phase-b-plan.md`, and `retention-curve-decision.md`.

| ID | Item | Resolution |
|----|------|--------------|
| M-1 | Shell `TopBar` kicker/title | `kicker="BÁO CÁO"`, `title="Phân Tích Video"`; right slot unchanged. |
| M-2 | `meta.niche_label` missing on `/video/analyze` | `_resolve_niche_label()` + field on every response (cache + fresh). |
| M-3 | `meta.retention_source` hardcoded | Wired from `build_niche_benchmark_payload` → `retention_source`. |
| M-4 | Win/flop report kickers | Win: `BÁO CÁO PHÂN TÍCH · {niche_label}`. Flop: `CHẨN ĐOÁN · N ĐIỂM LỖI CẤU TRÚC`; strip duplicate kicker. |
| M-5 | Retention block vs B.0.1 + reference | `RetentionCurve`: `retentionSource` prop, modeled vs real kicker, `p-[18px]`, benchmark stroke `var(--gv-chart-benchmark)`. |
| M-6 | Flop issue title typography | `IssueCard` title uses `var(--gv-font-serif)` at 18px / reference tracking. |
| S-1 | Stale clients without `retention_source` | `useVideoAnalysis` `select` defaults `meta.retention_source` to `"modeled"`. |

Also: lessons title `3 điều bạn có thể copy`; retention drop annotation `drop −…% @ …s`; `retentionCurveMath` + tests updated for API shape.
