"""B.4 / D.1.2 — ``/script/generate`` shot scaffold.

Original B.4 shape tests live at the top (frozen HTTP contract).
D.1.2 bottom-half exercises the Gemini swap:
  * happy path: Gemini returns 6 valid shots → creative fields surface
    verbatim while t0/t1/corpus_avg/winner_avg stay deterministic.
  * fallback: any Gemini failure routes through
    ``_deterministic_creative_rows`` without changing the response shape.
  * coercion: Gemini drift on overlay/intel_scene_type is snapped back
    to the canonical backbone for that position.
"""

from unittest.mock import patch

from getviews_pipeline.script_generate import (
    ScriptGenerateBody,
    ScriptGenerateLLM,
    ScriptShotLLM,
    _segment_lengths,
    build_script_shots,
)

# ── Frozen B.4 shape contract ──────────────────────────────────────────────


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
    # Force fallback so this test remains deterministic regardless of env.
    with patch(
        "getviews_pipeline.script_generate._call_script_gemini",
        side_effect=RuntimeError("no api key in CI"),
    ):
        shots = build_script_shots(body)
    assert len(shots) == 6
    assert shots[0]["t0"] == 0
    assert shots[-1]["t1"] == 48
    assert "Review tai nghe test" in shots[0]["voice"] or "Khi bạn" in shots[0]["voice"]
    assert shots[0]["intel_scene_type"] == "face_to_camera"
    assert shots[2]["overlay"] == "STAT BURST"
    assert "corpus_avg" in shots[0] and "winner_avg" in shots[0]


# ── D.1.2 — Gemini swap with frozen contract ──────────────────────────────


def _fake_llm_shots() -> ScriptGenerateLLM:
    """Return a canonical 6-shot LLM payload for the happy path test."""
    return ScriptGenerateLLM(
        shots=[
            ScriptShotLLM(
                cam="Cận mặt",
                voice="Mình vừa test tai nghe 2 triệu và thật sự khác biệt.",
                viz="Tay cầm 2 tai, text 200K vs 2TR nổi",
                overlay="BOLD CENTER",
                intel_scene_type="face_to_camera",
                overlay_winner="white sans 28pt · bottom-center",
            ),
            ScriptShotLLM(
                cam="Cắt nhanh b-roll",
                voice="Sự khác biệt nghe được ngay lần đầu.",
                viz="Slow-mo unbox, hai tai đặt cạnh",
                overlay="SUB-CAPTION",
                intel_scene_type="product_shot",
                overlay_winner="yellow outlined · mid-left",
            ),
            ScriptShotLLM(
                cam="Side-by-side",
                voice="Bass của 200K bí, 2 triệu mở ra như sân khấu.",
                viz="Split-screen waveform visualizer",
                overlay="STAT BURST",
                intel_scene_type="demo",
                overlay_winner="number callout 72pt",
            ),
            ScriptShotLLM(
                cam="POV nghe",
                voice="Mid-range khác hẳn — đây là test 3 thể loại nhạc.",
                viz="POV nghe, đèn ấm",
                overlay="LABEL",
                intel_scene_type="face_to_camera",
                overlay_winner="caption strip · bottom",
            ),
            ScriptShotLLM(
                cam="Cận tay + texture",
                voice="Build cũng khác — cảm giác cầm khác hệ.",
                viz="Xoay tai, ánh sáng bên",
                overlay="NONE",
                intel_scene_type="action",
                overlay_winner="—",
            ),
            ScriptShotLLM(
                cam="Cận mặt + câu hỏi",
                voice="Bạn chọn cái nào? Comment cho mình biết.",
                viz="Câu hỏi to trên màn",
                overlay="QUESTION XL",
                intel_scene_type="face_to_camera",
                overlay_winner="question mark · full bleed",
            ),
        ]
    )


def test_build_script_shots_gemini_happy_path_preserves_contract():
    body = ScriptGenerateBody(
        topic="Review tai nghe 200k vs 2 triệu",
        hook="Mình test xong rồi đây",
        hook_delay_ms=1200,
        duration=32,
        tone="Chuyên gia",
        niche_id=3,
    )
    with patch(
        "getviews_pipeline.script_generate._call_script_gemini",
        return_value=_fake_llm_shots(),
    ):
        shots = build_script_shots(body)
    # Contract: 6 shots, t0=0, t_last=duration, all required keys present.
    assert len(shots) == 6
    assert shots[0]["t0"] == 0
    assert shots[-1]["t1"] == 32
    required = {
        "t0", "t1", "cam", "voice", "viz", "overlay",
        "corpus_avg", "winner_avg", "intel_scene_type", "overlay_winner",
    }
    for s in shots:
        assert required <= set(s.keys())
    # Creative fields come from the LLM — verify verbatim.
    assert shots[0]["voice"].startswith("Mình vừa test tai nghe")
    assert shots[2]["voice"].startswith("Bass của 200K")
    # Benchmarks still match the backbone (Gemini does NOT own these).
    assert shots[2]["corpus_avg"] == 7.8
    assert shots[2]["winner_avg"] == 8.0


def test_build_script_shots_gemini_overlay_drift_coerced_to_backbone():
    """If Gemini returns a valid but wrong-slot overlay, we coerce."""
    llm = _fake_llm_shots()
    # Drift: put "QUESTION XL" on shot 0 (should be BOLD CENTER) and
    # "face_to_camera" stays — shots[0].intel_scene_type still canonical.
    llm.shots[0].overlay = "QUESTION XL"
    llm.shots[0].intel_scene_type = "product_shot"
    body = ScriptGenerateBody(
        topic="Test drift",
        hook="Hook drift",
        hook_delay_ms=1200,
        duration=32,
        tone="Hài",
        niche_id=1,
    )
    with patch("getviews_pipeline.script_generate._call_script_gemini", return_value=llm):
        shots = build_script_shots(body)
    # Coerced back to the canonical shot-0 backbone.
    assert shots[0]["overlay"] == "BOLD CENTER"
    assert shots[0]["intel_scene_type"] == "face_to_camera"


def test_build_script_shots_fallback_on_gemini_failure():
    """Any Gemini exception routes through deterministic creative — same shape."""
    body = ScriptGenerateBody(
        topic="Fallback topic",
        hook="Fallback hook",
        hook_delay_ms=1200,
        duration=32,
        tone="Năng lượng",
        niche_id=1,
    )
    with patch(
        "getviews_pipeline.script_generate._call_script_gemini",
        side_effect=Exception("Gemini boom"),
    ):
        shots = build_script_shots(body)
    assert len(shots) == 6
    assert shots[0]["t0"] == 0
    assert shots[-1]["t1"] == 32
    # Deterministic template formats the topic into shot 0 voice.
    assert "Fallback" in shots[0]["voice"] or "Hook: mở với" in shots[0]["voice"]
    # Overlay + intel_scene_type still come from _BACKBONE (not mutable).
    assert shots[0]["overlay"] == "BOLD CENTER"
    assert shots[5]["overlay"] == "QUESTION XL"
