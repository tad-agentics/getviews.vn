import { useQuery } from "@tanstack/react-query";
import type { SceneIntelligenceResponse } from "@/lib/api-types";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

export const scriptSceneIntelKeys = {
  byNiche: (nicheId: number) => ["script-scene-intelligence", nicheId] as const,
};

/**
 * GET ``/script/scene-intelligence`` (Cloud Run, JWT). Plan: ``staleTime`` 6h.
 */
export function useScriptSceneIntelligence(nicheId: number | null) {
  const base = env.VITE_CLOUD_RUN_API_URL;

  return useQuery<SceneIntelligenceResponse>({
    queryKey: scriptSceneIntelKeys.byNiche(nicheId ?? 0),
    queryFn: async () => {
      if (!base) throw new Error("Cloud Run URL chưa cấu hình");
      if (nicheId == null) throw new Error("Thiếu niche_id");
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session?.access_token) throw new Error("Chưa đăng nhập");
      const qs = new URLSearchParams({ niche_id: String(nicheId) });
      const res = await fetch(`${base}/script/scene-intelligence?${qs}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || `HTTP ${res.status}`);
      }
      return (await res.json()) as SceneIntelligenceResponse;
    },
    enabled: Boolean(base && nicheId != null),
    staleTime: 1000 * 60 * 60 * 6,
  });
}
