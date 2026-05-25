"""Supabase client helpers for Cloud Run.

Two client types:

1. user_supabase(access_token) — RLS-scoped, runs as the calling user.
   Use for credit deduction, is_processing, and other user-scoped RPCs.

2. get_service_client() — service_role key, bypasses RLS.
   Use ONLY for batch operations (corpus ingest, analytics, trend velocity).
   Never use for user-facing request handlers.
"""

from __future__ import annotations

import os
from typing import Any

from supabase import Client, ClientOptions, create_client


def _require(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise ValueError(f"Environment variable {name!r} is not set")
    return val


def user_supabase(access_token: str) -> Client:
    """Return a Supabase client authenticated as the calling user.

    All queries run through RLS as that user. Use this for credit deduction
    (decrement_credit RPC) and is_processing updates.
    """
    url = _require("SUPABASE_URL")
    anon_key = _require("SUPABASE_ANON_KEY")
    return create_client(
        url,
        anon_key,
        options=ClientOptions(
            headers={"Authorization": f"Bearer {access_token}"},
            auto_refresh_token=False,
            persist_session=False,
        ),
    )


def get_service_client() -> Any:
    """Return a Supabase client with service_role key (bypasses RLS).

    Use ONLY for batch/admin operations: corpus ingest, analytics,
    trend velocity, signal grading. Never for user-facing requests.
    """
    url = _require("SUPABASE_URL")
    key = _require("SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)
