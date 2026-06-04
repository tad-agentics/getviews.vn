/** Replace stats jargon (median, p75, …) in diagnosis prose for creator-facing copy. */

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

export function humanizeStatsProse(text: string): string {
  if (!text.trim()) return text;
  let out = text;
  for (const [pattern, replacement] of REPLACEMENTS) {
    out = out.replace(pattern, replacement);
  }
  return out;
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
  const parts = humanized.split(/\n\n+/);
  const verdict = (parts[0] ?? humanized).trim();
  const support = parts.slice(1).join("\n\n").trim();
  return { verdict, support };
}
