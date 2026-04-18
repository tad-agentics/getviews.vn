"""Unit tests for pattern_fingerprint pure functions."""

from __future__ import annotations

from getviews_pipeline.pattern_fingerprint import (
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
