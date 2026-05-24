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
  { id: "video_flop", label: "Khám Video flop" },
  { id: "video_win", label: "Khám Video win" },
  { id: "channel", label: "Khám Kênh" },
  { id: "script", label: "Tạo kịch bản" },
];

const TIKTOK_URL_IN_TEXT =
  /(?:https?:\/\/)?(?:www\.)?(?:vm\.|vt\.)?tiktok\.com\b/i;

export function studioComposerPlaceholder(pill: StudioComposerPill, nicheLabel: string): string {
  switch (pill) {
    case "video_flop":
      return `Dán URL TikTok video flop trong ngách ${nicheLabel}…`;
    case "video_win":
      return `Dán URL TikTok video đang chạy trong ngách ${nicheLabel}…`;
    case "channel":
      return "@handle hoặc dán link profile TikTok…";
    case "script":
      return `Mô tả video cần kịch bản trong ngách ${nicheLabel}…`;
  }
}

export function studioComposerShortcutHint(pill: StudioComposerPill): string {
  switch (pill) {
    case "video_flop":
      return "Chọn flop — dán URL TikTok rồi bấm Gửi";
    case "video_win":
      return "Chọn video win — dán URL TikTok rồi bấm Gửi";
    case "channel":
      return "Chọn kênh — nhập @handle rồi bấm Gửi";
    case "script":
      return "Chọn kịch bản — mô tả video rồi bấm Gửi";
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

  const entry = planAnswerEntry(trimmed, false);
  if (entry.kind === "redirect") {
    return { kind: "navigate", to: entry.to };
  }

  if (pill === "script") {
    return {
      kind: "navigate",
      to: buildAnswerHandoffPath({ q: trimmed, depth, from: "composer" }),
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
    return { basic: "Đọc corpus · 0 credit", deep: "Memo SSE · 3 credit" };
  }
  return { basic: "Giải mã nhanh · 1 credit", deep: "Đầy đủ góc · 2 credit" };
}
