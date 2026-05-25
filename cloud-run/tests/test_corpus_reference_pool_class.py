"""Evidence reference pool — class-first cohort (§4.8.4)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.corpus_context import (
    _fetch_corpus_reference_rows,
    _merge_eligible_reference_rows,
    fetch_corpus_reference_pool_sync,
)


def test_ladder_stops_at_content_class_when_pool_sufficient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scopes_called: list[str] = []

    def _fake_merge(_client: object, *, scope: str, **_: object) -> list[dict]:
        scopes_called.append(scope)
        if scope == "content_class":
            return [{"video_id": str(i)} for i in range(6)]
        return []

    monkeypatch.setattr(
        "getviews_pipeline.corpus_context._merge_eligible_reference_rows",
        _fake_merge,
    )
    monkeypatch.setattr(
        "getviews_pipeline.profile_niches.content_class_ids_for_legacy_niche",
        lambda _c, _n: [11, 12],
    )

    rows, scope = _fetch_corpus_reference_rows(
        MagicMock(),
        niche_id=4,
        days=30,
        limit=40,
        content_class_id=11,
    )

    assert scope == "content_class"
    assert len(rows) == 6
    assert scopes_called == ["content_class"]


def test_ladder_widens_to_junction_when_class_thin(monkeypatch: pytest.MonkeyPatch) -> None:
    scopes_called: list[str] = []

    def _fake_merge(_client: object, *, scope: str, **_: object) -> list[dict]:
        scopes_called.append(scope)
        if scope == "content_class":
            return [{"video_id": "only-one"}]
        if scope == "junction":
            return [{"video_id": f"j{i}"} for i in range(6)]
        return [{"video_id": "niche-fallback"}]

    monkeypatch.setattr(
        "getviews_pipeline.corpus_context._merge_eligible_reference_rows",
        _fake_merge,
    )
    monkeypatch.setattr(
        "getviews_pipeline.profile_niches.content_class_ids_for_legacy_niche",
        lambda _c, _n: [11, 12],
    )

    rows, scope = _fetch_corpus_reference_rows(
        MagicMock(),
        niche_id=4,
        days=30,
        limit=40,
        content_class_id=11,
    )

    assert scope == "junction"
    assert len(rows) == 6
    assert scopes_called == ["content_class", "junction"]


def test_merge_eligible_prefers_reference_eligible_rows() -> None:
    client = MagicMock()
    query = MagicMock()
    client.table.return_value = query
    query.select.return_value = query
    query.gt.return_value = query
    query.gte.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.limit.return_value = query

    eligible = [{"video_id": "e1", "views": 100}]
    fallback = [{"video_id": "e1", "views": 100}, {"video_id": "f1", "views": 50}]
    query.execute.side_effect = [MagicMock(data=eligible), MagicMock(data=fallback)]

    with patch(
        "getviews_pipeline.corpus_context._settings",
        MagicMock(corpus_boost_hard_reject=False),
    ):
        rows = _merge_eligible_reference_rows(
            client,
            niche_id=4,
            days=30,
            limit=10,
            scope="content_class",
            content_class_id=11,
            junction_class_ids=[11],
        )

    assert [r["video_id"] for r in rows] == ["e1", "f1"]
    eligible_calls = [c for c in query.eq.call_args_list if c.args == ("reference_eligible", True)]
    assert eligible_calls


def test_sync_pool_builds_awemes_with_class_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "getviews_pipeline.corpus_context._fetch_corpus_reference_rows",
        lambda *_a, **_k: (
            [
                {
                    "video_id": "x1",
                    "views": 9000,
                    "creator_handle": "peer",
                    "analysis_json": {"hook_analysis": {"hook_type": "question"}},
                }
            ],
            "content_class",
        ),
    )

    with patch("getviews_pipeline.corpus_context._anon_client", return_value=MagicMock()):
        out = fetch_corpus_reference_pool_sync(
            "Thời trang",
            content_class_id=11,
            legacy_niche_id=4,
        )

    assert len(out) == 1
    assert out[0]["aweme_id"] == "x1"
    assert out[0].get("_corpus_content_class_id") is None  # row omitted field
