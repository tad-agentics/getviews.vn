import { useQuery } from "@tanstack/react-query";
import { throwSessionExpired } from "@/lib/authErrors";
import { env } from "@/lib/env";
import { fetchWithTimeout } from "@/lib/fetchWithTimeout";
import { supabase } from "@/lib/supabase";

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
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session?.access_token) throw new Error("Chưa đăng nhập");

      const qs = new URLSearchParams({ keyword: kw });
      const res = await fetchWithTimeout(`${cloudRunUrl}/channel/user-search?${qs.toString()}`, {
        method: "GET",
        headers: { Authorization: `Bearer ${session.access_token}` },
        timeoutMs: 20_000,
      });

      if (res.status === 401) {
        throwSessionExpired("401_from_cloud_run");
      }
      if (res.status === 429) {
        const err = new Error("ensemble_quota");
        err.name = "EnsembleQuota";
        throw err;
      }
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(text || `HTTP ${res.status}`);
      }
      return (await res.json()) as ChannelUserSearchResponse;
    },
    enabled: Boolean(cloudRunUrl && kw.length >= 2),
    staleTime: 60_000,
    retry: false,
  });
}
