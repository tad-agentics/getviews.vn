import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { corsHeaders } from "../_shared/cors.ts";

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
  const now = new Date().toISOString();

  try {
    const { count, error: countErr } = await supabase
      .from("profiles")
      .select("*", { count: "exact", head: true })
      .gt("daily_free_query_count", 0);

    if (countErr) throw countErr;

    const { error } = await supabase
      .from("profiles")
      .update({
        daily_free_query_count: 0,
        daily_free_query_reset_at: now,
      })
      .gt("daily_free_query_count", 0);

    if (error) throw error;

    return new Response(JSON.stringify({ reset_count: count ?? 0 }), {
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
