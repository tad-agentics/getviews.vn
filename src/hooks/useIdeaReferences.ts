import { useQuery } from "@tanstack/react-query";
import type { ScriptIdeaReferencesResponse } from "@/lib/api-types";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

/**
 * S3 — GET ``/script/idea-references`` (Cloud Run, JWT). Drives the
 * IdeaRefStrip above the storyboard in /app/script per design pack
 * ``screens/script.jsx`` lines 1284-1360.
 *
 * ``hookType`` accepts either the raw enum (``"question"``) or the VN
 * display label (``"Câu hỏi mở đầu"``) — the BE's ``_resolve_hook_type``
 * normalizes both. Pass null when no hook is selected; the BE falls
 * back to overall niche top-views.
 */
export const ideaReferencesKeys = {
  byNicheAndHook: (nicheId: number, hookType: string | null, limit: number) =>
    ["script-idea-references", nicheId, hookType ?? null, limit] as const,
};

export function useIdeaReferences(
  nicheId: number | null,
  hookType: string | null,
  limit: number = 5,
) {
  const base = env.VITE_CLOUD_RUN_API_URL;

  return useQuery<ScriptIdeaReferencesResponse>({
    queryKey: ideaReferencesKeys.byNicheAndHook(nicheId ?? 0, hookType, limit),
    queryFn: async () => {
      if (!base) throw new Error("Cloud Run URL chưa cấu hình");
      if (nicheId == null) throw new Error("Thiếu niche_id");
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session?.access_token) throw new Error("Chưa đăng nhập");
      const qs = new URLSearchParams({
        niche_id: String(nicheId),
        limit: String(limit),
      });
      const ht = hookType?.trim();
      if (ht) qs.set("hook_type", ht);
      const res = await fetch(`${base}/script/idea-references?${qs}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || `HTTP ${res.status}`);
      }
      return (await res.json()) as ScriptIdeaReferencesResponse;
    },
    enabled: Boolean(base && nicheId != null),
    staleTime: 1000 * 60 * 30,
  });
}
