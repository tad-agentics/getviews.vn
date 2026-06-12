from __future__ import annotations

SECTION_EMIT_THRESHOLD = 0.5
SECTION_EMIT_THRESHOLD_DEEP_RELAXED = 0.45
MAX_SIGNALS_PER_SECTION_DEEP = 5


def section_emit_threshold() -> float:
    """Section gate: 0.45 when the relax env flag is on (§4.3), else 0.5."""
    from getviews_pipeline.settings import settings

    if settings.getviews_deep_relax_salience:
        return SECTION_EMIT_THRESHOLD_DEEP_RELAXED
    return SECTION_EMIT_THRESHOLD
