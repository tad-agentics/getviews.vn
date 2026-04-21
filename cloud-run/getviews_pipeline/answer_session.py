"""Phase C.1 — answer_sessions / answer_turns orchestration (Cloud Run).

D.2.3 additions: server-side usage-event emission for
``classifier_low_confidence`` + ``pattern_what_stalled_empty`` so the
D.5.1 cost / quality dashboard can attribute weak classifier rounds and
empty Pattern diagnoses back to their source sessions.
"""

from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

_IDEMPOTENCY: dict[str, tuple[str, float]] = {}
_IDEMPOTENCY_TTL_SEC = 120.0

# D.2.3 — classifier confidence thresholds. Aligned with Vercel Edge's
# GEMINI_DISAGREE_WIN_MIN_CONFIDENCE (0.3) and the intent-router's practice
# of treating < 0.6 as "not confident enough to ship a high-quality
# narrative." The low-confidence event fires so D.5.1 can surface how
# often paid turns run on shaky classifications.
CLASSIFIER_LOW_CONFIDENCE_THRESHOLD = 0.6
CLASSIFIER_MEDIUM_CONFIDENCE_THRESHOLD = 0.8


def _confidence_label(score: float | None) -> str:
    """Numeric confidence → enum label for ``answer_turns.classifier_confidence``."""
    if score is None:
        return "medium"
    if score >= CLASSIFIER_MEDIUM_CONFIDENCE_THRESHOLD:
        return "high"
    if score >= CLASSIFIER_LOW_CONFIDENCE_THRESHOLD:
        return "medium"
    return "low"


def log_usage_event_server(
    sb: Any,
    *,
    user_id: str,
    action: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Fire-and-forget server-side insert into ``public.usage_events``.

    Uses the service client to bypass RLS (caller scopes `user_id` itself).
    Never raises — a logging failure shouldn't break the /answer turn.
    """
    try:
        sb.table("usage_events").insert(
            {
                "user_id": user_id,
                "action": action,
                "metadata": metadata or {},
            }
        ).execute()
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("[usage_events] server emit failed action=%s: %s", action, exc)


def resolve_turn_observability_events(
    *,
    fmt: str,
    payload: dict[str, Any] | None,
    classifier_confidence_score: float | None,
    intent_id: str | None,
    niche_id: int | None,
    session_id: str,
    turn_index: int,
) -> list[tuple[str, dict[str, Any]]]:
    """Pure predicate for D.2.3 observability events.

    Returns a list of ``(action, metadata)`` pairs ready for
    ``log_usage_event_server``. Extracted so the event firing logic is
    testable in isolation from the full ``append_turn`` call chain.
    """
    out: list[tuple[str, dict[str, Any]]] = []
    if (
        classifier_confidence_score is not None
        and classifier_confidence_score < CLASSIFIER_LOW_CONFIDENCE_THRESHOLD
    ):
        out.append(
            (
                "classifier_low_confidence",
                {
                    "intent_id": intent_id,
                    "confidence_score": round(float(classifier_confidence_score), 4),
                    "session_id": session_id,
                    "turn_index": turn_index,
                },
            )
        )
    if fmt == "pattern":
        body = payload or {}
        ws = list(body.get("what_stalled") or [])
        conf = body.get("confidence") or {}
        ws_reason = conf.get("what_stalled_reason")
        if not ws and ws_reason is not None:
            out.append(
                (
                    "pattern_what_stalled_empty",
                    {
                        "niche_id": niche_id,
                        "reason": ws_reason,
                        "session_id": session_id,
                        "turn_index": turn_index,
                    },
                )
            )
    return out


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
    classifier_confidence_score: float | None = None,
    intent_id: str | None = None,
) -> dict[str, Any]:
    """Append validated turn; primary kind deducts credit via user client (caller passes token).

    D.2.3 kwargs:
      - ``classifier_confidence_score`` (0.0–1.0) from the Vercel Edge
        classifier round. Derives the ``answer_turns.classifier_confidence``
        enum label and gates the ``classifier_low_confidence`` event.
      - ``intent_id`` is the classifier's ``primary`` label; included in
        the event metadata so D.5.1 can attribute low-confidence rates
        per intent.
    """
    from getviews_pipeline.supabase_client import user_supabase

    logger.info(
        "[answer/turns] append_turn user=%s session=%s kind=%s q_len=%d",
        user_id, session_id, kind, len(query or ""),
    )
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
        logger.warning(
            "[answer/turns] session_not_found session=%s user=%s hit=%s",
            session_id, user_id, bool(session),
        )
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
            logger.warning("[answer/turns] insufficient_credits user=%s session=%s", user_id, session_id)
            raise RuntimeError("insufficient_credits")

    fmt = session.get("format") or "pattern"
    from getviews_pipeline.adaptive_window import ReportKind, choose_adaptive_window_days

    niche_pk = int(session.get("niche_id") or 0)
    adaptive_kind: ReportKind = fmt if fmt in ("pattern", "ideas", "timing") else "pattern"
    window_days = choose_adaptive_window_days(niche_pk, adaptive_kind)
    logger.info(
        "[answer/turns] build fmt=%s niche=%s window_days=%s",
        fmt, niche_pk, window_days,
    )

    inner: dict[str, Any]
    try:
        if fmt == "pattern":
            # C.5.3 — auto-merge timing subreport on "post gì khi nào"
            # style queries (plan §A.4 Report + timing case; also covers
            # intent #18 content_calendar).
            from getviews_pipeline.intent_router import detect_pattern_subreports

            subs = detect_pattern_subreports(query)
            inner = build_pattern_report(
                niche_pk,
                query,
                session.get("intent_type") or "trend_spike",
                window_days=window_days,
                subreports=subs or None,
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
    except Exception:
        logger.exception(
            "[answer/turns] build FAILED fmt=%s niche=%s session=%s",
            fmt, niche_pk, session_id,
        )
        raise

    try:
        payload_dict = validate_and_store_report(fmt, inner)
    except Exception:
        logger.exception(
            "[answer/turns] validate FAILED fmt=%s session=%s inner_keys=%s",
            fmt, session_id, list(inner.keys()) if isinstance(inner, dict) else type(inner).__name__,
        )
        raise

    confidence_label = _confidence_label(classifier_confidence_score)
    credits_used = 1 if kind == "primary" else 0
    row_ins = {
        "session_id": session_id,
        "turn_index": turn_index,
        "kind": kind,
        "query": query,
        "payload": payload_dict,
        "classifier_confidence": confidence_label,
        "intent_confidence": "high" if kind == "primary" else "medium",
        "cloud_run_run_id": str(uuid.uuid4()),
        "credits_used": credits_used,
    }
    try:
        ins = sb_srv.table("answer_turns").insert(row_ins).execute()
    except Exception:
        logger.exception(
            "[answer/turns] persist FAILED session=%s turn_index=%s kind=%s",
            session_id, turn_index, kind,
        )
        raise
    turn = ins.data[0] if isinstance(ins.data, list) else ins.data
    logger.info(
        "[answer/turns] persisted session=%s turn_index=%s kind=%s payload_kind=%s",
        session_id, turn_index, kind,
        (payload_dict or {}).get("kind") if isinstance(payload_dict, dict) else None,
    )

    # D.2.3 — observability events. Both go through the service-client
    # insert so usage_events RLS policies don't reject; failures are
    # swallowed inside log_usage_event_server.
    for action, metadata in resolve_turn_observability_events(
        fmt=fmt,
        payload=payload_dict,
        classifier_confidence_score=classifier_confidence_score,
        intent_id=intent_id,
        niche_id=session.get("niche_id"),
        session_id=session_id,
        turn_index=turn_index,
    ):
        log_usage_event_server(sb_srv, user_id=user_id, action=action, metadata=metadata)

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
