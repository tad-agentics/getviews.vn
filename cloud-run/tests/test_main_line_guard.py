"""Phase 0.1 — CI guard: main.py must not grow beyond the current ceiling.

Run this test whenever code is added to main.py. A failure is a signal to
extract the new routes into a router file instead of appending to main.py.

Current baseline: 3493 lines (as of 2026-04-22 refactor).
Ceiling: baseline + 100 lines of grace for hotfix headroom.
"""

from __future__ import annotations

from pathlib import Path

_MAIN_PY = Path(__file__).parent.parent / "main.py"
_LINE_CEILING = 3600  # baseline 3493 + 100 grace


def test_main_py_line_count_within_ceiling() -> None:
    """main.py must stay below _LINE_CEILING.

    Failing this test means new routes were added directly to main.py.
    Extract them into a router under getviews_pipeline/routers/ instead.
    """
    actual = _MAIN_PY.read_text(encoding="utf-8").count("\n")
    assert actual <= _LINE_CEILING, (
        f"main.py has grown to {actual} lines (ceiling {_LINE_CEILING}). "
        "Extract new routes into getviews_pipeline/routers/ before adding more."
    )
