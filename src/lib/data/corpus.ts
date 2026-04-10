import { supabase } from "@/lib/supabase";

export async function getRelatedVideos(videoId: string, nicheId: number, limit = 5) {
  const { data, error } = await supabase
    .from("video_corpus")
    .select("id, video_id, tiktok_url, thumbnail_url, creator_handle, views, engagement_rate")
    .eq("niche_id", nicheId)
    .neq("id", videoId)
    .order("engagement_rate", { ascending: false })
    .limit(limit);
  if (error) throw error;
  return data ?? [];
}
