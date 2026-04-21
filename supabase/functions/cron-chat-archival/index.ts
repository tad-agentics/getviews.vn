/**
 * cron-chat-archival — Phase D.5.4
 *
 * Nightly (03:00 UTC via scheduled trigger — wire it in the Supabase
 * dashboard) hard-deletes every `chat_sessions` row with
 * `updated_at < now() - 90 days` and records the deletion in
 * `chat_archival_audit` for support / retention compliance.
 *
 * Hard delete is the documented contract (phase-c-plan.md §C.7 + the
 * `chat_sessions` migration _034 soft-delete removal). Cascade handles
 * `chat_messages` via the existing FK; we never read or delete messages
 * directly here.
 *
 * Auth: requires the Authorization header to match SUPABASE_SERVICE_ROLE_KEY.
 * Supabase's scheduled invoker passes this automatically; external callers
 * get 401.
 *
 * Returns:
 *   { archived_count: N, errors: [] }   on success (N may be 0)
 *   { error: "..." }                    on setup failure
 *
 * Partial-failure semantics: if a single session's audit insert fails,
 * the function logs it in `errors[]` and continues with the next session.
 * The delete only runs when the audit row landed, so a session that fails
 * audit stays in the DB for the next run to retry.
 */
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { corsHeaders } from "../_shared/cors.ts";

const NINETY_DAYS_MS = 90 * 86_400 * 1_000;

interface ArchivalError {
  session_id: string;
  stage: "audit" | "delete";
  message: string;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const auth = req.headers.get("Authorization") ?? "";
  const token = auth.replace(/^Bearer\s+/i, "").trim();
  if (token !== serviceKey) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const url = Deno.env.get("SUPABASE_URL")!;
  const supabase = createClient(url, serviceKey);
  const cutoffIso = new Date(Date.now() - NINETY_DAYS_MS).toISOString();

  try {
    // 1. Pull every session whose most recent activity is past the window.
    //    We fetch id + user_id + timestamps so the audit row can carry them;
    //    no chat_messages data is exposed by this query.
    const { data: stale, error: listErr } = await supabase
      .from("chat_sessions")
      .select("id, user_id, created_at, updated_at")
      .lt("updated_at", cutoffIso);

    if (listErr) throw listErr;

    const errors: ArchivalError[] = [];
    let archivedCount = 0;

    for (const row of stale ?? []) {
      const sessionId = row.id as string;

      // 2. Count messages at archive time — the audit captures live count,
      //    not a cached one, so even if a past migration neglected to
      //    maintain a denormalised counter the number stays honest.
      const { count, error: countErr } = await supabase
        .from("chat_messages")
        .select("*", { count: "exact", head: true })
        .eq("session_id", sessionId);

      if (countErr) {
        errors.push({ session_id: sessionId, stage: "audit", message: String(countErr) });
        continue;
      }

      // 3. Insert the audit row. If this fails, we skip the delete — the
      //    session sticks around for the next run to retry. Better than
      //    a silent delete with no audit trail.
      const { error: auditErr } = await supabase.from("chat_archival_audit").insert({
        session_id: sessionId,
        user_id: row.user_id,
        message_count: count ?? 0,
        session_created_at: row.created_at,
        session_updated_at: row.updated_at,
      });

      if (auditErr) {
        errors.push({ session_id: sessionId, stage: "audit", message: String(auditErr) });
        continue;
      }

      // 4. Hard-delete the session; FK cascade drops chat_messages.
      const { error: delErr } = await supabase
        .from("chat_sessions")
        .delete()
        .eq("id", sessionId);

      if (delErr) {
        errors.push({ session_id: sessionId, stage: "delete", message: String(delErr) });
        continue;
      }

      archivedCount += 1;
    }

    return new Response(
      JSON.stringify({ archived_count: archivedCount, errors }),
      {
        status: 200,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      },
    );
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
