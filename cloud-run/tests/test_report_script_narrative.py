"""Wave 2 — script narrative synthesis fallback."""

from __future__ import annotations

from unittest.mock import patch

from getviews_pipeline.report_script import synthesize_script_narrative_vi


def test_synthesize_script_narrative_vi_fallback_shape() -> None:
    shots = [
        {
            "t0": 0,
            "t1": 3,
            "cam": "Cận mặt",
            "voice": "Hook mở",
            "viz": "Text to",
            "overlay": "BOLD",
        }
    ]
    with patch(
        "getviews_pipeline.report_script._generate_content_models",
        side_effect=RuntimeError("offline"),
    ):
        out = synthesize_script_narrative_vi(
            topic="Test topic",
            hook="Hook mở",
            duration=30,
            tone="Chuyên gia",
            niche_label="Làm đẹp",
            shots=shots,
        )
    assert out["_schema_version"] == "script_v1"
    assert out["headline_vi"]
    assert len(out["diagnosis_vi"]["sections"]) == 3
    ids = [s["section_id"] for s in out["diagnosis_vi"]["sections"]]
    assert ids == ["hook_analysis", "script_structure", "next_video"]
