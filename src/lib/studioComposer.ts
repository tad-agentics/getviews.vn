import { buildAnswerHandoffPath } from "./answerHandoff";
import {
  extractChannelHandleFromMessage,
  normalizeChannelHandleInput,
  parseChannelExploreHandle,
} from "./channelHandle";
import { buildChannelStudioPath } from "./channelStudioHandoff";
import { nonTikTokUrlValidationMessage } from "@/lib/tiktokUrl";
import { planAnswerEntry } from "@/routes/_app/intent-router";

export type StudioComposerPill = "video" | "channel" | "script";

export const STUDIO_COMPOSER_PILLS: { id: StudioComposerPill; label: string }[] = [
  { id: "video", label: "Phân tích video" },
  { id: "channel", label: "Soi kênh đối thủ" },
  { id: "script", label: "Viết kịch bản" },
];

export function studioComposerPlaceholder(pill: StudioComposerPill, nicheLabel: string): string {
  switch (pill) {
    case "video":
      return `Dán link TikTok trong ngách ${nicheLabel} để phân tích…`;
    case "channel":
      return "Nhập @username hoặc dán link kênh TikTok để phân tích…";
    case "script":
      return `Mô tả ý tưởng video trong ngách ${nicheLabel} để viết kịch bản…`;
  }
}

export type StudioComposerSubmitPlan =
  | { kind: "navigate"; to: string }
  | { kind: "blocked"; reason: "empty" | "non_tiktok_url"; message?: string };

export function planStudioComposerSubmit(
  pill: StudioComposerPill,
  text: string,
): StudioComposerSubmitPlan {
  const trimmed = text.trim();
  if (!trimmed) return { kind: "blocked", reason: "empty" };

  const urlBlock = nonTikTokUrlValidationMessage(trimmed);
  if (urlBlock) {
    return { kind: "blocked", reason: "non_tiktok_url", message: urlBlock };
  }

  if (pill === "channel") {
    const fromMsg = extractChannelHandleFromMessage(trimmed);
    const parsed = parseChannelExploreHandle(trimmed);
    const handle =
      fromMsg ??
      (parsed ? normalizeChannelHandleInput(parsed) : null) ??
      normalizeChannelHandleInput(trimmed);
    return {
      kind: "navigate",
      to: buildChannelStudioPath({ handle: handle ?? undefined }),
    };
  }

  const entry = planAnswerEntry(trimmed, false);
  if (entry.kind === "blocked") {
    return { kind: "blocked", reason: "non_tiktok_url", message: entry.message };
  }
  if (entry.kind === "redirect") {
    return { kind: "navigate", to: entry.to };
  }

  // Both "video" and "script" pills hand off the same way now — the
  // performance tier (and any flop framing) is derived downstream, not
  // chosen at the composer.
  return {
    kind: "navigate",
    to: buildAnswerHandoffPath({ q: trimmed, from: "composer" }),
  };
}
