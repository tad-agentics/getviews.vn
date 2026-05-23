import type { HookTimelineEvent } from "@/lib/api-types";

type HookTimelineCarrier = {
  hook_timeline?: HookTimelineEvent[] | null;
  user_video?: {
    analysis?: {
      hook_analysis?: {
        hook_timeline?: HookTimelineEvent[] | null;
      } | null;
    } | null;
  } | null;
} | null | undefined;

/** Prefer top-level ``hook_timeline`` (answer-session report); fall back to nested chat extraction. */
export function resolveHookTimeline(source: HookTimelineCarrier): HookTimelineEvent[] {
  const top = source?.hook_timeline;
  if (Array.isArray(top) && top.length > 0) return top;
  const nested = source?.user_video?.analysis?.hook_analysis?.hook_timeline;
  if (Array.isArray(nested) && nested.length > 0) return nested;
  return [];
}
