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
| [`src/routes/_app/answer/AnswerScreen.tsx`](../../src/routes/_app/answer/AnswerScreen.tsx) | No | No direct ED HTTP from browser in audit pass. |
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

**Region:** `asia-southeast1` (prod Cloud Scheduler + Cloud Run `getviews-pipeline`).

| Job | Target | Schedule | Auth |
|-----|--------|----------|------|
| `getviews-corpus-ingest` | `POST https://getviews-pipeline-qve2iyonqa-as.a.run.app/batch/ingest` | `0 2 * * *` · `Asia/Ho_Chi_Minh` (02:00 ICT) | Header `X-Batch-Secret` must equal Cloud Run env **`BATCH_SECRET`** |
| `getviews-morning-ritual` | `POST …/batch/morning-ritual` (same service) | `0 22 * * *` · `Asia/Ho_Chi_Minh` | Same header pattern |

**Attempt deadline:** `1500s` (25m) on `getviews-corpus-ingest` — long multi-niche runs may need the job deadline + Cloud Run timeout headroom (see `cloud-run/deploy.sh`).

**Manual run:** `gcloud scheduler jobs run getviews-corpus-ingest --location=asia-southeast1`

## Operational status

- **2026-04-20:** `getviews-corpus-ingest` was returning **401** because `X-Batch-Secret` on the Scheduler job did not match Cloud Run `BATCH_SECRET`. Header was updated to match; subsequent runs show `POST /batch/ingest` accepted and EnsembleData traffic **200**. Re-verify if either secret rotates.
- **2026-04-21 (status refresh):** Latest **complete** batch in Cloud Run logs — **2026-04-20 19:38:57 UTC**, `POST /batch/ingest` **200**; `[ed-meter]` `label=batch_ingest`, **21** niches, **inserted=137**, skipped=0, failed=0, `est_units=147.00` (ED: `tt/hashtag/posts` 105, `tt/keyword/search` 42). Earlier run same day in logs — **2026-04-20 09:56:56 UTC**, **200**, inserted=145, skipped=4, failed=0, `est_units=147.00`.
- **2026-04-21 — manual Scheduler run:** `gcloud scheduler jobs run getviews-corpus-ingest --location=asia-southeast1` logged **`POST /batch/ingest` triggered** at **04:56:46 UTC** and `[corpus] Starting batch ingest for 21 niches`. **Confirm** completion via Log Explorer (`POST /batch/ingest … 200` + `[ed-meter] label=batch_ingest`). Scheduler **1500s** attempt deadline can show a failed *handshake* while Cloud Run continues — see `artifacts/docs/tech-spec.md`.
