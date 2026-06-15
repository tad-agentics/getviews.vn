/** Replace stats jargon (median, p75, …) in diagnosis prose for creator-facing copy. */

import { HOOK_NAMES_VI } from "@/lib/constants/hook-names-vi";
import {
  CONVERSION_OBJECTIVE_VI,
  HOOK_TIMELINE_EVENT_VI,
  STYLE_TAG_VI,
} from "@/lib/constants/enum-labels-vi";
import { formatViews } from "@/lib/formatters";

const CHANNEL_MEDIAN = "mức view thường trên kênh";
const NICHE_MEDIAN = "mức view thường trong ngách";
const GENERIC_MEDIAN = "mức view thường";

/** Ordered — specific patterns before generic median/trung vị fallbacks. */
const REPLACEMENTS: ReadonlyArray<[RegExp, string]> = [
  [/\bp90\b/gi, "mức rất cao trong ngách (top 10%)"],
  [/\bp75\b/gi, "mức cao trong ngách (top 25%)"],
  [/\bp25\b/gi, "mức thấp trong ngách (bottom 25%)"],
  [/\bp50\b/gi, "mức giữa ngách"],
  [
    /(?:median|trung vị)\s+([\d.,]+)\s*view\s+của kênh/gi,
    `${CHANNEL_MEDIAN} (khoảng $1 lượt xem)`,
  ],
  [/(?:median|trung vị)\s+kênh/gi, CHANNEL_MEDIAN],
  [/(?:median|trung vị)\s+ngách/gi, NICHE_MEDIAN],
  [/×\s*(?:median|trung vị)\s+ngách/gi, `× ${NICHE_MEDIAN}`],
  [/×\s*(?:median|trung vị)/gi, `× ${GENERIC_MEDIAN}`],
  [/so với\s+(?:median|trung vị)/gi, `so với ${GENERIC_MEDIAN}`],
  [/dưới\s+(?:median|trung vị)/gi, `dưới ${GENERIC_MEDIAN}`],
  [/trên\s+(?:median|trung vị)/gi, `trên ${GENERIC_MEDIAN}`],
  [/\bmedian\b/gi, GENERIC_MEDIAN],
  [/trung vị/gi, GENERIC_MEDIAN],
];

/** Mirrors ``voice_copy._JARGON_SUBS`` — keep in sync with Python. */
const JARGON_REPLACEMENTS: ReadonlyArray<[RegExp, string]> = [
  [/\bpain[\s_-]?points?\b/gi, "điểm nhạy"],
  [/\bpattern[\s_-]?interrupt\b/gi, "ngắt nhịp"],
  [/\boverlay checklist\b/gi, "danh sách bước trên màn hình"],
  [/\btext[\s_-]?overlay\b/gi, "chữ trên màn hình"],
  [/\bface[\s_-]?enter\b/gi, "khuôn mặt xuất hiện"],
  [/\bentertainment[\s_-]?first\b/gi, "giải trí là chính"],
  [/\bdead[\s_-]?air\b/gi, "khoảng lặng"],
  [/\bjump[\s_-]?cut\b/gi, "cắt giật"],
  [/\bdiscoverability\b/gi, "khả năng được tìm thấy"],
  [/\bformat\s+['"]faceless['"]/gi, "định dạng không lộ mặt"],
  [/\bformat\s+faceless\b/gi, "định dạng không lộ mặt"],
  [/\barchetypes?\b/gi, "hình mẫu"],
  [/\bbookmarks?\b/gi, "lưu"],
  [/\bexperts?\b/gi, "chuyên gia"],
  [/\btutorials?\b/gi, "hướng dẫn"],
  [/\btemplates?\b/gi, "mẫu"],
  [/\bpromises?\b/gi, "lời hứa"],
  [/\btips?\b/gi, "mẹo"],
  [/\bheatmaps?\b/gi, "bản đồ nhiệt"],
  [/\bcorpus\b/gi, "kho video"],
  [/\bformats?\b/gi, "định dạng"],
  [/\bprice[\s_-]?anchor\b/gi, "neo giá"],
  [/\bnegative[\s_-]?markers?\b/gi, "dấu hiệu tiêu cực"],
  [/\b(?:audio[\s_-]?)?transcript\b/gi, "lời thoại"],
  [/\bcuriousity[\s_-]?gap\b/gi, "Tạo khoảng trống tò mò"],
  [/\bcompletion[\s_-]?rates?\b/gi, "tỷ lệ xem hết"],
];

function collapseJargonDuplicates(text: string): string {
  return text
    .replace(/ngắt nhịp\s*\(\s*ngắt nhịp\s*\)/gi, "ngắt nhịp")
    .replace(/\(\s*ngắt nhịp\s*\)\s*\(\s*ngắt nhịp\s*\)/gi, "(ngắt nhịp)")
    .replace(/góc nhìn\s+góc nhìn\s+POV/gi, "góc nhìn POV");
}

const ENUM_PROSE_VI: Record<string, string> = {
  ...HOOK_NAMES_VI,
  ...STYLE_TAG_VI,
  ...HOOK_TIMELINE_EVENT_VI,
  ...CONVERSION_OBJECTIVE_VI,
};

function substituteEnumCodesInProse(text: string): string {
  let out = text;
  const keys = Object.keys(ENUM_PROSE_VI).sort((a, b) => b.length - a.length);
  for (const key of keys) {
    if (!key || key === "none" || key === "other") continue;
    const pattern = new RegExp(`\\b${key.replace(/_/g, "[\\s_-]")}\\b`, "gi");
    out = out.replace(pattern, ENUM_PROSE_VI[key]!);
  }
  return out;
}

export function humanizeStatsProse(text: string): string {
  if (!text.trim()) return text;
  let out = text;
  for (const [pattern, replacement] of REPLACEMENTS) {
    out = out.replace(pattern, replacement);
  }
  for (const [pattern, replacement] of JARGON_REPLACEMENTS) {
    out = out.replace(pattern, replacement);
  }
  out = out.replace(/(\d[\d.,]+)\s*view\b/gi, (_, raw: string) => {
    const n = Number(String(raw).replace(/[.,]/g, ""));
    if (!Number.isFinite(n) || n <= 0) return `${raw} view`;
    return `${formatViews(n)} view`;
  });
  return collapseJargonDuplicates(substituteEnumCodesInProse(out));
}

/** Split v6 section text into bold verdict + optional support sentences (redesign 2026-05). */
export function splitVerdictProse(text: string): { verdict: string; support: string } {
  const humanized = humanizeStatsProse(text.trim());
  if (!humanized) return { verdict: "", support: "" };
  const boldMatch = humanized.match(/\*\*([^*]+)\*\*/);
  if (boldMatch) {
    const verdict = boldMatch[1].trim();
    const support = humanized.replace(/\*\*[^*]+\*\*/, "").replace(/^\s+/, "").trim();
    return { verdict, support };
  }
  const parts = humanized.split(/\n\n+/).map((p) => p.trim()).filter(Boolean);
  if (parts.length <= 1) {
    // No explicit verdict marker — render as normal prose, not a fake bold headline.
    return { verdict: "", support: humanized };
  }
  return { verdict: parts[0] ?? "", support: parts.slice(1).join("\n\n").trim() };
}
