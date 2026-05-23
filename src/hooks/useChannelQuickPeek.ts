import { useQuery } from "@tanstack/react-query";

import { cloudRunAuthedFetch, throwCloudRunError } from "@/lib/cloudRunClient";

export type ChannelQuickPeek = {
  finding_id: string | null;
  teaser: string | null;
};

async function fetchChannelQuickPeek(handle: string): Promise<ChannelQuickPeek> {
  const clean = handle.replace(/^@/, "").trim();
  if (!clean) return { finding_id: null, teaser: null };
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
