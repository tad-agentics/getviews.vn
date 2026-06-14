"""Vietnamese copy linter — enforces the copy-rules.mdc forbidden list.

Wave 3 PR #3 — "diagnosis-copy-tightening". The ``.cursor/rules/copy-rules.mdc``
file defines forbidden openers + forbidden words, but it was only a human-
facing doc; Gemini prompts individually maintained inconsistent partial
copies of the list, and nobody checked FE UI literals against it.

This module is the single source of truth, importable both:

  * at test time — to assert prompt assemblies, few-shot examples, and
    FE UI strings never ship a forbidden phrase.
  * at runtime (future) — to flag Gemini outputs post-hoc for voice drift
    without re-parsing the whole synthesis text.

Pure function; no DB, no LLM, no IO. Case-insensitive matching against
Vietnamese diacritics via ``str.casefold()``. Word-boundary-aware so
that ``"bùng"`` by itself doesn't match ``"bùng nổ"`` (and vice versa
— ``"bùng nổ"`` must land as a phrase, not a bigram).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

# Mirrors .cursor/rules/copy-rules.mdc — keep in sync. When adding here,
# also update the doc. The order matters only for deterministic test
# output; matching is unordered.
FORBIDDEN_OPENERS: tuple[str, ...] = (
    "Chào bạn",
    "Xin chào",
    "Rất vui",
    "Tuyệt vời",
    "Wow",
    "Chúc mừng",
    "Đây là",
    "Dưới đây là",
)

FORBIDDEN_WORDS: tuple[str, ...] = (
    "tuyệt vời",
    "hoàn hảo",
    "bí mật",
    "công thức vàng",
    "đột phá",
    "kỷ lục",
    "triệu view",
    "bùng nổ",
    "siêu hot",
    "thần thánh",
    "hack",
    "chiến lược độc quyền",
    "ai cũng phải biết",
    "không thể bỏ qua",
    "chắc chắn thành công",
)

# Extra hook / guru clichés for Gemini prompts only — not wired into
# ``lint_forbidden_copy`` (FE copy-rules.mdc is narrower). Keep in sync with
# historical extraction + channel-diagnosis prompt steering.
FORBIDDEN_PROMPT_EXTRAS: tuple[str, ...] = (
    "tính năng ẩn",
    "bí mật không ai nói",
    "sự thật shock",
    "chỉ 1%",
    "hack não",
    "đừng bỏ qua",
    "xem ngay kẻo muộn",
    "chấn động",
    "viral chóng mặt",
    "nội dung chất lượng",
    "empties haul",
    "jump-cut",
    "archetype",
    "corpus",
    "dead air",
    "heatmap",
    "p75",
    "p25",
    "p50",
    "p90",
    "median",
    "trung vị",
)


def build_forbidden_phrases_prompt_block(
    *,
    include_prompt_extras: bool = True,
    heading: str = "## Copy-rules — cấm mở đầu và từ ngữ",
) -> str:
    """Return a Vietnamese block to paste into Gemini system/user prompts.

    Single injectable surface for HI-10 — built from ``FORBIDDEN_*`` +
    optional ``FORBIDDEN_PROMPT_EXTRAS``.
    """
    opener_q = ", ".join(f"\"{o}\"" for o in FORBIDDEN_OPENERS)
    words_seq: tuple[str, ...] = (
        FORBIDDEN_WORDS + FORBIDDEN_PROMPT_EXTRAS
        if include_prompt_extras
        else FORBIDDEN_WORDS
    )
    word_q = ", ".join(f"\"{w}\"" for w in words_seq)
    return (
        f"{heading}\n\n"
        f"- **Không mở đầu bất kỳ đoạn nào bằng:** {opener_q}\n"
        f"- **Không dùng trong toàn bộ output:** {word_q}\n"
    )


@dataclass(frozen=True)
class CopyViolation:
    """One violation surfaced by the linter.

    ``kind`` is ``"opener"`` or ``"word"``. ``match`` is the offending
    phrase as it appears in the original text (with original casing),
    ``start`` is the character index into the input. Tests assert on
    ``kind + normalized_phrase`` — the position is diagnostic only.
    """
    kind: str
    phrase: str   # canonical phrase from FORBIDDEN_* (lowercase)
    match: str    # verbatim slice from the input
    start: int


def _casefold_strip(s: str) -> str:
    """Casefold + NFC-normalize for stable Vietnamese diacritic matching.

    Without NFC, composed vs decomposed diacritics (e.g. ``ằ`` as ``à + `` vs
    a single codepoint) would miss. ``str.casefold()`` handles the
    uppercase/lowercase dimension including Turkish-I edge cases.
    """
    return unicodedata.normalize("NFC", s).casefold()


def _first_non_space(text: str) -> int:
    """Index of the first non-whitespace character, or -1 if empty."""
    for i, ch in enumerate(text):
        if not ch.isspace():
            return i
    return -1


def lint_forbidden_copy(text: str) -> list[CopyViolation]:
    """Return all forbidden-opener + forbidden-word hits in ``text``.

    ``text`` is treated as a single block — paragraphs separated by
    blank lines are each checked for forbidden openers independently
    so a mid-response "Wow, …" also flags. Word checks are block-wide.

    Matching rules:

    * Openers match case-insensitively at the first non-whitespace
      character of each paragraph (paragraph = split on two+ newlines).
    * Words match case-insensitively anywhere, with a loose word-boundary
      — the phrase must not be preceded or followed by a letter/digit
      so ``"hackathon"`` doesn't trigger ``"hack"`` and ``"tuyệt vời
      nhất"`` does trigger ``"tuyệt vời"``.
    """
    violations: list[CopyViolation] = []
    folded = _casefold_strip(text)

    # ── Openers ─────────────────────────────────────────────────────
    # Split on 2+ newlines — paragraph boundaries. A forbidden opener
    # in the 3rd paragraph is still a forbidden opener.
    cursor = 0
    for paragraph in re.split(r"\n{2,}", text):
        p_offset = cursor
        cursor += len(paragraph) + 2  # approx — we only need relative order
        stripped_start = _first_non_space(paragraph)
        if stripped_start < 0:
            continue
        head = paragraph[stripped_start : stripped_start + 40]
        head_fold = _casefold_strip(head)
        for phrase in FORBIDDEN_OPENERS:
            pf = _casefold_strip(phrase)
            if head_fold.startswith(pf):
                # Lift the matched slice back to the original-case text.
                match = paragraph[stripped_start : stripped_start + len(phrase)]
                violations.append(CopyViolation(
                    kind="opener",
                    phrase=pf,
                    match=match,
                    start=p_offset + stripped_start,
                ))
                break  # one opener violation per paragraph is enough

    # ── Forbidden words / phrases ──────────────────────────────────
    # Loose word-boundary that ALSO works for Vietnamese diacritics —
    # we can't rely on \b because Python's default \b treats diacritics
    # as word chars but some markers (apostrophes, quotes, punctuation)
    # are fine. We emulate by checking the surrounding codepoints.
    for phrase in FORBIDDEN_WORDS:
        pf = _casefold_strip(phrase)
        for m in re.finditer(re.escape(pf), folded):
            a, b = m.start(), m.end()
            before = folded[a - 1] if a > 0 else " "
            after = folded[b] if b < len(folded) else " "
            if _is_word_char(before) or _is_word_char(after):
                continue
            violations.append(CopyViolation(
                kind="word",
                phrase=pf,
                match=text[a:b],
                start=a,
            ))

    violations.sort(key=lambda v: v.start)
    return violations


def _is_word_char(ch: str) -> bool:
    """True for ASCII letter/digit + any Vietnamese-diacritic letter.

    Anything in Unicode category ``L*`` (letter) or ``N*`` (number) counts;
    whitespace, punctuation, and control chars don't.
    """
    if not ch:
        return False
    cat = unicodedata.category(ch)
    return cat[0] in ("L", "N")


# Soft replacements for runtime scrub (words only — openers need rewrite).
_SOFT_SCRUB_WORDS: dict[str, str] = {
    "bùng nổ": "tăng mạnh",
    "công thức vàng": "cách làm",
    "triệu view": "view cao",
    "bí mật": "điểm khác",
    "tuyệt vời": "ổn",
    "hoàn hảo": "đủ dùng",
    "đột phá": "khác biệt",
    "siêu hot": "đang chạy",
    "thần thánh": "hiệu quả",
    "hack": "mẹo",
    "chiến lược độc quyền": "cách riêng",
    "ai cũng phải biết": "nên thử",
    "không thể bỏ qua": "đáng chú ý",
    "chắc chắn thành công": "có cơ hội",
}


def scrub_forbidden_copy(text: str) -> tuple[str, list[CopyViolation]]:
    """Return ``text`` with forbidden *words* soft-scrubbed; openers are logged only."""
    violations = lint_forbidden_copy(text)
    if not violations:
        return text, []
    out = text
    for phrase, replacement in _SOFT_SCRUB_WORDS.items():
        pf = _casefold_strip(phrase)
        while True:
            m = re.search(re.escape(pf), _casefold_strip(out))
            if not m:
                break
            a, b = m.start(), m.end()
            out = out[:a] + replacement + out[b:]
    return out, violations


def scrub_vi_strings_in_obj(obj: Any, *, path: str = "") -> tuple[Any, int]:
    """Walk dict/list; scrub string values whose key ends with ``_vi``."""
    hits = 0
    if isinstance(obj, str):
        if path.endswith("_vi") or path.endswith("_vi]"):
            cleaned, v = scrub_forbidden_copy(obj)
            if v:
                hits += len(v)
            return cleaned, hits
        return obj, hits
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            child_path = f"{path}.{k}" if path else k
            cleaned, n = scrub_vi_strings_in_obj(v, path=child_path)
            out[k] = cleaned
            hits += n
        return out, hits
    if isinstance(obj, list):
        items: list[Any] = []
        for i, v in enumerate(obj):
            cleaned, n = scrub_vi_strings_in_obj(v, path=f"{path}[{i}]")
            items.append(cleaned)
            hits += n
        return items, hits
    return obj, hits


def assert_copy_clean(text: str, *, label: str = "copy") -> None:
    """Raise ``AssertionError`` listing every violation — used by tests.

    Kept separate from ``lint_forbidden_copy`` so the latter is useful
    at runtime without pulling in pytest semantics.
    """
    violations = lint_forbidden_copy(text)
    if not violations:
        return
    lines = [f"{label} violates copy-rules.mdc:"]
    for v in violations:
        lines.append(f"  [{v.kind}] {v.phrase!r} at {v.start} — {v.match!r}")
    raise AssertionError("\n".join(lines))
