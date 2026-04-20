# Answer session contract (Phase C.0.5)

## Tables

- `answer_sessions` — one row per research session; `format` ∈ `pattern` | `ideas` | `timing` | `generic`.
- `answer_turns` — append-only; `payload` is **§J `ReportV1`** JSON (validated with Pydantic before insert on Cloud Run).

## TD-1 — Credits

- **Primary turn** (`kind === 'primary'`): **1 credit** via Supabase RPC `decrement_credit(p_user_id)` **before** SSE stream starts; insufficient balance → **402 Payment Required**; no `answer_turns` row.
- **Follow-up turns** (`timing`, `creators`, `script`): **0 credits** (session already paid).
- **Generic** humility fallback: **0 credits**.

Integer-only; never client-side read-then-write.

## TD-4 — SSE replay

- Same `stream_id` + `seq` buffer as video `/stream` (`session_store.py`, TTL **120s**).
- Resume query: `?resume_from_seq=<n>`.
- **Caveat:** buffer is per Cloud Run instance; reconnect on a different pod may miss replay (acceptable for C.1 MVP).

## Idempotency

- `POST /answer/sessions` accepts `Idempotency-Key: <uuid>`; server caches **120s** on `(user_id, key)`; replays return the same `session_id`.

## Service role

- Validated report payloads are inserted with **service role** (bypasses RLS). Authenticated users **SELECT** only on `answer_sessions` / `answer_turns`.
