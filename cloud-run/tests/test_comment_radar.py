"""Unit tests for comment_radar.score_comments — pure helper, no network."""

from __future__ import annotations

from getviews_pipeline.comment_radar import CommentRadar, score_comments


# ── Empty / edge input ─────────────────────────────────────────────────────


def test_empty_list_returns_empty_radar() -> None:
    r = score_comments([])
    assert isinstance(r, CommentRadar)
    assert r.sampled == 0
    assert r.language == "unknown"


def test_all_spam_skipped() -> None:
    r = score_comments(["", "   ", "!!!", "ok", "❤️❤️❤️❤️❤️❤️"])
    assert r.sampled == 0


def test_total_available_reflects_raw_count() -> None:
    r = score_comments(["ok", ""], total_available=123)
    assert r.total_available == 123


# ── Purchase intent ────────────────────────────────────────────────────────


def test_purchase_intent_vietnamese_basic() -> None:
    comments = [
        "Sản phẩm xịn quá, tôi sẽ mua luôn!",
        "Giá bao nhiêu vậy shop?",
        "Link đâu cho mình xin với",
    ]
    r = score_comments(comments)
    assert r.purchase_intent_count == 3


def test_purchase_intent_collects_up_to_3_phrases() -> None:
    comments = [
        "Tôi sẽ mua ngay thôi",
        "Mình sẽ thử sản phẩm này",
        "Giá bao nhiêu vậy ạ",
        "Link đâu mình xin",
        "Shop ở đâu vậy",
    ]
    r = score_comments(comments)
    assert len(r.purchase_intent_phrases) == 3
    assert r.purchase_intent_count == 5


def test_purchase_intent_phrase_strips_handles_and_urls() -> None:
    comments = ["@shop.vn giá bao nhiêu https://shopee.vn/foo bạn ơi?"]
    r = score_comments(comments)
    assert r.purchase_intent_phrases
    # @shop.vn and URL stripped from the phrase
    phrase = r.purchase_intent_phrases[0]
    assert "@shop.vn" not in phrase
    assert "https" not in phrase


def test_purchase_intent_english_fallback() -> None:
    r = score_comments(["Where to buy this please?", "How much is it??"])
    assert r.purchase_intent_count == 2


# ── Sentiment buckets ──────────────────────────────────────────────────────


def test_positive_comments_drive_positive_bucket() -> None:
    r = score_comments(["Hay quá chị ơi!", "Thích quá", "Đỉnh vl", "Chất lượng xịn"])
    assert r.positive_pct > 70


def test_negative_comments_drive_negative_bucket() -> None:
    r = score_comments([
        "Cái này lừa đảo rồi",
        "Không tin nổi",
        "Phí thời gian xem",
        "Nhảm quá",
    ])
    assert r.negative_pct > 70


def test_neutral_on_unmatched_text() -> None:
    r = score_comments([
        "Video dài 30 giây",
        "Xem xong rồi",
        "Watched this yesterday",
    ])
    assert r.neutral_pct > 50


def test_purchase_intent_counts_as_positive() -> None:
    r = score_comments(["Tôi sẽ mua ngay", "Link đâu vậy?"])
    assert r.positive_pct >= 50


def test_mixed_positive_and_negative_goes_neutral() -> None:
    r = score_comments(["Đẹp quá nhưng lừa đảo"])
    assert r.neutral_pct == 100.0


def test_emoji_signals_counted() -> None:
    # Not pure-emoji spam — has text too.
    r = score_comments(["Chị ơi xịn quá ❤️🔥", "Tệ lắm 👎"])
    assert r.positive_pct > 0
    assert r.negative_pct > 0


# ── Questions asked ────────────────────────────────────────────────────────


def test_questions_counted_via_question_mark() -> None:
    r = score_comments([
        "Mình dùng thấy ổn",
        "Dùng cho da dầu được không?",
        "Giá bao nhiêu?",
    ])
    assert r.questions_asked == 2


def test_questions_counted_via_keywords() -> None:
    # "giá" / "link" / "ở đâu" without a literal "?"
    r = score_comments(["giá bao nhiêu ạ", "link đâu ad ơi"])
    assert r.questions_asked >= 2


# ── Language detection ─────────────────────────────────────────────────────


def test_language_vi_when_most_vietnamese() -> None:
    r = score_comments([
        "Chị làm video hay quá",
        "Sản phẩm xịn",
        "Hữu ích ghê",
        "Cảm ơn chị nhiều",
    ])
    assert r.language == "vi"


def test_language_non_vi_when_mostly_english() -> None:
    r = score_comments([
        "Love this content",
        "Amazing work",
        "Where to buy this?",
    ])
    assert r.language == "non-vi"


def test_language_mixed_when_balanced() -> None:
    r = score_comments([
        "Chị ơi link đâu?",
        "Love this",
        "Where to buy?",
        "Xịn quá",
    ])
    assert r.language == "mixed"


# ── Sample cap ─────────────────────────────────────────────────────────────


def test_sample_cap_respected() -> None:
    comments = [f"Hay quá {i}" for i in range(100)]
    r = score_comments(comments, sample_cap=20)
    assert r.sampled <= 20


def test_total_available_preserved_when_capped() -> None:
    comments = [f"Hay quá {i}" for i in range(100)]
    r = score_comments(comments, sample_cap=20, total_available=100)
    assert r.total_available == 100


# ── Radar shape (for frontend contract) ───────────────────────────────────


def test_asdict_shape_matches_spec() -> None:
    r = score_comments(["Tôi sẽ mua ngay!", "Giá bao nhiêu?", "Hay quá"])
    d = r.asdict()
    assert set(d.keys()) == {
        "sampled", "total_available", "sentiment", "purchase_intent",
        "questions_asked", "language",
    }
    assert set(d["sentiment"].keys()) == {"positive_pct", "negative_pct", "neutral_pct"}
    assert set(d["purchase_intent"].keys()) == {"count", "top_phrases"}


def test_percentages_sum_to_100_when_sampled() -> None:
    r = score_comments([
        "Hay quá", "Không thích", "Bình thường", "Tôi sẽ mua", "Video này nhảm",
    ])
    total = r.positive_pct + r.negative_pct + r.neutral_pct
    assert 99.0 <= total <= 101.0  # allow for rounding

