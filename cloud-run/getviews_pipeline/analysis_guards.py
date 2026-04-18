"""Post-extraction + post-synthesis trust guards.

Four helpers — pure, fail-soft — that close the P0/P1 risks surfaced in the
video-frame-analysis audit:

    validate_transcript(text)                          — catches Gemini Vietnamese
                                                          gibberish before it reaches
                                                          the diagnosis payload.
    clamp_timestamp(t, duration)                       — nulls out-of-range timestamps
                                                          returned by the extractor.
    is_cached_analysis_fresh(indexed_at, ttl_days=14)  — flags corpus cache rows past
                                                          their trust window.
    scan_synthesis_for_fabricated_metrics(text)        — flags (doesn't block) synthesis
                                                          passages that cite metrics
                                                          without a corpus anchor.

All four are unit-tested without a live API. Wiring lives in
analysis_core._finish_analysis, corpus_context.get_cached_analysis, and
gemini.synthesize_diagnosis_v2 — each call site is defensive: a None / ok-false
return degrades to a disclaimer, never an exception.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Transcript validation
# ---------------------------------------------------------------------------

# Characters with Vietnamese diacritic combining marks.
# NFKD decomposes "à" → "a" + U+0300 (combining grave); we scan for any
# combining diacritic in the string to count Vietnamese-flavoured characters.
_VI_DIACRITIC_CHARS: frozenset[int] = frozenset(
    range(0x0300, 0x036F + 1)   # Latin-1 combining diacritical marks
)
# Vietnamese-specific precomposed letters NFKD doesn't decompose (đ, Đ).
_VI_SPECIAL_LETTERS: frozenset[str] = frozenset("đĐ")

_UNCLEAR_MARKER_RE = re.compile(r"\[(?:không\s*rõ|unclear|inaudible)\]", re.IGNORECASE)
_PLACEHOLDER_RE = re.compile(r"^\s*\[?\s*(?:transcription|transcript|không rõ)\s*\]?\s*\.?\s*$", re.IGNORECASE)

# Minimum length before we even try to judge quality — shorter than this and we
# assume it's a true short clip with minimal speech.
_MIN_TRANSCRIPT_LEN = 40


@dataclass(frozen=True)
class TranscriptVerdict:
    ok: bool
    reason: str            # "ok" | "too_short" | "no_vietnamese" | "placeholder_only" | "mostly_noise"
    vi_ratio: float        # share of char positions marked as Vietnamese
    ascii_ratio: float     # share of ASCII letters — high suggests English rendering

    def asdict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "vi_ratio": round(self.vi_ratio, 3),
            "ascii_ratio": round(self.ascii_ratio, 3),
        }


def _vietnamese_char_count(s: str) -> int:
    """Count characters that carry Vietnamese-style diacritics or are đ/Đ."""
    if not s:
        return 0
    nfkd = unicodedata.normalize("NFKD", s)
    count = 0
    for c in nfkd:
        if ord(c) in _VI_DIACRITIC_CHARS:
            count += 1
    for c in s:
        if c in _VI_SPECIAL_LETTERS:
            count += 1
    return count


def validate_transcript(
    text: str,
    *,
    min_vi_ratio: float = 0.02,
) -> TranscriptVerdict:
    """Return a verdict on whether `text` looks like a real Vietnamese transcript.

    Heuristic ladder (cheap + fail-soft):

      1. Empty / whitespace-only          → reason="too_short"
      2. Placeholder markers only         → reason="placeholder_only"
      3. Short string (< 40 chars)        → reason="too_short" (permissive ok)
      4. Vietnamese diacritic ratio below `min_vi_ratio` → reason="no_vietnamese"
      5. Mostly symbols / numbers / punctuation → reason="mostly_noise"
      6. Otherwise                         → ok=True, reason="ok"

    The default min_vi_ratio of 0.02 means at least ~1 diacritic per 50 chars —
    a one-sentence Vietnamese transcript clears this handily, while an English
    translation ("This is a review of...") does not.

    Returns verdict even for `ok=False` so the caller can surface the reason
    in the diagnosis disclaimer rather than silently swapping in gibberish.
    """
    s = (text or "").strip()

    if not s:
        return TranscriptVerdict(ok=True, reason="too_short", vi_ratio=0.0, ascii_ratio=0.0)

    # Placeholder-only — Gemini fell through to the "[không rõ]" marker for
    # every token. Not gibberish, but not usable either.
    if _PLACEHOLDER_RE.fullmatch(s):
        return TranscriptVerdict(
            ok=False, reason="placeholder_only", vi_ratio=0.0, ascii_ratio=0.0,
        )

    total_letters = sum(1 for c in s if c.isalpha())

    # Noise check runs FIRST — a long string that's mostly punctuation and
    # digits should be rejected regardless of letter count.
    # Strip the "[không rõ]" marker first — legitimate transcripts with a few
    # unclear moments shouldn't fail on punctuation density.
    stripped = _UNCLEAR_MARKER_RE.sub("", s).strip()
    if len(stripped) >= _MIN_TRANSCRIPT_LEN:
        non_alpha_non_space = sum(
            1 for c in stripped if not c.isalpha() and not c.isspace()
        )
        noise_ratio = non_alpha_non_space / max(len(stripped), 1)
        if noise_ratio > 0.5 or total_letters < 10:
            return TranscriptVerdict(
                ok=False, reason="mostly_noise",
                vi_ratio=0.0,
                ascii_ratio=sum(1 for c in s if c.isascii() and c.isalpha()) / max(total_letters, 1),
            )

    if total_letters < _MIN_TRANSCRIPT_LEN:
        # Short clip — accept without scoring. A true 4-second product cutaway
        # may transcribe to 2 words.
        return TranscriptVerdict(
            ok=True, reason="too_short",
            vi_ratio=0.0,
            ascii_ratio=sum(1 for c in s if c.isascii() and c.isalpha()) / max(total_letters, 1),
        )

    vi_count = _vietnamese_char_count(s)
    vi_ratio = vi_count / total_letters
    ascii_letters = sum(1 for c in s if c.isascii() and c.isalpha())
    ascii_ratio = ascii_letters / total_letters

    if vi_ratio < min_vi_ratio:
        return TranscriptVerdict(
            ok=False, reason="no_vietnamese", vi_ratio=vi_ratio, ascii_ratio=ascii_ratio,
        )

    return TranscriptVerdict(ok=True, reason="ok", vi_ratio=vi_ratio, ascii_ratio=ascii_ratio)


TRANSCRIPT_UNAVAILABLE_MARKER = "[Transcript không khả dụng — Gemini không nhận diện được tiếng Việt]"


# ---------------------------------------------------------------------------
# Timestamp clamping
# ---------------------------------------------------------------------------


def clamp_timestamp(t: float | None, duration: float | None) -> float | None:
    """Null out-of-range or non-finite timestamps; otherwise return t unchanged.

    Rules:
      - t is None                              → None
      - duration is None or <= 0               → return t unchanged (cannot validate)
      - t not a number / NaN / Inf             → None
      - t < 0                                  → None
      - t > duration + 0.5s slack              → None

    The 0.5s slack accommodates Gemini's occasional one-frame overshoot on
    short clips. Values slightly past duration are clamped to duration instead
    of nulled — this preserves "happens right at the end" signals.
    """
    if t is None or duration is None:
        return t
    try:
        tf = float(t)
        d = float(duration)
    except (TypeError, ValueError):
        return None
    if tf != tf:  # NaN
        return None
    if tf == float("inf") or tf == float("-inf"):
        return None
    if d <= 0:
        return tf
    if tf < 0:
        return None
    if tf > d + 0.5:
        return None
    if tf > d:
        return d
    return tf


def clamp_scene_range(
    start: float | None, end: float | None, duration: float | None,
) -> tuple[float | None, float | None]:
    """Clamp a scene's [start, end] against the video duration."""
    cs = clamp_timestamp(start, duration)
    ce = clamp_timestamp(end, duration)
    if cs is not None and ce is not None and cs > ce:
        # Inverted range → drop the scene rather than silently flip it.
        return None, None
    return cs, ce


def apply_timestamp_guards(analysis: dict[str, Any], duration: float | None) -> dict[str, Any]:
    """Mutate an analysis dict in place with validated timestamps.

    Touches: hook_analysis.face_appears_at, hook_analysis.first_speech_at,
    hook_analysis.hook_timeline[].t, text_overlays[].appears_at,
    scenes[].start/end, key_timestamps[].

    Returns the same dict for chaining.
    """
    if not isinstance(analysis, dict) or not analysis:
        return analysis

    ha = analysis.get("hook_analysis")
    if isinstance(ha, dict):
        ha["face_appears_at"] = clamp_timestamp(ha.get("face_appears_at"), duration)
        ha["first_speech_at"] = clamp_timestamp(ha.get("first_speech_at"), duration)
        timeline = ha.get("hook_timeline")
        if isinstance(timeline, list):
            cleaned: list[dict[str, Any]] = []
            for ev in timeline:
                if not isinstance(ev, dict):
                    continue
                t = clamp_timestamp(ev.get("t"), duration)
                if t is None:
                    continue
                cleaned.append({**ev, "t": t})
            ha["hook_timeline"] = cleaned

    overlays = analysis.get("text_overlays")
    if isinstance(overlays, list):
        cleaned_overlays: list[dict[str, Any]] = []
        for ov in overlays:
            if not isinstance(ov, dict):
                continue
            at = clamp_timestamp(ov.get("appears_at"), duration)
            if at is None:
                continue
            cleaned_overlays.append({**ov, "appears_at": at})
        analysis["text_overlays"] = cleaned_overlays

    scenes = analysis.get("scenes")
    if isinstance(scenes, list):
        cleaned_scenes: list[dict[str, Any]] = []
        for sc in scenes:
            if not isinstance(sc, dict):
                continue
            cs, ce = clamp_scene_range(sc.get("start"), sc.get("end"), duration)
            if cs is None or ce is None:
                continue
            cleaned_scenes.append({**sc, "start": cs, "end": ce})
        analysis["scenes"] = cleaned_scenes

    kt = analysis.get("key_timestamps")
    if isinstance(kt, list):
        clamped_kt: list[float] = []
        for v in kt:
            c = clamp_timestamp(v, duration)
            if c is not None:
                clamped_kt.append(c)
        analysis["key_timestamps"] = clamped_kt

    return analysis


# ---------------------------------------------------------------------------
# Corpus cache staleness
# ---------------------------------------------------------------------------


def is_cached_analysis_fresh(
    indexed_at: str | datetime | None,
    *,
    ttl_days: int = 14,
    now: datetime | None = None,
) -> bool:
    """Return True if an analysis row is within the trust window.

    Accepts ISO-8601 string (what Supabase returns) or datetime directly.
    Returns True on parse failure so a malformed timestamp doesn't unnecessarily
    kick a cache hit.
    """
    if indexed_at is None:
        return False
    if isinstance(indexed_at, datetime):
        dt = indexed_at
    else:
        try:
            dt = datetime.fromisoformat(str(indexed_at).replace("Z", "+00:00"))
        except ValueError:
            logger.warning("[analysis_guards] unparseable indexed_at=%r — treating as fresh", indexed_at)
            return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    current = now or datetime.now(tz=timezone.utc)
    age = current - dt
    return age <= timedelta(days=ttl_days)


# ---------------------------------------------------------------------------
# Fabricated-metrics scan on synthesis output
# ---------------------------------------------------------------------------

# Regex triggers — words that introduce a prediction or estimate plus a nearby
# numeric figure. If the same sentence lacks a corpus citation, we flag it.
_PREDICTION_WORDS = (
    r"dự\s*kiến",
    r"kỳ\s*vọng",
    r"dự\s*đoán",
    r"ước\s*tính",
    r"được\s*dự\s*đoán",
    r"predicted?",
    r"expected",
    r"forecast(?:ed)?",
    r"estimate[sd]?",
)
_PREDICTION_RE = re.compile(
    r"(?:" + r"|".join(_PREDICTION_WORDS) + r")[^.!?\n]*?\d+",
    re.IGNORECASE,
)
# Corpus anchor — a sentence that contains one of these clauses is trusted
# because the data source is explicit.
_ANCHOR_RE = re.compile(
    r"(dựa\s*trên|theo\s*(corpus|dữ\s*liệu)|từ\s*\d+\s*video|corpus\s*có)",
    re.IGNORECASE,
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?\n])\s+")


@dataclass(frozen=True)
class FabricatedMetricsScan:
    flags: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not self.flags

    def asdict(self) -> dict[str, Any]:
        return {"clean": self.clean, "flags": list(self.flags)}


def scan_synthesis_for_fabricated_metrics(text: str) -> FabricatedMetricsScan:
    """Flag sentences that predict metrics without a corpus anchor.

    Does NOT block — callers log the flags and optionally append a disclaimer.
    Better to ship a slightly verbose response than to silently drop signal.
    Confusion between "predicted number with anchor" vs "invented number" is
    the specific failure mode we're guarding against.
    """
    if not text or not text.strip():
        return FabricatedMetricsScan(flags=())

    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    flags: list[str] = []
    for sentence in sentences:
        if not _PREDICTION_RE.search(sentence):
            continue
        if _ANCHOR_RE.search(sentence):
            continue  # anchored prediction — trusted
        # Truncate long sentences so logs stay readable.
        flags.append(sentence[:200])
    return FabricatedMetricsScan(flags=tuple(flags))


__all__ = [
    "FabricatedMetricsScan",
    "TRANSCRIPT_UNAVAILABLE_MARKER",
    "TranscriptVerdict",
    "apply_timestamp_guards",
    "clamp_scene_range",
    "clamp_timestamp",
    "is_cached_analysis_fresh",
    "scan_synthesis_for_fabricated_metrics",
    "validate_transcript",
]
