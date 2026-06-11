"""B.4 — POST ``/script/generate``: credit gate + Gemini-bounded shot scaffold.

**D.1.2** upgrade: the deterministic template backbone is now a fallback —
the happy path calls Gemini with a pydantic-bound response schema so
shots carry topic-tailored Vietnamese copy instead of generic placeholder
text.

**Wave 2.5 Phase B PR #6** upgrade: each shot is now paired with up to
3 ``references`` — real creator scenes from ``video_shots`` matched by
``pick_shot_references`` on (niche_id, hook_type, framing, pace, …).
HTTP contract ADDS ``references: [...]`` per shot; existing fields
unchanged so FE clients that don't know about references ignore the
new key cleanly.

Fields Gemini owns (creative):
    cam, voice, viz, overlay, intel_scene_type, overlay_winner,
    framing, pace, overlay_style, subject, motion  (Optional — PR #6)

Fields we own (deterministic — never hallucinated):
    t0, t1          — from _segment_lengths(duration)
    corpus_avg      — positional defaults from _BACKBONE
    winner_avg      — positional defaults from _BACKBONE
    references      — pick_shot_references() against video_shots

On any Gemini error the full deterministic path runs — the response is
still valid, just generic. Client continues to merge
``scene_intelligence`` for corpus/winner bars and tips. Reference
lookup runs even on the fallback path — the positional backbone knows
the canonical framing/pace/overlay_style for each of the 6 shots, so
matcher has a non-empty descriptor either way.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from getviews_pipeline.models import (
    FramingType,
    MotionType,
    OverlayStyleType,
    PaceType,
    SubjectType,
)

logger = logging.getLogger(__name__)

ScriptTone = Literal["Hài", "Chuyên gia", "Tâm sự", "Năng lượng", "Mỉa mai"]

OverlayT = Literal["BOLD CENTER", "SUB-CAPTION", "STAT BURST", "LABEL", "QUESTION XL", "NONE"]
IntelSceneT = Literal["face_to_camera", "product_shot", "demo", "action"]


class InsufficientCreditsError(Exception):
    """``decrement_credit`` returned NULL (no credits to spend) or raised."""


class ScriptGenerateBody(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    hook: str = Field(..., min_length=1, max_length=200)
    hook_delay_ms: int = Field(ge=400, le=3000)
    duration: int = Field(ge=15, le=90)
    tone: ScriptTone
    niche_id: int = Field(ge=1)
    # S6 — per-shot regenerate (per design pack ``screens/script.jsx``
    # lines 1149-1157). When set, the response carries only the shot at
    # this index so the FE can splice it back into local state without
    # disturbing the user's other 5 shots. ``None`` keeps the legacy
    # full-script regen behaviour. Validated against the deterministic
    # 6-shot output in ``run_script_generate_sync``.
    shot_index: int | None = Field(default=None, ge=0, le=5)


class VoLine(BaseModel):
    """One line of structured voice-over (per design pack
    ``screens/script.jsx`` lines 448-452, 1103-1230).

    ``t`` is a freeform timestamp string (``"0:00"`` / ``"0:14"``) — the
    FE renders it as a tabular-nums label. ``text`` may carry inline
    ``*stress*`` markers that ``FormattedVO`` highlights. ``cue`` is an
    optional inline tag (``"[dừng 0.3s]"`` / ``"[CUT close-up]"`` /
    ``"[SFX click]"``) the FE renders as a ``CueChip`` next to the line.
    """

    t: str = Field(..., min_length=1, max_length=12)
    text: str = Field(..., min_length=1, max_length=240)
    cue: str | None = Field(default=None, max_length=80)


class ScriptShotLLM(BaseModel):
    """Gemini's per-shot output. t0/t1/corpus_avg/winner_avg are NOT here —
    those stay deterministic so Gemini can't drift the timing or invent
    scene-intel numbers that mislead the frontend bars.

    Wave 2.5 Phase B PR #6: optional enrichment fields feed
    ``pick_shot_references`` with the descriptor the matcher scores on.
    Optional because (a) old Gemini output doesn't have them, (b) the
    deterministic fallback fills them from the positional backbone.

    S5 (2026-06-02) — ``vo`` adds structured voice-over (timed lines +
    inline cues + ``*stress*`` markers). ``voice`` stays as the
    flattened legacy field for back-compat with old drafts + clipboard
    exports; both fields ship together so the FE can render either.
    """

    cam: str = Field(..., min_length=1, max_length=80)
    voice: str = Field(..., min_length=1, max_length=220)
    vo: list[VoLine] | None = None
    viz: str = Field(..., min_length=1, max_length=200)
    overlay: OverlayT
    intel_scene_type: IntelSceneT
    overlay_winner: str = Field(default="—", max_length=80)

    # 2026-06-11 — one-line data-grounded rationale per shot, rendered as a
    # caption under the shot card. Must cite the evidence blocks injected
    # into the prompt; null when there was nothing to cite.
    reason_vi: str | None = Field(default=None, max_length=140)

    # 2026-05-11 — enrichment dimensions mirrored from the Scene model
    # (getviews_pipeline.models). All Optional; see module docstring.
    framing: FramingType | None = None
    pace: PaceType | None = None
    overlay_style: OverlayStyleType | None = None
    subject: SubjectType | None = None
    motion: MotionType | None = None


class ScriptGenerateLLM(BaseModel):
    shots: list[ScriptShotLLM] = Field(..., min_length=6, max_length=6)


# Positional backbone — owns overlay/intel_scene_type order + corpus/winner
# benchmarks. Gemini is asked to respect the overlay + intel_scene_type
# in the prompt, and if it drifts we coerce back to these canonical values
# inside `_assemble_shots`. Wave 2.5 Phase B PR #6 added canonical
# framing/pace/overlay_style/subject/motion per position so the matcher
# has a descriptor even on the deterministic fallback path.
_WEIGHTS: tuple[int, ...] = (3, 5, 8, 8, 6, 2)

# One row per of the 6 shots. Indexes:
#   0 cam, 1 overlay, 2 intel_scene_type, 3 voice_tpl, 4 viz_tpl,
#   5 corpus_avg, 6 winner_avg, 7 overlay_winner,
#   8 framing, 9 pace, 10 overlay_style, 11 subject, 12 motion
_BACKBONE: tuple[
    tuple[
        str, OverlayT, IntelSceneT, str, str, float, float, str,
        FramingType, PaceType, OverlayStyleType, SubjectType, MotionType,
    ],
    ...,
] = (
    ("Cận mặt", "BOLD CENTER", "face_to_camera",
     "Hook: mở với {hook} — {topic}", 'Chữ nổi + "{topic_short}"',
     2.8, 2.4, "white sans 28pt · bottom-center",
     "close_up", "static", "bold_center", "face", "static"),
    ("Cắt nhanh b-roll", "SUB-CAPTION", "product_shot",
     "B-roll: nhấn {topic_short}", "Cắt nhanh, slow-mo nhẹ",
     4.2, 5.0, "yellow outlined · mid-left",
     "medium", "fast", "sub_caption", "product", "handheld"),
    ("Side-by-side", "STAT BURST", "demo",
     "So sánh / demo trung tâm: {topic_short}", "Split-screen, số liệu nổi",
     7.8, 8.0, "number callout 72pt",
     "medium", "medium", "sticker", "mixed", "static"),
    ("POV nghe", "LABEL", "face_to_camera",
     "Giọng {tone}: giải thích {topic_short}", "POV, ánh sáng ấm",
     6.2, 7.5, "caption strip · bottom",
     "medium", "slow", "chyron", "face", "handheld"),
    ("Cận tay + texture", "NONE", "action",
     "Texture + cảm nhận: {topic_short}", "Cận chi tiết, xoay nhẹ",
     5.1, 5.0, "—",
     "extreme_close_up", "slow", "none", "action", "slow_mo"),
    ("Cận mặt + câu hỏi", "QUESTION XL", "face_to_camera",
     "CTA: hỏi người xem về {topic_short}", "Câu hỏi to trên màn",
     2.4, 2.5, "question mark · full bleed",
     "close_up", "static", "bold_center", "face", "static"),
)


def _shot_to_descriptor(
    *,
    intel_scene_type: IntelSceneT,
    framing: FramingType | None,
    pace: PaceType | None,
    overlay_style: OverlayStyleType | None,
    subject: SubjectType | None,
    motion: MotionType | None,
    backbone_idx: int,
) -> dict[str, Any]:
    """Project a shot's creative fields into the ``video_shots``-column
    descriptor shape that ``pick_shot_references`` scores on.

    Prefer Gemini-emitted enrichment fields when present; otherwise fall
    back to the positional backbone. Always emits the legacy
    ``scene_type`` alongside so pre-PR #2 legacy shots still score via
    the scene_type fallback branch inside the matcher.
    """
    row = _BACKBONE[min(backbone_idx, len(_BACKBONE) - 1)]
    canon_framing = row[8]
    canon_pace = row[9]
    canon_overlay_style = row[10]
    canon_subject = row[11]
    canon_motion = row[12]
    return {
        "framing": framing or canon_framing,
        "pace": pace or canon_pace,
        "overlay_style": overlay_style or canon_overlay_style,
        "subject": subject or canon_subject,
        "motion": motion or canon_motion,
        "scene_type": intel_scene_type,  # legacy fallback dimension
    }


def _sanitize_snippet(s: str, max_len: int) -> str:
    t = re.sub(r"\s+", " ", (s or "").strip())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def _segment_lengths(total: int) -> list[int]:
    if total < 15:
        total = 15
    wsum = sum(_WEIGHTS)
    parts: list[int] = []
    acc = 0
    for i, w in enumerate(_WEIGHTS):
        if i == len(_WEIGHTS) - 1:
            parts.append(max(1, total - acc))
            break
        seg = max(1, round(total * w / wsum))
        if acc + seg >= total:
            seg = max(1, total - acc - (len(_WEIGHTS) - i - 1))
        parts.append(seg)
        acc += seg
    drift = total - sum(parts)
    if parts and drift != 0:
        parts[-1] = max(1, parts[-1] + drift)
    return parts


# Tuple shape emitted by both the Gemini path and the deterministic
# fallback, consumed by _assemble_shots:
#   (cam, overlay, intel_scene, voice, viz, overlay_winner,
#    framing, pace, overlay_style, subject, motion, vo, reason_vi)
# ``vo`` is the structured voice-over (S5) — list of {t, text, cue}
# dicts. ``None`` on legacy paths; ``_assemble_shots`` derives a
# single-line fallback from ``voice`` so the FE always has a rendering
# path for the structured layout. ``reason_vi`` is the per-shot
# data-grounded rationale — ``None`` on the deterministic path.
_CreativeRow = tuple[
    str, OverlayT, IntelSceneT, str, str, str,
    FramingType | None, PaceType | None, OverlayStyleType | None,
    SubjectType | None, MotionType | None,
    list[dict[str, Any]] | None,
    str | None,
]


def _deterministic_creative_rows(
    *, topic: str, hook: str, tone: str,
) -> list[_CreativeRow]:
    """Render the fallback creative fields from the _BACKBONE templates.

    Returns 11-tuples per position — the last five are the canonical
    enrichment fields from the backbone, mirroring what Gemini would
    emit on the happy path.
    """
    topic_short = _sanitize_snippet(topic, 36)
    out: list[_CreativeRow] = []
    for row in _BACKBONE:
        (cam, overlay, intel_scene, voice_tpl, viz_tpl, _cavg, _wavg, owin,
         framing, pace, overlay_style, subject, motion) = row
        voice = voice_tpl.format(hook=hook, topic=topic, topic_short=topic_short, tone=tone)
        viz = viz_tpl.format(hook=hook, topic=topic, topic_short=topic_short, tone=tone)
        # Deterministic fallback emits a single-line ``vo`` derived from
        # the flattened voice. Caller (_assemble_shots) overrides ``t``
        # with the real shot start once the segment lengths are known.
        out.append((
            cam, overlay, intel_scene, voice, viz, owin,
            framing, pace, overlay_style, subject, motion, None, None,
        ))
    return out


def _assemble_shots(
    *,
    duration: int,
    creative: list[_CreativeRow],
) -> list[dict[str, Any]]:
    """Stitch creative + deterministic fields into the frozen shot payload.

    Each shot dict now also carries framing/pace/overlay_style/subject/
    motion (Optional — may be None if Gemini omitted and the backbone
    defaults weren't threaded). The outer runner adds ``references``.
    """
    lens = _segment_lengths(duration)
    t0 = 0
    out: list[dict[str, Any]] = []
    for i, creative_row in enumerate(creative):
        (cam, overlay, intel_scene, voice, viz, owin,
         framing, pace, overlay_style, subject, motion, vo_in, reason_in) = creative_row
        span = lens[i] if i < len(lens) else 1
        t1 = t0 + span
        canon_overlay = _BACKBONE[i][1]
        canon_intel = _BACKBONE[i][2]
        # Coerce overlay + intel_scene_type to the canonical backbone for
        # this position if Gemini drifted — the frontend scene merge
        # relies on the positional overlay/intel mapping.
        final_overlay: OverlayT = overlay if overlay == canon_overlay else canon_overlay
        final_intel: IntelSceneT = intel_scene if intel_scene == canon_intel else canon_intel
        # S5 — structured ``vo``. Prefer the upstream value (Gemini path)
        # when it actually carries lines; otherwise derive a single-line
        # fallback from the flat ``voice`` string so the FE always has
        # the new shape to render. Empty / null upstream → fallback.
        vo_lines: list[dict[str, Any]]
        if vo_in:
            vo_lines = list(vo_in)
        else:
            voice_clean = _sanitize_snippet(voice, 220)
            vo_lines = [{"t": _format_timestamp(t0), "text": voice_clean, "cue": None}]
        out.append(
            {
                "t0": t0,
                "t1": t1,
                "cam": _sanitize_snippet(cam, 80),
                "voice": _sanitize_snippet(voice, 220),
                "vo": vo_lines,
                "viz": _sanitize_snippet(viz, 200),
                "overlay": final_overlay,
                "corpus_avg": _BACKBONE[i][5],
                "winner_avg": _BACKBONE[i][6],
                "intel_scene_type": final_intel,
                "overlay_winner": _sanitize_snippet(owin, 80) or "—",
                "reason_vi": _sanitize_snippet(reason_in, 140) if reason_in else None,
                "framing": framing,
                "pace": pace,
                "overlay_style": overlay_style,
                "subject": subject,
                "motion": motion,
            }
        )
        t0 = t1
    return out


def _format_timestamp(seconds: int) -> str:
    """Render a seconds count as ``"M:SS"`` for VO line display.

    Matches the design pack's ``vo[i].t`` format (e.g. ``"0:00"``, ``"0:14"``).
    Used by the deterministic fallback path; Gemini emits its own
    timestamps from the prompt (see ``_call_script_gemini``).
    """
    s = max(0, int(seconds))
    return f"{s // 60}:{s % 60:02d}"


def _format_views_compact(n: int) -> str:
    """Vietnamese-friendly compact view count: 1234567 → '1.2tr', 12345 → '12k'."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}tr"
    if n >= 1_000:
        return f"{n // 1_000}k"
    return str(n)


def _fetch_top_niche_hooks(
    client: Any | None,
    niche_id: int,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Top hooks in the niche by avg_views, with retention + sample size.

    Used by ``_call_script_gemini`` as evidence-backed context: instead
    of relying on ``_BACKBONE``'s generic structure, the LLM sees what's
    actually winning in the niche this week and grounds the script's
    hook + tone in real performance data.

    Returns a list of dicts shaped for ``_format_hook_evidence_block``;
    empty list on any failure (graceful — Gemini falls back to its
    default creative output and the deterministic ``_BACKBONE`` rows
    cover the structural fields anyway).
    """
    if client is None or niche_id is None or niche_id < 1:
        return []
    try:
        res = (
            client.table("hook_effectiveness")
            .select("hook_type, avg_views, avg_completion_rate, sample_size")
            .eq("niche_id", niche_id)
            .order("avg_views", desc=True)
            .limit(max(limit * 2, 6))  # over-fetch; we filter "other"/"none"
            .execute()
        )
        rows = res.data or []
    except Exception as exc:
        logger.warning(
            "[script/generate] hook_effectiveness fetch failed niche=%s: %s",
            niche_id, exc,
        )
        return []

    out: list[dict[str, Any]] = []
    for r in rows:
        ht = (r.get("hook_type") or "").strip().lower()
        if not ht or ht in ("other", "none"):
            continue
        out.append({
            "hook_type": ht,
            "avg_views": int(r.get("avg_views") or 0),
            "completion_pct": round(float(r.get("avg_completion_rate") or 0) * 100, 1),
            "sample_size": int(r.get("sample_size") or 0),
        })
        if len(out) >= limit:
            break
    return out


def _format_hook_evidence_block(hooks: list[dict[str, Any]]) -> str:
    """Compact Vietnamese evidence block for the Gemini prompt.

    Empty string when no hooks — caller treats it as "no evidence
    section in the prompt" so the prompt shape stays the same as before
    L2.2. Uses HOOK_TYPE_VI for the human label and keeps the English
    enum visible so Gemini can map back if needed.
    """
    if not hooks:
        return ""
    from getviews_pipeline.enum_labels_vi import hook_type_vi

    lines = ["", "Hook đang thắng trong ngách (top tuần qua, có dữ liệu):"]
    for i, h in enumerate(hooks, start=1):
        vi = hook_type_vi(h["hook_type"], default=h["hook_type"])
        n = _format_views_compact(h["avg_views"])
        lines.append(
            f"{i}. {vi} ({h['hook_type']}) — trung bình {n} view, "
            f"giữ chân {h['completion_pct']}% ({h['sample_size']} video)"
        )
    lines.append(
        "Khi viết shot 1 (hook), ưu tiên giọng + cấu trúc giống hook "
        "hạng cao nhất ở trên — đây là pattern đã được kiểm chứng trên ngách, "
        "không phải mẫu chung."
    )
    return "\n".join(lines)


def _fetch_winning_hook_lines(
    client: Any,
    niche_id: int,
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Verbatim opening lines from the niche's top corpus videos.

    Quality audit 2026-06-11: the script prompt only saw hook-type *labels*
    (hook_effectiveness stats) — never how a winning hook actually SOUNDS in
    spoken Vietnamese. 8.9K corpus rows carry ``hook_analysis.hook_phrase``
    from Gemini video extraction; the top few by views are the best style
    exemplars available. Returns [] on any failure — never raises.
    """
    if client is None or not niche_id or niche_id < 1:
        return []
    try:
        res = (
            client.table("video_corpus")
            .select("creator_handle,views,analysis_json")
            .eq("ingest_loop_niche_id", niche_id)
            .or_("quality_tier.is.null,quality_tier.in.(high,medium)")
            .order("views", desc=True)
            .limit(limit * 4)  # over-fetch; rows without a hook_phrase are skipped
            .execute()
        )
    except Exception as exc:
        logger.warning("[script/generate] hook lines fetch failed niche=%s: %s", niche_id, exc)
        return []
    out: list[dict[str, Any]] = []
    seen_phrases: set[str] = set()
    for row in res.data or []:
        analysis = row.get("analysis_json") if isinstance(row.get("analysis_json"), dict) else {}
        ha = analysis.get("hook_analysis") if isinstance(analysis.get("hook_analysis"), dict) else {}
        phrase = str(ha.get("hook_phrase") or "").strip()
        if len(phrase) < 8 or phrase.lower() in seen_phrases:
            continue
        seen_phrases.add(phrase.lower())
        out.append({
            "phrase": phrase[:120],
            "handle": str(row.get("creator_handle") or "").lstrip("@"),
            "views": int(row.get("views") or 0),
        })
        if len(out) >= limit:
            break
    return out


def _format_hook_lines_block(lines: list[dict[str, Any]]) -> str:
    if not lines:
        return ""
    rendered = "\n".join(
        f'- "{ln["phrase"]}" — @{ln["handle"] or "?"} ({ln["views"]:,} view)'.replace(",", ".")
        for ln in lines
    )
    return (
        "\nHOOK THẬT ĐANG THẮNG TRONG NGÁCH (trích nguyên văn từ video — học "
        "CÁCH DIỄN ĐẠT văn nói, độ dài câu, nhịp; KHÔNG copy y nguyên):\n"
        f"{rendered}\n"
        "Voice của shot 1 phải nghe tự nhiên như các câu trên — tiếng Việt văn "
        "nói, không văn viết.\n"
    )


def _fetch_reference_structure(
    client: Any | None,
    niche_id: int,
    *,
    max_scenes: int = 8,
) -> dict[str, Any] | None:
    """Scene-by-scene structure of the niche's top-viewed ``video_shots`` video.

    2026-06-11 (Lightreel audit): the prompt's 6-shot template paced every
    script identically regardless of what actually wins in the niche. This
    surfaces how the niche's proven winner paces its scenes (length, cut
    density, overlay placement) so Gemini grounds viz/vo rhythm in it —
    the template itself stays fixed. Returns None on any failure.
    """
    if client is None or not niche_id or niche_id < 1:
        return None
    try:
        top = (
            client.table("video_shots")
            .select("video_id,creator_handle,views")
            .eq("niche_id", niche_id)
            .order("views", desc=True, nullsfirst=False)
            .limit(1)
            .execute()
        )
        rows = top.data or []
        video_id = str((rows[0] if rows else {}).get("video_id") or "")
        if not video_id:
            return None
        scenes_res = (
            client.table("video_shots")
            .select("scene_index,start_s,end_s,description,framing,pace,overlay_style")
            .eq("video_id", video_id)
            .order("scene_index", desc=False)
            .limit(max_scenes)
            .execute()
        )
        scenes = scenes_res.data or []
        if not scenes:
            return None
        return {
            "video_id": video_id,
            "handle": str(rows[0].get("creator_handle") or "").lstrip("@"),
            "views": int(rows[0].get("views") or 0),
            "scenes": scenes,
        }
    except Exception as exc:
        logger.warning(
            "[script/generate] reference structure fetch failed niche=%s: %s", niche_id, exc,
        )
        return None


def _format_reference_structure_block(ref: dict[str, Any] | None) -> str:
    """Vietnamese prompt block describing the reference video's scene rhythm.

    Empty string when no reference — the prompt shape then matches the
    pre-injection form exactly (same convention as the hook blocks).
    """
    if not ref or not ref.get("scenes"):
        return ""
    handle = ref.get("handle") or "?"
    lines = [
        "",
        f"NHỊP CẢNH CỦA VIDEO TOP NGÁCH (@{handle} — "
        f"{_format_views_compact(int(ref.get('views') or 0))} view):",
    ]
    for n, s in enumerate(ref["scenes"], start=1):
        t0 = float(s.get("start_s") or 0)
        t1 = float(s.get("end_s") or 0)
        desc = _sanitize_snippet(str(s.get("description") or ""), 80) or "—"
        dims = "/".join(
            str(s.get(k)) for k in ("framing", "pace", "overlay_style") if s.get(k)
        )
        lines.append(f"- Cảnh {n} ({t0:.1f}–{t1:.1f}s): {desc}" + (f" | {dims}" if dims else ""))
    lines.append(
        "Giữ NGUYÊN template 6 shot bên dưới; học NHỊP của video này — độ dài "
        "mỗi cảnh, mật độ cắt, vị trí overlay — khi viết viz và vo."
    )
    return "\n".join(lines)


def _build_format_rationale(
    top_hooks: list[dict[str, Any]],
    hook_lines: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Deterministic "why this structure" payload surfaced above the shot list.

    2026-06-11 (Lightreel audit): the hook evidence was injected into the
    Gemini prompt but the *user* never saw why the script was shaped this
    way. This re-uses the exact rows already fetched — no LLM, no new
    queries — so the numbers can't drift from what the prompt cited.
    None when there is no evidence (FE then renders nothing).
    """
    proofs: list[dict[str, Any]] = []
    for h in top_hooks[:3]:
        from getviews_pipeline.enum_labels_vi import hook_type_vi

        proofs.append({
            "kind": "hook_stat",
            "label_vi": hook_type_vi(h["hook_type"], default=h["hook_type"]),
            "hook_type": h["hook_type"],
            "avg_views": h["avg_views"],
            "completion_pct": h["completion_pct"],
            "sample_size": h["sample_size"],
        })
    for ln in hook_lines[:3]:
        proofs.append({
            "kind": "hook_line",
            "phrase": ln["phrase"],
            "handle": ln["handle"],
            "views": ln["views"],
        })
    if not proofs:
        return None
    n_videos = sum(p["sample_size"] for p in proofs if p["kind"] == "hook_stat")
    if n_videos > 0:
        text = (
            f"Hook và nhịp cảnh bám theo pattern đang thắng trong ngách — "
            f"kiểm chứng trên {n_videos} video trong kho mẫu, không phải mẫu chung."
        )
    else:
        text = (
            "Hook và nhịp cảnh bám theo các video top ngách trong kho mẫu, "
            "không phải mẫu chung."
        )
    return {"text_vi": text, "proofs": proofs}


def _call_script_gemini(
    body: ScriptGenerateBody,
    *,
    top_hooks: list[dict[str, Any]] | None = None,
    hook_lines: list[dict[str, Any]] | None = None,
    reference_block: str = "",
) -> ScriptGenerateLLM:
    """Pydantic-bound Gemini synthesis for 6 shots. Raises on any failure."""
    from google.genai import types

    from getviews_pipeline.config import GEMINI_SYNTHESIS_FALLBACKS, GEMINI_SYNTHESIS_MODEL
    from getviews_pipeline.gemini import (
        _generate_content_models,
        _normalize_response,
        _response_text,
    )

    topic = _sanitize_snippet(body.topic, 500)
    hook = _sanitize_snippet(body.hook, 200)
    delay_s = round(body.hook_delay_ms / 1000.0, 2)
    # L2.2 — evidence block from hook_effectiveness. Empty string when no
    # data; the prompt then matches the pre-L2.2 shape exactly.
    hook_evidence = _format_hook_evidence_block(top_hooks or [])
    hook_evidence += _format_hook_lines_block(hook_lines or [])
    hook_evidence += reference_block

    prompt = f"""Bạn là biên kịch TikTok tiếng Việt ngắn (dưới {body.duration}s). Viết kịch bản 6 shot cho video.

Chủ đề: {topic}
Hook (dùng cho shot 1): {hook}
Hook rơi lúc: {delay_s}s
Tone: {body.tone}
Thời lượng tổng: {body.duration}s
{hook_evidence}

Cấu trúc 6 shot CỐ ĐỊNH (phải giữ đúng overlay + intel_scene_type theo template):
1. cam="Cận mặt", overlay="BOLD CENTER", intel_scene_type="face_to_camera" — hook mạnh trong 3s đầu.
2. cam="Cắt nhanh b-roll", overlay="SUB-CAPTION", intel_scene_type="product_shot" — mở rộng ngữ cảnh.
3. cam="Side-by-side", overlay="STAT BURST", intel_scene_type="demo" — demo / so sánh có số liệu.
4. cam="POV nghe", overlay="LABEL", intel_scene_type="face_to_camera" — POV giải thích, giọng {body.tone}.
5. cam="Cận tay + texture", overlay="NONE", intel_scene_type="action" — chi tiết / texture, không text.
6. cam="Cận mặt + câu hỏi", overlay="QUESTION XL", intel_scene_type="face_to_camera" — CTA câu hỏi.

Với mỗi shot, viết:
- cam: giữ đúng như template ở trên.
- voice: voiceover dạng phẳng 1–2 câu tiếng Việt tự nhiên, tone={body.tone}, nhắc chủ đề hoặc hook (≤ 220 ký tự, dùng để export clipboard / Zalo).
- vo: voiceover *có cấu trúc*, danh sách 1–3 dòng `{{t, text, cue?}}`:
    • t: timestamp dạng "M:SS" trong khoảng shot (ví dụ "0:00", "0:14").
    • text: lời thoại — CÓ THỂ chèn `*từ_nhấn*` để FE in đậm cụm cần nhấn (vd: "Mình *vừa test* xong").
    • cue (optional): chỉ dẫn dàn dựng `[dừng 0.3s]` / `[CUT close-up]` / `[B-roll: zoom giá]` / `[SFX click]` — bỏ qua nếu không cần.
  Nội dung `vo` ghép lại nên trùng ý với `voice`; KHÔNG dài quá `voice`.
- viz: chỉ dẫn visual ngắn (< 20 từ) tiếng Việt.
- overlay: theo template — KHÔNG đổi.
- intel_scene_type: theo template — KHÔNG đổi.
- overlay_winner: gợi ý style overlay ngắn (có thể tiếng Anh) — ví dụ "white sans 28pt · bottom-center".
- reason_vi (optional, ≤140 ký tự): 1 câu vì sao shot này quay/nói như vậy, TRÍCH đúng 1 bằng chứng từ \
các block dữ liệu ở trên (hook đang thắng / câu hook thật / nhịp cảnh video top). Không có bằng chứng \
phù hợp → để null. KHÔNG bịa số liệu.

Thêm các dimension mô tả shot (dùng để matcher tìm video tham chiếu
tương tự trong kho video mẫu — enum phải trùng đúng taxonomy; nếu không chắc
để null):
- framing: close_up | medium | wide | extreme_close_up
- pace: static | slow | medium | fast | cut_heavy
- overlay_style: none | bold_center | sub_caption | chyron | sticker
- subject: face | product | text | action | ambient | mixed
- motion: static | handheld | slow_mo | time_lapse | match_cut

Quy tắc copy:
- Tự nhiên, đời thường; tránh "bí mật", "công thức vàng", "triệu view", "bùng nổ".
- Không mở bằng "Chào bạn" / "Tuyệt vời" / "Wow".
- Tôn trọng độ dài: voice ≤ 220 ký tự, viz ≤ 200 ký tự.
"""
    config = types.GenerateContentConfig(
        temperature=0.7,
        response_mime_type="application/json",
        response_json_schema=ScriptGenerateLLM.model_json_schema(),
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_SYNTHESIS_MODEL,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=config,
        call_site="script_generate",
    )
    raw = _response_text(response)
    return ScriptGenerateLLM.model_validate_json(_normalize_response(raw))


def build_script_shots(
    body: ScriptGenerateBody,
    *,
    client: Any | None = None,
    top_hooks: list[dict[str, Any]] | None = None,
    hook_lines: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Gemini-first shot builder with deterministic fallback.

    Returns the B.4 response shape — 6 shots each with
    t0/t1/cam/voice/viz/overlay/corpus_avg/winner_avg/intel_scene_type/
    overlay_winner plus the Wave 2.5 Phase B PR #6 enrichment fields
    (framing/pace/overlay_style/subject/motion). ``references`` is
    added by the outer ``run_script_generate_sync`` — matcher needs
    the Supabase client which isn't in scope here.

    ``client`` (optional, L2.2 — service-role Supabase) gates the hook
    evidence enrichment: when present, the top niche hooks from
    ``hook_effectiveness`` are injected into the Gemini prompt so the
    LLM grounds its hook + tone choices in real performance data
    instead of generic backbone defaults. ``None`` keeps the legacy
    Gemini-only behaviour — useful for tests and any caller that
    doesn't have a service client at this layer.

    ``top_hooks`` / ``hook_lines`` may be passed pre-fetched (the
    answer-session runner fetches them once to also build the
    ``format_rationale`` payload); ``None`` means fetch here.
    """
    topic = _sanitize_snippet(body.topic, 500)
    hook = _sanitize_snippet(body.hook, 200)
    if top_hooks is None:
        top_hooks = _fetch_top_niche_hooks(client, body.niche_id) if client is not None else []
    if hook_lines is None:
        hook_lines = _fetch_winning_hook_lines(client, body.niche_id) if client is not None else []
    reference_block = _format_reference_structure_block(
        _fetch_reference_structure(client, body.niche_id) if client is not None else None
    )

    creative: list[_CreativeRow] | None = None
    try:
        llm = _call_script_gemini(
            body, top_hooks=top_hooks, hook_lines=hook_lines, reference_block=reference_block,
        )
        creative = [
            (
                s.cam, s.overlay, s.intel_scene_type,
                s.voice, s.viz, s.overlay_winner or "—",
                s.framing, s.pace, s.overlay_style, s.subject, s.motion,
                # S5 — pass Gemini's structured ``vo`` through to the
                # assembler. ``None`` falls back to the single-line
                # derivation from ``voice`` inside ``_assemble_shots``.
                [line.model_dump() for line in s.vo] if s.vo else None,
                s.reason_vi,
            )
            for s in llm.shots
        ]
        logger.info("[script/generate] source=gemini niche=%s duration=%ds", body.niche_id, body.duration)
    except Exception as exc:
        logger.warning("[script/generate] Gemini path failed, falling back deterministic: %s", exc)
        creative = None

    if creative is None:
        creative = _deterministic_creative_rows(topic=topic, hook=hook, tone=body.tone)
        logger.info("[script/generate] source=fallback niche=%s duration=%ds", body.niche_id, body.duration)

    return _assemble_shots(duration=body.duration, creative=creative)


def _decrement_credit_or_raise(user_sb: Any, *, user_id: str) -> None:
    try:
        rpc_resp = user_sb.rpc("decrement_credit", {"p_user_id": user_id}).execute()
        # RPC returns INTEGER balance (can be 0) on success or NULL → Python
        # None on no-credits. ``is None`` is the correct insufficient-credits
        # check (see migration 20260409000002_profiles.sql contract).
        if rpc_resp.data is None:
            raise InsufficientCreditsError()
    except InsufficientCreditsError:
        raise
    except Exception as exc:
        logger.warning("[script/generate] decrement_credit failed: %s", exc)
        raise InsufficientCreditsError() from exc


# Per-shot reference cap (Wave 2.5 Phase B PR #6). 3 creator scenes per
# shot is plenty — the UX surfaces them as a horizontal strip of cards.
_REFERENCES_PER_SHOT = 3


def _attach_shot_references(
    shots: list[dict[str, Any]],
    *,
    niche_id: int,
    service_sb: Any,
    topic_text: str | None = None,
    hook_type: str | None = None,
) -> None:
    """Mutate ``shots`` in place, adding a ``references`` list to each.

    Uses the service-role client (not the user client) because
    ``video_shots`` is writer-only under RLS — readers need the
    service client, same as other corpus-backed surfaces.

    ``topic_text`` (the script's topic + hook sentence) gates references
    on subject affinity, and ``hook_type`` penalises mismatched hook
    intents — quality audit 2026-06-11: without these, a skincare-warning
    script surfaced makeup/gossip scenes as "Cùng ngách".

    Threads ``exclude_video_ids`` across shots so one creator doesn't
    monopolize the whole reference panel. Never raises — a matcher
    failure just yields ``references: []`` for that shot.
    """
    from getviews_pipeline.shot_reference_matcher import pick_shot_references

    used: set[str] = set()
    for i, shot in enumerate(shots):
        descriptor = _shot_to_descriptor(
            intel_scene_type=shot["intel_scene_type"],
            framing=shot.get("framing"),
            pace=shot.get("pace"),
            overlay_style=shot.get("overlay_style"),
            subject=shot.get("subject"),
            motion=shot.get("motion"),
            backbone_idx=i,
        )
        refs = pick_shot_references(
            shot_descriptor=descriptor,
            niche_id=niche_id,
            hook_type=hook_type,
            topic_text=topic_text,
            limit=_REFERENCES_PER_SHOT,
            exclude_video_ids=used,
            client=service_sb,
        )
        shot["references"] = [r.to_dict() for r in refs]
        for r in refs:
            used.add(r.video_id)


def run_script_generate_sync(
    user_sb: Any,
    *,
    user_id: str,
    body: ScriptGenerateBody,
    service_sb: Any | None = None,
    deduct_credit: bool = True,
) -> dict[str, Any]:
    """Generate 6-shot script. When ``deduct_credit`` is False (answer-session
    path), the caller already charged credits — skip the per-call RPC."""
    if deduct_credit:
        _decrement_credit_or_raise(user_sb, user_id=user_id)
    # L2.2 — pass service_sb to ``build_script_shots`` so the Gemini
    # prompt can inject the niche's top hook_effectiveness rows as
    # evidence. service_sb (not user_sb) because hook_effectiveness is
    # service-role-readable; user-scoped reads would hit RLS. Evidence is
    # fetched once here so ``format_rationale`` cites the same rows the
    # prompt saw.
    top_hooks = (
        _fetch_top_niche_hooks(service_sb, body.niche_id) if service_sb is not None else []
    )
    hook_lines = (
        _fetch_winning_hook_lines(service_sb, body.niche_id) if service_sb is not None else []
    )
    shots = build_script_shots(
        body, client=service_sb, top_hooks=top_hooks, hook_lines=hook_lines,
    )

    # Reference lookup against video_shots. service_sb is optional at
    # this layer so tests can inject a mock; in the route handler we
    # pass the real service client. If it's None, we still return a
    # valid response — every shot just has references=[].
    if service_sb is not None:
        try:
            _attach_shot_references(
                shots,
                niche_id=body.niche_id,
                service_sb=service_sb,
                # Topic affinity gate: script topic + hook sentence carry
                # the subject tokens the matcher scores captions against.
                topic_text=f"{body.topic} {body.hook}",
            )
        except Exception as exc:
            logger.warning("[script/generate] reference attach failed: %s", exc)
            for s in shots:
                s.setdefault("references", [])
    else:
        for s in shots:
            s.setdefault("references", [])

    ref_count = sum(len(s.get("references") or []) for s in shots)
    logger.info(
        "[script/generate] user=%s niche=%d shots=%d refs=%d",
        user_id, body.niche_id, len(shots), ref_count,
    )
    # S6 — per-shot regen narrows the response to a single shot. We still
    # ran the full Gemini call (cheaper than a new prompt + grounding
    # round-trip) but the FE only needs shot[shot_index] to splice back
    # into its local state. Out-of-range indices return the full set so
    # an old client never breaks.
    if body.shot_index is not None and 0 <= body.shot_index < len(shots):
        shots = [shots[body.shot_index]]
    return {"shots": shots, "format_rationale": _build_format_rationale(top_hooks, hook_lines)}
