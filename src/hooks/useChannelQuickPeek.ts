import { useQuery } from "@tanstack/react-query";

import { cloudRunAuthedFetch, throwCloudRunError } from "@/lib/cloudRunClient";

export type ChannelQuickPeekBreakout = {
  video_id: string;
  views: number;
  hook_type?: string | null;
  breakout_multiplier?: number | null;
};

export type ChannelQuickPeekFinding = {
  finding_id: string;
  teaser: string;
  strength: string;
};

/** F5 — corpus-only channel summary (Trends teaser + ChannelScreen Nhanh). */
export type ChannelQuickPeek = {
  finding_id: string | null;
  teaser: string | null;
  median_views: number | null;
  dominant_hook: string | null;
  breakout_video: ChannelQuickPeekBreakout | null;
  findings: ChannelQuickPeekFinding[];
  corpus_video_count: number;
};

async function fetchChannelQuickPeek(handle: string): Promise<ChannelQuickPeek> {
  const clean = handle.replace(/^@/, "").trim();
  if (!clean) {
    return {
      finding_id: null,
      teaser: null,
      median_views: null,
      dominant_hook: null,
      breakout_video: null,
      findings: [],
      corpus_video_count: 0,
    };
  }
  const qs = new URLSearchParams({ handle: clean });
  const res = await cloudRunAuthedFetch(`/channel/quick-peek?${qs.toString()}`, {
    method: "GET",
  });
  if (!res.ok) await throwCloudRunError(res);
  return (await res.json()) as ChannelQuickPeek;
}

export function useChannelQuickPeek(handle: string | null | undefined, enabled = true) {
  const clean = handle?.replace(/^@/, "").trim() ?? "";
  return useQuery({
    queryKey: ["channel_quick_peek", clean],
    queryFn: () => fetchChannelQuickPeek(clean),
    enabled: enabled && clean.length > 0,
    staleTime: 5 * 60 * 1000,
  });
}
