from __future__ import annotations

SECTION_EMIT_THRESHOLD = 0.5
SECTION_EMIT_THRESHOLD_DEEP_RELAXED = 0.45
MAX_SIGNALS_PER_SECTION_IN_PROMPT = 3
MAX_SIGNALS_PER_SECTION_DEEP = 5


def section_emit_threshold(*, depth: str = "basic") -> float:
    """Default section gate (0.5); deep may relax to 0.45 when env flag is on (§4.3)."""
    if depth != "deep":
        return SECTION_EMIT_THRESHOLD
    from getviews_pipeline.settings import settings

    if settings.getviews_deep_relax_salience:
        return SECTION_EMIT_THRESHOLD_DEEP_RELAXED
    return SECTION_EMIT_THRESHOLD
