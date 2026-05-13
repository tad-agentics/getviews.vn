"""Reference-video selection service.

Phase 1.1: thin re-export from pipelines.py so callers can migrate to
services.references without a code change on their end.

Phase 3 (two-core split): this module will own the actual reference-selection
logic once run_extraction_core and run_video_diagnosis_core are extracted.
"""

from __future__ import annotations

from getviews_pipeline.pipelines import (  # noqa: F401
    REF_N,
    _niche_aweme_pool,
    _slim_reference_video,
)

__all__ = ["REF_N", "_slim_reference_video", "_niche_aweme_pool"]
