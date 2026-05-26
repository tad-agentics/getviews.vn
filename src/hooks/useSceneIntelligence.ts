import { useQuery } from "@tanstack/react-query";

import type { SceneIntelligenceResponse } from "@/lib/api-types";
import { cloudRunAuthedFetch, throwCloudRunError } from "@/lib/cloudRunClient";
import { env } from "@/lib/env";

export function sceneIntelligenceQueryKey(nicheId: number | null | undefined) {
  return ["scene-intelligence", nicheId ?? null] as const;
}

/**
 * B.4.2 — nightly ``scene_intelligence`` rows for script studio pacing tips.
 * Fail-open: caller treats missing/empty scenes as no panel.
 */
export function useSceneIntelligence(nicheId: number | null | undefined) {
  return useQuery<SceneIntelligenceResponse>({
    queryKey: sceneIntelligenceQueryKey(nicheId),
    enabled: typeof nicheId === "number" && nicheId > 0 && Boolean(env.VITE_CLOUD_RUN_API_URL),
    staleTime: 60 * 60 * 1000,
    queryFn: async () => {
      const base = env.VITE_CLOUD_RUN_API_URL;
      if (!base) throw new Error("Cloud Run URL chưa cấu hình");
      const res = await cloudRunAuthedFetch(
        `/script/scene-intelligence?niche_id=${encodeURIComponent(String(nicheId))}`,
        { timeoutMs: 15_000 },
      );
      if (!res.ok) await throwCloudRunError(res);
      return (await res.json()) as SceneIntelligenceResponse;
    },
  });
}
