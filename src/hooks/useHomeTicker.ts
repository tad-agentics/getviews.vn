import { useQuery } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

export type TickerBucket =
  | "breakout" | "hook_mới" | "cảnh_báo" | "âm_thanh";

export type TickerItem = {
  bucket: TickerBucket;
  label_vi: string;           // "BREAKOUT", "HOOK MỚI", etc.
  headline_vi: string;
  target_kind: "video" | "creator" | "pattern" | "sound" | "none";
  target_id: string | null;
};

/** GET /home/ticker — up to 10 interleaved items across 4 buckets.
 *
 * Creator-only pivot (claude/remove-kol-creator-only): `kol_nổi` was
 * dropped from the bucket set. The server may still emit it during
 * transitional rollout — we filter at the hook layer so legacy items
 * never reach the renderer (TickerMarquee). */
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
      // Bucket arrives as a free string from the server so the filter
      // can drop legacy `kol_nổi` items without TS thinking the
      // comparison is unreachable.
      type RawTickerItem = Omit<TickerItem, "bucket"> & { bucket: string };
      const body = (await res.json()) as { items: RawTickerItem[] };
      return (body.items ?? []).filter(
        (it) => it.bucket !== "kol_nổi",
      ) as TickerItem[];
    },
    enabled,
    staleTime: 10 * 60 * 1000, // 10 min
    retry: false,
  });
}
