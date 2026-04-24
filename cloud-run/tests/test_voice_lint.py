"""Wave 3 PR #3 — voice_lint coverage + proof that the shipped voice
assets (example diagnoses) don't themselves leak forbidden copy.

Three test surfaces:

1. ``lint_forbidden_copy`` itself — positive detection on every opener
   + word, negative pass on clean copy, word-boundary edge cases.
2. The canonical few-shot diagnosis outputs (``EXAMPLE_DIAGNOSIS_GOOD``
   + ``EXAMPLE_DIAGNOSIS_WITH_PROBLEMS``) — what we're teaching Gemini
   to produce. These MUST be clean or we're training the model on the
   forbidden voice.
3. Diagnostic FE UI literals (covered via a separate grep-style test
   inside ``DiagnosticBody.test.tsx`` already — this file pins the
   Python-side server-emitted copy only).
"""

from __future__ import annotations

import pytest

from getviews_pipeline.voice_guide import (
    EXAMPLE_DIAGNOSIS_GOOD,
    EXAMPLE_DIAGNOSIS_WITH_PROBLEMS,
)
from getviews_pipeline.voice_lint import (
    FORBIDDEN_OPENERS,
    FORBIDDEN_WORDS,
    CopyViolation,
    assert_copy_clean,
    lint_forbidden_copy,
)

# ── Positive detection — one test per opener / word ────────────────

@pytest.mark.parametrize("opener", FORBIDDEN_OPENERS)
def test_every_forbidden_opener_is_detected(opener: str) -> None:
    text = f"{opener}, video bạn đang chạy 3,2x so với ngách."
    vs = lint_forbidden_copy(text)
    assert any(v.kind == "opener" for v in vs), (
        f"opener {opener!r} slipped through — violations={vs}"
    )


@pytest.mark.parametrize("opener", FORBIDDEN_OPENERS)
def test_opener_case_insensitive(opener: str) -> None:
    """Gemini often emits different casing — UPPERCASE openers, lowercase,
    title case. All must be caught."""
    text = f"{opener.upper()}! video bạn đang chạy 3,2x."
    vs = lint_forbidden_copy(text)
    assert any(v.kind == "opener" for v in vs)


@pytest.mark.parametrize("word", FORBIDDEN_WORDS)
def test_every_forbidden_word_is_detected(word: str) -> None:
    text = f"Video này là {word} của ngách skincare."
    vs = lint_forbidden_copy(text)
    assert any(v.kind == "word" and v.phrase == word.casefold() for v in vs), (
        f"word {word!r} slipped through — violations={vs}"
    )


# ── Negative pass — canonical "peer expert" copy must be clean ─────

def test_clean_peer_voice_passes() -> None:
    text = (
        "Video bạn đang chạy 4,2x so với mức trung bình của ngách - "
        "vượt trội. Hook Cảnh Báo đang là top 1 trong skincare tháng này.\n"
        "Gợi ý: giữ nguyên công thức, Bóc Phốt là hook thứ 2 chưa bão hoà."
    )
    assert lint_forbidden_copy(text) == []


def test_example_diagnosis_good_is_clean() -> None:
    """The few-shot 'good' example is what we show Gemini. Any forbidden
    copy here would train the model to emit forbidden copy."""
    assert_copy_clean(
        EXAMPLE_DIAGNOSIS_GOOD, label="EXAMPLE_DIAGNOSIS_GOOD",
    )


def test_example_diagnosis_with_problems_is_clean() -> None:
    """Same invariant for the 'problems' few-shot."""
    assert_copy_clean(
        EXAMPLE_DIAGNOSIS_WITH_PROBLEMS,
        label="EXAMPLE_DIAGNOSIS_WITH_PROBLEMS",
    )


# ── Word-boundary edge cases ───────────────────────────────────────

def test_hack_does_not_trigger_on_hackathon() -> None:
    """``hack`` is forbidden but must respect word boundaries.
    ``hackathon`` is a legitimate English loan-word creators use."""
    text = "Tuần này hackathon của team creator chạy tốt."
    assert lint_forbidden_copy(text) == []


def test_hack_standalone_flagged() -> None:
    text = "Đây là hack bạn nên thử ngay."
    vs = lint_forbidden_copy(text)
    # Also catches the "Đây là" opener — we only care that hack hits.
    assert any(v.kind == "word" and v.phrase == "hack" for v in vs)


def test_breakout_phrase_not_flagged() -> None:
    """``vượt trội`` is the sanctioned replacement for ``bùng nổ``."""
    text = "Video vượt trội 3,2x so với mức trung bình của ngách."
    assert lint_forbidden_copy(text) == []


def test_bung_no_space_not_flagged() -> None:
    """``bùng`` alone isn't the phrase — only the two-word ``bùng nổ`` is."""
    text = "Âm thanh bùng to bất ngờ ở giây thứ 3."
    assert lint_forbidden_copy(text) == []


def test_bung_no_phrase_is_flagged() -> None:
    text = "Video bùng nổ 10 triệu view sau 2 ngày."
    vs = lint_forbidden_copy(text)
    assert any(v.phrase == "bùng nổ" for v in vs)
    # Also catches "triệu view"
    assert any(v.phrase == "triệu view" for v in vs)


def test_opener_only_flagged_at_paragraph_start() -> None:
    """Mid-sentence "Wow" is suspicious but not a forbidden opener.
    Only paragraph-leading matches count as openers."""
    text = "Hook chạy tốt. Wow factor ở giây 3 kéo watch time rất tốt."
    vs = lint_forbidden_copy(text)
    # "Wow" mid-sentence → no opener violation (it's not at a paragraph head).
    assert not any(v.kind == "opener" for v in vs)


def test_opener_flagged_on_subsequent_paragraphs() -> None:
    text = (
        "Video bạn chạy 3,2x ngách skincare.\n"
        "\n"
        "Chào bạn! Dưới đây là phân tích chi tiết."
    )
    vs = lint_forbidden_copy(text)
    # Both "Chào bạn" at paragraph 2 start + "Dưới đây là" after it —
    # the implementation reports one opener per paragraph, so only one
    # opener violation. But the paragraph-1 "Video bạn…" line is clean.
    openers = [v for v in vs if v.kind == "opener"]
    assert len(openers) >= 1
    assert openers[0].phrase == _case_fold("Chào bạn")


# ── assert_copy_clean raising ─────────────────────────────────────

def test_assert_copy_clean_raises_with_label() -> None:
    with pytest.raises(AssertionError) as exc:
        assert_copy_clean("Đây là bí mật của ngách.", label="unit")
    msg = str(exc.value)
    assert "unit violates copy-rules.mdc" in msg
    assert "'bí mật'" in msg


def test_assert_copy_clean_silent_on_clean_text() -> None:
    # No exception = pass.
    assert_copy_clean("Video chạy 3,2x so với mức trung bình ngách.")


# ── CopyViolation dataclass shape ─────────────────────────────────

def test_violation_start_index_lands_inside_original_text() -> None:
    text = "Video này tuyệt vời lắm nhé."
    vs = lint_forbidden_copy(text)
    v = vs[0]
    # Start index must point at the matched slice in original casing.
    assert text[v.start : v.start + len(v.match)] == v.match
    assert isinstance(v, CopyViolation)


# ── Helpers ────────────────────────────────────────────────────────

def _case_fold(s: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFC", s).casefold()
