import { useQuery } from "@tanstack/react-query";
import type { ChannelAnalyzeResponse } from "@/lib/api-types";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

/** Strip @ and whitespace for cache keys and API query. */
export function channelAnalyzeHandleKey(handle: string | null | undefined): string | null {
  const h = (handle ?? "").trim().replace(/^@+/, "");
  return h || null;
}

export type UseChannelAnalyzeOptions = {
  handle?: string | null;
  /** Maps to Cloud Run `force_refresh=true` (bypass 7d cache when allowed). */
  forceRefresh?: boolean;
  enabled?: boolean;
};

/**
 * GET `/channel/analyze` (Cloud Run, JWT). Backend caches ~7d; client
 * ``staleTime`` aligned so navigation does not hammer the endpoint.
 */
export function useChannelAnalyze({
  handle = null,
  forceRefresh = false,
  enabled = true,
}: UseChannelAnalyzeOptions) {
  const key = channelAnalyzeHandleKey(handle);
  const cloudRunUrl = env.VITE_CLOUD_RUN_API_URL;

  const queryKey = key
    ? (["channel-analyze", key, forceRefresh ? "force" : "ok"] as const)
    : (["channel-analyze", "__idle__"] as const);

  return useQuery<ChannelAnalyzeResponse>({
    queryKey,
    queryFn: async () => {
      if (!cloudRunUrl) throw new Error("Cloud Run URL chưa cấu hình");
      if (!key) throw new Error("Thiếu handle kênh");
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session?.access_token) throw new Error("Chưa đăng nhập");

      const qs = new URLSearchParams({ handle: key });
      if (forceRefresh) qs.set("force_refresh", "true");

      const res = await fetch(`${cloudRunUrl}/channel/analyze?${qs.toString()}`, {
        method: "GET",
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      if (res.status === 402) {
        const body = (await res.json().catch(() => ({}))) as { error?: string };
        if (body.error === "insufficient_credits") {
          throw new Error("Không đủ credit phân tích sâu. Kiểm tra gói hoặc mua thêm trong Cài đặt.");
        }
        throw new Error("Yêu cầu thanh toán / credit.");
      }
      if (res.status === 404) {
        const detail = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new Error(detail.detail ?? "Không tìm thấy kênh trong ngách này");
      }
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }
      return (await res.json()) as ChannelAnalyzeResponse;
    },
    enabled: Boolean(enabled && key && cloudRunUrl),
    staleTime: 1000 * 60 * 60 * 24 * 7,
    retry: false,
  });
}
