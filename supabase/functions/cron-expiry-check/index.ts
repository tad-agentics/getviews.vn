import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
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

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  const denied = requireService(req);
  if (denied) return denied;

  const url = Deno.env.get("SUPABASE_URL")!;
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const supabase = createClient(url, serviceKey);
  const appUrl = Deno.env.get("PUBLIC_APP_URL") ?? "https://getviews.vn";

  try {
    const now = new Date().toISOString();

    const { data: soon, error: q1 } = await supabase
      .from("subscriptions")
      .select("id, user_id, tier, expires_at, reminder_7d_sent_at, reminder_3d_sent_at, reminder_1d_sent_at")
      .eq("status", "active")
      .lte("expires_at", new Date(Date.now() + 7 * 86400_000).toISOString())
      .gte("expires_at", now);

    if (q1) throw q1;

    for (const row of soon ?? []) {
      const exp = new Date(row.expires_at).getTime();
      const days = Math.ceil((exp - Date.now()) / 86400_000);
      let template: "expiry_reminder_7d" | "expiry_reminder_3d" | "expiry_reminder_1d" | null = null;
      let field: "reminder_7d_sent_at" | "reminder_3d_sent_at" | "reminder_1d_sent_at" | null = null;

      if (days <= 7 && days > 3 && !row.reminder_7d_sent_at) {
        template = "expiry_reminder_7d";
        field = "reminder_7d_sent_at";
      } else if (days <= 3 && days > 1 && !row.reminder_3d_sent_at) {
        template = "expiry_reminder_3d";
        field = "reminder_3d_sent_at";
      } else if (days <= 1 && !row.reminder_1d_sent_at) {
        template = "expiry_reminder_1d";
        field = "reminder_1d_sent_at";
      }

      if (!template || !field) continue;

      const { data: profile } = await supabase.from("profiles").select("email, display_name").eq("id", row.user_id).single();
      if (!profile?.email) continue;

      await fetch(`${url}/functions/v1/send-email`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${serviceKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          template,
          to: profile.email,
          data: {
            display_name: profile.display_name ?? "",
            tier: row.tier,
            expires_at: row.expires_at,
            renewal_url: `${appUrl}/app/settings`,
          },
        }),
      });

      await supabase.from("subscriptions").update({ [field]: now }).eq("id", row.id);
    }

    const { data: expired, error: q2 } = await supabase
      .from("subscriptions")
      .select("id, user_id")
      .eq("status", "active")
      .lt("expires_at", now);

    if (q2) throw q2;

    const seen = new Set<string>();
    for (const row of expired ?? []) {
      await supabase.from("subscriptions").update({ status: "expired" }).eq("id", row.id);
      if (seen.has(row.user_id)) continue;
      seen.add(row.user_id);
      await supabase
        .from("profiles")
        .update({
          subscription_tier: "free",
        })
        .eq("id", row.user_id);
    }

    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error(e);
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
