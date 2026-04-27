import { useQuery } from "@tanstack/react-query";

import type { DouyinFeedResponse } from "@/lib/api-types";
import { throwSessionExpired } from "@/lib/authErrors";
import { readErrorDetail } from "@/lib/cloudRunErrors";
import { env } from "@/lib/env";
import { fetchWithTimeout } from "@/lib/fetchWithTimeout";
import { supabase } from "@/lib/supabase";

/**
 * D4a (2026-06-04) — Kho Douyin feed hook.
 *
 * GET ``/douyin/feed`` returns ``{niches, videos}`` in one round-trip.
 * The FE filters + sorts client-side (corpus is small enough — D2 cap
 * is ~50/day with ~30-day retention = ~1.5K rows max).
 *
 * Cache: 10-min staleTime — fresh enough that opening the screen on
 * Monday after the weekend ingest shows new videos, but not so
 * aggressive that flipping niches refetches.
 *
 * Auth: requires a Supabase session (Cloud Run validates the JWT).
 * 401 from upstream auto-signs the user out via ``throwSessionExpired``.
 */
export const douyinFeedKeys = {
  all: ["douyin", "feed"] as const,
};

export function useDouyinFeed(enabled: boolean = true) {
  const base = env.VITE_CLOUD_RUN_API_URL;

  return useQuery<DouyinFeedResponse>({
    queryKey: douyinFeedKeys.all,
    queryFn: async () => {
      if (!base) throw new Error("Cloud Run URL chưa cấu hình");
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session?.access_token) throw new Error("Chưa đăng nhập");
      const res = await fetchWithTimeout(`${base}/douyin/feed`, {
        method: "GET",
        headers: { Authorization: `Bearer ${session.access_token}` },
        timeoutMs: 15_000,
      });
      if (res.status === 401) {
        throwSessionExpired("401_from_cloud_run");
      }
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return (await res.json()) as DouyinFeedResponse;
    },
    enabled: enabled && Boolean(base),
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
