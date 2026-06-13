"""Reserved anatomy includes sound + persona for section cap."""

from __future__ import annotations

from getviews_pipeline.diagnose_sections import _reorder_and_cap_sections


def test_sound_and_persona_survive_deep_section_cap() -> None:
    sections = [
        "diagnosis",
        "compliance",
        "hook_analysis",
        "niche_pattern",
        "channel_pattern",
        "commerce",
        "metadata",
        "editing",
        "sound",
        "persona",
        "script_structure",
        "boost_attribution",
    ]
    manifest = {
        "metadata": [type("S", (), {"salience": 0.9})()],
        "boost_attribution": [type("S", (), {"salience": 0.85})()],
        "editing": [type("S", (), {"salience": 0.41})()],
        "sound": [type("S", (), {"salience": 0.4})()],
        "persona": [type("S", (), {"salience": 0.42})()],
        "script_structure": [type("S", (), {"salience": 0.5})()],
    }
    out = _reorder_and_cap_sections(sections, manifest=manifest)
    assert "script_structure" in out
    assert "editing" in out
    assert "sound" in out
    assert "persona" in out
