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
 * Auth: no JWT required — sendBeacon can't set Authorization. But we DO
 * gate on Origin against the shared allowlist (getviews.vn + Vercel
 * previews + localhost). The browser always sends Origin on cross-origin
 * POSTs (including sendBeacon); a fetch from curl or a random script will
 * either omit it or set a non-allowed value, and gets rejected. This
 * blocks ~99% of trivial spam without breaking the FE-de-duped happy path.
 *
 * Validation: `video_id` is required and constrained to the TikTok aweme_id
 * shape (15-20 digits) so a malicious caller can't insert arbitrary strings
 * and pollute the admin top-10.
 *
 * Response: 200 with {} (sendBeacon ignores it, but useful for debugging).
 *           400 if body is unparseable, video_id is missing, or shape is off.
 *           403 if Origin is missing or off-allowlist.
 *           500 on DB error.
 */

import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { buildCorsHeaders, isAllowedOrigin } from "../_shared/cors.ts";

// Aweme ids are numeric; allowing 14-22 digits gives margin for TikTok's
// occasional ID-length drift while still rejecting obvious garbage.
const AWEME_ID_RE = /^\d{14,22}$/;

Deno.serve(async (req: Request) => {
  const cors = buildCorsHeaders(req);

  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: cors });
  }

  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "method not allowed" }), {
      status: 405,
      headers: { ...cors, "Content-Type": "application/json" },
    });
  }

  const origin = req.headers.get("origin");
  if (!isAllowedOrigin(origin)) {
    return new Response(JSON.stringify({ error: "origin not allowed" }), {
      status: 403,
      headers: { ...cors, "Content-Type": "application/json" },
    });
  }

  let body: { video_id?: string; failed_url?: string } = {};
  try {
    body = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: "invalid JSON" }), {
      status: 400,
      headers: { ...cors, "Content-Type": "application/json" },
    });
  }

  const video_id = (body.video_id ?? "").trim();
  if (!video_id || !AWEME_ID_RE.test(video_id)) {
    return new Response(JSON.stringify({ error: "video_id must be aweme id (14-22 digits)" }), {
      status: 400,
      headers: { ...cors, "Content-Type": "application/json" },
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
      headers: { ...cors, "Content-Type": "application/json" },
    });
  }

  return new Response("{}", {
    status: 200,
    headers: { ...cors, "Content-Type": "application/json" },
  });
});
