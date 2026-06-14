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
    # Hook-timeline events + overlay_style are translated to Vietnamese here so
    # the cited digest never feeds raw enum codes into the report prose.
    assert d["hook_timeline"] == (
        "Khuôn mặt xuất hiện 0.2s → Lời thoại đầu 0.5s → Chữ hiện lên màn hình 0.9s"
    )
    assert "face_enter" not in d["hook_timeline"]
    assert "text_overlay" not in d["hook_timeline"]
    assert len(d["scene_pattern"]) == 2
    assert d["scene_pattern"][0].startswith("0.0–2.5s close up/fast/Chữ in đậm ở giữa")
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


def test_reference_evidence_lines_include_peer_hook_timestamps() -> None:
    from getviews_pipeline.pipelines import _reference_evidence_lines

    refs = [{
        "aweme_id": "999",
        "statistics": {"play_count": 9000},
        "analysis": {
            "hook_analysis": {
                "hook_phrase": "Hook",
                "hook_type": "question",
                "hook_timeline": [{"event": "face_enter", "t": 0.4}],
            },
        },
    }]
    block = _reference_evidence_lines(refs, "corpus")
    assert "mốc hook peer: 0.4–3.4s" in block


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


# ── 5. Prose-discipline contracts (CEO direction 2026-06-11) ─────────


def test_channel_prompt_carries_sentence_discipline() -> None:
    from getviews_pipeline import channel_diagnose_prompts as cdp

    src = cdp.__doc__ or ""
    # The system prompt text lives in module-level constants; scan the module source.
    import inspect

    text = inspect.getsource(cdp)
    assert "KỶ LUẬT CÂU" in text
    assert "khóa pattern" in text
    assert "CẤM câu đệm" in text
    assert "cùng video" in text  # prose and FE card must reference the same video
    del src


def test_video_diagnosis_prompt_carries_cadence_rules() -> None:
    from getviews_pipeline.diagnose_prompts import build_diagnosis_v6_user_prompt

    prompt = build_diagnosis_v6_user_prompt(
        sections_to_emit=["verdict"],
        manifest_for_llm={},
        ctx={},
        content_format="tutorial",
        niche_name="Skincare",
        corpus_size=100,
        reference_videos=[],
        user_analysis={},
        user_stats={"views": 100},
        performance_tier="average",
        channel_context=None,
        errors=None,
        wants_directions=False,
    )
    assert "KỶ LUẬT CÂU" in prompt
    assert "CẤM câu đệm" in prompt


def test_script_narrative_summary_carries_shot_references() -> None:
    from getviews_pipeline.report_script import _shots_summary_for_narrative

    shots = [{
        "t0": 0, "t1": 3, "cam": "Cận mặt", "voice": "Hook mở", "overlay": "BOLD",
        "references": [{
            "creator_handle": "@beautyvn", "views": 250_000,
            "description": "Cận mặt creator nói câu mở đầu",
        }],
    }]
    block = _shots_summary_for_narrative(shots)
    assert "ref: @beautyvn (250k view)" in block
    assert "Cận mặt creator" in block
    # Shots without references stay one-line (no dangling ref label).
    plain = _shots_summary_for_narrative([{"t0": 0, "t1": 3, "cam": "x", "voice": "y", "overlay": "z"}])
    assert "ref:" not in plain


# ── 6. Visible-thumbnail reference preference (2026-06-11) ───────────


def test_visible_thumbnail_wins_at_equal_proximity() -> None:
    from getviews_pipeline.pipelines import _ref_has_visible_thumbnail

    assert _ref_has_visible_thumbnail({"thumbnail_url": "https://r2/x.webp"}) is True
    assert _ref_has_visible_thumbnail({"thumbnail_url": None}) is False
    # Live ED aweme with a fresh cover counts as visible.
    assert _ref_has_visible_thumbnail(
        {"video": {"cover": {"url_list": ["https://cdn/c.jpg"]}}}
    ) is True
    assert _ref_has_visible_thumbnail({"video": {"cover": {"url_list": []}}}) is False


def test_mirror_runs_even_when_queue_enqueue_fails() -> None:
    """The 7-week queue outage must never again take thumbnail mirroring
    down with it — the two concerns are independent."""
    import asyncio
    import inspect

    from getviews_pipeline import pipelines

    src = inspect.getsource(pipelines)
    # Source-level tripwire: the enqueue except-branch must not return
    # before _mirror_queue_thumbnails_for_rows.
    idx = src.find("[corpus_queue] enqueue failed")
    tail = src[idx : idx + 400]
    assert "return" not in tail.split("_mirror_queue_thumbnails_for_rows")[0], (
        "enqueue failure path returns before mirroring — regression of the "
        "2026-06-11 decoupling fix"
    )
    del asyncio


# ── 7. Frame-first thumbnails (2026-06-11 directive) ─────────────────


def test_capture_returns_none_when_r2_unconfigured(tmp_path) -> None:
    from getviews_pipeline.r2 import capture_thumbnail_from_video

    vid_file = tmp_path / "v.mp4"
    vid_file.write_bytes(b"\x00" * 64)
    # r2 unconfigured in tests → hard None, never raises.
    assert capture_thumbnail_from_video(vid_file, "v1") is None


def test_capture_skips_when_thumbnail_already_exists(monkeypatch, tmp_path) -> None:
    from getviews_pipeline import r2

    monkeypatch.setattr(r2, "r2_configured", lambda: True)
    monkeypatch.setattr(r2, "_ffmpeg_available", lambda: True)
    monkeypatch.setattr(r2, "r2_public_thumbnail_exists", lambda vid: True)
    monkeypatch.setattr(r2, "r2_public_thumbnail_url", lambda vid: f"https://r2/thumbnails/{vid}.webp")
    vid_file = tmp_path / "v.mp4"
    vid_file.write_bytes(b"\x00" * 64)
    assert r2.capture_thumbnail_from_video(vid_file, "v1") == "https://r2/thumbnails/v1.webp"


def test_resolve_prefers_fresh_frame_over_existing_cover_webp(monkeypatch) -> None:
    """prefer_frame=True must OVERWRITE a cover-mirrored webp with the real
    frame — the video's opening frame beats the platform's default cover."""
    import asyncio

    from getviews_pipeline import r2

    monkeypatch.setattr(r2, "copy_first_frame_to_thumbnail", lambda vid: f"https://r2/thumbnails/{vid}.webp")
    # exists-check would short-circuit without prefer_frame:
    monkeypatch.setattr(r2, "r2_public_thumbnail_exists", lambda vid: True)
    monkeypatch.setattr(r2, "r2_public_thumbnail_url", lambda vid: "https://r2/OLD-cover.webp")

    out = asyncio.run(
        r2.resolve_ingest_thumbnail_url("v9", "https://cdn/x.jpg", prefer_frame=True)
    )
    assert out == "https://r2/thumbnails/v9.webp"  # frame transcode won

    out2 = asyncio.run(
        r2.resolve_ingest_thumbnail_url("v9", "https://cdn/x.jpg", prefer_frame=False)
    )
    assert out2 == "https://r2/OLD-cover.webp"  # legacy behaviour unchanged


def test_live_analysis_banks_frame_capture_before_gemini() -> None:
    """Source tripwire: _analyze_video must capture the frame after download
    and BEFORE the Gemini call, and thread r2_thumbnail_url into the result."""
    import inspect

    from getviews_pipeline import analysis_core

    src = inspect.getsource(analysis_core._analyze_video)
    cap = src.find("capture_thumbnail_from_video")
    gemini = src.find("analyze_video,")
    assert 0 < cap < gemini, "frame capture must run before the Gemini analysis call"
    assert 'result["r2_thumbnail_url"]' in src


# ── 8. Inline reference playback (2026-06-11) ────────────────────────


def test_slim_reference_ships_r2_playback_only() -> None:
    from getviews_pipeline.pipelines import _slim_reference_video

    base = {
        "aweme_id": "111",
        "author": {"unique_id": "creator1"},
        "statistics": {"play_count": 5000},
    }
    # R2-hosted corpus clip → shipped for inline playback.
    r2_ref = {**base, "_corpus_video_url": "https://pub-x.r2.dev/videos/111.mp4"}
    assert _slim_reference_video(r2_ref)["playback_url"] == "https://pub-x.r2.dev/videos/111.mp4"
    # Expiring platform play URL → never shipped.
    cdn_ref = {**base, "_corpus_video_url": "https://v16.tiktokcdn.com/play/111.mp4"}
    assert _slim_reference_video(cdn_ref)["playback_url"] is None
    # No clip at all → None (FE keeps the external TikTok link).
    assert _slim_reference_video(base)["playback_url"] is None


# ── 9. Live-search reference playback (2026-06-11 part 2) ────────────


def test_bank_video_clip_skips_when_exists(monkeypatch, tmp_path) -> None:
    from getviews_pipeline import r2

    monkeypatch.setattr(r2, "r2_configured", lambda: True)
    monkeypatch.setattr(r2, "_ffmpeg_available", lambda: True)
    monkeypatch.setattr(r2, "r2_object_exists", lambda key: True)
    monkeypatch.setattr(r2, "R2_VIDEO_PUBLIC_URL", "https://pub-x.r2.dev")
    vid_file = tmp_path / "v.mp4"
    vid_file.write_bytes(b"\x00" * 64)
    assert r2.bank_video_clip(vid_file, "v77") == "https://pub-x.r2.dev/videos/v77.mp4"
    # Unconfigured → quiet None.
    monkeypatch.setattr(r2, "r2_configured", lambda: False)
    assert r2.bank_video_clip(vid_file, "v77") is None


def test_live_slim_input_carries_banked_clip_and_thumbnail() -> None:
    from getviews_pipeline.pipelines import _slim_reference_video
    from getviews_pipeline.video_analyze import _live_analyzed_to_slim_input

    result = {
        "metadata": {
            "video_id": "555",
            "author": {"username": "@livecreator"},
            "metrics": {"views": 90_000},
            "description": "video hay",
            "thumbnail_url": "https://p16.tiktokcdn.com/cover.jpg",
        },
        "analysis": {"hook_analysis": {"hook_type": "question"}},
        "r2_thumbnail_url": "https://pub-x.r2.dev/thumbnails/555.webp",
        "r2_video_url": "https://pub-x.r2.dev/videos/555.mp4",
    }
    slim_in = _live_analyzed_to_slim_input(result)
    # Banked assets beat the platform CDN values.
    assert slim_in["thumbnail_url"] == "https://pub-x.r2.dev/thumbnails/555.webp"
    card = _slim_reference_video(slim_in, "live_search")
    assert card["playback_url"] == "https://pub-x.r2.dev/videos/555.mp4"
    assert card["source"] == "live_search"


def test_analyze_video_awaits_clip_before_unlink() -> None:
    """Source tripwire: the finally block must bounded-await the clip task
    before deleting the temp file — ffmpeg must never lose its input."""
    import inspect

    from getviews_pipeline import analysis_core

    src = inspect.getsource(analysis_core._analyze_video)
    fin = src.rfind("finally:")
    tail = src[fin:]
    assert "clip_task" in tail and tail.find("clip_task") < tail.find("video_path.unlink()"), (
        "finally must wait on clip_task before video_path.unlink()"
    )
