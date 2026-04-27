"""D.1.1 — ``draft_scripts`` persistence + Copy export.

Backs four endpoints in ``main.py``:

* ``POST /script/save``            — insert a draft, return ``{draft_id}``.
* ``GET /script/drafts``           — list the caller's drafts (newest first).
* ``GET /script/drafts/{id}``      — restore a single draft by id.
* ``POST /script/drafts/{id}/export`` — format=\"copy\" (clipboard text).

RLS on ``public.draft_scripts`` scopes reads / writes by ``auth.uid()``; the
module stays authoritative on shape + export formatting so main.py is just
HTTP glue + credit handling (future — D.1.1 has no credit gate per the plan).
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Per design pack ``screens/script.jsx`` lines 838-857, the export modal
# offers 3 user-facing formats. ``copy`` stays as a legacy alias for the
# clipboard-paste callers (current ``useScriptExport`` default) — internal
# logic treats it as ``plain``.
ExportFormat = Literal["shoot", "markdown", "plain", "copy"]


class DraftCreateBody(BaseModel):
    """POST /script/save body. Shape matches ``POST /script/generate`` plus
    the optional session-lineage field so a draft can point back at the
    ``/answer`` turn that inspired it."""

    topic: str = Field(..., min_length=1, max_length=500)
    hook: str = Field(..., min_length=1, max_length=300)
    hook_delay_ms: int = Field(ge=400, le=3000)
    duration_sec: int = Field(ge=15, le=90)
    tone: str = Field(..., min_length=1, max_length=40)
    shots: list[dict[str, Any]] = Field(default_factory=list)
    niche_id: int | None = None
    source_session_id: str | None = None


class DraftExportBody(BaseModel):
    format: ExportFormat


class DraftNotFoundError(Exception):
    """Draft row not found (or RLS hid it). Caller maps to HTTP 404."""


def insert_draft(sb: Any, *, user_id: str, body: DraftCreateBody) -> dict[str, Any]:
    """Insert a draft row. Returns the row dict (including server-assigned id)."""
    row: dict[str, Any] = {
        "user_id": user_id,
        "topic": body.topic.strip(),
        "hook": body.hook.strip(),
        "hook_delay_ms": int(body.hook_delay_ms),
        "duration_sec": int(body.duration_sec),
        "tone": body.tone.strip(),
        "shots": body.shots,
    }
    if body.niche_id is not None:
        row["niche_id"] = int(body.niche_id)
    if body.source_session_id is not None:
        row["source_session_id"] = body.source_session_id
    res = sb.table("draft_scripts").insert(row).execute()
    data = res.data
    if isinstance(data, list):
        data = data[0] if data else None
    if not data or not isinstance(data, dict):
        raise RuntimeError("draft insert returned no row")
    return data


def list_drafts(sb: Any, *, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """List the caller's drafts, newest updated first."""
    res = (
        sb.table("draft_scripts")
        .select("id,topic,hook,hook_delay_ms,duration_sec,tone,shots,niche_id,source_session_id,created_at,updated_at")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(res.data or [])


def fetch_draft(sb: Any, *, user_id: str, draft_id: str) -> dict[str, Any]:
    """Fetch a single draft by id. Raises ``DraftNotFoundError`` when RLS hides
    the row or the id is unknown."""
    res = (
        sb.table("draft_scripts")
        .select("*")
        .eq("id", draft_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    data = res.data
    if not data:
        raise DraftNotFoundError(draft_id)
    return data


# ── Export formatters ──────────────────────────────────────────────────────


def _shot_time_prefix(s: dict[str, Any]) -> str:
    t0 = int(s.get("t0") or 0)
    t1 = int(s.get("t1") or 0)
    return f"{t0:02d}-{t1:02d}s"


def format_draft_for_copy(draft: dict[str, Any]) -> str:
    """Plain-text export for Zalo / clipboard paste.

    No markdown, no emoji; mono time prefix per shot so the reader can align
    script against footage without extra tooling. Trailing newline included so
    append-to-notes doesn't concatenate into the next line.
    """
    topic = (draft.get("topic") or "").strip()
    hook = (draft.get("hook") or "").strip()
    tone = (draft.get("tone") or "").strip()
    duration = int(draft.get("duration_sec") or 0)
    # Defend against corrupt rows (e.g. historical bug where ``shots`` was
    # persisted as ``[null]``). Filtering non-dict entries keeps the
    # downstream loops safe from attribute errors.
    shots = [s for s in (draft.get("shots") or []) if isinstance(s, dict)]

    lines: list[str] = [f"[KỊCH BẢN] {topic}".rstrip()]
    if hook:
        lines.append(f"Hook: {hook}")
    meta_bits = []
    if tone:
        meta_bits.append(f"Tone: {tone}")
    if duration:
        meta_bits.append(f"Thời lượng: {duration}s")
    if meta_bits:
        lines.append(" · ".join(meta_bits))
    lines.append("")

    for i, s in enumerate(shots, start=1):
        cam = (s.get("cam") or "").strip()
        voice = (s.get("voice") or "").strip()
        viz = (s.get("viz") or "").strip()
        overlay = (s.get("overlay") or "NONE").strip()
        lines.append(f"Shot {i}. {_shot_time_prefix(s)}  {cam}".rstrip())
        if voice:
            lines.append(f"  Voice: {voice}")
        if viz:
            lines.append(f"  Viz:   {viz}")
        if overlay and overlay != "NONE":
            lines.append(f"  Overlay: {overlay}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def format_draft_for_shoot(draft: dict[str, Any]) -> str:
    """Filming-friendly export — box-drawing chars frame each shot so the
    creator can read it on a phone propped next to camera (per design pack
    ``screens/script.jsx`` lines 856-856 sample). All ASCII so phone
    note apps render cleanly.
    """
    topic = (draft.get("topic") or "").strip()
    hook = (draft.get("hook") or "").strip()
    tone = (draft.get("tone") or "").strip()
    duration = int(draft.get("duration_sec") or 0)
    shots = [s for s in (draft.get("shots") or []) if isinstance(s, dict)]

    lines: list[str] = []
    bar = "═" * 39
    lines.append(bar)
    lines.append(topic.upper() if topic else "KỊCH BẢN")
    lines.append(bar)
    meta_bits: list[str] = []
    if duration:
        meta_bits.append(f"ĐỘ DÀI {duration}s")
    if tone:
        meta_bits.append(f"GIỌNG {tone}")
    if meta_bits:
        lines.append("   ".join(meta_bits))
    if hook:
        lines.append(f"HOOK: {hook}")
    lines.append("")

    for i, s in enumerate(shots, start=1):
        t0 = int(s.get("t0") or 0)
        t1 = int(s.get("t1") or 0)
        cam = (s.get("cam") or "").strip()
        voice = (s.get("voice") or "").strip()
        viz = (s.get("viz") or "").strip()
        overlay = (s.get("overlay") or "NONE").strip()
        label = "HOOK" if i == 1 else f"SHOT {i}"
        head = f"┌─ {label} ─ {t0 // 60:02d}:{t0 % 60:02d} → {t1 // 60:02d}:{t1 % 60:02d} "
        # Pad header to a consistent ~46-char visual width.
        lines.append(head + ("─" * max(0, 46 - len(head))))
        if cam:
            lines.append(f"│ CAM   {cam}")
        if viz:
            lines.append(f"│ VIZ   {viz}")
        if overlay and overlay != "NONE":
            lines.append(f"│ OV    {overlay}")
        if voice:
            lines.append("│")
            lines.append(f'│ "{voice}"')
        lines.append("└" + "─" * 45)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def format_draft_for_markdown(draft: dict[str, Any]) -> str:
    """Markdown export for Notion / Obsidian / any markdown editor (per
    design pack ``screens/script.jsx`` lines 850-851 sample). Voice-over
    is rendered as a blockquote so it visually separates from the
    cinematography metadata."""
    topic = (draft.get("topic") or "").strip()
    hook = (draft.get("hook") or "").strip()
    tone = (draft.get("tone") or "").strip()
    duration = int(draft.get("duration_sec") or 0)
    shots = [s for s in (draft.get("shots") or []) if isinstance(s, dict)]

    lines: list[str] = []
    lines.append(f"# {topic}" if topic else "# Kịch bản")
    meta_bits: list[str] = []
    if duration:
        meta_bits.append(f"**Độ dài:** {duration}s")
    if tone:
        meta_bits.append(f"**Giọng:** {tone}")
    if meta_bits:
        lines.append("")
        lines.append(" · ".join(meta_bits))
    if hook:
        lines.append("")
        lines.append(f"**Hook:** {hook}")

    for i, s in enumerate(shots, start=1):
        t0 = int(s.get("t0") or 0)
        t1 = int(s.get("t1") or 0)
        cam = (s.get("cam") or "").strip()
        voice = (s.get("voice") or "").strip()
        viz = (s.get("viz") or "").strip()
        overlay = (s.get("overlay") or "NONE").strip()
        title = "Hook" if i == 1 else f"Shot {i}"
        lines.append("")
        lines.append(f"## {title} · {t0 // 60:02d}:{t0 % 60:02d}–{t1 // 60:02d}:{t1 % 60:02d}")
        meta = []
        if cam:
            meta.append(f"**Cam:** {cam}")
        if viz:
            meta.append(f"**Viz:** {viz}")
        if overlay and overlay != "NONE":
            meta.append(f"**Overlay:** {overlay}")
        if meta:
            lines.append("")
            lines.append("  \n".join(meta))
        if voice:
            lines.append("")
            lines.append(f"> {voice}")

    return "\n".join(lines).rstrip() + "\n"


def export_draft(draft: dict[str, Any], *, fmt: ExportFormat) -> tuple[str, str]:
    """Render a draft for the export channel. Returns (payload, content_type).

    ``shoot`` → box-drawn filming script (text/plain).
    ``markdown`` → markdown blockquote VO (text/markdown).
    ``plain`` / ``copy`` → flat clipboard-paste text (text/plain). ``copy``
    is a legacy alias kept for the existing ``useScriptExport`` callers.
    """
    if fmt == "shoot":
        return format_draft_for_shoot(draft), "text/plain; charset=utf-8"
    if fmt == "markdown":
        return format_draft_for_markdown(draft), "text/markdown; charset=utf-8"
    if fmt in ("plain", "copy"):
        return format_draft_for_copy(draft), "text/plain; charset=utf-8"
    raise ValueError(f"unknown export format: {fmt!r}")
