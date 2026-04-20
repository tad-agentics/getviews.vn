# Phase D.0.v — Cross-pod SSE replay evaluation

**Date:** 2026-04-20
**Blocks:** D.5.2 (conditional Redis escalation trigger)
**Status:** Decision locked — **No-op today; D.5.2 ships instrumentation first, escalation deferred until data exists**

---

## Background

`phase-c-plan.md` §C.0.5 set the contract:

> **TD-4 (SSE reconnection) inherited.** Buffer TTL is 120s
> (`_STREAM_REPLAY_TTL_SEC` in `session_store.py:41`). Mid-turn
> dropouts resume from `seq` rather than re-billing. **Best-effort
> caveat:** the buffer is per-instance; with Cloud Run
> `max-instances: 5` and `--concurrency 20`, a reconnect that hits a
> different pod gets a fresh stream rather than a replay. Acceptable
> for C.1 MVP; if measured drop-rate on answer follow-ups exceeds 2%
> post-ship, promote to a Redis-backed buffer in Phase D.

D.0.v is where that escalation decision gets made.

---

## Current state inspection

### In-memory replay buffer (`cloud-run/getviews_pipeline/session_store.py`)

```
_STREAM_REPLAY_TTL_SEC = 120.0        # line 37
_stream_chunks: dict[str, …] = {}     # line 38 — per-process dict
put_stream_chunks(stream_id, chunks)  # line 41-47 — write + TTL
get_stream_chunks(stream_id)          # line 49+     — read
```

Module header explicitly documents the acceptable-degradation caveat:

> "The SSE replay buffer (`put_stream_chunks` / `get_stream_chunks`)
> remains in-process and is intentionally best-effort — a reconnect
> to a different instance gets a fresh stream rather than a replay.
> This is acceptable for MVP."

### Measurement gap — there is no drop-rate telemetry today

Expected instrumentation (per the plan's D.0.v spike work):

> Read `[stream-resume]` log lines from `session_store.py` for the
> last 14 days; count cross-pod misses.

**Actual state:** `grep -rn "stream-resume\|\[stream.resume\]"
cloud-run/ → 0 hits.** The log line the plan assumed would exist was
never written. `session_store.put_stream_chunks` /
`get_stream_chunks` are silent — no resume attempt, no cache hit /
miss, no cross-pod indicator is logged.

This means the 2% threshold cannot be measured from existing data.
D.0.v cannot make the escalation decision today; it defers to
D.5.2 instrumentation.

---

## Decision

### Today (D.0 → D.0.6)

- **No Redis promotion.** The `phase-c-plan.md` trigger ("if measured
  drop-rate > 2%") has no data behind it; escalating without data
  would be speculative.
- **D.5.2 ships SSE drop-rate instrumentation** per its existing
  spec (see Phase D plan §D.5.2). Three client-side events via
  `logUsage`: `sse_drop`, `sse_resume_attempt`, `sse_resume_success`.
  Plus a server-side log line in `session_store.get_stream_chunks`
  tagged `[stream-resume] hit|miss stream_id=… cross_pod_likely=…`.
- **After D.5.2 ships, 14 days of data in `usage_events`** produces
  the first real drop-rate measurement. The escalation trigger
  re-evaluates against that data.

### Trigger for D.5.2.b (Redis promotion) — deferred to post-D.5.2

If the 14-day rolling drop-rate on `sse_resume_attempt` where
`cross_pod_likely=true` exceeds **2% of answer-turn requests**:

- Open `D.5.2.b — Upstash Redis replay buffer` as a post-D hotfix
  (violates hard-stop rule 5 only in spirit; the escalation is a
  hardening response, not a feature).
- Drop-in: swap the module-local `_stream_chunks: dict` for an Upstash
  Redis client with the same `put_stream_chunks` /
  `get_stream_chunks` signature. No endpoint signature changes.
- Cost: Upstash Redis Pay-As-You-Go at Tiny (~10K cmd/day free tier);
  projected $10–$20/mo at current traffic.
- Sizing:
  - Per stream: ~5–10 chunks × ~500 bytes = ~5 KB.
  - 120s TTL = rolling ~1,000 streams in buffer at steady state.
  - Upstash Regional Cache (Singapore) for ≤ 5ms round-trip.

If the rolling drop-rate stays ≤ 2%, no action — document the no-op
in the post-D.5.2 audit note and close the trigger.

### If drop-rate data never materialises (< 50 events over 14 days)

Low-confidence path: either cross-pod reconnect is genuinely rare
(acceptable) or the instrumentation isn't landing for other reasons
(investigate). D.5.2.c debug pass — not scheduled; add if needed.

---

## Instrumentation contract for D.5.2 (restated here so D.0 locks it)

### Server-side — `session_store.py`

Add inside `get_stream_chunks(stream_id)`:

```python
def get_stream_chunks(stream_id: str) -> list[str] | None:
    _prune_expired()
    hit = _stream_chunks.get(stream_id)
    if hit is None:
        # Cross-pod indicator: if the caller's request routing suggests
        # this pod didn't originate the stream, log cross_pod_likely=true.
        # Heuristic — cold-start marker + no prior writes in this pod's
        # _stream_chunks dict for this session prefix.
        logger.info(
            "[stream-resume] miss stream_id=%s cross_pod_likely=%s",
            stream_id,
            "true" if _looks_cross_pod(stream_id) else "false",
        )
        return None
    logger.info("[stream-resume] hit stream_id=%s chunks=%d", stream_id, len(hit["chunks"]))
    return hit["chunks"]
```

### Client-side — `useSessionStream.ts`

Already emits reconnect attempts via `resume_stream_id` / `resume_from_seq`.
D.5.2 wires three `logUsage` calls:

- `sse_drop` — fired when `fetch` throws mid-stream or `res.body.getReader()`
  closes unexpectedly.
- `sse_resume_attempt` — fired on reconnect issuance with
  `{endpoint, session_id, attempted_seq, cross_pod_likely}`.
  `cross_pod_likely` is populated from the response header
  `x-cloud-run-revision` (if it differs from the value captured on the
  original stream open).
- `sse_resume_success` — fired when a payload arrives within 5s of
  resume.

Events land in `usage_events`; D.5.1 cost dashboard + ad-hoc Supabase
SQL query produce the rolling drop-rate over 14 days.

---

## Out-of-scope flags

- **D.0.v does not ship code.** Only a decision record and the
  instrumentation contract for D.5.2.
- **D.0.v does not commit to Upstash.** The Redis promotion is
  conditional on post-D.5.2 data.
- **D.0.v does not audit per-instance memory growth.** If the
  in-process `_stream_chunks` dict leaks under sustained traffic
  (missing `_prune_expired` calls, TTL not firing), D.5.2
  instrumentation will surface it — handle as a separate fix.

---

## Sign-off

No-op decision today. D.5.2 ships the telemetry; escalation trigger
re-evaluates against 14 days of post-D.5.2 data. Upstash Redis
promotion plan documented for fast-follow if data warrants.

**Deliverable merged; feeds D.5.2.**
