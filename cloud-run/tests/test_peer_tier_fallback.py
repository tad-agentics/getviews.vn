"""Tests for peer creator tier fallback chain."""

from __future__ import annotations

from getviews_pipeline.channel_diagnose import _peer_tier_fallback_chain


class _FakeQuery:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def neq(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        return type("R", (), {"data": self._rows})()


class _FakeSb:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def table(self, _name: str):
        return _FakeQuery(self._rows)


def test_peer_fallback_uses_class_tier_rows():
    rows = [
        {"creator_handle": "a"},
        {"creator_handle": "b"},
        {"creator_handle": "c"},
        {"creator_handle": "d"},
    ]
    sb = _FakeSb(rows)
    out, source = _peer_tier_fallback_chain(
        sb, legacy_niche_id=1, exclude_handle="me", content_class_id=5, creator_tier="micro",
    )
    assert len(out) == 4
    assert source == "content_class"
