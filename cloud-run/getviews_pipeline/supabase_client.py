"""User-scoped Supabase client for Cloud Run request handlers.

Pattern mirrors api/chat.ts userSupabase():

    function userSupabase(accessToken: string) {
      return createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
        auth: { persistSession: false, autoRefreshToken: false },
        global: { headers: { Authorization: `Bearer ${accessToken}` } },
      });
    }

Using the anon key + the caller's JWT means all queries run through RLS as
that user — credits and chat_messages operations are correctly scoped.

DO NOT use SERVICE_ROLE_KEY here — it bypasses RLS.
"""

from __future__ import annotations

import os

from supabase import ClientOptions, Client, create_client


def _require(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise ValueError(f"Environment variable {name!r} is not set")
    return val


def user_supabase(access_token: str) -> Client:
    """Return a Supabase client authenticated as the calling user.

    All queries run through RLS as that user — matching the pattern in
    api/chat.ts. Use this for credit deduction (decrement_credit RPC),
    is_processing updates, and chat_messages inserts.
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
