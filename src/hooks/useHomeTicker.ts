import { useQuery } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

export type TickerBucket =
  | "breakout" | "hook_mới" | "cảnh_báo" | "kol_nổi" | "âm_thanh";

export type TickerItem = {
  bucket: TickerBucket;
  label_vi: string;           // "BREAKOUT", "HOOK MỚI", etc.
  headline_vi: string;
  target_kind: "video" | "creator" | "pattern" | "sound" | "none";
  target_id: string | null;
};

/** GET /home/ticker — up to 10 interleaved items across 5 buckets. */
export function useHomeTicker(enabled = true) {
  return useQuery<TickerItem[]>({
    queryKey: ["home", "ticker"],
    queryFn: async () => {
      const cloudRunUrl = env.VITE_CLOUD_RUN_API_URL;
      if (!cloudRunUrl) return [];
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return [];
      const res = await fetch(`${cloudRunUrl}/home/ticker`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.status === 404) return [];
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const body = (await res.json()) as { items: TickerItem[] };
      return body.items ?? [];
    },
    enabled,
    staleTime: 10 * 60 * 1000, // 10 min
    retry: false,
  });
}
