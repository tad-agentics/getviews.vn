import { buildAnswerHandoffPath, type AnswerHandoffDepth, type AnswerHandoffMode } from "./answerHandoff";
import {
  extractChannelHandleFromMessage,
  normalizeChannelHandleInput,
  parseChannelExploreHandle,
} from "./channelHandle";
import { buildChannelStudioPath } from "./channelStudioHandoff";
import { nonTikTokUrlValidationMessage } from "@/lib/tiktokUrl";
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
  | { kind: "blocked"; reason: "empty" | "non_tiktok_url"; message?: string };

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
      to: buildChannelStudioPath({ handle: handle ?? undefined, depth }),
    };
  }

  const entry = planAnswerEntry(trimmed, false, depth);
  if (entry.kind === "blocked") {
    return { kind: "blocked", reason: "non_tiktok_url", message: entry.message };
  }
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

export type ComposerDepthCopy = {
  cost: number;
  shortLabel: string;
  whatYouGet: string;
};

/** What each depth delivers — used for visible composer hint (not hover-only). */
export function composerDepthCopy(pill: StudioComposerPill): {
  basic: ComposerDepthCopy;
  deep: ComposerDepthCopy;
} {
  if (pill === "channel") {
    return {
      basic: {
        cost: 0,
        shortLabel: "Cơ bản",
        whatYouGet: "Số liệu kênh + insight từ corpus — xem ngay, không trừ credit",
      },
      deep: {
        cost: 3,
        shortLabel: "Chuyên sâu",
        whatYouGet: "Chẩn đoán đầy đủ: persona, hook, gợi ý video tiếp theo",
      },
    };
  }
  return {
    basic: {
      cost: 1,
      shortLabel: "Cơ bản",
      whatYouGet: "Chẩn đoán hook, lỗi chính, so sánh ngách (~1 phút)",
    },
    deep: {
      cost: 2,
      shortLabel: "Chuyên sâu",
      whatYouGet: "Thêm biểu đồ nhiệt giờ đăng, pattern ngách, các mục khóa trong báo cáo",
    },
  };
}

/** Visible hint under composer — explains mode, cost, and remaining runs. */
export function composerDepthHint(
  pill: StudioComposerPill,
  depth: AnswerHandoffDepth,
  creditsRemaining?: number,
): { activeLine: string; compareLine: string; creditsLine: string | null } {
  const { basic, deep } = composerDepthCopy(pill);
  const active = depth === "deep" ? deep : basic;
  const other = depth === "deep" ? basic : deep;

  const activeLine = `${active.shortLabel} · ${active.cost} credit/lần — ${active.whatYouGet}`;
  const compareLine = `${other.shortLabel} · ${other.cost} credit: ${other.whatYouGet}`;

  let creditsLine: string | null = null;
  if (creditsRemaining != null) {
    if (active.cost === 0) {
      const deepRuns =
        deep.cost > 0 ? Math.floor(creditsRemaining / deep.cost) : 0;
      creditsLine =
        `Bạn còn ${creditsRemaining} credit — ${active.shortLabel} không trừ credit; Chuyên sâu kênh ≈ ${deepRuns} lần.`;
    } else {
      const runs = Math.floor(creditsRemaining / active.cost);
      creditsLine = `Bạn còn ${creditsRemaining} credit → khoảng ${runs} lần ở mức ${active.shortLabel}.`;
    }
  }

  return { activeLine, compareLine, creditsLine };
}

/** Tooltip copy for each Cơ bản / Chuyên sâu button. */
export function composerDepthTooltip(
  pill: StudioComposerPill,
  depth: AnswerHandoffDepth,
  creditsRemaining?: number,
  channelDeepCreditCost = 3,
): string {
  const { basic, deep } = composerDepthCopy(pill);
  const row = depth === "deep" ? deep : basic;
  const lines: string[] = [
    `${row.shortLabel} — ${row.cost} credit mỗi lần`,
    row.whatYouGet,
  ];

  if (
    depth === "deep" &&
    pill === "channel" &&
    creditsRemaining != null &&
    creditsRemaining < channelDeepCreditCost
  ) {
    lines.push(
      `Cần tối thiểu ${channelDeepCreditCost} credit — bạn còn ${creditsRemaining}.`,
    );
    return lines.join("\n");
  }

  if (creditsRemaining != null) {
    if (row.cost > 0) {
      const runs = Math.floor(creditsRemaining / row.cost);
      lines.push(`Bạn còn ${creditsRemaining} credit → khoảng ${runs} lần.`);
    } else if (depth === "basic" && deep.cost > 0) {
      const deepRuns = Math.floor(creditsRemaining / deep.cost);
      lines.push(
        `Không trừ credit. Chuyên sâu ≈ ${deepRuns} lần với ${creditsRemaining} credit.`,
      );
    }
  }

  return lines.join("\n");
}
