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

from getviews_pipeline.report_diagnostic import build_diagnostic_report
from getviews_pipeline.report_generic import build_generic_report
from getviews_pipeline.report_ideas import build_ideas_report
from getviews_pipeline.report_lifecycle import build_lifecycle_report
from getviews_pipeline.report_pattern import build_pattern_report
from getviews_pipeline.report_timing import build_timing_report
from getviews_pipeline.report_types import LifecycleMode, validate_and_store_report
from getviews_pipeline.supabase_client import get_service_client

logger = logging.getLogger(__name__)

# ── Idempotency — L1 in-process + L2 Postgres ─────────────────────────────────
#
# L1: in-process dict, 120s TTL. Fast path for quick retries from the same
#     Cloud Run instance. Unsafe across instances — L2 is the source of truth.
#
# L2: public.answer_session_idempotency table (migration 20260503000000).
#     INSERT ... ON CONFLICT DO NOTHING + SELECT pattern enforces uniqueness
#     at the database level so multiple instances never duplicate sessions.
#     Rows are retained for 24h; a daily janitor call (via /batch/analytics
#     or any cron) cleans them up.

_IDEMPOTENCY: dict[str, tuple[str, float]] = {}
_IDEMPOTENCY_TTL_SEC = 120.0


# Allowed turn kinds (mirrors the CHECK constraint on answer_turns.kind
# and the appendTurnKindForQuery mapping in src/routes/_app/intent-router.ts).
_TURN_KINDS: frozenset[str] = frozenset(
    {"primary", "timing", "creators", "script", "generic"}
)


def select_builder_for_turn(session_fmt: str, kind: str) -> str:
    """Map ``(session.format, turn.kind)`` to the report builder.

    The primary turn uses the session's declared format — that's what the
    session was created for. Follow-up turns were historically using the
    session format too (2026-04 audit: "The follow up questions generate
    the same report every time"), which made every follow-up rebuild the
    original pattern report regardless of whether the user asked a timing
    question, creator-search question, shot-list question, or generic
    follow-up. The turn's ``kind`` now drives builder selection for
    non-primary turns so the report actually reflects the new question.

    Mapping:
        - ``primary`` → session format (pattern / ideas / timing / generic /
          lifecycle / diagnostic)
        - ``timing``  → timing (adaptive window + posting-hour aggregates)
        - ``script``  → ideas (shot-list / draft feedback sits on ideas)
        - ``creators`` / ``generic`` / unknown → generic
    """
    if kind == "primary":
        return (
            session_fmt
            if session_fmt in (
                "pattern", "ideas", "timing", "generic", "lifecycle", "diagnostic",
            )
            else "pattern"
        )
    if kind == "timing":
        return "timing"
    if kind == "script":
        return "ideas"
    # "creators", "generic", or an unexpected value — the generic builder
    # surfaces corpus evidence + a free-form narrative, which is the
    # correct landing when the turn doesn't fit a structured builder.
    return "generic"


# Intent id → lifecycle mode discriminator. Kept centralised so the
# dispatcher and the intent router agree on which mode each intent
# produces. See ``artifacts/docs/report-template-prd-lifecycle.md``.
_INTENT_TO_LIFECYCLE_MODE: dict[str, LifecycleMode] = {
    "format_lifecycle_optimize": "format",
    "fatigue": "hook_fatigue",
    "subniche_breakdown": "subniche",
}


def lifecycle_mode_for_intent(intent_type: str | None) -> LifecycleMode:
    """Map ``answer_sessions.intent_type`` → ``LifecyclePayload.mode``.

    Defaults to ``"format"`` for unknown / missing intents so a lifecycle
    session never fails to build — the three mapped intents cover every
    case the intent router emits today.
    """
    if not intent_type:
        return "format"
    return _INTENT_TO_LIFECYCLE_MODE.get(intent_type, "format")

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


def _idem_db_get(sb: Any, user_id: str, idempotency_key: str) -> str | None:
    """Check L2 (Postgres) for an existing idempotency mapping.

    Returns the cached session_id string or None when no match found.
    """
    try:
        res = (
            sb.table("answer_session_idempotency")
            .select("session_id")
            .eq("user_id", user_id)
            .eq("idempotency_key", idempotency_key)
            .single()
            .execute()
        )
        data = res.data or {}
        return data.get("session_id")
    except Exception:
        # Table may not exist yet (pre-migration) or DB is momentarily unreachable.
        # Fail open — the insert path will catch any real duplicate via PK constraint.
        return None


def _idem_db_store(sb: Any, user_id: str, idempotency_key: str, session_id: str) -> None:
    """Upsert the idempotency mapping into L2 (Postgres). Never raises."""
    try:
        sb.table("answer_session_idempotency").insert(
            {
                "user_id": user_id,
                "idempotency_key": idempotency_key,
                "session_id": session_id,
            }
        ).on_conflict("user_id,idempotency_key").ignore().execute()
    except Exception as exc:
        logger.warning("[answer_session] idem_db_store failed: %s", exc)


def create_session(
    user_id: str,
    *,
    initial_q: str,
    intent_type: str,
    niche_id: int | None,
    format: str,
    idempotency_key: str | None,
) -> dict[str, Any]:
    """Insert answer_sessions (service role) with two-level idempotency.

    Checks L1 (in-process, 120s) then L2 (Postgres) before creating a new session.
    This prevents duplicate rows when multiple Cloud Run instances receive the same
    Idempotency-Key within the dedup window.
    """
    _prune_idempotency()
    sb = get_service_client()

    if idempotency_key:
        cache_key = f"{user_id}:{idempotency_key}"

        # L1: in-process cache (fast path, same instance)
        hit = _IDEMPOTENCY.get(cache_key)
        if hit and hit[0] and time.monotonic() - hit[1] <= _IDEMPOTENCY_TTL_SEC:
            sid = hit[0]
            row = sb.table("answer_sessions").select("*").eq("id", sid).single().execute()
            return row.data

        # L2: Postgres (cross-instance correctness)
        existing_sid = _idem_db_get(sb, user_id, idempotency_key)
        if existing_sid:
            # Warm L1 from L2 so subsequent same-instance calls hit the fast path
            _IDEMPOTENCY[cache_key] = (existing_sid, time.monotonic())
            row = sb.table("answer_sessions").select("*").eq("id", existing_sid).single().execute()
            return row.data

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
        cache_key = f"{user_id}:{idempotency_key}"
        # Store in L2 first (source of truth), then warm L1
        _idem_db_store(sb, user_id, idempotency_key, session_id)
        _IDEMPOTENCY[cache_key] = (session_id, time.monotonic())

    return row


def clean_expired_idempotency_rows(sb: Any | None = None) -> int:
    """Delete answer_session_idempotency rows older than 24h. Returns deleted count.

    Intended to be called from the daily batch/analytics cron. Fails open
    so a Supabase blip never breaks the analytics job.
    """
    if sb is None:
        sb = get_service_client()
    try:
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        res = (
            sb.table("answer_session_idempotency")
            .delete()
            .lt("created_at", cutoff)
            .execute()
        )
        deleted = len(res.data or [])
        logger.info("[answer_session] cleaned %d expired idempotency rows", deleted)
        return deleted
    except Exception as exc:
        logger.warning("[answer_session] clean_expired_idempotency_rows failed: %s", exc)
        return 0


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

    session_fmt = session.get("format") or "pattern"
    builder_fmt = select_builder_for_turn(session_fmt, kind)
    from getviews_pipeline.adaptive_window import ReportKind, choose_adaptive_window_days

    niche_pk = int(session.get("niche_id") or 0)
    # Lifecycle + diagnostic have their own sample-size floors in
    # ``adaptive_window.py`` (lifecycle=80, diagnostic=30) — without the
    # 2026-05-07 extension the dispatcher silently clamped both to the
    # pattern floor (30), which under-sized the lifecycle window.
    adaptive_kind: ReportKind = (
        builder_fmt
        if builder_fmt in ("pattern", "ideas", "timing", "lifecycle", "diagnostic")
        else "pattern"
    )
    window_days = choose_adaptive_window_days(niche_pk, adaptive_kind)
    logger.info(
        "[answer/turns] build session_fmt=%s kind=%s builder_fmt=%s niche=%s window_days=%s",
        session_fmt, kind, builder_fmt, niche_pk, window_days,
    )

    inner: dict[str, Any]
    try:
        if builder_fmt == "pattern":
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
        elif builder_fmt == "ideas":
            inner = build_ideas_report(
                niche_pk,
                query,
                session.get("intent_type") or "brief_generation",
                window_days=window_days,
            )
        elif builder_fmt == "timing":
            # ``content_calendar`` intent shares the timing template but
            # needs ``calendar_slots[]`` populated. The builder also
            # infers this from query keywords; passing the intent-level
            # hint makes the behaviour explicit for primary turns.
            timing_mode = (
                "calendar"
                if (session.get("intent_type") or "") == "content_calendar"
                else None
            )
            inner = build_timing_report(
                niche_pk, query, window_days=window_days, mode=timing_mode,
            )
        elif builder_fmt == "lifecycle":
            inner = build_lifecycle_report(
                niche_pk,
                query,
                lifecycle_mode_for_intent(session.get("intent_type")),
                window_days=window_days,
            )
        elif builder_fmt == "diagnostic":
            inner = build_diagnostic_report(
                niche_pk, query, window_days=window_days,
            )
        else:
            inner = build_generic_report(session.get("niche_id"), query)
    except Exception:
        logger.exception(
            "[answer/turns] build FAILED builder_fmt=%s niche=%s session=%s",
            builder_fmt, niche_pk, session_id,
        )
        raise

    try:
        payload_dict = validate_and_store_report(builder_fmt, inner)
    except Exception:
        logger.exception(
            "[answer/turns] validate FAILED builder_fmt=%s session=%s inner_keys=%s",
            builder_fmt, session_id, list(inner.keys()) if isinstance(inner, dict) else type(inner).__name__,
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
        fmt=builder_fmt,
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
