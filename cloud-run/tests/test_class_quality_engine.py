"""Tests for ACQE viability tiers."""

from __future__ import annotations

from getviews_pipeline.class_quality_engine import (
    COLD_START_RUNS,
    MERGE_CONFUSION_RATE,
    _assignment_tier,
    _build_assignment_patch,
    _disagreement_score,
    _find_duplicate_class_pairs,
    _junction_ok_for_row,
    _resolve_assignment_tier,
    _tier_for_class,
    _vpn_for_tier,
)


def test_tier_for_class_healthy():
    assert _tier_for_class(35, 5) == "Healthy"


def test_tier_for_class_thin():
    assert _tier_for_class(12, 1) == "Thin"


def test_tier_for_class_dormant():
    assert _tier_for_class(2, 0) == "Dormant"


def test_vpn_for_tier():
    assert _vpn_for_tier("Healthy") == (15, True)
    assert _vpn_for_tier("Thin") == (8, True)
    assert _vpn_for_tier("Dormant") == (0, False)


def test_assignment_tier_validated():
    assert _assignment_tier(0.85, 0.1) == "validated"
    assert _assignment_tier(0.5, 0.1) == "low_conf"


def test_resolve_assignment_tier_junction_gate():
    assert _resolve_assignment_tier(0.85, 0.1, junction_ok=True) == "validated"
    assert _resolve_assignment_tier(0.85, 0.1, junction_ok=False) == "low_conf"


def test_build_assignment_patch_junction_miss_downgrades():
    patch = _build_assignment_patch({
        "niche_resolution_confidence": 0.9,
        "ingest_loop_content_class_id": 10,
        "content_class_id": 10,
        "inferred_creator_niche_id": 99999,
    })
    assert patch["class_assignment_tier"] == "low_conf"


def test_disagreement_same_class():
    assert _disagreement_score(10, 10, 0.9) == 0.0


def test_disagreement_mismatch():
    d = _disagreement_score(10, 20, 0.7)
    assert d is not None and d > 0.4


def test_cold_start_constant():
    assert COLD_START_RUNS == 3


def test_merge_confusion_threshold():
    assert MERGE_CONFUSION_RATE == 0.15


def test_find_duplicate_class_pairs_empty_client():
    class _Q:
        def select(self, *_a, **_k):
            return self

        def execute(self):
            return type("R", (), {"data": []})()

    client = type("C", (), {"table": lambda _s, _n: _Q()})()
    assert _find_duplicate_class_pairs(client) == []

