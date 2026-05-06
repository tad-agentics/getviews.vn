"""Pattern-subreport detection for the Pattern report builder.

Pre-L1.5 this module also held a destination-dispatch matrix
(``INTENT_TO_DESTINATION``, ``destination_for_intent``, the Gemini-label
matrix, ``resolve_destination``) used by the now-deleted
``/classify-intent`` endpoint. The report-based UX classifies + routes
client-side via ``src/routes/_app/intent-router.ts``, so the BE no
longer needs its own routing matrix.

What stays in this module: the ``_TIMING_MERGE_RE`` keyword cues +
``detect_pattern_subreports`` which the answer-session dispatcher calls
to fold a timing subreport into a Pattern payload when the user query
asks "post gì khi nào". This is the only multi-intent merge that
survived the chat→report migration.
"""

from __future__ import annotations

import re

# ── §A.4 — multi-intent merge detection (C.5.3) ────────────────────────────

# Content-calendar / "post gì khi nào" keyword cues that should add a timing
# subreport to an otherwise Pattern-shaped answer. Matches the plan's
# "Report + timing" merge case (intent #18 content_calendar).
_TIMING_MERGE_RE = re.compile(
    r"(giờ nào|thứ mấy|khi nào post|post khi nào|post .{0,12}khi nào|"
    r"khung giờ|lịch post|thời điểm đăng|post giờ|best time|posting time)",
    re.IGNORECASE,
)


def detect_pattern_subreports(query: str) -> list[str]:
    """Return the list of subreports to fold into a Pattern payload.

    C.5.3 scope: only ``"timing"`` is auto-merged today. The classifier
    (C.7) can supersede this with a richer shape; until then, a keyword
    pass gives us the "Post gì khi nào" merge case without the LLM call.
    """
    q = (query or "").strip()
    if not q:
        return []
    subs: list[str] = []
    if _TIMING_MERGE_RE.search(q):
        subs.append("timing")
    return subs
