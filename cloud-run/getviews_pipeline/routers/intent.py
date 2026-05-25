"""Legacy intent router — ``POST /stream`` sunset (Wave 5, 2026-05).

V1 GTM routes all paid intents through ``POST /answer/sessions/{id}/turns``.
Text follow-ups use Vercel ``POST /api/chat``. This module keeps the
``/stream`` route registered (410 Gone) plus intent normalisation helpers
used by tests and historical session rows.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import AliasChoices, Field

from getviews_pipeline.api_models import StrictBody
from getviews_pipeline.deps import require_user

router = APIRouter()


def _normalize_intent_name(raw: str | None) -> str | None:
    """Fold legacy / external intent_type strings into current enum values.

    L1.5 Tier B added ``"comparison"`` (legacy alias for COMPETITOR_PROFILE,
    historical sessions only) and consolidated the FOLLOWUP collapse so
    callers passing the chat-era ``"followup"`` string land on the modern
    follow_up_unclassifiable surface. ``"find_creators"`` stays as a
    back-compat alias even after the enum value was removed — historical
    Gemini classifier outputs may still carry it.
    """
    if raw is None:
        return None
    aliases = {
        "tiktok_url_diagnosis": "video_diagnosis",
        "kol_search": "creator_search",
        "find_creators": "creator_search",  # L1.5: enum removed, alias kept
        "kol_finder": "creator_search",
        "followup": "follow_up_unclassifiable",  # L1.5: chat-era → modern
        "comparison": "competitor_profile",  # L1.5: legacy session rows
        # L1.5 audit — METADATA_ONLY removed (no longer no-cost). Historical
        # session intent_type strings fold into the generic-fallback path.
        "metadata_only": "follow_up_unclassifiable",
    }
    return aliases.get(raw, raw)


class StreamRequest(StrictBody):
    session_id: str
    query: str
    intent_type: str | None = None
    niche_id: int | None = None
    resume_stream_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("resume_stream_id", "stream_id"),
    )
    last_seq: int | None = None


@router.post("/stream")
async def stream(
    body: StreamRequest,
    user: dict = Depends(require_user),
) -> JSONResponse:
    """Legacy chat SSE — removed. Use ``/answer/sessions/{id}/turns`` instead."""
    _ = body, user
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "error": "stream_sunset",
            "message_vi": (
                "Luồng chat cũ đã ngừng. Dùng Studio (/app/answer) "
                "hoặc /api/chat cho câu hỏi text."
            ),
            "replacement": "/answer/sessions/{session_id}/turns",
        },
    )
