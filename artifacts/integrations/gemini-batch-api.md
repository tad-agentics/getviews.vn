# Gemini Batch API — research gate for HI-13

**Status:** **IMPLEMENTED** behind env (2026-05-16). Set `CORPUS_INGEST_USE_GEMINI_BATCH=true` on the batch Cloud Run service. Default remains **off** until operators validate latency + provider stability.

**2026-05-19 fixes (HI-13 hardening):** batch JSON parse uses `_normalize_response` (fences); poll timeout calls `batches.cancel` and skips deleting uploaded **video** Files until terminal; logs `batch_stats` (`failed_request_count`, etc.). Tests: `cloud-run/tests/test_hi13_batch_job.py`.

## Go / no-go checklist

| Criterion | Result | Evidence |
|-----------|--------|----------|
| Batch supports structured JSON extraction config | **LIKELY YES** (pilot to confirm `response_json_schema`) | Batch guide documents per-request `config` with `response_mime_type` + `response_schema` (Pydantic); links to [structured output](https://ai.google.dev/gemini-api/docs/structured-output). Interactive path in `cloud-run/getviews_pipeline/gemini.py` uses `response_json_schema` + `thinking_config` on `GenerateContentConfig` — expect same fields under each JSONL line’s `request` / inline dict `config` if it maps to [`GenerateContentRequest`](https://ai.google.dev/api/batch-mode#GenerateContentRequest), **not** yet proven with a real `VideoAnalysis` payload. |
| Video / Files API inputs in batch | **YES** (pattern) | [Batch API — input file](https://ai.google.dev/gemini-api/docs/batch-api#input-file): JSONL lines are full generate requests; “if working with multimodal input, you can reference other uploaded files within your JSONL file.” Aligns with pipeline `Part(file_data=..., video_metadata=...)` **in principle**; **pilot** still required for our clip size + dual Part (full + hook window). |
| `system_instruction` honored | **YES** | Same doc shows per-request `system_instruction` in examples ([batch-api](https://ai.google.dev/gemini-api/docs/batch-api)). |
| `thinking_config` / `thinking_budget=0` honored | **TBD** | Not called out in batch guide snippets; implied by shared request shape — **verify in pilot** (cost-sensitive; see `gemini.py` `_extraction_json_config`). |
| Per-item failure semantics (partial success) | **YES** | Guide: check `batchStats.failedRequestCount`; file output is JSONL per line — response or status/error object per request ([batch-api best practices](https://ai.google.dev/gemini-api/docs/batch-api)). |
| Wall-clock: batch inside nightly ingest window | **RISK** | **SLO: completion within 24 hours** ([batch-api](https://ai.google.dev/gemini-api/docs/batch-api)); many jobs faster. Nightly indexer must tolerate **next-day** completion or use **smaller chunks** if same-night guarantees matter. |
| Pricing: discount applies to video / frame tokens | **YES** (for `gemini-3.1-flash-lite`) | [Pricing — Gemini 3.1 Flash-Lite → Batch](https://ai.google.dev/gemini-api/docs/pricing): Batch input **$0.125 / 1M tokens** for **“(text / image / video)”** vs Standard **$0.25** — same half-off multiplier as other Batch rows; output **$0.75** vs **$1.50** (thinking included in output pricing per table). |
| Reliability | **RISK** | Doc banner (fetched 2026-05-16): Batch API **ongoing incident** — jobs may **randomly fail**; treat as **blocker for default cutover** until cleared or mitigated with retries. |

## Limits (from batch guide)

- **Inline** `src`: total under **20MB**; **JSONL file** via File API up to **2GB** per input file ([batch-api](https://ai.google.dev/gemini-api/docs/batch-api)).
- **50%** of standard interactive cost for the same model ([batch-api](https://ai.google.dev/gemini-api/docs/batch-api) + [pricing](https://ai.google.dev/gemini-api/docs/pricing)).

## Flex vs Batch (cost note)

For `gemini-3.1-flash-lite`, **Flex** tier on the pricing page matches **Batch** token rates in the captured table (same input/output numbers). Flex is **interactive latency**, not async batch — different tradeoff if you need same-day completion without batch queue behavior.

## Recommendation

1. **Do not** replace nightly corpus ingest with Batch-only until: (a) provider incident resolved or acceptable retry story, (b) one pilot batch with **production-like** JSONL (Files-backed video Parts, `VideoAnalysis` schema, `thinking_budget=0`), (c) measured wall-clock vs cron window.
2. **Pilot scope:** small JSONL (e.g. tens of rows), then scale; monitor `failedRequestCount` and line-level errors.
3. **HI-13 plan / issue files:** keep **NO-GO for default ingest** until pilot PASS; promote only after human sign-off on plan amendment (per `qa-gated-implementation`).

## References

- [Gemini Batch API](https://ai.google.dev/gemini-api/docs/batch-api)
- [Batch mode API — GenerateContentRequest](https://ai.google.dev/api/batch-mode#GenerateContentRequest)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Internal: `cloud-run/pyproject.toml` (`google-genai`), `cloud-run/getviews_pipeline/gemini.py` (`_extraction_json_config`, video Parts), `corpus_ingest.py`.
