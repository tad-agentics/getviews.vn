import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { corsHeaders } from "../_shared/cors.ts";
import { requireServiceRole } from "../_shared/auth.ts";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const denied = requireServiceRole(req);
  if (denied) return denied;

  const url = Deno.env.get("SUPABASE_URL")!;
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const supabase = createClient(url, serviceKey);
  const cutoff = new Date(Date.now() - 30 * 86400_000).toISOString();

  try {
    const { count, error: countErr } = await supabase
      .from("processed_webhook_events")
      .select("*", { count: "exact", head: true })
      .lt("created_at", cutoff);

    if (countErr) throw countErr;

    const { error } = await supabase.from("processed_webhook_events").delete().lt("created_at", cutoff);
    if (error) throw error;

    return new Response(JSON.stringify({ deleted_count: count ?? 0 }), {
      status: 200,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
