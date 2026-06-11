"""Credit compensation for failed paid pipelines (TD-1).

``decrement_credit`` runs before the expensive work on both paid paths
(`POST /answer/sessions/{id}/turns` and `POST /channel/diagnose`). When the
work fails afterwards — Gemini 429, builder crash, diagnose task error — the
charge must be compensated, otherwise the user pays for nothing.

``refund_credit`` is service-role-only (it mints credits; see migration
20260902000000), so refunds always go through the service client regardless
of which client took the deduction.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def refund_credits(user_id: str, amount: int, *, context: str) -> bool:
    """Best-effort compensating refund. Never raises.

    A refund failure must not mask the original pipeline error, so all
    exceptions are swallowed and logged at ERROR — the log line is the
    signal for manual compensation.
    """
    if amount <= 0:
        return False
    try:
        from getviews_pipeline.supabase_client import get_service_client

        rpc = (
            get_service_client()
            .rpc("refund_credit", {"p_user_id": user_id, "p_amount": amount})
            .execute()
        )
        if rpc.data is None:
            logger.error(
                "[credits] refund returned NULL (unknown user?) user=%s amount=%d ctx=%s",
                user_id, amount, context,
            )
            return False
        logger.info(
            "[credits] refunded user=%s amount=%d balance=%s ctx=%s",
            user_id, amount, rpc.data, context,
        )
        return True
    except Exception:
        logger.exception(
            "[credits] REFUND FAILED — manual compensation needed user=%s amount=%d ctx=%s",
            user_id, amount, context,
        )
        return False
