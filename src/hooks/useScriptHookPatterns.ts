import { useQuery } from "@tanstack/react-query";
import type { HookPatternsResponse } from "@/lib/api-types";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

export const scriptHookPatternsKeys = {
  byNiche: (nicheId: number) => ["script-hook-patterns", nicheId] as const,
};

/**
 * GET ``/script/hook-patterns`` (Cloud Run, JWT). Plan: align with hook panel refresh.
 */
export function useScriptHookPatterns(nicheId: number | null) {
  const base = env.VITE_CLOUD_RUN_API_URL;

  return useQuery<HookPatternsResponse>({
    queryKey: scriptHookPatternsKeys.byNiche(nicheId ?? 0),
    queryFn: async () => {
      if (!base) throw new Error("Cloud Run URL chưa cấu hình");
      if (nicheId == null) throw new Error("Thiếu niche_id");
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session?.access_token) throw new Error("Chưa đăng nhập");
      const qs = new URLSearchParams({ niche_id: String(nicheId) });
      const res = await fetch(`${base}/script/hook-patterns?${qs}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || `HTTP ${res.status}`);
      }
      return (await res.json()) as HookPatternsResponse;
    },
    enabled: Boolean(base && nicheId != null),
    staleTime: 1000 * 60 * 60 * 6,
  });
}
