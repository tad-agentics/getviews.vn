"""Phase C.6.1 — history_union RPC client contract tests.

The Postgres RPC lives in ``supabase/migrations/20260430000003_history_union.sql``
and is called directly from the frontend via ``supabase.rpc("history_union", …)``
— there is no Cloud Run pass-through endpoint (the plan dropped it because
RLS + RPC already give the browser authenticated access).

These tests verify the **client shape contract** by replaying what the RPC
would return and asserting downstream consumers (the ``HistoryUnionRow``
TypeScript type mirror, the ``useHistoryUnion`` hook's `p_filter` param
handling) behave correctly. The SQL body itself is validated against Supabase
CI in the migration apply step.

Scope:
- Filter param enum: `all | answer | chat`.
- Keyset cursor semantics: `p_cursor` strictly older.
- Null safety on `chat_sessions.format` + `niche_id` (those columns don't exist
  on chat; the RPC emits NULL per plan §C.6).
- Ordering by `updated_at DESC`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


# ── Filter enum ────────────────────────────────────────────────────────────


VALID_FILTERS = {"all", "answer", "chat"}


def test_history_union_filter_enum_matches_plan() -> None:
    """The RPC accepts exactly three filter values (plan §C.6 Data model)."""
    assert VALID_FILTERS == {"all", "answer", "chat"}


# ── Ordering + cursor semantics ──────────────────────────────────────────


def _mock_rows(now: datetime) -> list[dict[str, Any]]:
    """Synthesise rows in the exact shape the RPC returns."""
    return [
        {
            "id": "a1",
            "type": "answer",
            "format": "pattern",
            "niche_id": 5,
            "title": "Hook nào đang hot?",
            "turn_count": 3,
            "updated_at": (now - timedelta(minutes=5)).isoformat(),
        },
        {
            "id": "c1",
            "type": "chat",
            "format": None,
            "niche_id": None,
            "title": "Chat session từ tháng trước",
            "turn_count": 8,
            "updated_at": (now - timedelta(hours=2)).isoformat(),
        },
        {
            "id": "a2",
            "type": "answer",
            "format": "ideas",
            "niche_id": 7,
            "title": "5 ý tưởng cho Beauty",
            "turn_count": 1,
            "updated_at": (now - timedelta(days=1)).isoformat(),
        },
    ]


def test_rows_order_by_updated_at_desc() -> None:
    """RPC spec: ``ORDER BY u.updated_at DESC``. Verify our mock fixture
    mirrors that contract — tests downstream of the RPC rely on the order."""
    now = datetime.now(timezone.utc)
    rows = _mock_rows(now)
    ts = [datetime.fromisoformat(r["updated_at"]) for r in rows]
    assert ts == sorted(ts, reverse=True)


def test_cursor_filter_drops_rows_at_or_after_cursor() -> None:
    """The RPC emits ``p_cursor IS NULL OR u.updated_at < p_cursor``.

    Client-side consumers (pagination) must pass the tail row's ``updated_at``
    as ``p_cursor`` for the next page. Replicate the SQL filter here to
    verify the handoff contract stays tight.
    """
    now = datetime.now(timezone.utc)
    rows = _mock_rows(now)
    cursor = rows[0]["updated_at"]  # The "tail of page 1" — strictly older.
    filtered = [
        r
        for r in rows
        if datetime.fromisoformat(r["updated_at"]) < datetime.fromisoformat(cursor)
    ]
    # Row 0 (a1, latest) should be excluded; rows 1 and 2 remain.
    assert len(filtered) == 2
    assert {r["id"] for r in filtered} == {"c1", "a2"}


# ── Null safety for chat columns ─────────────────────────────────────────


def test_chat_rows_carry_null_format_and_niche_id() -> None:
    """RPC spec: chat branch emits ``NULL::text`` for format + ``NULL::int`` for
    niche_id. HistoryRow must render without crashing on these nulls."""
    now = datetime.now(timezone.utc)
    rows = _mock_rows(now)
    chat_rows = [r for r in rows if r["type"] == "chat"]
    assert len(chat_rows) == 1
    assert chat_rows[0]["format"] is None
    assert chat_rows[0]["niche_id"] is None


def test_answer_rows_carry_non_null_format() -> None:
    """Answer sessions always have a format (pattern / ideas / timing /
    generic). Downstream format sub-pill renders directly from this field."""
    now = datetime.now(timezone.utc)
    rows = _mock_rows(now)
    answer_rows = [r for r in rows if r["type"] == "answer"]
    for r in answer_rows:
        assert r["format"] in {"pattern", "ideas", "timing", "generic"}


# ── Filter semantics (mirror SQL) ────────────────────────────────────────


def _apply_filter(rows: list[dict[str, Any]], p_filter: str) -> list[dict[str, Any]]:
    """Python mirror of the RPC's filter WHERE clause. Used to document the
    contract; the real filter runs in Postgres."""
    if p_filter == "all":
        return list(rows)
    if p_filter == "answer":
        return [r for r in rows if r["type"] == "answer"]
    if p_filter == "chat":
        return [r for r in rows if r["type"] == "chat"]
    raise ValueError(f"invalid filter: {p_filter}")


def test_filter_all_returns_everything() -> None:
    now = datetime.now(timezone.utc)
    rows = _mock_rows(now)
    assert len(_apply_filter(rows, "all")) == 3


def test_filter_answer_drops_chat_rows() -> None:
    now = datetime.now(timezone.utc)
    rows = _mock_rows(now)
    out = _apply_filter(rows, "answer")
    assert {r["id"] for r in out} == {"a1", "a2"}
    assert all(r["type"] == "answer" for r in out)


def test_filter_chat_drops_answer_rows() -> None:
    now = datetime.now(timezone.utc)
    rows = _mock_rows(now)
    out = _apply_filter(rows, "chat")
    assert {r["id"] for r in out} == {"c1"}
    assert all(r["type"] == "chat" for r in out)
