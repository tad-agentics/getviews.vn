"""Quality pass 2026-06-11 — reference credibility + evidence-depth synthesis.

Pins the four behaviours added after the analysis-quality audit:
1. Topic-affinity scoring in the shot matcher (a skincare script must not
   surface gossip scenes as "Cùng ngách").
2. The user-evidence digest that replaces the 24-key prompt truncation —
   scene grammar / transcript / hook timeline compressed for DEPTH on the
   existing sections, not new topics.
3. Enriched reference-evidence lines (hook phrase + spoken opening per ref).
4. Real winning hook lines in the script prompt.
"""

from __future__ import annotations

from unittest.mock import MagicMock

# ── 1. Matcher topic gate ────────────────────────────────────────────


def _mock_shots_client(shots: list[dict], corpus_rows: list[dict]) -> MagicMock:
    client = MagicMock()

    def table(name: str) -> MagicMock:
        m = MagicMock()
        if name == "video_shots":
            m.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=shots
            )
        elif name == "video_corpus":
            m.select.return_value.in_.return_value.execute.return_value = MagicMock(
                data=corpus_rows
            )
        return m

    client.table.side_effect = table
    return client


def _shot_row(vid: str, **over) -> dict:
    base = {
        "video_id": vid, "scene_index": 0, "start_s": 0.0, "end_s": 2.0,
        "scene_type": None, "framing": "close_up", "pace": "slow",
        "overlay_style": "bold_center", "subject": "face", "motion": "static",
        "hook_type": None, "creator_handle": f"creator_{vid}",
        "thumbnail_url": "t.png", "tiktok_url": "u", "frame_url": "f.jpg",
        "description": "", "views": 50_000,
    }
    base.update(over)
    return base


def test_topic_overlap_outranks_mechanics_only() -> None:
    from getviews_pipeline.shot_reference_matcher import pick_shot_references

    shots = [
        _shot_row("vid_makeup"),
        _shot_row("vid_skincare"),
    ]
    corpus = [
        {"video_id": "vid_makeup", "caption": "biến hình trang điểm em trai",
         "analysis_json": {"content_context": {"subject_matter": "makeup transformation"}}},
        {"video_id": "vid_skincare", "caption": "retinol kết hợp aha sai cách làm da kích ứng",
         "analysis_json": {"content_context": {"subject_matter": "skincare routine retinol"}}},
    ]
    refs = pick_shot_references(
        shot_descriptor={"framing": "close_up", "pace": "slow",
                         "overlay_style": "bold_center", "subject": "face",
                         "motion": "static"},
        niche_id=2,
        topic_text="Dừng ngay việc kết hợp Retinol với AHA nếu không muốn da kích ứng",
        client=_mock_shots_client(shots, corpus),
    )
    assert refs, "topic-matching candidate must survive the gate"
    assert refs[0].video_id == "vid_skincare"
    assert "topic" in refs[0].match_signals
    assert refs[0].match_label.startswith("Cùng ngách, chủ đề")


def test_min_score_filters_weak_mechanics_matches() -> None:
    """A single weak dimension (motion +5) no longer clears the gate."""
    from getviews_pipeline.shot_reference_matcher import pick_shot_references

    shots = [_shot_row("v1", framing="wide", pace="fast",
                       overlay_style="none", subject="product")]
    refs = pick_shot_references(
        shot_descriptor={"framing": "close_up", "pace": "slow",
                         "overlay_style": "bold_center", "subject": "face",
                         "motion": "static"},
        niche_id=2,
        client=_mock_shots_client(shots, []),
    )
    assert refs == []


# ── 2. User evidence digest ──────────────────────────────────────────


def test_digest_compresses_scenes_transcript_and_timeline() -> None:
    from getviews_pipeline.diagnose_prompts import build_user_evidence_digest

    analysis = {
        "hook_timeline": [
            {"event": "face_enter", "t": 0.2},
            {"event": "first_word", "t": 0.5},
            {"event": "text_overlay", "t": 0.9},
        ],
        "scenes": [
            {"start_s": 0.0, "end_s": 2.5, "framing": "close_up", "pace": "fast",
             "overlay_style": "bold_center", "description": "Cận mặt creator nói câu mở"},
            {"start_s": 2.5, "end_s": 8.0, "framing": "medium", "pace": "slow",
             "overlay_style": None, "description": "Quay sản phẩm trên bàn"},
        ],
        "audio_transcript": "Sáu giờ sáng mẹ dậy chuẩn bị cơm cho con mang đi làm " * 20,
        "audio_track_role": "voiceover_chính",
        "sound_layering": "voice+nhạc nền nhẹ",
    }
    d = build_user_evidence_digest(analysis)
    assert d["hook_timeline"] == "face_enter 0.2s → first_word 0.5s → text_overlay 0.9s"
    assert len(d["scene_pattern"]) == 2
    assert d["scene_pattern"][0].startswith("0.0–2.5s close_up/fast/bold_center")
    assert d["transcript_opening"].endswith("…")
    assert "voiceover_chính" in d["audio_character"]


def test_digest_empty_analysis_yields_empty_digest() -> None:
    from getviews_pipeline.diagnose_prompts import build_user_evidence_digest

    assert build_user_evidence_digest({}) == {}


def test_prompt_carries_digest_and_full_scalars_and_retention_hedge() -> None:
    from getviews_pipeline.diagnose_prompts import build_diagnosis_v6_user_prompt

    user_analysis = {
        # 30 scalar keys — the old [:24] cliff would have dropped the tail.
        **{f"k{i:02d}": i for i in range(28)},
        "loop_architecture_score": 0.8,
        "scenes": [{"start_s": 0, "end_s": 2, "framing": "close_up",
                    "description": "cảnh mở"}],
        "audio_transcript": "xin chào cả nhà hôm nay mình thử",
    }
    prompt = build_diagnosis_v6_user_prompt(
        sections_to_emit=["verdict"],
        manifest_for_llm={},
        ctx={},
        content_format="tutorial",
        niche_name="Skincare",
        corpus_size=100,
        reference_videos=[],
        user_analysis=user_analysis,
        user_stats={"views": 100, "retention_source": "modeled"},
        performance_tier="average",
        channel_context=None,
        errors=None,
        wants_directions=False,
    )
    # scalar tail survives (old cliff dropped keys past 24)
    assert "loop_architecture_score" in prompt
    # heavy arrays ride the digest, not raw
    assert "USER_EVIDENCE_DIGEST" in prompt
    assert "scene_pattern" in prompt
    assert "xin chào cả nhà" in prompt  # transcript opening in digest
    # modeled retention must carry the hedge
    assert "ƯỚC TÍNH" in prompt
    # depth contract present
    assert "KHÔNG mở chủ đề/section mới" in prompt
    assert "làm như @handle" in prompt


# ── 3. Reference evidence lines ──────────────────────────────────────


def test_reference_evidence_lines_carry_hook_and_opening() -> None:
    from getviews_pipeline.pipelines import _reference_evidence_lines

    refs = [{
        "aweme_id": "123",
        "desc": "video skincare retinol",
        "creator_handle": "@beautyvn",
        "statistics": {"play_count": 250_000},
        "content_format": "talking_head",
        "_from_corpus": True,
        "analysis": {
            "hook_analysis": {"hook_phrase": "Đừng bôi retinol kiểu này", "hook_type": "canh_bao"},
            "audio_transcript": "Mình từng làm hỏng da vì trộn retinol với aha và đây là bài học",
        },
    }]
    block = _reference_evidence_lines(refs, "corpus")
    assert "@beautyvn" in block
    assert 'hook (canh_bao): "Đừng bôi retinol kiểu này"' in block
    assert "lời mở (transcript)" in block


# ── 4. Winning hook lines in the script prompt ───────────────────────


def test_format_hook_lines_block_renders_verbatim_lines() -> None:
    from getviews_pipeline.script_generate import _format_hook_lines_block

    block = _format_hook_lines_block([
        {"phrase": "Đừng bôi retinol kiểu này", "handle": "beautyvn", "views": 250_000},
    ])
    assert "HOOK THẬT ĐANG THẮNG TRONG NGÁCH" in block
    assert '"Đừng bôi retinol kiểu này" — @beautyvn' in block
    assert "KHÔNG copy y nguyên" in block
    assert _format_hook_lines_block([]) == ""


def test_fetch_winning_hook_lines_dedupes_and_skips_short() -> None:
    from getviews_pipeline.script_generate import _fetch_winning_hook_lines

    rows = [
        {"creator_handle": "a", "views": 900,
         "analysis_json": {"hook_analysis": {"hook_phrase": "Đừng bôi retinol kiểu này nhé"}}},
        {"creator_handle": "b", "views": 800,
         "analysis_json": {"hook_analysis": {"hook_phrase": "đừng bôi retinol kiểu này nhé"}}},  # dupe
        {"creator_handle": "c", "views": 700,
         "analysis_json": {"hook_analysis": {"hook_phrase": "ngắn"}}},  # too short
        {"creator_handle": "d", "views": 600, "analysis_json": {}},  # no hook
        {"creator_handle": "e", "views": 500,
         "analysis_json": {"hook_analysis": {"hook_phrase": "Sai lầm này khiến da bạn tệ hơn"}}},
    ]
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.or_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=rows
    )
    out = _fetch_winning_hook_lines(client, 2, limit=5)
    assert [o["handle"] for o in out] == ["a", "e"]


def test_fetch_winning_hook_lines_never_raises() -> None:
    from getviews_pipeline.script_generate import _fetch_winning_hook_lines

    client = MagicMock()
    client.table.side_effect = Exception("db down")
    assert _fetch_winning_hook_lines(client, 2) == []
    assert _fetch_winning_hook_lines(None, 2) == []
