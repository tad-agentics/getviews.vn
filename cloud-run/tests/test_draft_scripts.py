"""D.1.1 — draft_scripts persistence + export contract (no network).

Covers the four endpoints' unit-level logic in isolation from FastAPI:
  * insert_draft: row shape + optional field handling
  * list_drafts: select / order / limit chain
  * fetch_draft: DraftNotFoundError when RLS hides or id is unknown
  * format_draft_for_copy: Zalo-friendly plain-text shape
  * export_draft (copy path): content_type wiring
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from getviews_pipeline.script_save import (
    DraftCreateBody,
    DraftNotFoundError,
    export_draft,
    fetch_draft,
    format_draft_for_copy,
    insert_draft,
    list_drafts,
)


def _sample_shots() -> list[dict[str, object]]:
    return [
        {
            "t0": 0,
            "t1": 3,
            "cam": "Cận mặt",
            "voice": "Mình vừa test xong rồi đây.",
            "viz": "Tay cầm 2 tai nghe",
            "overlay": "BOLD CENTER",
        },
        {
            "t0": 3,
            "t1": 8,
            "cam": "Cắt nhanh b-roll",
            "voice": "Khác biệt nghe được ngay lần đầu.",
            "viz": "Slow-mo unbox",
            "overlay": "SUB-CAPTION",
        },
    ]


def _sample_body(**overrides) -> DraftCreateBody:
    data = dict(
        topic="Review tai nghe 200k vs 2 triệu",
        hook="Mình test xong rồi đây",
        hook_delay_ms=1200,
        duration_sec=32,
        tone="Chuyên gia",
        shots=_sample_shots(),
        niche_id=3,
    )
    data.update(overrides)
    return DraftCreateBody(**data)


# ── insert_draft ──────────────────────────────────────────────────────────


def test_insert_draft_builds_row_with_user_id_and_returns_inserted():
    sb = MagicMock()
    sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "d-1", "topic": "Review tai nghe 200k vs 2 triệu"}]
    )
    row = insert_draft(sb, user_id="u-1", body=_sample_body())

    assert row["id"] == "d-1"
    call = sb.table.return_value.insert.call_args
    assert call is not None
    payload = call.args[0]
    assert payload["user_id"] == "u-1"
    assert payload["topic"] == "Review tai nghe 200k vs 2 triệu"
    assert payload["niche_id"] == 3
    assert "source_session_id" not in payload  # optional, not sent when None
    assert len(payload["shots"]) == 2


def test_insert_draft_includes_source_session_id_when_provided():
    sb = MagicMock()
    sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "d-2"}]
    )
    insert_draft(
        sb,
        user_id="u-1",
        body=_sample_body(source_session_id="sess-abc"),
    )
    payload = sb.table.return_value.insert.call_args.args[0]
    assert payload["source_session_id"] == "sess-abc"


def test_insert_draft_raises_when_no_row_returned():
    sb = MagicMock()
    sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
    with pytest.raises(RuntimeError, match="no row"):
        insert_draft(sb, user_id="u-1", body=_sample_body())


# ── list_drafts ───────────────────────────────────────────────────────────


def test_list_drafts_orders_by_updated_at_desc_and_limits():
    sb = MagicMock()
    exec_mock = MagicMock(data=[{"id": "d-1", "topic": "A"}, {"id": "d-2", "topic": "B"}])
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = exec_mock
    out = list_drafts(sb, user_id="u-1", limit=10)
    assert len(out) == 2
    sb.table.assert_called_with("draft_scripts")
    # `.order("updated_at", desc=True)` is what the frontend list UX relies on.
    sb.table.return_value.select.return_value.eq.return_value.order.assert_called_with(
        "updated_at", desc=True
    )


# ── fetch_draft ───────────────────────────────────────────────────────────


def test_fetch_draft_raises_not_found_when_empty_row():
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data=None
    )
    with pytest.raises(DraftNotFoundError):
        fetch_draft(sb, user_id="u-1", draft_id="nope")


def test_fetch_draft_returns_dict_when_row_exists():
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data={"id": "d-1", "topic": "Test", "user_id": "u-1"}
    )
    out = fetch_draft(sb, user_id="u-1", draft_id="d-1")
    assert out["id"] == "d-1"


# ── format_draft_for_copy ─────────────────────────────────────────────────


def test_format_draft_for_copy_has_header_meta_and_shot_lines():
    draft = {
        "topic": "Review tai nghe 200k vs 2 triệu",
        "hook": "Mình test xong rồi đây",
        "tone": "Chuyên gia",
        "duration_sec": 32,
        "shots": _sample_shots(),
    }
    out = format_draft_for_copy(draft)
    assert "[KỊCH BẢN] Review tai nghe 200k vs 2 triệu" in out
    assert "Hook: Mình test xong rồi đây" in out
    assert "Tone: Chuyên gia · Thời lượng: 32s" in out
    assert "Shot 1. 00-03s  Cận mặt" in out
    assert "Voice: Mình vừa test xong rồi đây." in out
    assert "Viz:" in out
    assert "Overlay: BOLD CENTER" in out
    # Ends with single newline for clipboard safety.
    assert out.endswith("\n")
    assert not out.endswith("\n\n")


def test_format_draft_for_copy_skips_overlay_none_and_empty_fields():
    draft = {
        "topic": "Short",
        "hook": "",
        "tone": "",
        "duration_sec": 0,
        "shots": [
            {"t0": 0, "t1": 5, "cam": "Cận tay", "voice": "", "viz": "Texture", "overlay": "NONE"}
        ],
    }
    out = format_draft_for_copy(draft)
    assert "Overlay:" not in out  # NONE is not rendered
    assert "Voice:" not in out  # empty voice skipped
    assert "Viz:   Texture" in out


# ── export_draft ──────────────────────────────────────────────────────────


def test_export_draft_copy_returns_text_and_content_type():
    draft = {
        "topic": "X",
        "hook": "H",
        "tone": "T",
        "duration_sec": 15,
        "shots": _sample_shots(),
    }
    payload, ct = export_draft(draft, fmt="copy")
    assert isinstance(payload, str)
    assert ct.startswith("text/plain")
    assert "[KỊCH BẢN] X" in payload


def test_export_draft_unknown_format_raises():
    """Unknown ``fmt`` (e.g. legacy 'pdf' caller) gets a clear error."""
    draft = {"topic": "X", "hook": "H", "tone": "T", "duration_sec": 15, "shots": []}
    with pytest.raises(ValueError, match="unknown export format"):
        export_draft(draft, fmt="pdf")  # type: ignore[arg-type]
