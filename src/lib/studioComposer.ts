import { buildAnswerHandoffPath, type AnswerHandoffDepth, type AnswerHandoffMode } from "./answerHandoff";
import {
  extractChannelHandleFromMessage,
  normalizeChannelHandleInput,
  parseChannelExploreHandle,
} from "./channelHandle";
import { buildChannelStudioPath } from "./channelStudioHandoff";
import { planAnswerEntry } from "@/routes/_app/intent-router";

export type StudioComposerPill = "video_flop" | "video_win" | "channel" | "script";

export const STUDIO_COMPOSER_PILLS: { id: StudioComposerPill; label: string }[] = [
  { id: "video_flop", label: "Sửa video flop" },
  { id: "video_win", label: "Học video viral" },
  { id: "channel", label: "Soi kênh đối thủ" },
  { id: "script", label: "Viết kịch bản" },
];

const TIKTOK_URL_IN_TEXT =
  /(?:https?:\/\/)?(?:www\.)?(?:vm\.|vt\.)?tiktok\.com\b/i;

export function studioComposerPlaceholder(pill: StudioComposerPill, nicheLabel: string): string {
  switch (pill) {
    case "video_flop":
      return `Dán link video bị flop trong ngách ${nicheLabel} để tìm lỗi…`;
    case "video_win":
      return `Dán link video đang lên xu hướng trong ngách ${nicheLabel} để giải mã…`;
    case "channel":
      return "Nhập @username hoặc dán link kênh TikTok để phân tích…";
    case "script":
      return `Mô tả ý tưởng video trong ngách ${nicheLabel} để viết kịch bản…`;
  }
}

export type StudioComposerSubmitPlan =
  | { kind: "navigate"; to: string }
  | { kind: "blocked"; reason: "empty" };

function videoModeForPill(
  pill: StudioComposerPill,
  text: string,
): AnswerHandoffMode | undefined {
  if (!TIKTOK_URL_IN_TEXT.test(text)) return undefined;
  if (pill === "video_flop") return "flop";
  if (pill === "video_win") return "win";
  return undefined;
}

export function planStudioComposerSubmit(
  pill: StudioComposerPill,
  text: string,
  depth: AnswerHandoffDepth,
): StudioComposerSubmitPlan {
  const trimmed = text.trim();
  if (!trimmed) return { kind: "blocked", reason: "empty" };

  if (pill === "channel") {
    const fromMsg = extractChannelHandleFromMessage(trimmed);
    const parsed = parseChannelExploreHandle(trimmed);
    const handle =
      fromMsg ??
      (parsed ? normalizeChannelHandleInput(parsed) : null) ??
      normalizeChannelHandleInput(trimmed);
    return {
      kind: "navigate",
      to: buildChannelStudioPath({ handle: handle ?? undefined, depth }),
    };
  }

  const entry = planAnswerEntry(trimmed, false, depth);
  if (entry.kind === "redirect") {
    return { kind: "navigate", to: entry.to };
  }

  if (pill === "script") {
    return {
      kind: "navigate",
      to: buildAnswerHandoffPath({ q: trimmed, from: "composer", includeDepth: false }),
    };
  }

  const mode = videoModeForPill(pill, trimmed);
  return {
    kind: "navigate",
    to: buildAnswerHandoffPath({ q: trimmed, depth, mode, from: "composer" }),
  };
}

export function composerDepthTitles(pill: StudioComposerPill): {
  basic: string;
  deep: string;
} {
  if (pill === "channel") {
    return { basic: "Xem nhanh sẵn có · 0 credit", deep: "Chẩn đoán chi tiết · 3 credit" };
  }
  return { basic: "Phân tích nhanh · 1 credit", deep: "Phân tích chuyên sâu · 2 credit" };
}
