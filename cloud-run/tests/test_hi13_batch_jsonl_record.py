"""HI-13 — batch JSONL request record shape (offline; no Gemini API)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from google.genai import types

from getviews_pipeline.gemini import build_video_corpus_batch_jsonl_record


def test_build_video_corpus_batch_jsonl_record_has_key_and_request() -> None:
    file_resource = SimpleNamespace(
        uri="https://generativelanguage.googleapis.com/v1beta/files/xyz",
        mime_type="video/mp4",
        name="files/xyz",
    )
    base_cfg = types.GenerateContentConfig(temperature=0.2)

    with (
        patch("getviews_pipeline.gemini._get_client"),
        patch(
            "getviews_pipeline.gemini._configure_extraction_generate_config",
            return_value=base_cfg,
        ),
        patch(
            "getviews_pipeline.gemini._build_video_extraction_content_parts",
            return_value=[
                types.Part(
                    file_data=types.FileData(
                        file_uri=file_resource.uri,
                        mime_type="video/mp4",
                    ),
                    video_metadata=types.VideoMetadata(fps=1.0),
                )
            ],
        ),
    ):
        rec = build_video_corpus_batch_jsonl_record(
            "7123456789",
            file_resource,
            supplemental_user_prefix=None,
        )

    assert rec["key"] == "7123456789"
    assert "request" in rec
    req = rec["request"]
    assert "contents" in req
    assert "config" in req
    assert req["contents"][0]["role"] == "user"
    parts = req["contents"][0]["parts"]
    assert any("file_data" in p for p in parts)
    assert any(p.get("text") for p in parts if isinstance(p, dict))
