import pytest

from getviews_pipeline.analysis_core import detect_language_market_mismatch

langdetect = pytest.importorskip("langdetect", reason="langdetect not installed — skip language detection tests")


def test_vietnamese_hook_returns_none():
    assert detect_language_market_mismatch("Đồng hồ này có xứng đáng không?") is None


def test_english_hook_returns_error():
    # Use an unambiguously English sentence (brand-heavy text confuses langdetect).
    result = detect_language_market_mismatch(
        "Here is my honest review of this product after one week of daily use"
    )
    assert result is not None
    assert result["error_id"] == "lang_market_mismatch"
    assert result["sev"] == "high"
    assert "title" in result
    assert "detail" in result
    assert "fix" in result


def test_brand_name_only_returns_none():
    assert detect_language_market_mismatch("Curnon") is None


def test_hashtags_stripped():
    assert detect_language_market_mismatch("#watch #luxury #ootd") is None


def test_very_short_hook_returns_none():
    assert detect_language_market_mismatch("OK") is None
