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


# ── S6: per-shot regenerate (shot_index) ─────────────────────────────


def test_run_script_generate_sync_shot_index_returns_only_that_shot() -> None:
    """When ``shot_index`` is set, the response carries only the matching
    shot — FE splices it back into local state without disturbing the
    other 5 shots."""
    user_sb = MagicMock()
    user_sb.rpc.return_value.execute.return_value = SimpleNamespace(data=True)
    body = ScriptGenerateBody(
        topic="x", hook="y", hook_delay_ms=1200,
        duration=30, tone="Hài", niche_id=7, shot_index=2,
    )
    with patch(
        "getviews_pipeline.script_generate._call_script_gemini",
        side_effect=RuntimeError("skip gemini"),
    ):
        out = run_script_generate_sync(user_sb, user_id="u1", body=body)
    # Only one shot in the response.
    assert len(out["shots"]) == 1
    # And it's specifically shot index 2 from the deterministic 6-shot
    # backbone — t0/t1 of shot[2] for a 30s script.
    shot = out["shots"][0]
    assert "t0" in shot and "t1" in shot
    assert shot["t1"] > shot["t0"]


def test_run_script_generate_sync_shot_index_none_returns_full_set() -> None:
    """Default (no ``shot_index``) keeps the legacy full-script regen
    behaviour — all 6 shots returned."""
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


def test_script_generate_body_rejects_shot_index_out_of_range() -> None:
    """Pydantic validates 0 <= shot_index <= 5 (six-shot ceiling)."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ScriptGenerateBody(
            topic="x", hook="y", hook_delay_ms=1200,
            duration=30, tone="Hài", niche_id=7, shot_index=6,
        )
    with pytest.raises(ValidationError):
        ScriptGenerateBody(
            topic="x", hook="y", hook_delay_ms=1200,
            duration=30, tone="Hài", niche_id=7, shot_index=-1,
        )


# ── S5: structured ``vo`` voice-over ─────────────────────────────────


def test_assembled_shots_carry_single_line_vo_fallback() -> None:
    """Deterministic fallback (no Gemini) emits a single-line ``vo``
    derived from the flattened ``voice`` string. Each shot's vo[0].t is
    the shot's start in M:SS format."""
    body = ScriptGenerateBody(
        topic="x", hook="y", hook_delay_ms=1200,
        duration=30, tone="Hài", niche_id=7,
    )
    shots = build_script_shots(body)
    assert len(shots) == 6
    for s in shots:
        vo = s.get("vo")
        assert isinstance(vo, list) and len(vo) == 1
        line = vo[0]
        assert "t" in line and "text" in line
        # Cue is None on the deterministic path.
        assert line.get("cue") is None
        # Timestamp is M:SS for the shot's start.
        assert line["t"] == f"{s['t0'] // 60}:{s['t0'] % 60:02d}"
        # Text mirrors the flat voice (back-compat).
        assert line["text"] == s["voice"]


def test_assembled_shots_preserve_gemini_vo_when_emitted() -> None:
    """When Gemini emits a structured ``vo`` array, ``_assemble_shots``
    must thread it through unchanged (with cue + multi-line) instead of
    replacing it with the single-line voice fallback."""
    from getviews_pipeline.script_generate import _assemble_shots

    gemini_vo = [
        {"t": "0:00", "text": "Mình *vừa test* xong.", "cue": None},
        {"t": "0:01", "text": "Khác *thật sự* hẳn.", "cue": "[dừng 0.3s]"},
    ]
    creative = [(
        "Cận mặt", "BOLD CENTER", "face_to_camera",
        "Mình vừa test xong. Khác thật sự hẳn.",
        "Tay cầm 2 sản phẩm",
        "white sans 28pt",
        "close_up", "static", "bold_center", "face", "static",
        gemini_vo, None,
    )] + [
        # Five filler rows so the assembler returns the canonical 6 shots.
        (
            "Cắt nhanh b-roll", "SUB-CAPTION", "product_shot",
            "voice", "viz", "—",
            None, None, None, None, None, None, None,
        ),
    ] * 5
    out = _assemble_shots(duration=30, creative=creative)
    assert out[0]["vo"] == gemini_vo
    # Filler rows fall back to single-line vo.
    assert len(out[1]["vo"]) == 1
    assert out[1]["vo"][0]["cue"] is None


def test_gemini_reason_vi_threads_through_to_shot_payload() -> None:
    """``reason_vi`` emitted by Gemini lands on the shot dict; shots
    without it carry an explicit None (FE branches on null)."""
    llm = _fake_llm_shots()
    llm.shots[0].reason_vi = "Hook câu hỏi đạt trung bình 320k view trong ngách."
    body = ScriptGenerateBody(
        topic="x", hook="y", hook_delay_ms=1200,
        duration=32, tone="Chuyên gia", niche_id=1,
    )
    with patch(
        "getviews_pipeline.script_generate._call_script_gemini",
        return_value=llm,
    ):
        shots = build_script_shots(body)
    assert shots[0]["reason_vi"] == "Hook câu hỏi đạt trung bình 320k view trong ngách."
    assert shots[1]["reason_vi"] is None


def test_fallback_shots_carry_null_reason_vi() -> None:
    body = ScriptGenerateBody(
        topic="x", hook="y", hook_delay_ms=1200,
        duration=30, tone="Hài", niche_id=1,
    )
    with patch(
        "getviews_pipeline.script_generate._call_script_gemini",
        side_effect=RuntimeError("no api key"),
    ):
        shots = build_script_shots(body)
    for s in shots:
        assert s["reason_vi"] is None


def test_voline_pydantic_validates_required_fields() -> None:
    """``VoLine.t`` and ``VoLine.text`` are required; ``cue`` defaults None."""
    import pytest
    from pydantic import ValidationError

    from getviews_pipeline.script_generate import VoLine

    line = VoLine(t="0:14", text="Hello *bold* world")
    assert line.cue is None
    assert line.text == "Hello *bold* world"

    with pytest.raises(ValidationError):
        VoLine(t="", text="hi")  # empty t fails min_length=1
    with pytest.raises(ValidationError):
        VoLine(t="0:00", text="")  # empty text fails min_length=1


# ── L1.1: decrement_credit guard contract ─────────────────────────────────
#
# The Supabase RPC ``decrement_credit`` returns INTEGER (the new balance,
# possibly 0 when the caller just spent their last credit) on success, or
# NULL → Python None when no credits remain. The original code used
# ``if rpc.data is False`` which never matched (None ≠ False) — users
# with 0 credits silently passed the guard and ran expensive Gemini calls.
# These tests pin the corrected contract on ``_decrement_credit_or_raise``:
# the off-by-one case (just spent last credit, balance == 0) MUST NOT
# raise, while NULL (no credits) MUST raise.
def test_decrement_credit_or_raise_raises_on_null() -> None:
    """RPC returns None (insufficient_credits) → raises."""
    import pytest

    from getviews_pipeline.script_generate import (
        InsufficientCreditsError,
        _decrement_credit_or_raise,
    )

    sb = MagicMock()
    sb.rpc.return_value.execute.return_value = SimpleNamespace(data=None)

    with pytest.raises(InsufficientCreditsError):
        _decrement_credit_or_raise(sb, user_id="user-with-no-credits")


def test_decrement_credit_or_raise_succeeds_on_zero_balance() -> None:
    """RPC returns 0 (just spent last credit) → must NOT raise."""
    from getviews_pipeline.script_generate import _decrement_credit_or_raise

    sb = MagicMock()
    sb.rpc.return_value.execute.return_value = SimpleNamespace(data=0)

    # No exception — returns implicitly None.
    _decrement_credit_or_raise(sb, user_id="user-just-spent-last-credit")


def test_decrement_credit_or_raise_succeeds_on_positive_balance() -> None:
    """RPC returns positive int (typical happy path) → must NOT raise."""
    from getviews_pipeline.script_generate import _decrement_credit_or_raise

    sb = MagicMock()
    sb.rpc.return_value.execute.return_value = SimpleNamespace(data=4)

    _decrement_credit_or_raise(sb, user_id="user-with-credits")


# ── L2.2: hook_effectiveness evidence injection into Gemini prompt ────────
#
# Hook Library plumbing — every script generated via ``/script/generate``
# (and by extension, the daily_ritual ``MỞ SCRIPT`` handoff) now grounds
# its hook + tone in the niche's top performing hooks instead of the
# generic ``_BACKBONE`` template. Tests pin the contract for the helpers
# + the prompt-injection shape.


def test_format_views_compact_vietnamese_units() -> None:
    """Vietnamese-friendly compact view counts: tr (triệu) / k / raw."""
    from getviews_pipeline.script_generate import _format_views_compact

    assert _format_views_compact(0) == "0"
    assert _format_views_compact(456) == "456"
    assert _format_views_compact(1_500) == "1k"  # integer floor
    assert _format_views_compact(12_345) == "12k"
    assert _format_views_compact(1_234_567) == "1.2tr"
    assert _format_views_compact(2_500_000) == "2.5tr"


def test_fetch_top_niche_hooks_filters_other_and_none() -> None:
    """Helper drops ``other``/``none`` hook_types — they're noise for evidence."""
    from getviews_pipeline.script_generate import _fetch_top_niche_hooks

    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[
            {"hook_type": "question", "avg_views": 320_000, "avg_completion_rate": 0.62, "sample_size": 47},
            {"hook_type": "other", "avg_views": 180_000, "avg_completion_rate": 0.55, "sample_size": 22},
            {"hook_type": "shock_stat", "avg_views": 240_000, "avg_completion_rate": 0.71, "sample_size": 31},
            {"hook_type": None, "avg_views": 90_000, "avg_completion_rate": 0.4, "sample_size": 8},
            {"hook_type": "story_open", "avg_views": 210_000, "avg_completion_rate": 0.58, "sample_size": 19},
            {"hook_type": "none", "avg_views": 150_000, "avg_completion_rate": 0.5, "sample_size": 12},
        ]
    )

    out = _fetch_top_niche_hooks(sb, niche_id=2, limit=3)

    # 3 entries, in order, no other/none/null
    assert [h["hook_type"] for h in out] == ["question", "shock_stat", "story_open"]
    # completion_pct converted to percentage
    assert out[0]["completion_pct"] == 62.0
    assert out[0]["sample_size"] == 47


def test_fetch_top_niche_hooks_returns_empty_on_error() -> None:
    """Any Supabase failure must not break script generation — return [] gracefully."""
    from getviews_pipeline.script_generate import _fetch_top_niche_hooks

    sb = MagicMock()
    sb.table.side_effect = RuntimeError("supabase down")

    assert _fetch_top_niche_hooks(sb, niche_id=2) == []
    # And no client = empty (used by tests + any caller without service role).
    assert _fetch_top_niche_hooks(None, niche_id=2) == []
    # Invalid niche_id = empty.
    assert _fetch_top_niche_hooks(sb, niche_id=0) == []


def test_format_hook_evidence_block_empty_returns_empty_string() -> None:
    """No hooks → empty string so the prompt shape stays the same as before L2.2."""
    from getviews_pipeline.script_generate import _format_hook_evidence_block

    assert _format_hook_evidence_block([]) == ""


def test_format_hook_evidence_block_renders_vietnamese_with_metrics() -> None:
    """Evidence block uses Vietnamese hook labels + compact view counts."""
    from getviews_pipeline.script_generate import _format_hook_evidence_block

    hooks = [
        {"hook_type": "question", "avg_views": 320_000, "completion_pct": 62.0, "sample_size": 47},
        {"hook_type": "shock_stat", "avg_views": 1_500_000, "completion_pct": 71.0, "sample_size": 31},
    ]
    block = _format_hook_evidence_block(hooks)

    # Vietnamese label + English enum (so Gemini can reason on either)
    assert "Đặt câu hỏi" in block
    assert "(question)" in block
    assert "Số liệu gây sốc" in block
    # Metrics shape: tr/k units + retention + sample size
    assert "320k view" in block
    assert "1.5tr view" in block
    assert "giữ chân 62.0%" in block
    assert "47 video" in block
    # Closing instruction tells Gemini this is evidence, not boilerplate
    assert "kiểm chứng" in block


def test_build_script_shots_passes_top_hooks_to_gemini(monkeypatch) -> None:
    """``build_script_shots`` threads top_hooks into ``_call_script_gemini``."""
    from getviews_pipeline import script_generate as sg

    seen: dict[str, object] = {}

    def fake_call_gemini(body, *, top_hooks=None, hook_lines=None, reference_block=""):
        seen["top_hooks"] = top_hooks
        # Force the deterministic fallback path so we don't need to mock
        # the full Gemini response shape — the assertion is on what got
        # passed in, not on the script output.
        raise RuntimeError("forced fallback")

    monkeypatch.setattr(sg, "_call_script_gemini", fake_call_gemini)

    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[
            {"hook_type": "question", "avg_views": 100_000, "avg_completion_rate": 0.6, "sample_size": 10},
        ]
    )

    body = sg.ScriptGenerateBody(
        topic="skincare", hook="Bạn có biết...", hook_delay_ms=800,
        duration=30, tone="Tâm sự", niche_id=2,
    )
    sg.build_script_shots(body, client=sb)

    assert seen["top_hooks"], "build_script_shots must fetch + thread top_hooks when client provided"
    assert seen["top_hooks"][0]["hook_type"] == "question"


def test_build_format_rationale_none_without_evidence() -> None:
    from getviews_pipeline.script_generate import _build_format_rationale

    assert _build_format_rationale([], []) is None


def test_build_format_rationale_shapes_proofs_and_text() -> None:
    from getviews_pipeline.script_generate import _build_format_rationale

    top_hooks = [
        {"hook_type": "question", "avg_views": 320_000, "completion_pct": 62.0, "sample_size": 47},
    ]
    hook_lines = [
        {"phrase": "Biết không, mua hàng online giờ ngon hơn đi chợ", "handle": "fashionista", "views": 1_200_000},
    ]
    out = _build_format_rationale(top_hooks, hook_lines)
    assert out is not None
    kinds = [p["kind"] for p in out["proofs"]]
    assert kinds == ["hook_stat", "hook_line"]
    assert out["proofs"][0]["label_vi"]  # Vietnamese label resolved
    assert out["proofs"][1]["views"] == 1_200_000
    # Sample size from hook_stat rows feeds the verifiable claim.
    assert "47 video" in out["text_vi"]
    # Copy rules — no hype words.
    for banned in ("bí mật", "công thức vàng", "triệu view", "bùng nổ"):
        assert banned not in out["text_vi"]


def test_run_script_generate_sync_returns_format_rationale_key() -> None:
    """Response always carries the key — None without evidence so old
    and new FE clients both behave."""
    user_sb = MagicMock()
    user_sb.rpc.return_value.execute.return_value = SimpleNamespace(data=1)
    body = ScriptGenerateBody(
        topic="x", hook="y", hook_delay_ms=1200,
        duration=30, tone="Hài", niche_id=7,
    )
    with patch(
        "getviews_pipeline.script_generate._call_script_gemini",
        side_effect=RuntimeError("skip gemini"),
    ):
        out = run_script_generate_sync(user_sb, user_id="u1", body=body)
    assert "format_rationale" in out
    assert out["format_rationale"] is None  # no service_sb → no evidence


def test_format_reference_structure_block_empty_and_rendered() -> None:
    from getviews_pipeline.script_generate import _format_reference_structure_block

    assert _format_reference_structure_block(None) == ""
    assert _format_reference_structure_block({"scenes": []}) == ""

    block = _format_reference_structure_block({
        "video_id": "v1",
        "handle": "topcreator",
        "views": 485_200,
        "scenes": [
            {"scene_index": 0, "start_s": 0.0, "end_s": 2.1,
             "description": "Mở hộp đồng hồ", "framing": "close_up",
             "pace": "fast", "overlay_style": "bold_center"},
            {"scene_index": 1, "start_s": 2.1, "end_s": 4.0,
             "description": None, "framing": None, "pace": None, "overlay_style": None},
        ],
    })
    assert "NHỊP CẢNH CỦA VIDEO TOP NGÁCH" in block
    assert "@topcreator" in block
    assert "485k view" in block
    assert "Cảnh 1 (0.0–2.1s): Mở hộp đồng hồ | close_up/fast/bold_center" in block
    # Null description/dims degrade gracefully.
    assert "Cảnh 2 (2.1–4.0s): —" in block
    # Closing instruction keeps the 6-shot contract.
    assert "Giữ NGUYÊN template 6 shot" in block


def test_fetch_reference_structure_graceful_on_error_or_no_client() -> None:
    from getviews_pipeline.script_generate import _fetch_reference_structure

    assert _fetch_reference_structure(None, 3) is None
    assert _fetch_reference_structure(MagicMock(), 0) is None
    sb = MagicMock()
    sb.table.side_effect = RuntimeError("supabase down")
    assert _fetch_reference_structure(sb, 3) is None


def test_build_script_shots_omits_top_hooks_when_no_client(monkeypatch) -> None:
    """Without a client, build_script_shots passes empty top_hooks (legacy path)."""
    from getviews_pipeline import script_generate as sg

    seen: dict[str, object] = {}

    def fake_call_gemini(body, *, top_hooks=None, hook_lines=None, reference_block=""):
        seen["top_hooks"] = top_hooks
        raise RuntimeError("forced fallback")

    monkeypatch.setattr(sg, "_call_script_gemini", fake_call_gemini)

    body = sg.ScriptGenerateBody(
        topic="skincare", hook="Bạn có biết...", hook_delay_ms=800,
        duration=30, tone="Tâm sự", niche_id=2,
    )
    sg.build_script_shots(body)  # no client

    # Either None or empty list — Gemini call sees no evidence block either way.
    assert not seen["top_hooks"]
