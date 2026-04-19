"""B.4 — deterministic ``/script/generate`` shot scaffold."""

from getviews_pipeline.script_generate import (
    ScriptGenerateBody,
    _segment_lengths,
    build_script_shots,
)


def test_segment_lengths_sum_matches_total():
    for total in (15, 32, 60, 90):
        parts = _segment_lengths(total)
        assert len(parts) == 6
        assert sum(parts) == total
        assert all(p >= 1 for p in parts)


def test_build_script_shots_shape_and_topic_in_voice():
    body = ScriptGenerateBody(
        topic="Review tai nghe test",
        hook="Khi bạn cần bass sâu",
        hook_delay_ms=1200,
        duration=48,
        tone="Chuyên gia",
        niche_id=3,
    )
    shots = build_script_shots(body)
    assert len(shots) == 6
    assert shots[0]["t0"] == 0
    assert shots[-1]["t1"] == 48
    assert "Review tai nghe test" in shots[0]["voice"] or "Khi bạn" in shots[0]["voice"]
    assert shots[0]["intel_scene_type"] == "face_to_camera"
    assert shots[2]["overlay"] == "STAT BURST"
    assert "corpus_avg" in shots[0] and "winner_avg" in shots[0]
