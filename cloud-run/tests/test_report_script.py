"""report_script — narrative shot summary helpers."""

from __future__ import annotations

from getviews_pipeline.report_script import _shots_summary_for_narrative


def test_shots_summary_uses_compact_view_format() -> None:
    block = _shots_summary_for_narrative(
        [
            {
                "t0": 0,
                "t1": 3,
                "cam": "Cận mặt",
                "voice": "Hook",
                "overlay": "BOLD",
                "references": [
                    {
                        "creator_handle": "hi.vidayyy",
                        "views": 27_461,
                        "description": "Cận mặt",
                    }
                ],
            }
        ]
    )
    assert "@hi.vidayyy (27k view)" in block
    assert "27.461" not in block
