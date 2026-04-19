# `ENSEMBLE_DATA_API_KEY` sharing audit (repo scope)

**Date:** 2026-04-19 (implementation pass)  
**Method:** ripgrep across workspace for `ensembledata`, `ENSEMBLE_DATA`, `ENSEMBLEDATA`.

## Findings

| Location | Uses ED HTTP? | Notes |
|----------|---------------|--------|
| [`cloud-run/getviews_pipeline/ensemble.py`](../../cloud-run/getviews_pipeline/ensemble.py) | Yes | Single choke point `_ensemble_get` (+ `fetch_post_info` direct GET for URL analysis). |
| [`cloud-run/getviews_pipeline/comment_radar.py`](../../cloud-run/getviews_pipeline/comment_radar.py) | Yes | Calls `_ensemble_get` for comments. |
| [`cloud-run/main.py`](../../cloud-run/main.py) | Indirect | FastAPI routes invoke pipeline / batch code. |
| [`cloud-run/scripts/run_batch_ingest.py`](../../cloud-run/scripts/run_batch_ingest.py) | Indirect | Documents env var for local runs. |
| [`src/routes/_app/ChatScreen.tsx`](../../src/routes/_app/ChatScreen.tsx) | No | UI string `ensembledata_quota` only. |
| [`artifacts/docs/tech-spec.md`](../../artifacts/docs/tech-spec.md) | Doc | Names secret for Edge — verify prod does **not** call ED from Vercel/Edge with the **same** key as Cloud Run. |

## Grep evidence (non–cloud-run)

- No `httpx` / `fetch` to `ensembledata.com` under `src/` in this audit pass.
- Python ED usage is **isolated to `cloud-run/getviews_pipeline/`**.

## Human checklist (cannot be fully automated here)

1. **GCP Cloud Run** — List all revisions/services that mount `ENSEMBLE_DATA_API_KEY` (or `ENSEMBLEDATA_API_TOKEN` alias). Confirm staging vs prod keys differ if budgets are separate.
2. **Cloud Scheduler / Workflows** — Note every cron hitting `/batch/ingest` and whether manual runs overlap the same UTC day.
3. **Local / CI** — Developers with the prod key in `.env` can add dashboard noise; prefer a dedicated dev key.
4. **Other products** — If any non–getviews.vn app shares the key, dashboard “units per video” will never reconcile to this repo alone.

## Scheduler mapping

Record your project’s scheduler job name → URL → schedule (UTC) in this section when known:

- _(fill in: e.g. `batch-ingest-daily` → `https://…/batch/ingest` → `0 2 * * *` UTC)_
