import { parseChannelDepth, type ChannelDepth } from "./channelDepth";

/** Studio Home (`/app`) query contract for channel analysis (§6 / F4–F5). */

export type ChannelStudioHandoffParams = {
  handle?: string;
  depth?: ChannelDepth;
  videoUrl?: string;
  creatorNicheId?: number;
  scrollTier?: "01" | "02" | "03";
  forceRefresh?: boolean;
};

export function buildChannelStudioPath({
  handle,
  depth,
  videoUrl,
  creatorNicheId,
  scrollTier,
  forceRefresh,
}: ChannelStudioHandoffParams): string {
  const params = new URLSearchParams();
  const clean = handle?.replace(/^@/, "").trim();
  if (clean) params.set("handle", clean);
  if (depth === "sau") params.set("depth", "sau");
  if (videoUrl?.trim()) params.set("video_url", videoUrl.trim());
  if (creatorNicheId != null && creatorNicheId >= 1) {
    params.set("creator_niche_id", String(creatorNicheId));
  }
  if (scrollTier) params.set("scrollTier", scrollTier);
  if (forceRefresh) params.set("force_refresh", "1");
  const qs = params.toString();
  return qs ? `/app?${qs}` : "/app";
}

/** Legacy `/app/channel` shim — preserve query params on redirect. */
export function channelRouteRedirectPath(searchParams: URLSearchParams): string {
  const nicheRaw = searchParams.get("creator_niche_id");
  const nicheParsed = nicheRaw ? parseInt(nicheRaw, 10) : NaN;
  return buildChannelStudioPath({
    handle: searchParams.get("handle") ?? undefined,
    depth: parseChannelDepth(searchParams.get("depth")),
    videoUrl: searchParams.get("video_url") ?? undefined,
    creatorNicheId: Number.isFinite(nicheParsed) ? nicheParsed : undefined,
    forceRefresh: searchParams.get("force_refresh") === "1",
  });
}
