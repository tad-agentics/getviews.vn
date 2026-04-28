"""Regression: EnsembleData get-used-units JSON shape (top-level vs per-platform data map)."""

from getviews_pipeline.routers.admin import _ed_used_units_from_payload


def test_top_level_units() -> None:
    assert _ed_used_units_from_payload({"units": 42}) == 42


def test_data_units_key() -> None:
    assert _ed_used_units_from_payload({"data": {"units": 100}}) == 100


def test_per_platform_map_sums() -> None:
    assert _ed_used_units_from_payload(
        {"data": {"tiktok": 900, "instagram": 100, "reddit": 0}}
    ) == 1000


def test_per_platform_tiktok_only() -> None:
    assert _ed_used_units_from_payload({"data": {"tiktok": 151}}) == 151


def test_empty_data() -> None:
    assert _ed_used_units_from_payload({"data": {}}) == 0
