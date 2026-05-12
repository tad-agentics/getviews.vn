import { useQuery } from "@tanstack/react-query";

import type { DouyinPatternsResponse } from "@/lib/api-types";
import { cloudRunAuthedFetch, throwCloudRunError } from "@/lib/cloudRunClient";
import { env } from "@/lib/env";

/**
 * D5d (2026-06-05) — Kho Douyin weekly pattern-signals hook.
 *
 * GET ``/douyin/patterns`` returns the most-recent week's 3 pattern
 * cards per active niche as a flat array ordered by (niche_id, rank).
 * FE groups by ``niche_id`` client-side to render the 3-up cards
 * above the §II video grid (D5e).
 *
 * Cache: 30-min staleTime — the underlying data only refreshes weekly
 * (Mondays 04:00 VN), so a 30-min FE cache is just enough to dedupe
 * tab focus refetches without staleness risk.
 *
 * Auth: requires a Supabase session (Cloud Run validates the JWT).
 * 401 from upstream auto-signs the user out.
 */
export const douyinPatternsKeys = {
  all: ["douyin", "patterns"] as const,
};

export function useDouyinPatterns(enabled: boolean = true) {
  const base = env.VITE_CLOUD_RUN_API_URL;

  return useQuery<DouyinPatternsResponse>({
    queryKey: douyinPatternsKeys.all,
    queryFn: async () => {
      if (!base) throw new Error("Cloud Run URL chưa cấu hình");
      const res = await cloudRunAuthedFetch("/douyin/patterns", {
        method: "GET",
        timeoutMs: 15_000,
      });
      if (!res.ok) {
        await throwCloudRunError(res);
      }
      return (await res.json()) as DouyinPatternsResponse;
    },
    enabled: enabled && Boolean(base),
    staleTime: 30 * 60 * 1000,
    retry: false,
  });
}
