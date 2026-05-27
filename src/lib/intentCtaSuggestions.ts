/**
 * §4.10.2 — Intent CTA matrix for Answer follow-up turns (W5-1).
 * Fixed Vietnamese labels + explicit intent_type; no free-text classify.
 */
import type { AnswerSessionFormat } from "@/lib/api-types";
import type { AnswerHandoffDepth, AnswerHandoffMode } from "@/lib/answerHandoff";

export type IntentCtaId =
  | "video_script"
  | "video_compare"
  | "video_deep"
  | "video_hook_variants"
  | "video_timing"
  | "script_shoot"
  | "script_sample_video"
  | "script_save_draft"
  | "pattern_script"
  | "pattern_viral_decode"
  | "timing_calendar"
  | "timing_hot_script"
  | "ideas_full_script"
  | "ideas_hook_ab"
  | "generic_script"
  | "generic_trends"
  | "video_channel";

export type IntentCtaActionKind =
  | "append_turn"
  | "handoff"
  | "compare_navigate"
  | "shoot_panel"
  | "channel_handoff";

export type IntentCtaSuggestion = {
  id: IntentCtaId;
  label: string;
  intentType: string;
  action: IntentCtaActionKind;
  /** Prerequisite missing — pill disabled with reason. */
  disabledReason?: string;
};

export type IntentCtaContext = {
  format: AnswerSessionFormat;
  mode: AnswerHandoffMode | null;
  depth: AnswerHandoffDepth;
  /** Resolved TikTok URL or aweme id for video-context CTAs. */
  videoQuery: string | null;
  scriptDraftId: string | null;
  /** Evidence tile URL for pattern → viral decode handoff. */
  evidenceVideoQuery: string | null;
  sessionInitialQ: string | null;
  /** TikTok @handle from video report meta — enables channel CTA. */
  creatorHandle: string | null;
};

type MatrixRow = Omit<IntentCtaSuggestion, "disabledReason">;

function channelCtaLabel(handle: string): string {
  const h = handle.replace(/^@/, "").trim();
  return h ? `Soi kênh @${h}` : "Soi kênh";
}

function baseVideoRows(ctx: IntentCtaContext): MatrixRow[] {
  const rows: MatrixRow[] = [
    {
      id: "video_script",
      label: "Tạo kịch bản",
      intentType: "shot_list",
      action: "append_turn",
    },
  ];
  // Flop report already shows Soi kênh in VideoBody header — skip rail duplicate.
  if (ctx.creatorHandle?.trim() && ctx.mode !== "flop") {
    rows.push({
      id: "video_channel",
      label: channelCtaLabel(ctx.creatorHandle),
      intentType: "channel_diagnosis",
      action: "channel_handoff",
    });
  }
  rows.push({
    id: "video_compare",
    label: "So sánh với video khác",
    intentType: "compare_videos",
    action: "compare_navigate",
  });
  if (ctx.mode === "flop") {
    rows.push({
      id: "video_hook_variants",
      label: "Sửa hook — tạo biến thể",
      intentType: "hook_variants",
      action: "append_turn",
    });
  } else {
    rows.push({
      id: "video_timing",
      label: "Giờ đăng tốt",
      intentType: "timing",
      action: "append_turn",
    });
  }
  if (ctx.depth === "basic") {
    rows.push({
      id: "video_deep",
      label: "Phân tích chuyên sâu (2 credit)",
      intentType: "video_diagnosis",
      action: "handoff",
    });
  }
  return rows;
}

const MATRIX: Record<AnswerSessionFormat, MatrixRow[]> = {
  video: [], // filled dynamically via baseVideoRows
  script: [
    {
      id: "script_shoot",
      label: "Quay kịch bản",
      intentType: "shot_list",
      action: "shoot_panel",
    },
    {
      id: "script_sample_video",
      label: "Phân tích video mẫu",
      intentType: "video_diagnosis",
      action: "handoff",
    },
  ],
  pattern: [
    {
      id: "pattern_script",
      label: "Tạo kịch bản theo công thức",
      intentType: "shot_list",
      action: "append_turn",
    },
    {
      id: "pattern_viral_decode",
      label: "Giải mã video viral",
      intentType: "video_diagnosis",
      action: "handoff",
    },
  ],
  timing: [
    {
      id: "timing_calendar",
      label: "Lên lịch tuần này",
      intentType: "content_calendar",
      action: "append_turn",
    },
    {
      id: "timing_hot_script",
      label: "Tạo kịch bản slot hot",
      intentType: "shot_list",
      action: "append_turn",
    },
  ],
  ideas: [
    {
      id: "ideas_full_script",
      label: "Viết kịch bản đủ quay",
      intentType: "shot_list",
      action: "append_turn",
    },
    {
      id: "ideas_hook_ab",
      label: "So sánh hook A/B",
      intentType: "compare_videos",
      action: "compare_navigate",
    },
  ],
  generic: [
    {
      id: "generic_script",
      label: "Tạo kịch bản",
      intentType: "shot_list",
      action: "append_turn",
    },
    {
      id: "generic_trends",
      label: "Xu hướng ngách",
      intentType: "trend_spike",
      action: "append_turn",
    },
  ],
  lifecycle: [
    {
      id: "generic_script",
      label: "Tạo kịch bản",
      intentType: "shot_list",
      action: "append_turn",
    },
    {
      id: "generic_trends",
      label: "Xu hướng ngách",
      intentType: "trend_spike",
      action: "append_turn",
    },
  ],
  diagnostic: [
    {
      id: "generic_script",
      label: "Tạo kịch bản",
      intentType: "shot_list",
      action: "append_turn",
    },
    {
      id: "video_compare",
      label: "So sánh với video khác",
      intentType: "compare_videos",
      action: "compare_navigate",
    },
  ],
  // Compare turns already show both videos side-by-side; no follow-up pills.
  compare: [],
};

function applyPrerequisites(row: MatrixRow, ctx: IntentCtaContext): IntentCtaSuggestion {
  if (row.action === "compare_navigate" && !ctx.videoQuery) {
    return { ...row, disabledReason: "Cần URL video trong phiên" };
  }
  if (row.id === "script_shoot" && !ctx.scriptDraftId) {
    return { ...row, disabledReason: "Lưu kịch bản trước khi quay" };
  }
  if (row.id === "pattern_viral_decode" && !ctx.evidenceVideoQuery && !ctx.videoQuery) {
    return { ...row, disabledReason: "Chưa có video mẫu" };
  }
  if (
    (row.intentType === "video_diagnosis" || row.id === "script_sample_video") &&
    row.action === "handoff" &&
    !ctx.videoQuery &&
    !ctx.evidenceVideoQuery
  ) {
    return { ...row, disabledReason: "Cần URL video" };
  }
  if (row.id === "video_channel" && !ctx.creatorHandle?.trim()) {
    return { ...row, disabledReason: "Chưa có @kênh trong báo cáo" };
  }
  return row;
}

const VISIBLE_CTA_LIMIT = 4;

/** When basic video has >4 rows, keep deep upgrade — drop lower-priority pills first. */
const VIDEO_CTA_DROP_PRIORITY: IntentCtaId[] = [
  "video_compare",
  "video_hook_variants",
  "video_timing",
  "video_channel",
];

function capVisibleSuggestions(
  rows: IntentCtaSuggestion[],
  ctx: IntentCtaContext,
): IntentCtaSuggestion[] {
  if (rows.length <= VISIBLE_CTA_LIMIT) return rows;
  const deepIdx = rows.findIndex((r) => r.id === "video_deep");
  const mustKeepDeep =
    ctx.format === "video" && ctx.depth === "basic" && deepIdx >= VISIBLE_CTA_LIMIT;
  if (!mustKeepDeep) return rows.slice(0, VISIBLE_CTA_LIMIT);

  const deep = rows[deepIdx]!;
  const kept = rows.slice(0, VISIBLE_CTA_LIMIT);
  for (const dropId of VIDEO_CTA_DROP_PRIORITY) {
    const swapIdx = kept.findIndex((r) => r.id === dropId);
    if (swapIdx >= 0) {
      const next = [...kept];
      next[swapIdx] = deep;
      return next;
    }
  }
  return rows.slice(0, VISIBLE_CTA_LIMIT);
}

/** 2–4 visible CTAs filtered by format, mode, depth, prerequisites. */
export function getIntentCtaSuggestions(ctx: IntentCtaContext): IntentCtaSuggestion[] {
  const raw =
    ctx.format === "video" ? baseVideoRows(ctx) : (MATRIX[ctx.format] ?? MATRIX.generic);
  const mapped = raw.map((row) => {
    const applied = applyPrerequisites(row, ctx);
    if (row.id === "video_channel" && ctx.creatorHandle?.trim()) {
      return { ...applied, label: channelCtaLabel(ctx.creatorHandle) };
    }
    return applied;
  });
  return capVisibleSuggestions(mapped, ctx);
}

/** Query string sent to append_turn — fixed copy, not user free text. */
export function intentCtaQueryForSuggestion(
  suggestion: IntentCtaSuggestion,
  ctx: IntentCtaContext,
): string {
  switch (suggestion.id) {
    case "video_script":
    case "pattern_script":
    case "ideas_full_script":
    case "timing_hot_script":
    case "generic_script":
      return "Tạo kịch bản từ kết quả phân tích này";
    case "video_hook_variants":
      return "Tạo biến thể hook cho video này";
    case "video_timing":
      return "Giờ đăng tốt nhất cho video này";
    case "timing_calendar":
      return "Lên lịch đăng tuần này";
    case "generic_trends":
      return "Xu hướng đang hot trong ngách";
    default:
      return suggestion.label;
  }
}
