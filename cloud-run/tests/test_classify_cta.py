"""Regression tests for ``_classify_cta`` — pins the VN pattern
additions landed 2026-05-10 per the cta-face-detect audit.

Each test case cites the raw CTA phrase from live corpus samples
that previously bucketed to 'other'. With the expanded regex they
route to the correct existing taxonomy bucket.
"""

from __future__ import annotations

from getviews_pipeline.corpus_ingest import _classify_cta


# ── shop_cart: additional VN shop-pressure variants ──────────────────

def test_chot_ngay_routes_to_shop_cart() -> None:
    """Live sample: 'tranh thủ đợt flash sale này mà chốt ngay combo'."""
    assert _classify_cta("tranh thủ đợt flash sale này mà chốt ngay combo") == "shop_cart"


def test_chot_nhe_routes_to_shop_cart() -> None:
    """Live sample: 'mỗi vợ chốt nhẹ một hai set'."""
    assert _classify_cta("mỗi vợ chốt nhẹ một hai set") == "shop_cart"


def test_chot_di_routes_to_shop_cart() -> None:
    assert _classify_cta("Chốt đi") == "shop_cart"


def test_san_deal_routes_to_shop_cart() -> None:
    """Live sample: 'Mọi người tranh thủ săn deal nhé.'"""
    assert _classify_cta("Mọi người tranh thủ săn deal nhé") == "shop_cart"


# ── try_it: additional VN try-it variants ────────────────────────────

def test_ap_dung_routes_to_try_it() -> None:
    """Live sample: 'Thử áp dụng đi'."""
    assert _classify_cta("Thử áp dụng đi") == "try_it"


def test_tham_khao_routes_to_try_it() -> None:
    """Live sample: 'Các tình yêu có thể thử tham khảo em này nhé.'"""
    assert _classify_cta("Các tình yêu có thể thử tham khảo em này nhé") == "try_it"


def test_lam_lien_routes_to_try_it() -> None:
    """Live sample: 'Làm liền bây giờ nha mọi người'."""
    assert _classify_cta("Làm liền bây giờ nha mọi người") == "try_it"


def test_ghe_routes_to_try_it() -> None:
    """Live sample: 'Nhanh chân ghé hỷ'."""
    assert _classify_cta("Nhanh chân ghé hỷ") == "try_it"


# ── follow: external channel follow ──────────────────────────────────

def test_len_kenh_routes_to_follow() -> None:
    """Live sample: 'Hãy lên kênh YT của Hoàng Tốc Độ xem nha'."""
    assert _classify_cta("Hãy lên kênh YT của Hoàng Tốc Độ xem nha") == "follow"


# ── comment: DM variants ─────────────────────────────────────────────

def test_inbox_routes_to_comment() -> None:
    """Live sample: 'inbox để mình tư vấn cho nhé'."""
    assert _classify_cta("inbox để mình tư vấn cho nhé") == "comment"


def test_nhan_minh_routes_to_comment() -> None:
    """Live sample: 'ai cần thì nhắn mình nha'."""
    assert _classify_cta("ai cần thì nhắn mình nha") == "comment"


# ── part2: future-episode announcements ──────────────────────────────

def test_video_sau_routes_to_part2() -> None:
    """Live sample: 'Video sau tôi sẽ chia sẻ 20 mindset cực đỉnh'."""
    assert _classify_cta("Video sau tôi sẽ chia sẻ 20 mindset cực đỉnh") == "part2"


# ── existing patterns still work ─────────────────────────────────────

def test_existing_patterns_unchanged() -> None:
    """Smoke: verify the pre-audit patterns still classify correctly."""
    assert _classify_cta("Lưu lại nhé") == "save"
    assert _classify_cta("Follow kênh của mình") == "follow"
    assert _classify_cta("Comment bên dưới") == "comment"
    assert _classify_cta("Chốt đơn ngay") == "shop_cart"
    assert _classify_cta("Link ở bio nhé") == "link_bio"
    assert _classify_cta("Phần 2 đang lên") == "part2"
    assert _classify_cta("Thử đi các bạn") == "try_it"


# ── null / empty handling unchanged ──────────────────────────────────

def test_none_cta_returns_none() -> None:
    assert _classify_cta(None) is None


def test_empty_string_returns_none() -> None:
    assert _classify_cta("") is None


def test_unmatched_falls_to_other() -> None:
    """Genuine non-taxonomy CTA still goes to 'other', not None."""
    assert _classify_cta("contact Coco let's get more profit") == "other"
