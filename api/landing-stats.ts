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
  const [hooksRes, thumbsRes, corpusRes] = await Promise.all([
    // Top 6 hook types by avg_views across all niches, no niche filter
    supabase
      .from("hook_effectiveness")
      .select("hook_type, avg_views, sample_size")
      .order("avg_views", { ascending: false })
      .limit(6),

    // One video per niche — just need video_id for R2 frame URL.
    // Pick highest-view video per niche, fixed 12 niches max.
    // Phase C dropped video_corpus.niche_id (20260822000001) — the legacy
    // bridge column is ingest_loop_niche_id; selecting the dropped column
    // made PostgREST 400 and silently emptied the landing thumbnails.
    supabase
      .from("video_corpus")
      .select("video_id, ingest_loop_niche_id, views")
      .not("ingest_loop_niche_id", "is", null)
      .order("views", { ascending: false })
      .limit(60),

    // Indexed corpus rows — marketing stat + B-02 verification (never hardcode in UI)
    supabase
      .from("video_corpus")
      .select("*", { count: "exact", head: true })
      .not("content_class_id", "is", null),
  ]);

  // Deduplicate to one video_id per niche (max 12 niches)
  const seen = new Set<number>();
  const thumbs: { video_id: string; niche_id: number }[] = [];
  for (const row of thumbsRes.data ?? []) {
    const nicheId = row.ingest_loop_niche_id as number;
    if (!seen.has(nicheId) && thumbs.length < 12) {
      seen.add(nicheId);
      thumbs.push({ video_id: row.video_id, niche_id: nicheId });
    }
  }

  const stats = {
    hooks: (hooksRes.data ?? []).map((h) => ({
      hook_type: h.hook_type as string,
      avg_views: h.avg_views as number,
      sample_size: h.sample_size as number,
    })),
    thumb_ids: thumbs.map((t) => t.video_id),
    corpus_indexed_count: corpusRes.count ?? null,
  };

  return new Response(JSON.stringify(stats), {
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
      ...corsHeaders,
    },
  });
}
