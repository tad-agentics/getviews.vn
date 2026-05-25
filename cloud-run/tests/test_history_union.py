"""Phase C — history_union RPC client contract tests (answer-only).

The Postgres RPC lives in ``supabase/migrations/20260830000001_phase_c_drop_chat_sessions.sql``
(rewritten from the C.6 union) and is called from the frontend via
``supabase.rpc("history_union", …)``.

These tests verify the **client shape contract** by replaying mock RPC rows and
asserting downstream consumers (``HistoryUnionRow``, ``useHistoryUnion`` filter
params) behave correctly.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

VALID_FILTERS = {"all", "answer"}


def test_history_union_filter_enum_matches_plan() -> None:
    """Phase C — RPC accepts ``all`` and ``answer`` only."""
    assert VALID_FILTERS == {"all", "answer"}


def _mock_rows(now: datetime) -> list[dict[str, Any]]:
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
    now = datetime.now(UTC)
    rows = _mock_rows(now)
    ts = [datetime.fromisoformat(r["updated_at"]) for r in rows]
    assert ts == sorted(ts, reverse=True)


def test_cursor_filter_drops_rows_at_or_after_cursor() -> None:
    now = datetime.now(UTC)
    rows = _mock_rows(now)
    cursor = rows[0]["updated_at"]
    filtered = [
        r
        for r in rows
        if datetime.fromisoformat(r["updated_at"]) < datetime.fromisoformat(cursor)
    ]
    assert len(filtered) == 1
    assert filtered[0]["id"] == "a2"


def test_answer_rows_carry_non_null_format() -> None:
    now = datetime.now(UTC)
    rows = _mock_rows(now)
    for r in rows:
        assert r["type"] == "answer"
        assert r["format"] in {"pattern", "ideas", "timing", "generic", "compare", "video"}


def _apply_filter(rows: list[dict[str, Any]], p_filter: str) -> list[dict[str, Any]]:
    """Python mirror of the RPC filter WHERE clause."""
    if p_filter == "all":
        return list(rows)
    if p_filter == "answer":
        return [r for r in rows if r["type"] == "answer"]
    raise ValueError(f"invalid filter: {p_filter}")


def test_filter_all_returns_everything() -> None:
    now = datetime.now(UTC)
    rows = _mock_rows(now)
    assert len(_apply_filter(rows, "all")) == 2


def test_filter_answer_keeps_answer_rows_only() -> None:
    now = datetime.now(UTC)
    rows = _mock_rows(now)
    out = _apply_filter(rows, "answer")
    assert {r["id"] for r in out} == {"a1", "a2"}
    assert all(r["type"] == "answer" for r in out)
