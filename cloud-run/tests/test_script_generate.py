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

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from getviews_pipeline.script_generate import (
    ScriptGenerateBody,
    ScriptGenerateLLM,
    ScriptShotLLM,
    _attach_shot_references,
    _segment_lengths,
    _shot_to_descriptor,
    build_script_shots,
    run_script_generate_sync,
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


# ── Wave 2.5 Phase B PR #6 — enrichment fields + references ─────────


def test_fallback_shots_carry_canonical_enrichment_fields() -> None:
    """The deterministic backbone now includes framing/pace/overlay_style
    per position — never None on the fallback path, so the matcher
    always has a non-empty descriptor even when Gemini is skipped."""
    body = ScriptGenerateBody(
        topic="Kem dưỡng da cho nữ",
        hook="Mình test 30 ngày",
        hook_delay_ms=1200, duration=30, tone="Tâm sự", niche_id=1,
    )
    with patch(
        "getviews_pipeline.script_generate._call_script_gemini",
        side_effect=RuntimeError("no api key"),
    ):
        shots = build_script_shots(body)
    # Shot 0 (Cận mặt / BOLD CENTER): close_up framing, static pace,
    # bold_center overlay_style, face subject.
    assert shots[0]["framing"] == "close_up"
    assert shots[0]["pace"] == "static"
    assert shots[0]["overlay_style"] == "bold_center"
    assert shots[0]["subject"] == "face"
    # Shot 1 (Cắt nhanh b-roll / SUB-CAPTION): medium framing, fast pace.
    assert shots[1]["framing"] == "medium"
    assert shots[1]["pace"] == "fast"


def test_gemini_emitted_enrichment_wins_over_backbone_default() -> None:
    """When Gemini emits framing/pace explicitly, those values pass
    through unchanged — they'd land in the descriptor and the matcher
    would score them."""
    llm = _fake_llm_shots()
    # Explicit override on shot 0 — not the canonical "close_up".
    llm.shots[0].framing = "extreme_close_up"
    llm.shots[0].pace = "slow"
    body = ScriptGenerateBody(
        topic="x", hook="y", hook_delay_ms=1200,
        duration=32, tone="Chuyên gia", niche_id=1,
    )
    with patch(
        "getviews_pipeline.script_generate._call_script_gemini",
        return_value=llm,
    ):
        shots = build_script_shots(body)
    assert shots[0]["framing"] == "extreme_close_up"
    assert shots[0]["pace"] == "slow"


def test_shot_to_descriptor_prefers_gemini_then_backbone() -> None:
    # Gemini provided framing but not pace → pace comes from backbone.
    d = _shot_to_descriptor(
        intel_scene_type="face_to_camera",
        framing="extreme_close_up",
        pace=None, overlay_style=None, subject=None, motion=None,
        backbone_idx=0,
    )
    assert d["framing"] == "extreme_close_up"   # Gemini
    assert d["pace"] == "static"                # backbone shot-0 default
    assert d["overlay_style"] == "bold_center"  # backbone
    assert d["subject"] == "face"               # backbone
    assert d["scene_type"] == "face_to_camera"  # always legacy dim


def test_shot_to_descriptor_clamps_out_of_range_idx() -> None:
    d = _shot_to_descriptor(
        intel_scene_type="action",
        framing=None, pace=None, overlay_style=None, subject=None, motion=None,
        backbone_idx=99,   # beyond the 6-shot backbone
    )
    # Uses the last backbone row (idx 5) — QUESTION XL shot.
    assert d["framing"] == "close_up"


def test_attach_shot_references_threads_exclude_across_shots() -> None:
    """One creator shouldn't dominate the whole 6-shot reference panel.
    Verify exclude_video_ids grows as each shot contributes refs."""
    shots = [
        {"intel_scene_type": "face_to_camera",
         "framing": "close_up", "pace": "static", "overlay_style": "bold_center",
         "subject": "face", "motion": "static"},
        {"intel_scene_type": "product_shot",
         "framing": "medium", "pace": "fast", "overlay_style": "sub_caption",
         "subject": "product", "motion": "handheld"},
    ]
    call_exclude_sets: list[set[str]] = []

    def fake_pick(**kwargs):
        # Snapshot the exclude set passed in — it should grow.
        exc = kwargs.get("exclude_video_ids") or set()
        call_exclude_sets.append(set(exc))
        # Return a dummy ref whose id depends on which call this is.
        from getviews_pipeline.shot_reference_matcher import ShotReference
        return [ShotReference(
            video_id=f"v{len(call_exclude_sets)}",
            scene_index=0, start_s=0, end_s=1,
            frame_url=None, thumbnail_url=None, tiktok_url=None,
            creator_handle=None, description=None,
            score=50, match_signals=["niche"], match_label="Cùng ngách",
        )]

    with patch(
        "getviews_pipeline.shot_reference_matcher.pick_shot_references",
        side_effect=fake_pick,
    ):
        _attach_shot_references(shots, niche_id=7, service_sb=MagicMock())

    assert call_exclude_sets[0] == set()
    assert call_exclude_sets[1] == {"v1"}
    # References attached in place.
    assert shots[0]["references"][0]["video_id"] == "v1"
    assert shots[1]["references"][0]["video_id"] == "v2"


def test_run_script_generate_sync_attaches_empty_refs_when_no_service_sb() -> None:
    """Legacy callers that don't pass service_sb still get a valid
    shape — every shot carries an explicit references=[]."""
    user_sb = MagicMock()
    user_sb.rpc.return_value.execute.return_value = SimpleNamespace(data=True)
    body = ScriptGenerateBody(
        topic="x", hook="y", hook_delay_ms=1200,
        duration=30, tone="Hài", niche_id=7,
    )
    with patch(
        "getviews_pipeline.script_generate._call_script_gemini",
        side_effect=RuntimeError("skip gemini"),
    ):
        out = run_script_generate_sync(user_sb, user_id="u1", body=body)
    assert len(out["shots"]) == 6
    for s in out["shots"]:
        assert s["references"] == []


def test_run_script_generate_sync_matcher_failure_is_non_fatal() -> None:
    user_sb = MagicMock()
    user_sb.rpc.return_value.execute.return_value = SimpleNamespace(data=True)
    service_sb = MagicMock()
    body = ScriptGenerateBody(
        topic="x", hook="y", hook_delay_ms=1200,
        duration=30, tone="Hài", niche_id=7,
    )
    with patch(
        "getviews_pipeline.script_generate._call_script_gemini",
        side_effect=RuntimeError("skip gemini"),
    ), patch(
        "getviews_pipeline.script_generate._attach_shot_references",
        side_effect=RuntimeError("matcher boom"),
    ):
        out = run_script_generate_sync(
            user_sb, user_id="u1", body=body, service_sb=service_sb,
        )
    # Still 6 shots, every one has references=[] (not missing key).
    assert len(out["shots"]) == 6
    for s in out["shots"]:
        assert s["references"] == []


def test_run_script_generate_sync_includes_references_on_each_shot() -> None:
    """End-to-end: user_sb credit deducted, service_sb matcher called
    6 times (once per shot), response has references on each shot."""
    user_sb = MagicMock()
    user_sb.rpc.return_value.execute.return_value = SimpleNamespace(data=True)
    service_sb = MagicMock()
    body = ScriptGenerateBody(
        topic="x", hook="y", hook_delay_ms=1200,
        duration=30, tone="Hài", niche_id=7,
    )

    from getviews_pipeline.shot_reference_matcher import ShotReference
    fake_refs = [
        ShotReference(
            video_id="v-fake", scene_index=0, start_s=0, end_s=1,
            frame_url="f", thumbnail_url="t", tiktok_url=None,
            creator_handle="@c", description="d",
            score=55, match_signals=["niche", "framing"],
            match_label="Cùng ngách, khung hình",
        ),
    ]

    with patch(
        "getviews_pipeline.script_generate._call_script_gemini",
        side_effect=RuntimeError("skip gemini"),
    ), patch(
        "getviews_pipeline.shot_reference_matcher.pick_shot_references",
        return_value=fake_refs,
    ) as mock_pick:
        out = run_script_generate_sync(
            user_sb, user_id="u1", body=body, service_sb=service_sb,
        )

    assert mock_pick.call_count == 6
    for s in out["shots"]:
        assert len(s["references"]) == 1
        assert s["references"][0]["match_label"].startswith("Cùng ngách")
