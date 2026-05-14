/**
 * track-thumbnail-failure — record a thumbnail image load failure.
 *
 * Called from VideoThumbnail.tsx via navigator.sendBeacon when the browser
 * fails to load a thumbnail URL. The component de-duplicates per video_id
 * per session; this function just inserts the record and returns fast.
 *
 * Request body (JSON):
 *   { video_id: string, failed_url?: string }
 *
 * Auth: none required — public endpoint. Origin is logged but not gated
 * because sendBeacon does not allow custom headers. Rate-limit risk is
 * low: one event per video_id per browser session (FE de-dup), and the
 * table volume is expected to be < 1k/week.
 *
 * Response: 200 with {} (sendBeacon ignores it, but useful for debugging).
 *           400 if body is unparseable or video_id is missing.
 *           500 on DB error.
 */

import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { corsHeaders } from "../_shared/cors.ts";

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "method not allowed" }), {
      status: 405,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  let body: { video_id?: string; failed_url?: string } = {};
  try {
    body = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: "invalid JSON" }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const video_id = (body.video_id ?? "").trim();
  if (!video_id) {
    return new Response(JSON.stringify({ error: "video_id required" }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const url = Deno.env.get("SUPABASE_URL")!;
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const supabase = createClient(url, serviceKey);

  const { error } = await supabase.from("thumbnail_failures").insert({
    video_id,
    failed_url: body.failed_url ?? null,
    user_agent: req.headers.get("user-agent") ?? null,
  });

  if (error) {
    console.error("[track-thumbnail-failure] DB insert error:", error.message);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  return new Response("{}", {
    status: 200,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
});
