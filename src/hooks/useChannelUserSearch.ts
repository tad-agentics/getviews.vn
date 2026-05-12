import { useQuery } from "@tanstack/react-query";
import { cloudRunAuthedFetch, throwCloudRunError } from "@/lib/cloudRunClient";
import { env } from "@/lib/env";

export type ChannelUserSearchRow = {
  unique_id: string;
  nickname: string;
  follower_count: number;
  avatar_url: string | null;
};

export type ChannelUserSearchResponse = {
  users: ChannelUserSearchRow[];
};

/**
 * GET `/channel/user-search` (Cloud Run, JWT). Debounce the keyword in the caller.
 */
export function useChannelUserSearch(debouncedKeyword: string | null) {
  const kw = (debouncedKeyword ?? "").trim();
  const cloudRunUrl = env.VITE_CLOUD_RUN_API_URL;

  return useQuery<ChannelUserSearchResponse>({
    queryKey: ["channel-user-search", kw] as const,
    queryFn: async () => {
      if (!cloudRunUrl) throw new Error("Cloud Run URL chưa cấu hình");
      const qs = new URLSearchParams({ keyword: kw });
      const res = await cloudRunAuthedFetch(`/channel/user-search?${qs.toString()}`, {
        method: "GET",
        timeoutMs: 20_000,
      });
      if (res.status === 429) {
        await throwCloudRunError(res, {
          429: { message: "ensemble_quota", name: "EnsembleQuota" },
        });
      }
      if (!res.ok) {
        await throwCloudRunError(res);
      }
      return (await res.json()) as ChannelUserSearchResponse;
    },
    enabled: Boolean(cloudRunUrl && kw.length >= 2),
    staleTime: 60_000,
    retry: false,
  });
}
