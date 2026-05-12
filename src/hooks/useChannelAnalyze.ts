import { useQuery } from "@tanstack/react-query";
import type { ChannelAnalyzeResponse } from "@/lib/api-types";
import { normalizeChannelHandleInput } from "@/lib/channelHandle";
import { cloudRunAuthedFetch, throwCloudRunError } from "@/lib/cloudRunClient";
import { env } from "@/lib/env";

/** Strip @ and whitespace for cache keys and API query. */
export function channelAnalyzeHandleKey(handle: string | null | undefined): string | null {
  return normalizeChannelHandleInput(handle);
}

export type UseChannelAnalyzeOptions = {
  handle?: string | null;
  /** Maps to Cloud Run ``creator_niche_id`` (corpus lens; default = profile). */
  creatorNicheId?: number | null;
  /** Maps to Cloud Run `force_refresh=true` (bypass 7d cache when allowed). */
  forceRefresh?: boolean;
  enabled?: boolean;
};

/**
 * GET `/channel/analyze` (Cloud Run, JWT). Backend caches ~7d; client
 * ``staleTime`` aligned so navigation does not hammer the endpoint.
 */
export function useChannelAnalyze({
  handle = null,
  creatorNicheId = null,
  forceRefresh = false,
  enabled = true,
}: UseChannelAnalyzeOptions) {
  const key = channelAnalyzeHandleKey(handle);
  const cloudRunUrl = env.VITE_CLOUD_RUN_API_URL;

  const normalizedCreatorNicheId =
    creatorNicheId != null &&
    Number.isFinite(creatorNicheId) &&
    creatorNicheId >= 1 &&
    creatorNicheId <= 64
      ? Math.trunc(creatorNicheId)
      : null;

  const nicheKey = normalizedCreatorNicheId != null ? String(normalizedCreatorNicheId) : "profile";

  const queryKey = key
    ? (["channel-analyze", key, nicheKey, forceRefresh ? "force" : "ok"] as const)
    : (["channel-analyze", "__idle__"] as const);

  return useQuery<ChannelAnalyzeResponse>({
    queryKey,
    queryFn: async () => {
      if (!cloudRunUrl) throw new Error("Cloud Run URL chưa cấu hình");
      if (!key) throw new Error("Thiếu handle kênh");

      const qs = new URLSearchParams({ handle: key });
      if (forceRefresh) qs.set("force_refresh", "true");
      if (normalizedCreatorNicheId != null) {
        qs.set("creator_niche_id", String(normalizedCreatorNicheId));
      }

      const res = await cloudRunAuthedFetch(`/channel/analyze?${qs.toString()}`, {
        method: "GET",
        timeoutMs: 45_000,
      });
      if (res.status === 402) {
        await throwCloudRunError(res, {
          402: { message: "insufficient_credits", name: "InsufficientCredits" },
        });
      }
      if (res.status === 429) {
        await throwCloudRunError(res, {
          429: { message: "daily_free_limit", name: "DailyFreeLimit" },
        });
      }
      if (res.status === 404) {
        const detail = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new Error(detail.detail ?? "Không tìm thấy kênh trong ngách so sánh này");
      }
      if (!res.ok) {
        await throwCloudRunError(res);
      }
      return (await res.json()) as ChannelAnalyzeResponse;
    },
    enabled: Boolean(enabled && key && cloudRunUrl),
    staleTime: 1000 * 60 * 60 * 24 * 7,
    retry: false,
  });
}
