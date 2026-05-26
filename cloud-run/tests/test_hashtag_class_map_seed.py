"""Tests for class-loop hashtag discovery seeding."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from getviews_pipeline.hashtag_class_map import (
    collect_seeds_for_class_sync,
    seed_class_discovery_sync,
)


class _Table:
    def __init__(self, name: str, store: dict[str, list[dict[str, Any]]]) -> None:
        self._name = name
        self._store = store
        self._filters: dict[str, Any] = {}
        self._in_filters: dict[str, list[Any]] = {}
        self._limit = 1000
        self._update_payload: dict[str, Any] | None = None
        self._is_null_cols: set[str] = set()
        self._is_not_null_cols: set[str] = set()

    def select(self, *_cols: str) -> _Table:
        return self

    def eq(self, col: str, val: Any) -> _Table:
        self._filters[col] = val
        return self

    def in_(self, col: str, vals: list[Any]) -> _Table:
        self._in_filters[col] = list(vals)
        return self

    def not_(self) -> _Table:
        self._negate_is = True
        return self

    def is_(self, col: str, val: Any) -> _Table:
        if val == "null":
            if getattr(self, "_negate_is", False):
                self._is_not_null_cols.add(col)
            else:
                self._is_null_cols.add(col)
        self._negate_is = False
        return self

    def order(self, *_args: Any, **_kwargs: Any) -> _Table:
        return self

    def limit(self, n: int) -> _Table:
        self._limit = n
        return self

    def range(self, start: int, end: int) -> _Table:
        self._range = (start, end)
        return self

    def update(self, payload: dict[str, Any]) -> _Table:
        self._update_payload = payload
        return self

    def upsert(self, payload: dict[str, Any], **_kw: Any) -> _Table:
        self._upsert_payload = payload
        return self

    def execute(self) -> MagicMock:
        rows = list(self._store.get(self._name, []))
        for col, val in self._filters.items():
            rows = [r for r in rows if r.get(col) == val]
        for col, vals in self._in_filters.items():
            rows = [r for r in rows if r.get(col) in vals]
        for col in self._is_null_cols:
            rows = [r for r in rows if r.get(col) is None]
        for col in self._is_not_null_cols:
            rows = [r for r in rows if r.get(col) is not None]
        if hasattr(self, "_range"):
            start, end = self._range
            rows = rows[start : end + 1]
        rows = rows[: self._limit]
        if self._update_payload is not None:
            for row in rows:
                row.update(self._update_payload)
        if hasattr(self, "_upsert_payload"):
            self._store.setdefault(self._name, []).append(dict(self._upsert_payload))
        out = MagicMock()
        out.data = rows
        return out


def _fake_client(store: dict[str, list[dict[str, Any]]]) -> MagicMock:
    client = MagicMock()
    client.table.side_effect = lambda name: _Table(name, store)
    return client


def test_collect_seeds_merges_niche_taxonomy_and_map() -> None:
    store = {
        "creator_niche_content_classes": [
            {"creator_niche_id": 2, "content_class_id": 6},
        ],
        "video_corpus": [
            {"content_class_id": 6, "ingest_loop_niche_id": 3, "hashtags": ["#outfit"]},
        ],
        "niche_taxonomy": [
            {"id": 3, "signal_hashtags": ["thoitrang", "outfit"]},
        ],
        "hashtag_niche_map": [
            {"hashtag": "phoido", "niche_id": 3, "occurrences": 50, "is_generic": False},
        ],
        "hashtag_class_map": [],
    }
    client = _fake_client(store)
    seeds = collect_seeds_for_class_sync(client, content_class_id=6, signal_hashtags=[])
    assert "thoitrang" in seeds
    assert "phoido" in seeds
    assert "outfit" in seeds


def test_seed_class_discovery_writes_map_and_signal() -> None:
    store = {
        "content_class_ingest_targets": [
            {"content_class_id": 6, "signal_hashtags": None, "active": True},
        ],
        "creator_niche_content_classes": [
            {"creator_niche_id": 2, "content_class_id": 6},
        ],
        "video_corpus": [
            {"content_class_id": 6, "ingest_loop_niche_id": 3, "hashtags": ["review"]},
        ],
        "niche_taxonomy": [
            {"id": 3, "signal_hashtags": ["thoitrang"]},
        ],
        "hashtag_niche_map": [
            {"hashtag": "phoido", "niche_id": 3, "occurrences": 50, "is_generic": False},
        ],
        "hashtag_class_map": [],
    }
    client = _fake_client(store)
    summary = seed_class_discovery_sync(
        client,
        active_only=True,
        backfill_signal_hashtags=True,
    )
    assert summary["classes_processed"] == 1
    assert summary["map_rows_written"] >= 1
    assert summary["signal_hashtags_updated"] == 1
    assert store["content_class_ingest_targets"][0]["signal_hashtags"]
    assert len(store["hashtag_class_map"]) >= 1
