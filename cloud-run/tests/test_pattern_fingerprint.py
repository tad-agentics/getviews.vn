"""Unit tests for pattern_fingerprint pure functions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from getviews_pipeline.pattern_fingerprint import (
    _clean_generated_name,
    _name_prompt,
    _recompute_weekly_counts_sync,
    bucket_tps,
    build_display_name,
    compute_signature,
    signature_hash,
)


# ── Bucket edges ───────────────────────────────────────────────────────────


def test_bucket_tps_long_take() -> None:
    assert bucket_tps(0.0) == "long_take"
    assert bucket_tps(0.29) == "long_take"


def test_bucket_tps_standard() -> None:
    assert bucket_tps(0.3) == "standard"
    assert bucket_tps(0.5) == "standard"
    assert bucket_tps(0.79) == "standard"


def test_bucket_tps_boundaries_dont_drift() -> None:
    # Two nearby videos shouldn't fracture into different buckets — fencepost
    # check for each edge.
    assert bucket_tps(0.79) == "standard"
    assert bucket_tps(0.8) == "tight_cut"
    assert bucket_tps(1.29) == "tight_cut"
    assert bucket_tps(1.3) == "fast_cut"
    assert bucket_tps(1.99) == "fast_cut"
    assert bucket_tps(2.0) == "hyper_cut"


def test_bucket_tps_none_defaults_to_standard() -> None:
    assert bucket_tps(None) == "standard"


# ── Signature ──────────────────────────────────────────────────────────────


def _mk_analysis(
    hook_type: str = "question",
    content_arc: str = "none",
    tone: str = "educational",
    energy: str = "medium",
    tps: float = 0.5,
    face_at: float | None = None,
    overlays: int = 0,
) -> dict:
    return {
        "hook_analysis": {"hook_type": hook_type, "face_appears_at": face_at},
        "content_arc": content_arc,
        "tone": tone,
        "energy_level": energy,
        "transitions_per_second": tps,
        "text_overlays": [{"text": f"t{i}", "appears_at": i} for i in range(overlays)],
    }


def test_signature_contains_seven_fields() -> None:
    sig = compute_signature(_mk_analysis())
    assert set(sig.keys()) == {
        "hook_type", "content_arc", "tone", "energy_level",
        "tps_bucket", "face_first", "has_text_overlay",
    }


def test_identical_videos_produce_identical_hash() -> None:
    a = _mk_analysis(hook_type="warning", content_arc="before_after", face_at=0.3, overlays=2)
    b = _mk_analysis(hook_type="warning", content_arc="before_after", face_at=0.5, overlays=3)
    # face_first + has_text_overlay are booleans — small differences shouldn't
    # change the signature, so the two above must hash identically.
    assert signature_hash(compute_signature(a)) == signature_hash(compute_signature(b))


def test_different_hook_types_hash_differently() -> None:
    a = _mk_analysis(hook_type="question")
    b = _mk_analysis(hook_type="warning")
    assert signature_hash(compute_signature(a)) != signature_hash(compute_signature(b))


def test_bucket_edges_create_new_signature() -> None:
    a = _mk_analysis(tps=0.79)  # standard
    b = _mk_analysis(tps=0.80)  # tight_cut
    assert signature_hash(compute_signature(a)) != signature_hash(compute_signature(b))


def test_face_first_under_one_second() -> None:
    assert compute_signature(_mk_analysis(face_at=0.4))["face_first"] is True
    assert compute_signature(_mk_analysis(face_at=1.0))["face_first"] is False
    assert compute_signature(_mk_analysis(face_at=None))["face_first"] is False


def test_has_text_overlay_ignores_empty_strings() -> None:
    a = {"text_overlays": [{"text": "", "appears_at": 0}, {"text": "  ", "appears_at": 1}]}
    b = {"text_overlays": [{"text": "", "appears_at": 0}, {"text": "BUY NOW", "appears_at": 1}]}
    assert compute_signature(a)["has_text_overlay"] is False
    assert compute_signature(b)["has_text_overlay"] is True


def test_missing_fields_use_defaults_and_dont_crash() -> None:
    sig = compute_signature({})
    assert sig["hook_type"] == "other"
    assert sig["tps_bucket"] == "standard"
    assert sig["face_first"] is False
    assert sig["has_text_overlay"] is False


# ── Hash stability ────────────────────────────────────────────────────────


def test_hash_is_deterministic() -> None:
    sig = compute_signature(_mk_analysis(hook_type="pain_point", tps=1.5))
    assert signature_hash(sig) == signature_hash(sig)


def test_hash_insensitive_to_dict_key_order() -> None:
    sig_a = {"a": 1, "b": 2, "c": 3}
    sig_b = {"c": 3, "a": 1, "b": 2}
    assert signature_hash(sig_a) == signature_hash(sig_b)


def test_hash_is_short_and_hex() -> None:
    h = signature_hash(compute_signature(_mk_analysis()))
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)


# ── Display name ──────────────────────────────────────────────────────────


def test_display_name_warning_before_after_fast_cut_face() -> None:
    sig = compute_signature(_mk_analysis(
        hook_type="pain_point",
        content_arc="before_after",
        tps=1.5,
        face_at=0.3,
    ))
    name = build_display_name(sig)
    assert "Chạm đau" in name
    assert "trước/sau" in name
    assert "cắt nhanh" in name
    assert "mặt người" in name


def test_display_name_minimal_for_default_signature() -> None:
    sig = compute_signature(_mk_analysis())  # question + standard, no face
    name = build_display_name(sig)
    # "Câu hỏi" is the hook; standard pace produces no pace suffix, no arc.
    assert "Câu hỏi" in name
    assert "cắt" not in name
    assert "mặt người" not in name


def test_display_name_unknown_hook_fallback() -> None:
    sig = compute_signature({"hook_analysis": {"hook_type": "made_up_type"}})
    # Unknown hook types map to "Khác" (other).
    assert build_display_name(sig).startswith("Khác")


# ── Gemini-generated display name helpers ─────────────────────────────────


def test_clean_generated_name_strips_quotes() -> None:
    assert _clean_generated_name('"Cảnh báo phá vỡ"') == "Cảnh báo phá vỡ"
    assert _clean_generated_name("'Cảnh báo phá vỡ'") == "Cảnh báo phá vỡ"
    assert _clean_generated_name("`Cảnh báo phá vỡ`") == "Cảnh báo phá vỡ"


def test_clean_generated_name_strips_markdown_bullets() -> None:
    assert _clean_generated_name("- Cảnh báo + trước sau") == "Cảnh báo + trước sau"
    assert _clean_generated_name("* Hook cận mặt") == "Hook cận mặt"
    assert _clean_generated_name("• Trước sau bật ngược") == "Trước sau bật ngược"


def test_clean_generated_name_takes_first_line_only() -> None:
    raw = "Cảnh báo phá vỡ\nPattern này chạy vì hook bất ngờ..."
    assert _clean_generated_name(raw) == "Cảnh báo phá vỡ"


def test_clean_generated_name_strips_trailing_punct() -> None:
    assert _clean_generated_name("Cảnh báo phá vỡ.") == "Cảnh báo phá vỡ"
    assert _clean_generated_name("Cận mặt bất ngờ!") == "Cận mặt bất ngờ"
    assert _clean_generated_name("Trend lift.....") == "Trend lift"


def test_clean_generated_name_strips_prefix_labels() -> None:
    assert _clean_generated_name("Tên pattern: Cảnh báo phá vỡ") == "Cảnh báo phá vỡ"
    assert _clean_generated_name("Pattern name: Hook direct") == "Hook direct"
    assert _clean_generated_name("Name: Trước sau") == "Trước sau"


def test_clean_generated_name_caps_length() -> None:
    raw = "Đây là một tên rất dài vượt quá giới hạn cho phép của pattern fingerprint module cần bị cắt"
    cleaned = _clean_generated_name(raw)
    # _NAME_MAX_CHARS is 60; the helper truncates and adds "…".
    assert len(cleaned) <= 61  # 60 chars + 1-char ellipsis
    assert cleaned.endswith("…")


def test_clean_generated_name_rejects_too_short() -> None:
    assert _clean_generated_name("ab") == ""
    assert _clean_generated_name("") == ""
    assert _clean_generated_name('""') == ""


def test_name_prompt_includes_signature_fields() -> None:
    sig = compute_signature(_mk_analysis(
        hook_type="pain_point",
        content_arc="before_after",
        tps=1.6,
        face_at=0.3,
        overlays=2,
    ))
    prompt = _name_prompt(sig, None)
    # Vietnamese labels for the signature features appear.
    assert "Chạm đau" in prompt
    assert "trước/sau" in prompt
    assert "cắt nhanh" in prompt
    assert "Có mặt người" in prompt
    assert "Có text overlay" in prompt


def test_name_prompt_includes_example_hook_when_available() -> None:
    sig = compute_signature(_mk_analysis())
    analysis = {
        "hook_analysis": {"hook_phrase": "ĐỪNG MUA KEM NÀY nếu chưa xem"},
        "content_direction": {"what_works": "Cận mặt + chữ vàng trên đen giây 0.5"},
    }
    prompt = _name_prompt(sig, analysis)
    assert "ĐỪNG MUA KEM NÀY" in prompt
    assert "Cận mặt" in prompt


def test_name_prompt_omits_example_block_when_analysis_empty() -> None:
    sig = compute_signature(_mk_analysis())
    prompt = _name_prompt(sig, None)
    assert "Ví dụ video" not in prompt
    # Empty analysis dict also → no example block.
    prompt2 = _name_prompt(sig, {})
    assert "Ví dụ video" not in prompt2


def test_recompute_weekly_counts_uses_iso_cutoff() -> None:
    """BUG-11 regression: ``.gte("indexed_at", "now() - interval '14 days'")``
    passes a literal SQL expression to PostgREST which can't evaluate it,
    so the recompute always fetched zero rows and Studio's LƯỢT DÙNG
    column stuck at 0 for every pattern. Fix computes the ISO cutoff in
    Python — the cutoff value MUST be ISO-8601, not a SQL expression."""
    # Capture the cutoff the implementation passes into ``.gte``.
    calls: list[tuple[str, str]] = []

    sb = MagicMock()
    # Chain used in _recompute_weekly_counts_sync: table(...).select(...).
    # gte(col, val).not_.is_(col, val).limit(n).execute()
    table_mock = MagicMock()
    sb.table.return_value = table_mock
    select_mock = MagicMock()
    table_mock.select.return_value = select_mock

    def gte(col: str, val: str) -> MagicMock:
        calls.append((col, val))
        return gte_mock

    gte_mock = MagicMock()
    select_mock.gte.side_effect = gte
    gte_mock.not_.is_.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

    # Also back the UPDATE chain even though we won't hit it (no pids).
    table_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    touched = _recompute_weekly_counts_sync(sb)
    assert touched == 0  # no rows in the mock — nothing to update

    # Exactly one gte(indexed_at, <ISO>) call, and the value parses.
    assert len(calls) == 1
    col, val = calls[0]
    assert col == "indexed_at"
    parsed = datetime.fromisoformat(val)
    assert parsed.tzinfo is not None
    # Cutoff should be ~14 days in the past, within a generous window.
    age = datetime.now(tz=timezone.utc) - parsed
    assert timedelta(days=13, hours=23) <= age <= timedelta(days=14, hours=1)
