"""Phase D.5.4 — chat_archival_audit migration + cron-chat-archival
Edge Function static-shape regression.

Neither the migration (Supabase SQL) nor the Edge Function (Deno) runs
under pytest. What *does* belong here is the set of assumptions a future
reader or D.5.4.b change would want locked in without spinning up a live
Supabase instance or Deno runtime:

  1. The migration declares the audit table with the plan-mandated
     columns + RLS enabled + a check on message_count.
  2. The Edge Function uses a 90-day cutoff (not 30 or 60 — easy to get
     wrong in a refactor), records the audit row *before* the delete so
     a failed delete doesn't orphan the audit trail, and is gated on
     the service_role token.
  3. Cascade behaviour (chat_messages auto-delete) is documented — we
     don't re-query or delete chat_messages directly.

Running Deno tests or hitting a Supabase local instance is a separate
follow-up; this file catches the class of regression that matters most
(cutoff getting fat-fingered, audit/delete order flipping, RLS
disabled).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION = REPO_ROOT / "supabase" / "migrations" / "20260501000003_chat_archival_audit.sql"
FUNCTION = REPO_ROOT / "supabase" / "functions" / "cron-chat-archival" / "index.ts"


@pytest.fixture(scope="module")
def migration_text() -> str:
    assert MIGRATION.exists(), f"Missing migration file: {MIGRATION}"
    return MIGRATION.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def function_text() -> str:
    assert FUNCTION.exists(), f"Missing Edge Function file: {FUNCTION}"
    return FUNCTION.read_text(encoding="utf-8")


class TestMigration:
    def test_declares_audit_table(self, migration_text: str) -> None:
        assert re.search(
            r"CREATE TABLE IF NOT EXISTS public\.chat_archival_audit",
            migration_text,
        )

    def test_includes_plan_mandated_columns(self, migration_text: str) -> None:
        for col in (
            "id",
            "session_id",
            "user_id",
            "message_count",
            "archived_at",
        ):
            assert re.search(rf"\b{col}\b", migration_text), (
                f"Migration missing expected column `{col}`"
            )

    def test_message_count_check_constraint_exists(self, migration_text: str) -> None:
        # A future migration shouldn't silently let negative counts land.
        assert re.search(
            r"chat_archival_audit_message_count_nonneg.*message_count\s*>=\s*0",
            migration_text,
            flags=re.DOTALL,
        )

    def test_rls_enabled(self, migration_text: str) -> None:
        assert "ENABLE ROW LEVEL SECURITY" in migration_text

    def test_no_authenticated_policy_defined(self, migration_text: str) -> None:
        # Audit table is service_role only. If a policy granting
        # authenticated access ever lands, make it a deliberate commit —
        # fail this test so a reviewer notices.
        assert "TO authenticated" not in migration_text
        assert "FOR ALL TO public" not in migration_text

    def test_user_id_cascade_to_null(self, migration_text: str) -> None:
        # User deletion must not cascade the audit row away — the row is
        # the record of the deletion itself.
        assert re.search(
            r"user_id\s+UUID\s+REFERENCES\s+auth\.users\(id\)\s+ON\s+DELETE\s+SET\s+NULL",
            migration_text,
            flags=re.IGNORECASE,
        )

    def test_indexes_on_archived_at_and_user_id(self, migration_text: str) -> None:
        assert "chat_archival_audit_archived_at_idx" in migration_text
        assert "chat_archival_audit_user_id_idx" in migration_text


class TestEdgeFunction:
    def test_uses_90_day_cutoff_not_30_or_60(self, function_text: str) -> None:
        # Fat-fingered constants are the single most likely regression on
        # a file like this. Assert the exact multiplier literally.
        assert re.search(r"NINETY_DAYS_MS\s*=\s*90\s*\*\s*86_?400\s*\*\s*1_?000", function_text)

    def test_gates_on_service_role_token(self, function_text: str) -> None:
        assert 'Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")' in function_text
        assert '"Unauthorized"' in function_text

    def test_inserts_audit_before_delete(self, function_text: str) -> None:
        # If the audit insert moves *after* the delete, a failed insert
        # would orphan deletions from the audit trail entirely.
        audit_pos = function_text.find('.from("chat_archival_audit").insert')
        delete_pos = function_text.find('.from("chat_sessions")\n        .delete()')
        assert audit_pos != -1, "Missing chat_archival_audit insert"
        assert delete_pos != -1, "Missing chat_sessions delete"
        assert audit_pos < delete_pos, (
            "Audit insert must precede chat_sessions delete — a failed insert "
            "must abort the delete for that session."
        )

    def test_skips_session_on_audit_failure(self, function_text: str) -> None:
        # The continue-after-error pattern is load-bearing for the partial-
        # failure semantics documented in the header. Snapshot-match the
        # control flow loosely.
        assert "stage: \"audit\"" in function_text
        assert "continue;" in function_text

    def test_does_not_read_or_delete_chat_messages_directly(self, function_text: str) -> None:
        # Cascade handles chat_messages; a direct delete would race the FK.
        # (A count() read on chat_messages IS allowed — we do that for the
        # audit. The prohibition is on `.delete()` specifically.)
        assert re.search(
            r'\.from\("chat_messages"\)\s*\.delete\(\)', function_text
        ) is None, "Edge function must not delete chat_messages directly; rely on FK cascade."

    def test_returns_archived_count_in_success_response(self, function_text: str) -> None:
        assert "archived_count" in function_text
        assert "errors" in function_text
