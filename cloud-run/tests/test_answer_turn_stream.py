"""PR A — /answer/sessions/:id/turns SSE streaming + TD-4 replay contract.

Covers the two-token wire shape plus the ``?resume_from_seq`` replay path.
Exercises the endpoint generator directly without spinning up FastAPI — the
handler is an ``AsyncIterator[bytes]`` so we can drive it with a stub user
and assert the emitted frames.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest

from getviews_pipeline import session_store


def _parse_sse_frame(frame: bytes) -> dict[str, Any]:
    line = frame.decode("utf-8").strip()
    assert line.startswith("data: "), f"expected SSE data line, got {line!r}"
    return json.loads(line[len("data: "):])


@pytest.fixture(autouse=True)
def _clear_stream_buffer() -> None:
    """Isolate each test from other modules' chunks."""
    session_store._stream_chunks.clear()  # type: ignore[attr-defined]
    yield
    session_store._stream_chunks.clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_fresh_run_emits_payload_then_done() -> None:
    from getviews_pipeline.routers.answer import AnswerTurnAppendBody, answer_append_turn

    body = AnswerTurnAppendBody(query="hook đang hot trong Tech", kind="primary")
    user = {"user_id": "u-1", "access_token": "t"}

    def fake_append_turn(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "turn": {"turn_index": 0, "kind": "primary"},
            "payload": {
                "kind": "pattern",
                "report": {"tldr": {"thesis": "test"}},
            },
        }

    with patch("getviews_pipeline.answer_session.append_turn", fake_append_turn):
        response = await answer_append_turn(
            "sess-1", body, user=user, resume_stream_id=None, resume_from_seq=None
        )
        frames = [chunk async for chunk in response.body_iterator]

    assert len(frames) == 2, f"expected 2 frames, got {len(frames)}"
    token1 = _parse_sse_frame(frames[0])
    token2 = _parse_sse_frame(frames[1])

    assert token1["seq"] == 1 and token1["done"] is False
    assert "payload" in token1 and token1["payload"]["kind"] == "pattern"
    assert token2["seq"] == 2 and token2["done"] is True
    assert token1["stream_id"] == token2["stream_id"]

    # Buffer populated for future replay.
    cached = session_store.get_stream_chunks(token1["stream_id"])
    assert cached is not None and len(cached) == 2


@pytest.mark.asyncio
async def test_insufficient_credits_emits_error_done_and_does_not_buffer() -> None:
    from getviews_pipeline.routers.answer import AnswerTurnAppendBody, answer_append_turn

    body = AnswerTurnAppendBody(query="q", kind="primary")
    user = {"user_id": "u-1", "access_token": "t"}

    def raise_402(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("insufficient_credits")

    with patch("getviews_pipeline.answer_session.append_turn", raise_402):
        response = await answer_append_turn(
            "sess-1", body, user=user, resume_stream_id=None, resume_from_seq=None
        )
        frames = [chunk async for chunk in response.body_iterator]

    assert len(frames) == 1
    token = _parse_sse_frame(frames[0])
    assert token["done"] is True
    assert token["error"] == "insufficient_credits"


@pytest.mark.asyncio
async def test_resume_replays_from_buffer_without_running_builder() -> None:
    """TD-4: reconnect with resume_stream_id + resume_from_seq replays cache,
    never calls append_turn, and re-emits the exact seq numbers the client
    saw on the live wire."""
    from getviews_pipeline.routers.answer import AnswerTurnAppendBody, answer_append_turn

    # Seed the buffer with seq-stamped items in the M5 shape: each item
    # carries its original seq plus the live event payload. The replay
    # path re-emits these verbatim.
    buffered_payload = {"kind": "pattern", "report": {"tldr": "cached"}}
    session_store.put_stream_chunks(
        "stream-xyz",
        [
            {"seq": 1, "payload": buffered_payload, "turn": None},
            {"seq": 2, "delta": "", "done": True},
        ],
    )

    body = AnswerTurnAppendBody(query="q", kind="primary")
    user = {"user_id": "u-1", "access_token": "t"}

    def fail_if_called(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("append_turn must not be called on resume")

    with patch("getviews_pipeline.answer_session.append_turn", fail_if_called):
        response = await answer_append_turn(
            "sess-1",
            body,
            user=user,
            resume_stream_id="stream-xyz",
            resume_from_seq=0,
        )
        frames = [chunk async for chunk in response.body_iterator]

    # Two tokens, seq matches the cached items.
    assert len(frames) == 2
    first = _parse_sse_frame(frames[0])
    last = _parse_sse_frame(frames[-1])
    assert first["stream_id"] == "stream-xyz"
    assert first["seq"] == 1
    assert first["payload"] == buffered_payload
    assert first["done"] is False
    assert "delta" not in first
    assert last["seq"] == 2
    assert last["done"] is True


@pytest.mark.asyncio
async def test_resume_skips_tokens_below_resume_from_seq() -> None:
    """If the client already received seq=1 (payload) but lost the connection
    before seq=2 (done), retrying with resume_from_seq=1 should emit just the
    trailing done marker."""
    from getviews_pipeline.routers.answer import AnswerTurnAppendBody, answer_append_turn

    buffered_payload = {"kind": "generic", "report": {"tldr": "x"}}
    session_store.put_stream_chunks(
        "stream-partial",
        [
            {"seq": 1, "payload": buffered_payload, "turn": None},
            {"seq": 2, "delta": "", "done": True},
        ],
    )

    body = AnswerTurnAppendBody(query="q", kind="primary")
    user = {"user_id": "u-1", "access_token": "t"}

    def fail_if_called(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("append_turn must not be called on resume")

    with patch("getviews_pipeline.answer_session.append_turn", fail_if_called):
        response = await answer_append_turn(
            "sess-1",
            body,
            user=user,
            resume_stream_id="stream-partial",
            resume_from_seq=1,
        )
        frames = [chunk async for chunk in response.body_iterator]

    assert len(frames) == 1
    token = _parse_sse_frame(frames[0])
    assert token["seq"] == 2
    assert token["done"] is True


@pytest.mark.asyncio
async def test_resume_above_all_cached_seq_falls_through_to_fresh_run() -> None:
    """If resume_from_seq is at or above every cached item, there's nothing
    new to replay — fall through to a fresh ``append_turn`` rather than
    closing the stream silently."""
    from getviews_pipeline.routers.answer import AnswerTurnAppendBody, answer_append_turn

    session_store.put_stream_chunks(
        "stream-stale",
        [
            {"seq": 1, "payload": {"kind": "pattern"}, "turn": None},
            {"seq": 2, "delta": "", "done": True},
        ],
    )

    body = AnswerTurnAppendBody(query="q", kind="primary")
    user = {"user_id": "u-1", "access_token": "t"}

    call_count = {"n": 0}

    def fake_append_turn(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        call_count["n"] += 1
        return {
            "turn": {"turn_index": 0, "kind": "primary"},
            "payload": {"kind": "pattern", "report": {}},
        }

    with patch("getviews_pipeline.answer_session.append_turn", fake_append_turn):
        response = await answer_append_turn(
            "sess-1",
            body,
            user=user,
            resume_stream_id="stream-stale",
            resume_from_seq=99,
        )
        frames = [chunk async for chunk in response.body_iterator]

    assert call_count["n"] == 1
    assert len(frames) == 2  # payload + done from the fresh run


@pytest.mark.asyncio
async def test_resume_cache_miss_falls_through_to_fresh_run() -> None:
    """Cross-pod reconnect (or TTL-expired buffer) must run the builder again
    rather than silently replay a ghost stream."""
    from getviews_pipeline.routers.answer import AnswerTurnAppendBody, answer_append_turn

    body = AnswerTurnAppendBody(query="q", kind="primary")
    user = {"user_id": "u-1", "access_token": "t"}

    call_count = {"n": 0}

    def fake_append_turn(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        call_count["n"] += 1
        return {
            "turn": {"turn_index": 0, "kind": "primary"},
            "payload": {"kind": "pattern", "report": {}},
        }

    with patch("getviews_pipeline.answer_session.append_turn", fake_append_turn):
        response = await answer_append_turn(
            "sess-1",
            body,
            user=user,
            resume_stream_id="not-in-buffer",
            resume_from_seq=0,
        )
        frames = [chunk async for chunk in response.body_iterator]

    assert call_count["n"] == 1
    assert len(frames) == 2  # payload + done
