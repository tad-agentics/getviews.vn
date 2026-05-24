import type { AnswerHandoffDepth } from "./answerHandoff";
import { parseChannelDepth, type ChannelDepth } from "./channelDepth";

/** `/app/channel` query contract for channel analysis (§6 / F4–F5). */

export type ChannelStudioHandoffParams = {
  handle?: string;
  /** Composer uses `basic`/`deep`; legacy URLs may use `nhanh`/`sau`. */
  depth?: AnswerHandoffDepth | ChannelDepth;
  videoUrl?: string;
  creatorNicheId?: number;
  scrollTier?: "01" | "02" | "03";
  forceRefresh?: boolean;
};

function depthQueryValue(depth?: AnswerHandoffDepth | ChannelDepth): string | null {
  if (!depth) return null;
  if (depth === "deep" || depth === "sau") return "deep";
  return null;
}

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
  const depthParam = depthQueryValue(depth);
  if (depthParam) params.set("depth", depthParam);
  if (videoUrl?.trim()) params.set("video_url", videoUrl.trim());
  if (creatorNicheId != null && creatorNicheId >= 1) {
    params.set("creator_niche_id", String(creatorNicheId));
  }
  if (scrollTier) params.set("scrollTier", scrollTier);
  if (forceRefresh) params.set("force_refresh", "1");
  const qs = params.toString();
  return qs ? `/app/channel?${qs}` : "/app/channel";
}

/** Legacy `/app?handle=` bookmarks → canonical channel route. */
export function studioHomeChannelRedirectPath(searchParams: URLSearchParams): string | null {
  const handle = searchParams.get("handle");
  if (!handle?.trim()) return null;
  const nicheRaw = searchParams.get("creator_niche_id");
  const nicheParsed = nicheRaw ? parseInt(nicheRaw, 10) : NaN;
  return buildChannelStudioPath({
    handle,
    depth: parseChannelDepth(searchParams.get("depth")),
    videoUrl: searchParams.get("video_url") ?? undefined,
    creatorNicheId: Number.isFinite(nicheParsed) ? nicheParsed : undefined,
    forceRefresh: searchParams.get("force_refresh") === "1",
  });
}
