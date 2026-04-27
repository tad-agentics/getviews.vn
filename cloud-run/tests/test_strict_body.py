"""``StrictBody`` request bodies must reject unknown keys.

Default Pydantic v2 behaviour silently drops extras. Audit #25 flipped
all FastAPI request bodies to ``StrictBody`` (extra="forbid") so a
typo in the caller surfaces as a 422 at the boundary instead of a
confusing 500 deep inside the pipeline. Pin one representative
class per router so the convention can't drift.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from getviews_pipeline.api_models import StrictBody
from getviews_pipeline.routers.intent import StreamRequest
from getviews_pipeline.routers.video import VideoAnalyzeRequest
from getviews_pipeline.routers.batch import BatchIngestRequest
from getviews_pipeline.routers.answer import AnswerSessionCreateBody
from getviews_pipeline.routers.admin import AdminTriggerRefreshBody


def test_strict_body_base_rejects_extras() -> None:
    class Foo(StrictBody):
        x: int

    with pytest.raises(ValidationError):
        Foo.model_validate({"x": 1, "typo": "boom"})


@pytest.mark.parametrize(
    "model_cls,valid_payload",
    [
        (StreamRequest, {"session_id": "s1", "query": "hi"}),
        (
            VideoAnalyzeRequest,
            {"video_id": "abc", "tiktok_url": None, "force_refresh": False, "mode": None},
        ),
        (BatchIngestRequest, {"niche_ids": [1, 2], "deep_pool": False}),
        (
            AnswerSessionCreateBody,
            {"initial_q": "q", "intent_type": "pattern_research", "format": "pattern"},
        ),
        (AdminTriggerRefreshBody, {"limit": 100, "stale_days": 3}),
    ],
)
def test_each_router_request_body_rejects_extras(
    model_cls: type, valid_payload: dict
) -> None:
    """Sanity: valid payload parses; same payload + ``typo`` rejects."""
    # Valid → parses cleanly.
    model_cls.model_validate(valid_payload)
    # Same payload + a stray field → 422 path triggers.
    with pytest.raises(ValidationError) as ei:
        model_cls.model_validate({**valid_payload, "totally_made_up": True})
    # Sanity: error message names the offender so a curl debug session
    # can spot the typo without reading source.
    assert "totally_made_up" in str(ei.value)
