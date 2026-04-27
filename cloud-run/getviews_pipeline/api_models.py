"""Shared Pydantic base classes for FastAPI request bodies.

The default Pydantic v2 behaviour for extra fields is ``extra="ignore"``,
which silently discards unknown keys. That's safe-but-quiet — a typo
in a caller (``intent_type`` vs ``intentType``, ``last_seq`` vs ``lastSeq``)
parses cleanly and the handler runs against a half-populated body.
The bug surfaces as a confusing 500 minutes later inside the pipeline
instead of as a 422 at the boundary.

``StrictBody`` flips this to ``extra="forbid"`` so every request body
class that extends it rejects unknown keys with a clear validation
error. Use for endpoint inputs only — internal pipeline DTOs that
might absorb passthrough fields should keep the default.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictBody(BaseModel):
    """Request-body base class. Extra keys → 422 instead of silent drop."""

    model_config = ConfigDict(extra="forbid")
