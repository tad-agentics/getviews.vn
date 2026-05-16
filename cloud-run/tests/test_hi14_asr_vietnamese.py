"""HI-14 — Vietnamese STT supplemental path (cache, flag-off, formatting)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.prompts import format_vietnamese_asr_supplement_for_video_extraction_vi
from getviews_pipeline.services import asr_vietnamese as asr


def test_format_supplement_includes_timed_line() -> None:
    s = format_vietnamese_asr_supplement_for_video_extraction_vi(
        [{"start_sec": 1.0, "end_sec": 2.5, "text": "Xin chào"}],
    )
    assert "Google STT vi-VN" in s
    assert "[1.0s–2.5s]" in s
    assert "Xin chào" in s


def test_sync_prepare_disabled_returns_empty() -> None:
    with patch.object(asr, "GCP_STT_VI_ENABLED", False):
        p = Path("/no/such/file")
        prefix, cost = asr.sync_prepare_vietnamese_asr_supplement(p, "123")
    assert prefix == ""
    assert cost is None


def test_sync_prepare_empty_video_id() -> None:
    with patch.object(asr, "GCP_STT_VI_ENABLED", True):
        with patch.object(Path, "is_file", return_value=True):
            prefix, cost = asr.sync_prepare_vietnamese_asr_supplement(Path("/x"), "  ")
    assert prefix == ""
    assert cost is None


def test_sync_prepare_cache_hit_no_stt_charge() -> None:
    fake_row = {
        "transcript": {"segments": [{"start_sec": 0.0, "end_sec": 1.0, "text": "Hi"}]},
    }
    p = MagicMock(spec=Path)
    p.resolve.return_value = p
    p.is_file.return_value = True
    with patch.object(asr, "GCP_STT_VI_ENABLED", True):
        with patch.object(asr, "_fetch_cache", return_value=fake_row):
            prefix, cost = asr.sync_prepare_vietnamese_asr_supplement(
                p,
                "vid1",
            )
    assert "Google STT vi-VN" in prefix
    assert "Hi" in prefix
    assert cost is None


def test_sync_prepare_miss_runs_pipeline_and_returns_cost() -> None:
    with patch.object(asr, "GCP_STT_VI_ENABLED", True):
        with patch.object(asr, "_fetch_cache", return_value=None):
            p = MagicMock(spec=Path)
            p.resolve.return_value = p
            p.is_file.return_value = True
            with patch.object(asr, "_extract_wav_16k_mono", return_value=Path("/tmp/x.wav")):
                with patch.object(asr, "_ffprobe_duration_sec", return_value=60.0):
                    with patch.object(
                        asr,
                        "_transcribe_wav_path",
                        return_value=[{"start_sec": None, "end_sec": None, "text": "A"}],
                    ):
                        with patch.object(asr, "_upsert_cache"):
                            with patch.object(asr, "GCP_STT_VI_PRICE_PER_MIN_USD", 0.024):
                                prefix, cost = asr.sync_prepare_vietnamese_asr_supplement(
                                    p,
                                    "vid2",
                                )
    assert "A" in prefix
    assert cost == pytest.approx(0.024, rel=1e-6)  # 1 min @ 0.024
