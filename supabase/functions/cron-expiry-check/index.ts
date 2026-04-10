import { createClient, type SupabaseClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { corsHeaders } from "../_shared/cors.ts";

function requireService(req: Request): Response | null {
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const auth = req.headers.get("Authorization") ?? "";
  const token = auth.replace(/^Bearer\s+/i, "").trim();
  if (token !== serviceKey) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
  return null;
}

type ReminderTemplate = "expiry_reminder_7d" | "expiry_reminder_3d" | "expiry_reminder_1d";
type ReminderField = "reminder_7d_sent_at" | "reminder_3d_sent_at" | "reminder_1d_sent_at";

async function invokeSendEmail(
  functionsUrl: string,
  serviceKey: string,
  to: string,
  template: ReminderTemplate,
  data: { name: string; expiry_date: string; site_url: string },
): Promise<boolean> {
  const res = await fetch(`${functionsUrl}/functions/v1/send-email`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${serviceKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ template, to, data }),
  });
  if (!res.ok) {
    const text = await res.text();
    console.error("send-email failed", res.status, text);
    return false;
  }
  return true;
}

function formatExpiryVi(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("vi-VN", { day: "numeric", month: "long", year: "numeric" });
}

/** Exclusive windows so one subscription does not receive 7d+3d+1d in the same cron run. */
async function sendReminderBatch(args: {
  supabase: SupabaseClient;
  functionsUrl: string;
  serviceKey: string;
  siteUrl: string;
  lowerIso: string;
  upperIso: string;
  reminderNullField: ReminderField;
  template: ReminderTemplate;
}): Promise<number> {
  const { supabase, functionsUrl, serviceKey, siteUrl, lowerIso, upperIso, reminderNullField, template } = args;

  const { data: rows, error } = await supabase
    .from("subscriptions")
    .select("id, user_id, expires_at")
    .eq("status", "active")
    .is(reminderNullField, null)
    .gt("expires_at", lowerIso)
    .lte("expires_at", upperIso);

  if (error) throw error;

  let sent = 0;
  for (const row of rows ?? []) {
    const { data: profile } = await supabase
      .from("profiles")
      .select("email, display_name")
      .eq("id", row.user_id)
      .single();
    if (!profile?.email) continue;

    const name = profile.display_name?.trim() || "bạn";
    const expiry_date = formatExpiryVi(row.expires_at);
    const ok = await invokeSendEmail(functionsUrl, serviceKey, profile.email, template, {
      name,
      expiry_date,
      site_url: siteUrl,
    });
    if (!ok) continue;

    const { error: upErr } = await supabase
      .from("subscriptions")
      .update({ [reminderNullField]: new Date().toISOString() })
      .eq("id", row.id);
    if (upErr) {
      console.error("reminder timestamp update failed", row.id, upErr);
      continue;
    }
    sent += 1;
  }
  return sent;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  const denied = requireService(req);
  if (denied) return denied;

  const functionsUrl = Deno.env.get("SUPABASE_URL")!;
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const supabase = createClient(functionsUrl, serviceKey);
  const siteUrl = (Deno.env.get("SITE_URL") ?? Deno.env.get("PUBLIC_APP_URL") ?? "https://getviews.vn").replace(/\/$/, "");

  const now = new Date();
  const nowIso = now.toISOString();
  const plus1 = new Date(now.getTime() + 86400_000).toISOString();
  const plus3 = new Date(now.getTime() + 3 * 86400_000).toISOString();
  const plus7 = new Date(now.getTime() + 7 * 86400_000).toISOString();

  try {
    const reminders_1d = await sendReminderBatch({
      supabase,
      functionsUrl,
      serviceKey,
      siteUrl,
      lowerIso: nowIso,
      upperIso: plus1,
      reminderNullField: "reminder_1d_sent_at",
      template: "expiry_reminder_1d",
    });

    const reminders_3d = await sendReminderBatch({
      supabase,
      functionsUrl,
      serviceKey,
      siteUrl,
      lowerIso: plus1,
      upperIso: plus3,
      reminderNullField: "reminder_3d_sent_at",
      template: "expiry_reminder_3d",
    });

    const reminders_7d = await sendReminderBatch({
      supabase,
      functionsUrl,
      serviceKey,
      siteUrl,
      lowerIso: plus3,
      upperIso: plus7,
      reminderNullField: "reminder_7d_sent_at",
      template: "expiry_reminder_7d",
    });

    const { data: expiredRows, error: exErr } = await supabase
      .from("subscriptions")
      .select("id, user_id")
      .eq("status", "active")
      .lt("expires_at", nowIso);

    if (exErr) throw exErr;

    const userIds = new Set<string>();
    for (const row of expiredRows ?? []) {
      const { error: u1 } = await supabase.from("subscriptions").update({ status: "expired" }).eq("id", row.id);
      if (u1) throw u1;
      userIds.add(row.user_id);
    }

    for (const uid of userIds) {
      const { error: u2 } = await supabase
        .from("profiles")
        .update({ subscription_tier: "free", deep_credits_remaining: 0 })
        .eq("id", uid);
      if (u2) throw u2;
    }

    return new Response(
      JSON.stringify({
        reminders_7d,
        reminders_3d,
        reminders_1d,
        expired_count: expiredRows?.length ?? 0,
      }),
      {
        status: 200,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      },
    );
  } catch (e) {
    console.error(e);
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
