# B.0.1 — Retention curve source (decision record)

**Status:** **Default = modeled curve** (no per-second TikTok retention series in
our EnsembleData integration as of this decision). **Re-open** when API
evidence shows a stable time-series field on post payloads.

**Date:** 2026-04-19  
**Owner:** pipeline + Phase B `/video`  
**Code:** `cloud-run/getviews_pipeline/video_structural.py` —
`model_retention_curve()`, `model_niche_benchmark_curve()`.

---

## Evidence (what we checked)

- EnsembleData entry points used today live in `getviews_pipeline/config.py`:
  - `https://ensembledata.com/apis/tt/post/info`
  - `https://ensembledata.com/apis/tt/post/multi-info`
  - plus search / user / hashtag routes — **none** are wired for a per-second
    “% viewers remaining” array in application code (`ensemble.py` parses
    metadata + metrics, not retention time-series).
- **Action for humans (optional):** with a valid `ENSEMBLE_DATA_API_KEY`, call
  `tt/post/info` for a known `aweme_id` and inspect the raw JSON for any field
  that resembles a retention array. If found: document path + units here,
  then switch `model_retention_curve()` to ingest real points and set
  `meta.retention_source = "real"` in the `/video/analyze` response.

---

## Decision

| Option | Outcome |
|--------|---------|
| **A — Real API series** | **Not selected** until a field is confirmed + rate limits documented. |
| **B — Modeled curve** | **Selected.** Sigmoid-like decay from 100% at \(t=0\) toward niche median retention at \(t \approx\) video duration, with a small breakout multiplier lift. Niche overlay uses a slightly higher end target so the dashed “ngách” line sits above the user curve in typical cases. |

---

## UI contract (Phase B)

- When `meta.retention_source === "modeled"` (or omitted — treat as modeled):
  label the block **ĐƯỜNG ƯỚC TÍNH** (not **ĐƯỜNG GIỮ CHÂN**), per
  `artifacts/plans/phase-b-plan.md`.
- When real telemetry exists: `retention_source: "real"` and use the
  **ĐƯỜNG GIỮ CHÂN · VS NGÁCH** label from `video.jsx`.

---

## Supabase — apply `video_diagnostics` migration

This environment was not `supabase link`ed; migrations ship in-repo only until
you push.

From the repo root (with CLI installed):

```bash
supabase link   # once, per project ref
supabase db push
```

Migration file: `supabase/migrations/20260423000051_video_diagnostics.sql`.

---

## B.0.2 & B.0.3 (pointer)

- **Match score (B.0.2):** formula and weights are locked in
  `artifacts/plans/phase-b-plan.md` § B.0.2 — implement in B.2.1.
- **Pins (B.0.3):** `profiles.reference_channel_handles` + RPC
  `toggle_reference_channel` — migration ships with B.2.1 per plan; no extra
  artifact required here.
