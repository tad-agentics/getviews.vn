/**
 * Corpus service — client-side helpers for querying video_corpus metadata.
 * Used by VideoRefCard to resolve thumbnail_url and video_url from a video_id.
 */
import { supabase } from "@/lib/supabase";

export interface VideoMeta {
  video_id: string;
  thumbnail_url: string | null;
  video_url: string | null;
  views: number;
  creator_handle: string | null;
  indexed_at: string | null;
}

/** Fetch lightweight metadata for a single video from video_corpus. */
export async function getVideoMeta(videoId: string): Promise<VideoMeta | null> {
  const { data, error } = await supabase
    .from("video_corpus")
    .select("video_id, thumbnail_url, video_url, views, creator_handle, indexed_at")
    .eq("video_id", videoId)
    .maybeSingle();

  if (error || !data) return null;
  return data as VideoMeta;
}

