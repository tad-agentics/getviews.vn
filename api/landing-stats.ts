export const config = { runtime: "edge" };
import { createClient } from "@supabase/supabase-js";
import { buildCorsHeaders } from "./_cors";

// Use service role key to bypass RLS — this route runs server-side only,
// the key is never exposed to the browser.
const supabase = createClient(
  process.env.SUPABASE_URL ?? process.env.VITE_SUPABASE_URL ?? "",
  process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.SUPABASE_ANON_KEY ?? process.env.VITE_SUPABASE_PUBLISHABLE_KEY ?? "",
);

export default async function handler(req: Request): Promise<Response> {
  const corsHeaders = buildCorsHeaders(req);
  const [hooksRes, thumbsRes] = await Promise.all([
    // Top 6 hook types by avg_views across all niches, no niche filter
    supabase
      .from("hook_effectiveness")
      .select("hook_type, avg_views, sample_size")
      .order("avg_views", { ascending: false })
      .limit(6),

    // One video per niche — just need video_id for R2 frame URL
    // Pick highest-view video per niche, fixed 12 niches max
    supabase
      .from("video_corpus")
      .select("video_id, niche_id, views")
      .order("views", { ascending: false })
      .limit(60),
  ]);

  // Deduplicate to one video_id per niche (max 12 niches)
  const seen = new Set<number>();
  const thumbs: { video_id: string; niche_id: number }[] = [];
  for (const row of thumbsRes.data ?? []) {
    if (!seen.has(row.niche_id) && thumbs.length < 12) {
      seen.add(row.niche_id);
      thumbs.push({ video_id: row.video_id, niche_id: row.niche_id });
    }
  }

  const stats = {
    hooks: (hooksRes.data ?? []).map((h) => ({
      hook_type: h.hook_type as string,
      avg_views: h.avg_views as number,
      sample_size: h.sample_size as number,
    })),
    thumb_ids: thumbs.map((t) => t.video_id),
  };

  return new Response(JSON.stringify(stats), {
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
      ...corsHeaders,
    },
  });
}
