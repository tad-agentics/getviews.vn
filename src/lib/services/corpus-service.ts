/**
 * Corpus service — client-side helpers for querying video_corpus metadata.
 * Used by VideoRefCard to resolve thumbnail_url and video_url from a video_id.
 *
 * Includes a simple in-memory cache to prevent N+1 queries when multiple
 * VideoRefCards render for the same video in a single chat response.
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

const _cache = new Map<string, { data: VideoMeta | null; ts: number }>();
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

/** Fetch lightweight metadata for a single video from video_corpus. */
export async function getVideoMeta(videoId: string): Promise<VideoMeta | null> {
  const cached = _cache.get(videoId);
  if (cached && Date.now() - cached.ts < CACHE_TTL_MS) {
    return cached.data;
  }

  const { data, error } = await supabase
    .from("video_corpus")
    .select("video_id, thumbnail_url, video_url, views, creator_handle, indexed_at")
    .eq("video_id", videoId)
    .maybeSingle();

  if (error) {
    console.warn(`[corpus-service] Failed to fetch metadata for ${videoId}:`, error.message);
    return null;
  }

  const result = (data as VideoMeta) ?? null;
  _cache.set(videoId, { data: result, ts: Date.now() });
  return result;
}

