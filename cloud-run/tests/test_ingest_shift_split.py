"""Unit tests for nightly ingest shift splitting (HI-13 throughput)."""

from __future__ import annotations

import pytest

from getviews_pipeline.corpus_ingest import (
    _is_final_ingest_shift,
    split_ingest_targets_for_shift,
)


def _targets(n: int) -> list[dict]:
    return [
        {"id": i, "_loop_content_class_id": 100 + i, "priority": n - i}
        for i in range(n)
    ]


def test_split_three_shifts_covers_all_without_overlap() -> None:
    all_targets = _targets(43)
    chunks: list[list[dict]] = []
    for letter in ("a", "b", "c"):
        chunk, meta = split_ingest_targets_for_shift(
            all_targets, shift=letter, shift_count=3,
        )
        chunks.append(chunk)
        assert meta["ingest_shift"] == letter
        assert meta["ingest_shift_count"] == 3
        assert meta["content_class_ids_planned"] == [
            int(t["_loop_content_class_id"]) for t in chunk
        ]

    assert sum(len(c) for c in chunks) == 43
    assert len(chunks[0]) == 15
    assert len(chunks[1]) == 14
    assert len(chunks[2]) == 14

    seen_cc: set[int] = set()
    for chunk in chunks:
        for t in chunk:
            cc = int(t["_loop_content_class_id"])
            assert cc not in seen_cc
            seen_cc.add(cc)
    assert len(seen_cc) == 43


def test_split_none_returns_full_list() -> None:
    all_targets = _targets(10)
    chunk, meta = split_ingest_targets_for_shift(
        all_targets, shift=None, shift_count=3,
    )
    assert chunk == all_targets
    assert len(meta["content_class_ids_planned"]) == 10


def test_split_invalid_shift_raises() -> None:
    with pytest.raises(ValueError, match="invalid ingest_shift"):
        split_ingest_targets_for_shift(_targets(5), shift="z", shift_count=3)


def test_split_out_of_range_raises() -> None:
    with pytest.raises(ValueError, match="out of range"):
        split_ingest_targets_for_shift(_targets(5), shift="c", shift_count=2)


def test_is_final_ingest_shift() -> None:
    assert _is_final_ingest_shift(None, 3) is True
    assert _is_final_ingest_shift("a", 3) is False
    assert _is_final_ingest_shift("b", 3) is False
    assert _is_final_ingest_shift("c", 3) is True
    assert _is_final_ingest_shift("b", 2) is True
