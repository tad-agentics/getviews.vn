"""Phase C.1 — answer_sessions / answer_turns orchestration (Cloud Run)."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from getviews_pipeline.report_generic import build_generic_report
from getviews_pipeline.report_ideas import build_ideas_report
from getviews_pipeline.report_pattern import ANSWER_FIXTURE_PATTERN, build_pattern_report
from getviews_pipeline.report_timing import build_timing_report
from getviews_pipeline.report_types import validate_and_store_report
from getviews_pipeline.supabase_client import get_service_client

_IDEMPOTENCY: dict[str, tuple[str, float]] = {}
_IDEMPOTENCY_TTL_SEC = 120.0


def _prune_idempotency() -> None:
    now = time.monotonic()
    dead = [k for k, (_, ts) in _IDEMPOTENCY.items() if now - ts > _IDEMPOTENCY_TTL_SEC]
    for k in dead:
        del _IDEMPOTENCY[k]


def create_session(
    user_id: str,
    *,
    initial_q: str,
    intent_type: str,
    niche_id: int | None,
    format: str,
    idempotency_key: str | None,
) -> dict[str, Any]:
    """Insert answer_sessions (service role)."""
    _prune_idempotency()
    if idempotency_key:
        cache_key = f"{user_id}:{idempotency_key}"
        hit = _IDEMPOTENCY.get(cache_key)
        if (
            hit
            and hit[0]
            and time.monotonic() - hit[1] <= _IDEMPOTENCY_TTL_SEC
        ):
            sid = hit[0]
            sb = get_service_client()
            row = sb.table("answer_sessions").select("*").eq("id", sid).single().execute()
            return row.data

    sb = get_service_client()
    title = (initial_q[:80] + "…") if len(initial_q) > 80 else initial_q
    insert_payload: dict[str, Any] = {
        "user_id": user_id,
        "initial_q": initial_q,
        "intent_type": intent_type,
        "format": format,
        "title": title or "Phiên nghiên cứu",
    }
    if niche_id is not None:
        insert_payload["niche_id"] = niche_id
    res = sb.table("answer_sessions").insert(insert_payload).execute()
    row = res.data[0] if isinstance(res.data, list) else res.data
    session_id = row["id"]
    if idempotency_key:
        _IDEMPOTENCY[f"{user_id}:{idempotency_key}"] = (session_id, time.monotonic())
    return row


def append_turn(
    user_id: str,
    access_token: str,
    session_id: str,
    *,
    query: str,
    kind: str,
) -> dict[str, Any]:
    """Append validated turn; primary kind deducts credit via user client (caller passes token)."""
    from getviews_pipeline.supabase_client import user_supabase

    sb_srv = get_service_client()
    sess = (
        sb_srv.table("answer_sessions")
        .select("id,user_id,format,niche_id")
        .eq("id", session_id)
        .single()
        .execute()
    )
    session = sess.data
    if not session or session["user_id"] != user_id:
        raise PermissionError("session_not_found")

    existing = (
        sb_srv.table("answer_turns").select("turn_index").eq("session_id", session_id).execute()
    )
    max_idx = max((r["turn_index"] for r in (existing.data or [])), default=-1)
    turn_index = max_idx + 1

    if kind == "primary":
        sb_user = user_supabase(access_token)
        rpc = sb_user.rpc("decrement_credit", {"p_user_id": user_id}).execute()
        if rpc.data is False:
            raise RuntimeError("insufficient_credits")

    fmt = session.get("format") or "pattern"
    from getviews_pipeline.adaptive_window import ReportKind, choose_adaptive_window_days

    niche_pk = int(session.get("niche_id") or 0)
    adaptive_kind: ReportKind = fmt if fmt in ("pattern", "ideas", "timing") else "pattern"
    window_days = choose_adaptive_window_days(niche_pk, adaptive_kind)

    inner: dict[str, Any]
    if fmt == "pattern":
        inner = build_pattern_report(
            niche_pk,
            query,
            session.get("intent_type") or "trend_spike",
            window_days=window_days,
        )
    elif fmt == "ideas":
        inner = build_ideas_report(
            niche_pk,
            query,
            session.get("intent_type") or "brief_generation",
            window_days=window_days,
        )
    elif fmt == "timing":
        inner = build_timing_report(niche_pk, query, window_days=window_days)
    else:
        inner = build_generic_report(session.get("niche_id"), query)

    payload_dict = validate_and_store_report(fmt, inner)

    credits_used = 1 if kind == "primary" else 0
    row_ins = {
        "session_id": session_id,
        "turn_index": turn_index,
        "kind": kind,
        "query": query,
        "payload": payload_dict,
        "classifier_confidence": "medium",
        "intent_confidence": "high" if kind == "primary" else "medium",
        "cloud_run_run_id": str(uuid.uuid4()),
        "credits_used": credits_used,
    }
    ins = sb_srv.table("answer_turns").insert(row_ins).execute()
    turn = ins.data[0] if isinstance(ins.data, list) else ins.data

    from datetime import datetime, timezone

    sb_srv.table("answer_sessions").update(
        {"updated_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", session_id).execute()
    return {"turn": turn, "payload": payload_dict}


def list_sessions(
    user_id: str,
    *,
    limit: int = 20,
    include_archived: bool = False,
    scope: str = "30d",
    cursor: str | None = None,
) -> list[dict[str, Any]]:
    """List sessions for drawer / history. ``scope=30d`` filters ``updated_at`` to last 30 days.

    Keyset pagination: pass ``cursor`` = ``updated_at`` ISO from the previous page's last row
    (strictly older rows). Ordered by ``updated_at DESC``.
    """
    sb = get_service_client()
    q = sb.table("answer_sessions").select("*").eq("user_id", user_id)
    if not include_archived:
        q = q.is_("archived_at", "null")
    if scope == "30d":
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        q = q.gte("updated_at", cutoff)
    if cursor:
        q = q.lt("updated_at", cursor)
    res = q.order("updated_at", desc=True).limit(limit).execute()
    return res.data or []


def get_session_turns(user_id: str, session_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sb = get_service_client()
    s = sb.table("answer_sessions").select("*").eq("id", session_id).single().execute()
    session = s.data
    if not session or session["user_id"] != user_id:
        raise PermissionError("session_not_found")
    t = (
        sb.table("answer_turns")
        .select("*")
        .eq("session_id", session_id)
        .order("turn_index", desc=False)
        .execute()
    )
    return session, t.data or []


def patch_session(
    user_id: str,
    session_id: str,
    *,
    title: str | None = None,
    archived_at: str | None = None,
) -> dict[str, Any]:
    sb = get_service_client()
    s = sb.table("answer_sessions").select("user_id").eq("id", session_id).single().execute()
    if not s.data or s.data["user_id"] != user_id:
        raise PermissionError("session_not_found")
    upd: dict[str, Any] = {}
    if title is not None:
        upd["title"] = title
    if archived_at is not None:
        upd["archived_at"] = archived_at
    if not upd:
        return s.data
    sb.table("answer_sessions").update(upd).eq("id", session_id).execute()
    return sb.table("answer_sessions").select("*").eq("id", session_id).single().execute().data
