"""Wave 2.5 Phase B PR #5 — per-shot reference-video matcher.

``pick_shot_references(shot_descriptor, niche_id, hook_type, …)`` returns the
top-K ``video_shots`` rows that best match a described script shot, with a
human-readable match_signal chip ("Cùng ngách, hook, khung hình"). The
``/script/generate`` path (Phase B PR #6) calls this once per shot so the
frontend (Phase B PR #7) can render 1–3 reference cards per shot — users
see a real creator scene that matches what they're about to shoot.

Inputs live at the ``video_shots`` column abstraction, on purpose:

    shot_descriptor = {
        "framing":       "close_up" | None,
        "pace":          "slow" | None,
        "overlay_style": "bold_center" | None,
        "subject":       "face" | None,
        "motion":        "static" | None,
        "scene_type":    "face_to_camera" | None,   # legacy 4-value fallback
    }

PR #6 will translate ScriptShotLLM (``intel_scene_type`` / ``overlay`` / etc.)
into this shape. Keeping the matcher unaware of the ScriptShotLLM schema lets
us reuse it from admin previews and eval harnesses too.

Scoring — additive, niche_id is a hard filter:

    niche_id match   (filter — no score; mismatches return [] early)
    hook_type match  +40 (when both sides non-null)
    hook_type MISMATCH −25 (both non-null and different — a gossip-reveal
                     scene must not anchor a warning script)
    topic overlap    +20 (≥1 strong shared token between the script topic
                     and the candidate video's caption/subject_matter),
                     +28 when ≥2 tokens overlap. Quality audit 2026-06-11:
                     without this, a skincare-warning script matched a
                     makeup-transformation and a gossip channel on pure
                     camera mechanics, labeled "Cùng ngách".
    framing match    +15
    pace match       +15
    overlay_style    +10
    subject match    +10
    motion match     +5
    scene_type       +10 only when framing is NULL on BOTH sides (pre-PR #2
                     legacy rows fall through to the coarse dimension)

``min_score`` defaults to 25 — at least two real dimensions beyond niche
(raised from 15 in the 2026-06-11 quality pass: a bad reference costs more
trust than no reference). ``limit`` defaults to 3 — creators want the best
few, not a list.

Label honesty: the "Cùng ngách" chip is only emitted when the TOPIC also
matched — a same-niche-id row matched purely on camera mechanics now reads
"Cùng nhịp, khung hình" instead of claiming subject affinity it doesn't have.

Tiebreaker when scores equal:
    has frame_url > has thumbnail_url > lexical video_id (stable)

No embeddings, no Gemini calls — pure Python scoring over a SQL result plus
one batched video_corpus lookup for topic text. Fast enough at the 10K+
corpus target: ~1K rows per niche × 6 shots per script ≈ <40ms per call.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from getviews_pipeline.r2 import r2_public_video_url

logger = logging.getLogger(__name__)

# ── Scoring weights ─────────────────────────────────────────────────

_WEIGHT_HOOK_TYPE = 40
_PENALTY_HOOK_MISMATCH = -25
_WEIGHT_TOPIC = 20
_WEIGHT_TOPIC_STRONG = 28
_WEIGHT_FRAMING = 15
_WEIGHT_PACE = 15
_WEIGHT_OVERLAY = 10
_WEIGHT_SUBJECT = 10
_WEIGHT_MOTION = 5
_WEIGHT_SCENE_TYPE_FALLBACK = 10

_DEFAULT_MIN_SCORE = 25
_DEFAULT_LIMIT = 3
_MAX_CANDIDATES_PER_NICHE = 1000
# Cap the video_corpus topic-text lookup to the strongest mechanics
# candidates so the extra query stays one IN(...) of bounded size.
_MAX_TOPIC_LOOKUP_VIDEOS = 40

# Vietnamese labels for the match_signal chip. Shown to the creator as
# the "why this reference" caption under each reference card.
_VN_LABELS: dict[str, str] = {
    "niche": "ngách",
    "topic": "chủ đề",
    "hook": "hook",
    "framing": "khung hình",
    "pace": "nhịp",
    "overlay": "overlay",
    "subject": "chủ thể",
    "motion": "chuyển động",
    "scene_type": "loại cảnh",
}

# Minimal Vietnamese stopword set for topic-token overlap. Deliberately
# small: false negatives (missing a stopword) only cost a slightly
# generous +20; false positives (treating a content word as stopword)
# would silently kill real topic matches.
_TOPIC_STOPWORDS = frozenset({
    "anh", "bạn", "bị", "cách", "cái", "cho", "chưa", "có", "của", "cũng",
    "đã", "đang", "đây", "để", "điều", "đó", "được", "em", "gì", "hay",
    "hơn", "khi", "không", "là", "làm", "lại", "lên", "mà", "mình", "muốn",
    "này", "ngay", "người", "nhé", "như", "nhưng", "những", "nếu", "phải",
    "ra", "rất", "rồi", "sao", "sau", "sẽ", "thì", "trong", "và", "vẫn",
    "việc", "với", "vì", "xem", "the", "and", "for", "you", "với",
})


def _topic_tokens(text: str | None) -> set[str]:
    """Lowercased content tokens (len ≥ 2, stopwords removed) for overlap."""
    if not text:
        return set()
    raw = re.split(r"[^0-9a-zA-ZÀ-ỹ]+", str(text).lower())
    return {t for t in raw if len(t) >= 2 and t not in _TOPIC_STOPWORDS}


@dataclass
class ShotReference:
    """One matched shot, ready for the FE reference card."""

    video_id: str
    scene_index: int
    start_s: float | None
    end_s: float | None
    frame_url: str | None
    thumbnail_url: str | None
    tiktok_url: str | None
    creator_handle: str | None
    description: str | None
    score: int
    # Denormalized from video_corpus.views — drives the "256K view" chip on
    # the FE RefClipCard. NULL when the source row predates the
    # ``20260601000000_video_shots_views`` migration's backfill window.
    # Default None keeps existing kwarg-based test fixtures backward-compat.
    views: int | None = None
    match_signals: list[str] = field(default_factory=list)
    match_label: str = ""
    playback_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _score_shot(
    shot: dict[str, Any],
    descriptor: dict[str, Any],
    hook_type: str | None,
) -> tuple[int, list[str]]:
    """Return ``(score, matched_signal_keys)`` for one shot row.

    ``matched_signal_keys`` is the internal list — callers translate to
    VN via ``_match_label_vn``. ``niche`` is prepended by caller since
    we hard-filter on it.
    """
    score = 0
    matched: list[str] = []

    # hook_type (strongest signal). A MISMATCH when both sides are set is
    # actively penalised — the scene grammar of a different hook intent
    # misleads the creator even when the camera mechanics line up.
    if hook_type and shot.get("hook_type"):
        if hook_type == shot["hook_type"]:
            score += _WEIGHT_HOOK_TYPE
            matched.append("hook")
        else:
            score += _PENALTY_HOOK_MISMATCH

    # Per-dimension exact-match scoring. Only counts when BOTH sides
    # are non-null — a NULL on either side is "unknown", not "no match".
    dims = [
        ("framing", _WEIGHT_FRAMING),
        ("pace", _WEIGHT_PACE),
        ("overlay_style", _WEIGHT_OVERLAY),
        ("subject", _WEIGHT_SUBJECT),
        ("motion", _WEIGHT_MOTION),
    ]
    dim_label_override = {"overlay_style": "overlay"}
    for field_name, weight in dims:
        d_val = descriptor.get(field_name)
        s_val = shot.get(field_name)
        if d_val and s_val and d_val == s_val:
            score += weight
            matched.append(dim_label_override.get(field_name, field_name))

    # Legacy scene_type fallback — only when framing is NULL on both
    # sides. Pre-PR #2 rows have no enrichment, but they do have
    # scene_type from the old 4-value taxonomy, so we can still score
    # the coarse dimension.
    if (
        not descriptor.get("framing")
        and not shot.get("framing")
        and descriptor.get("scene_type")
        and shot.get("scene_type")
        and descriptor["scene_type"] == shot["scene_type"]
    ):
        score += _WEIGHT_SCENE_TYPE_FALLBACK
        matched.append("scene_type")

    return score, matched


def _tiebreaker_key(ref: ShotReference) -> tuple[int, int, str]:
    """Higher-quality first when scores tie.

    frame_url presence > thumbnail presence > stable video_id.
    Negated integers so sort ASC gives the desired order when combined
    with ``-score``.
    """
    return (
        0 if ref.frame_url else 1,
        0 if ref.thumbnail_url else 1,
        ref.video_id,
    )


def _match_label_vn(signals: list[str]) -> str:
    """Build a human-readable VN chip: "Cùng chủ đề, hook, khung hình".

    Label honesty (quality audit 2026-06-11): "ngách" is only shown when
    the topic ALSO matched — a coarse legacy niche_id bucket spans makeup,
    skincare and gossip, so claiming "Cùng ngách" on a mechanics-only match
    overstated subject affinity. Mechanics-only matches now read as what
    they are ("Cùng nhịp, khung hình").
    """
    if not signals:
        return ""
    shown = signals if "topic" in signals else [s for s in signals if s != "niche"]
    if not shown:
        return ""
    parts = [_VN_LABELS.get(s, s) for s in shown]
    return "Cùng " + ", ".join(parts)


def _fetch_topic_texts_sync(
    client: Any, video_ids: list[str],
) -> dict[str, str]:
    """caption + subject_matter per video_id for topic-overlap scoring."""
    if not video_ids:
        return {}
    res = (
        client.table("video_corpus")
        .select("video_id,caption,analysis_json")
        .in_("video_id", video_ids)
        .execute()
    )
    out: dict[str, str] = {}
    for row in res.data or []:
        vid = str(row.get("video_id") or "")
        if not vid:
            continue
        analysis = row.get("analysis_json") if isinstance(row.get("analysis_json"), dict) else {}
        cc = analysis.get("content_context") if isinstance(analysis.get("content_context"), dict) else {}
        subject = str(cc.get("subject_matter") or "")
        caption = str(row.get("caption") or "")
        out[vid] = f"{caption} {subject}".strip()
    return out


def _fetch_niche_shots_sync(
    client: Any,
    niche_id: int,
    descriptor: dict[str, Any],
    hook_type: str | None,
) -> list[dict[str, Any]]:
    """Pull candidate shots from video_shots.

    SQL-side narrowing: we order by ``created_at DESC`` and cap at
    ``_MAX_CANDIDATES_PER_NICHE`` so scoring stays constant-time per
    call even when a niche grows past 2K shots.

    No OR filter on the descriptor — we want legacy-only (scene_type)
    and enriched (framing/pace/etc) shots equally considered, and
    PostgREST OR gets gnarly when half the descriptor values are NULL.
    Python scoring handles the sparse case correctly anyway.
    """
    q = (
        client.table("video_shots")
        .select(
            "video_id,scene_index,start_s,end_s,"
            "scene_type,framing,pace,overlay_style,subject,motion,"
            "hook_type,creator_handle,thumbnail_url,tiktok_url,"
            "frame_url,description,views"
        )
        .eq("niche_id", niche_id)
        .order("created_at", desc=True)
        .limit(_MAX_CANDIDATES_PER_NICHE)
    )
    result = q.execute()
    return list(result.data or [])


def pick_shot_references(
    shot_descriptor: dict[str, Any],
    *,
    niche_id: int,
    hook_type: str | None = None,
    topic_text: str | None = None,
    limit: int = _DEFAULT_LIMIT,
    min_score: int = _DEFAULT_MIN_SCORE,
    exclude_video_ids: set[str] | None = None,
    client: Any,
) -> list[ShotReference]:
    """Return up to ``limit`` ``ShotReference`` dicts matching the descriptor.

    ``niche_id`` is a HARD FILTER — cross-niche references would confuse
    the creator ("this is a cooking reference on my fitness script").

    ``hook_type`` is optional: match is +40, an explicit MISMATCH (both
    sides set, different) is −25. NULL on either side is neutral.

    ``topic_text`` (script topic + hook sentence) drives subject-affinity
    scoring against each candidate video's caption + subject_matter:
    +20 for ≥1 shared content token, +28 for ≥2. Without it, references
    can only match on camera mechanics.

    ``exclude_video_ids`` lets the caller de-dupe across shots within
    one script — if shot 1 surfaces ``v_abc``, shot 2 should show a
    different creator.

    Returns ``[]`` on DB error or empty niche — never raises. An empty
    result is intentional when nothing clears ``min_score``: a
    topic-mismatched reference costs more trust than no reference.
    """
    if not isinstance(niche_id, int):
        return []
    excluded = exclude_video_ids or set()

    try:
        candidates = _fetch_niche_shots_sync(
            client, niche_id, shot_descriptor, hook_type,
        )
    except Exception as exc:
        logger.warning(
            "[shot_ref] fetch failed niche_id=%s: %s", niche_id, exc,
        )
        return []

    # Phase 1 — mechanics score per shot (cheap, in-memory).
    mech: list[tuple[int, list[str], dict[str, Any]]] = []
    for shot in candidates:
        vid = shot.get("video_id")
        if not vid or vid in excluded:
            continue
        m_score, m_matched = _score_shot(shot, shot_descriptor, hook_type)
        mech.append((m_score, m_matched, shot))

    # Phase 2 — topic-overlap bonus for the strongest mechanics candidates.
    # One batched IN(...) lookup; failure degrades to mechanics-only.
    topic_by_vid: dict[str, set[str]] = {}
    want_tokens = _topic_tokens(topic_text)
    if want_tokens and mech:
        mech.sort(key=lambda t: -t[0])
        lookup_ids: list[str] = []
        seen_ids: set[str] = set()
        for _, _, shot in mech:
            vid = str(shot.get("video_id"))
            if vid not in seen_ids:
                seen_ids.add(vid)
                lookup_ids.append(vid)
            if len(lookup_ids) >= _MAX_TOPIC_LOOKUP_VIDEOS:
                break
        try:
            texts = _fetch_topic_texts_sync(client, lookup_ids)
            topic_by_vid = {vid: _topic_tokens(txt) for vid, txt in texts.items()}
        except Exception as exc:
            logger.warning("[shot_ref] topic lookup failed: %s", exc)

    scored: list[ShotReference] = []
    for m_score, m_matched, shot in mech:
        vid = str(shot.get("video_id"))
        score = m_score
        matched = list(m_matched)
        overlap = want_tokens & topic_by_vid.get(vid, set())
        if overlap:
            score += _WEIGHT_TOPIC_STRONG if len(overlap) >= 2 else _WEIGHT_TOPIC
            matched.insert(0, "topic")
        if score < min_score:
            continue
        signals = ["niche", *matched]
        views_raw = shot.get("views")
        try:
            views_val = int(views_raw) if views_raw is not None else None
        except (TypeError, ValueError):
            views_val = None
        scored.append(ShotReference(
            video_id=str(vid),
            scene_index=int(shot.get("scene_index", 0) or 0),
            start_s=shot.get("start_s"),
            end_s=shot.get("end_s"),
            frame_url=shot.get("frame_url"),
            thumbnail_url=shot.get("thumbnail_url"),
            tiktok_url=shot.get("tiktok_url"),
            creator_handle=shot.get("creator_handle"),
            description=shot.get("description"),
            views=views_val,
            score=score,
            match_signals=signals,
            match_label=_match_label_vn(signals),
            playback_url=r2_public_video_url(str(vid)),
        ))

    scored.sort(key=lambda r: (-r.score, _tiebreaker_key(r)))
    return scored[: max(0, int(limit))]
