"""Phase C.1 — answer_sessions / answer_turns orchestration (Cloud Run).

D.2.3 additions: server-side usage-event emission for
``classifier_low_confidence`` + ``pattern_what_stalled_empty`` so the
D.5.1 cost / quality dashboard can attribute weak classifier rounds and
empty Pattern diagnoses back to their source sessions.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from getviews_pipeline.report_diagnostic import build_diagnostic_report
from getviews_pipeline.report_generic import build_generic_report
from getviews_pipeline.report_ideas import build_ideas_report
from getviews_pipeline.report_lifecycle import build_lifecycle_report
from getviews_pipeline.report_pattern import build_pattern_report
from getviews_pipeline.report_script import build_script_report
from getviews_pipeline.report_timing import build_timing_report
from getviews_pipeline.report_types import LifecycleMode, validate_and_store_report
from getviews_pipeline.step_events import emit, emit_sentinel, step_error
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
          lifecycle / diagnostic / video / script)
        - ``timing``  → timing (adaptive window + posting-hour aggregates)
        - ``script``  → 6-shot script report (shot-list intent)
        - ``creators`` / ``generic`` / unknown → generic
    """
    if kind == "primary":
        return (
            session_fmt
            if session_fmt in (
                "pattern",
                "ideas",
                "timing",
                "generic",
                "lifecycle",
                "diagnostic",
                "video",
                "script",
            )
            else "pattern"
        )
    if kind == "timing":
        return "timing"
    if kind == "script":
        return "script"
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

# D.2.3 — classifier confidence thresholds. Treats < 0.6 as "not
# confident enough to ship a high-quality narrative." The low-confidence
# event fires so D.5.1 can surface how often paid turns run on shaky
# classifications. The historical sibling ``GEMINI_DISAGREE_WIN_MIN_CONFIDENCE``
# (0.3 — used by the Phase C.0.1 deterministic-vs-Gemini merger) was
# removed L1.5 audit when ``merge_deterministic_with_gemini`` was deleted.
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
        # supabase-py 2.x: insert() has no on_conflict; use upsert + ignore_duplicates
        # → PostgREST ON CONFLICT DO NOTHING on (user_id, idempotency_key).
        sb.table("answer_session_idempotency").upsert(
            {
                "user_id": user_id,
                "idempotency_key": idempotency_key,
                "session_id": session_id,
            },
            on_conflict="user_id,idempotency_key",
            ignore_duplicates=True,
        ).execute()
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
        from datetime import datetime, timedelta
        cutoff = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
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
    step_queue: asyncio.Queue | None = None,
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

    session_fmt = session.get("format") or "pattern"
    builder_fmt = select_builder_for_turn(session_fmt, kind)

    def _deduct_one_credit(u: Any) -> None:
        rpc = u.rpc("decrement_credit", {"p_user_id": user_id}).execute()
        if rpc.data is None:
            logger.warning(
                "[answer/turns] insufficient_credits user=%s session=%s",
                user_id,
                session_id,
            )
            raise RuntimeError("insufficient_credits")

    sb_user: Any | None = None

    def _user_client() -> Any:
        nonlocal sb_user
        if sb_user is None:
            sb_user = user_supabase(access_token)
        return sb_user

    # Script turns cost 3 credits (B.4 parity); generic follow-ups stay free.
    if builder_fmt == "script":
        u = _user_client()
        for _ in range(3):
            _deduct_one_credit(u)
    elif kind == "primary":
        _deduct_one_credit(_user_client())
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
                step_queue=step_queue,
            )
        elif builder_fmt == "ideas":
            inner = build_ideas_report(
                niche_pk,
                query,
                session.get("intent_type") or "brief_generation",
                window_days=window_days,
                step_queue=step_queue,
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
                niche_pk,
                query,
                window_days=window_days,
                mode=timing_mode,
                step_queue=step_queue,
            )
        elif builder_fmt == "lifecycle":
            inner = build_lifecycle_report(
                niche_pk,
                query,
                lifecycle_mode_for_intent(session.get("intent_type")),
                window_days=window_days,
                step_queue=step_queue,
            )
        elif builder_fmt == "diagnostic":
            inner = build_diagnostic_report(
                niche_pk, query, window_days=window_days, step_queue=step_queue,
            )
        elif builder_fmt == "video":
            # Bridges to /video/analyze pipeline (corpus-cached) +
            # on-demand fallback (PR #286). The user-scoped client
            # we built above for credit deduction also services the
            # corpus-row lookup — RLS guarantees visibility but we
            # already created sb_user only inside the credit branch,
            # so re-derive here for non-primary turns too.
            from getviews_pipeline.report_video import build_video_report

            sb_user_for_video = user_supabase(access_token)
            inner = build_video_report(
                service_sb=sb_srv,
                user_sb=sb_user_for_video,
                query=query,
                step_queue=step_queue,
            )
        elif builder_fmt == "script":
            inner = build_script_report(
                service_sb=sb_srv,
                user_sb=_user_client(),
                user_id=user_id,
                query=query,
                niche_id=niche_pk,
                step_queue=step_queue,
            )
        else:
            # AQ-9 — pass turn_context from session so Gemini can reference
            # the primary turn's top hooks when answering generic follow-ups.
            inner = build_generic_report(
                session.get("niche_id"),
                query,
                step_queue=step_queue,
                turn_context=session.get("turn_context") if kind != "primary" else None,
            )
    except RuntimeError as exc:
        _code = str(exc)
        # Carousel-specific errors need a Vietnamese step_error before the sentinel
        # so the frontend shows a meaningful message instead of a generic stream drop.
        _CAROUSEL_ERROR_MESSAGES: dict[str, str] = {
            "carousel_download_failed": (
                "GetViews chưa tải được ảnh carousel này — CDN TikTok đang chặn tải xuống. "
                "Thử lại sau ít phút hoặc hỏi 'Carousel skincare đang trending?' để "
                "xem xu hướng ngách này."
            ),
            "carousel_no_images": (
                "Bài ảnh TikTok chưa hỗ trợ — EnsembleData không trả về ảnh slide. "
                "Thử hỏi 'Carousel skincare đang trending?' để xem xu hướng ngách này."
            ),
        }
        if _code in _CAROUSEL_ERROR_MESSAGES and step_queue is not None:
            emit(step_queue, step_error(code=_code, message_vi=_CAROUSEL_ERROR_MESSAGES[_code]))
        else:
            logger.exception(
                "[answer/turns] build FAILED builder_fmt=%s niche=%s session=%s",
                builder_fmt, niche_pk, session_id,
            )
        raise
    except Exception as exc:
        # Surface Gemini 429 (quota exhausted / rate limit) as a user-readable message
        # instead of a generic stream drop. Check by string because google-genai's
        # ClientError is not always importable at the top level without version pinning.
        _exc_str = str(exc)
        if "429" in _exc_str or "RESOURCE_EXHAUSTED" in _exc_str:
            logger.warning(
                "[answer/turns] Gemini 429 RESOURCE_EXHAUSTED builder_fmt=%s session=%s",
                builder_fmt, session_id,
            )
            if step_queue is not None:
                emit(
                    step_queue,
                    step_error(
                        code="gemini_quota_exceeded",
                        message_vi=(
                            "Dịch vụ AI đang quá tải — thử lại sau 1-2 phút. "
                            "Nếu lỗi tiếp diễn, liên hệ hỗ trợ."
                        ),
                    ),
                )
        else:
            logger.exception(
                "[answer/turns] build FAILED builder_fmt=%s niche=%s session=%s",
                builder_fmt, niche_pk, session_id,
            )
        raise
    finally:
        if step_queue is not None:
            emit_sentinel(step_queue)

    try:
        payload_dict = validate_and_store_report(builder_fmt, inner)
    except Exception:
        logger.exception(
            "[answer/turns] validate FAILED builder_fmt=%s session=%s inner_keys=%s",
            builder_fmt, session_id, list(inner.keys()) if isinstance(inner, dict) else type(inner).__name__,
        )
        raise

    confidence_label = _confidence_label(classifier_confidence_score)

    if builder_fmt == "script":
        credits_used = 3
    elif kind == "primary":
        credits_used = 1
    else:
        credits_used = 0
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

    # AQ-9 — After primary turn: extract top hook names and evidence video IDs
    # from the payload and write turn_context to the session row so follow-up
    # builder dispatch can surface them without an extra DB query.
    session_update: dict = {"updated_at": datetime.now(UTC).isoformat()}
    if kind == "primary" and isinstance(payload_dict, dict):
        try:
            top_hook_types = [
                str(f.get("pattern") or "")
                for f in (payload_dict.get("findings") or [])[:3]
                if f.get("pattern")
            ]
            evidence_video_ids = [
                str(v.get("video_id") or "")
                for v in (payload_dict.get("evidence_videos") or [])[:5]
                if v.get("video_id")
            ]
            if top_hook_types or evidence_video_ids:
                session_update["turn_context"] = {
                    "top_hook_types": top_hook_types,
                    "evidence_video_ids": evidence_video_ids,
                }
                logger.info(
                    "[answer/turns] turn_context stored session=%s hooks=%s evidence_ids=%s",
                    session_id, top_hook_types, evidence_video_ids,
                )
        except Exception:
            logger.warning(
                "[answer/turns] turn_context extraction failed session=%s",
                session_id, exc_info=True,
            )

    sb_srv.table("answer_sessions").update(session_update).eq("id", session_id).execute()
    return {"turn": turn, "payload": payload_dict}


def list_sessions(
    user_id: str,
    *,
    limit: int = 20,
    include_archived: bool = False,
    scope: str = "30d",
    cursor: str | None = None,
) -> list[dict[str, Any]]:
    """List sessions for Studio sidebar / history. ``scope=30d`` filters ``updated_at`` to last 30 days.

    Keyset pagination: pass ``cursor`` = ``updated_at`` ISO from the previous page's last row
    (strictly older rows). Ordered by ``updated_at DESC``.

    A2 — Each row carries a denormalized ``turn_count`` so the FE
    sidebar can render "N lượt" per row without N+1 lookups. The
    count comes from one extra batched ``answer_turns`` query keyed by
    the page's session ids; sessions with no turns get ``turn_count=0``.
    """
    sb = get_service_client()
    q = sb.table("answer_sessions").select("*").eq("user_id", user_id)
    if not include_archived:
        q = q.is_("archived_at", "null")
    if scope == "30d":
        cutoff = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        q = q.gte("updated_at", cutoff)
    if cursor:
        q = q.lt("updated_at", cursor)
    res = q.order("updated_at", desc=True).limit(limit).execute()
    sessions: list[dict[str, Any]] = list(res.data or [])
    if not sessions:
        return sessions

    session_ids = [s["id"] for s in sessions if s.get("id")]
    counts: dict[str, int] = {}
    if session_ids:
        try:
            turns_res = (
                sb.table("answer_turns")
                .select("session_id")
                .in_("session_id", session_ids)
                .execute()
            )
            for row in turns_res.data or []:
                sid = row.get("session_id")
                if sid:
                    counts[sid] = counts.get(sid, 0) + 1
        except Exception:
            # Drawer renders without ``turn_count`` rather than failing the
            # whole list query — non-fatal enrichment.
            counts = {}

    for s in sessions:
        s["turn_count"] = int(counts.get(s.get("id"), 0))
    return sessions


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
