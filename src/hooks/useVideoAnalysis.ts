import { useQuery } from "@tanstack/react-query";
import type { RetentionCurveSource, VideoAnalyzeMode, VideoAnalyzeResponse } from "@/lib/api-types";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

export type VideoAnalysisKey = string | null;

/** Stable cache key fragment from query params (`?video_id=` / `?url=`). */
export function videoAnalysisKey(videoId: string | null, url: string | null): VideoAnalysisKey {
  const vid = videoId?.trim() ?? "";
  const u = url?.trim() ?? "";
  if (vid) return `id:${vid}`;
  if (u) return `url:${u}`;
  return null;
}

export type UseVideoAnalysisOptions = {
  videoId?: string | null;
  url?: string | null;
  /** Bypass Cloud Run 1h diagnostics cache (debug / prompt iteration). */
  forceRefresh?: boolean;
  /** When set, POST body asks Cloud Run for this branch (skips heuristic + cache). */
  mode?: VideoAnalyzeMode | null;
  enabled?: boolean;
};

/**
 * POST `/video/analyze` (Cloud Run, JWT). ``staleTime`` 1h — diagnostics MV.
 *
 * Query key matches plan: ``['video-analysis', videoIdOrUrl]`` where the second
 * segment is ``id:…`` / ``url:…`` from ``videoAnalysisKey``. ``mode`` and
 * ``forceRefresh`` are included so win/flop and busted runs cache separately.
 */
export function useVideoAnalysis({
  videoId = null,
  url = null,
  forceRefresh = false,
  mode = null,
  enabled = true,
}: UseVideoAnalysisOptions) {
  const key = videoAnalysisKey(videoId, url);
  const cloudRunUrl = env.VITE_CLOUD_RUN_API_URL;
  const modeKey = mode ?? "auto";

  const queryKey = key
    ? (["video-analysis", key, modeKey, forceRefresh ? "force" : "ok"] as const)
    : (["video-analysis", "__idle__"] as const);

  return useQuery<VideoAnalyzeResponse>({
    queryKey,
    queryFn: async () => {
      if (!cloudRunUrl) throw new Error("Cloud Run URL chưa cấu hình");
      if (!key) throw new Error("Thiếu video_id hoặc url");
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) throw new Error("Chưa đăng nhập");

      const body: Record<string, unknown> = { force_refresh: forceRefresh };
      if (mode === "win" || mode === "flop") body.mode = mode;
      if (videoId?.trim()) body.video_id = videoId.trim();
      else if (url?.trim()) body.tiktok_url = url.trim();

      const res = await fetch(`${cloudRunUrl}/video/analyze`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      if (res.status === 404) {
        const detail = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new Error(detail.detail ?? "Không tìm thấy video");
      }
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }
      return (await res.json()) as VideoAnalyzeResponse;
    },
    enabled: Boolean(enabled && key && cloudRunUrl),
    staleTime: 1000 * 60 * 60,
    retry: false,
    select: (row) => ({
      ...row,
      meta: {
        ...row.meta,
        retention_source: (row.meta.retention_source ?? "modeled") as RetentionCurveSource,
      },
      niche_meta: row.niche_meta
        ? { ...row.niche_meta, winners_sample_size: row.niche_meta.winners_sample_size ?? null }
        : null,
    }),
  });
}
