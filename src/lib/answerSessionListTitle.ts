/**
 * Sidebar / history display titles for answer sessions.
 * Mirrors ``answer_session_list_title`` (ISSUE-014) plus TikTok identity hints.
 */

import { formatTikTokSidebarHint } from "@/lib/tiktokUrl";

const LIST_TITLE_MAX = 120;
const SIDEBAR_MAX = 72;

const URL_LIKE_RE = /^https?:\/\//i;
const GENERIC_VIDEO_TITLE_RE =
  /^(?:Video của mình flop|Tại sao video này nổ\/flop\?|https?:\/\/|www\.tiktok\.com)/i;

/** SQL ``answer_session_list_title`` — prefer ``initial_q`` when stored title is a suffix fragment. */
export function answerSessionListTitle(
  title: string | null | undefined,
  initialQ: string | null | undefined,
): string {
  const t = (title ?? "").trim();
  const q = (initialQ ?? "").trim();
  if (!q) return t.slice(0, LIST_TITLE_MAX);
  if (!t) return q.slice(0, LIST_TITLE_MAX);
  if (
    t.length <= 8 &&
    q.length > t.length + 5 &&
    !q.startsWith(t) &&
    q.endsWith(t)
  ) {
    return q.slice(0, LIST_TITLE_MAX);
  }
  return (t || q).slice(0, LIST_TITLE_MAX);
}

function isUrlLike(text: string): boolean {
  const s = text.trim();
  return URL_LIKE_RE.test(s) || /\btiktok\.com\b/i.test(s);
}

function isGenericVideoTitle(text: string): boolean {
  return GENERIC_VIDEO_TITLE_RE.test(text.trim());
}

function sidebarIntentShort(
  intentType: string | null | undefined,
  format: string | null | undefined,
): string | null {
  switch (intentType) {
    case "video_diagnosis":
      return "Video";
    case "own_flop_no_url":
      return "Flop";
    case "compare_videos":
      return "So sánh";
    case "trend_spike":
      return "Xu hướng";
    case "content_directions":
      return "Hướng nội dung";
    case "fatigue":
      return "Mệt hook";
    case "brief_generation":
      return "Brief";
    case "shot_list":
      return "Kịch bản";
    default:
      break;
  }
  switch (format) {
    case "video":
      return "Video";
    case "pattern":
      return "Pattern";
    case "ideas":
      return "Ideas";
    case "timing":
      return "Timing";
    case "lifecycle":
      return "Vòng đời";
    case "diagnostic":
      return "Chẩn đoán";
    case "script":
      return "Kịch bản";
    case "compare":
      return "So sánh";
    default:
      return null;
  }
}

function truncateSidebar(text: string): string {
  const s = text.trim();
  if (s.length <= SIDEBAR_MAX) return s;
  return `${s.slice(0, SIDEBAR_MAX - 1)}…`;
}

export type AnswerSessionSidebarLabelInput = {
  /** User rename from sidebar — wins over auto title. */
  label?: string | null;
  title?: string | null;
  initial_q?: string | null;
  intent_type?: string | null;
  format?: string | null;
};

/** Primary line for AppLayout ``SessionRow`` (answer sessions). */
export function answerSessionSidebarLabel(input: AnswerSessionSidebarLabelInput): string {
  const userLabel = input.label?.trim();
  if (userLabel) return truncateSidebar(userLabel);

  const initialQ = (input.initial_q ?? "").trim();
  const derived = answerSessionListTitle(input.title, initialQ).trim();
  const tiktokHint =
    formatTikTokSidebarHint(initialQ) ?? (isUrlLike(derived) ? formatTikTokSidebarHint(derived) : null);

  if (isUrlLike(derived)) {
    return truncateSidebar(tiktokHint ?? "Link TikTok");
  }

  if (isGenericVideoTitle(derived) && tiktokHint) {
    const short = sidebarIntentShort(input.intent_type, input.format);
    return truncateSidebar(short ? `${short} · ${tiktokHint}` : tiktokHint);
  }

  if (tiktokHint && derived.length <= 16) {
    return truncateSidebar(tiktokHint);
  }

  return truncateSidebar(derived || "Phiên nghiên cứu");
}

/** Channel visit row — normalize handle display. */
export function channelSidebarLabel(handle: string | null | undefined): string {
  const raw = (handle ?? "").trim().replace(/^@/, "");
  return raw ? `@${raw}` : "Kênh TikTok";
}
