"""W4-4 — channel peer reference_eligible filter + fallback."""

from __future__ import annotations

from getviews_pipeline.channel_diagnose import (
    _peer_corpus_with_eligible_fallback,
    _peer_tier_fallback_chain,
    _run_peer_corpus_query,
)


class _FakeQuery:
    def __init__(self, eligible_rows: list[dict], all_rows: list[dict]):
        self._eligible = eligible_rows
        self._all = all_rows
        self._ref_filter = False

    def select(self, *_a, **_k):
        return self

    def eq(self, field, value):
        if field == "reference_eligible" and value is True:
            self._ref_filter = True
        return self

    def neq(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        data = self._eligible if self._ref_filter else self._all
        return type("R", (), {"data": data})()


class _FakeSb:
    def __init__(self, eligible_rows: list[dict], all_rows: list[dict]):
        self._eligible = eligible_rows
        self._all = all_rows

    def table(self, _name: str):
        return _FakeQuery(self._eligible, self._all)


def test_run_peer_corpus_query_applies_reference_eligible():
    sb = _FakeSb(
        eligible_rows=[{"creator_handle": "a", "reference_eligible": True}],
        all_rows=[
            {"creator_handle": "a", "reference_eligible": True},
            {"creator_handle": "b", "reference_eligible": False},
        ],
    )
    rows = _run_peer_corpus_query(
        sb, 1, "me", content_class_id=5, reference_eligible_only=True,
    )
    assert len(rows) == 1
    assert rows[0]["creator_handle"] == "a"


def test_peer_eligible_fallback_when_thin():
    eligible = [{"creator_handle": "a"}, {"creator_handle": "b"}]
    all_rows = eligible + [{"creator_handle": "c"}, {"creator_handle": "d"}]
    sb = _FakeSb(eligible, all_rows)
    out = _peer_corpus_with_eligible_fallback(sb, 1, "me", 5, "micro")
    assert len(out) == 4


def test_peer_tier_fallback_uses_class_tier_rows():
    rows = [{"creator_handle": f"h{i}"} for i in range(4)]
    sb = _FakeSb(rows, rows)
    out, source = _peer_tier_fallback_chain(
        sb, legacy_niche_id=1, exclude_handle="me", content_class_id=5, creator_tier="micro",
    )
    assert len(out) == 4
    assert source == "content_class"
