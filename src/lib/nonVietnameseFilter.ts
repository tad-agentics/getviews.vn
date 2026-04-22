/**
 * Off-language content heuristic for the Vietnamese-market corpus.
 *
 * BUG-14 (QA audit 2026-04-22): a Chinese-language video
 * ("沉浸式早八 淡颜韩系日常妆") surfaced in the Beauty/Skincare niche feed
 * alongside Vietnamese content. The root cause is upstream data tagging —
 * all 1208 corpus rows are ``language = 'vi'`` in the DB despite the
 * caption being Han + Hangul. Until the Gemini analyse pipeline is
 * tightened to detect CJK captions and set ``language`` correctly, the
 * client filters anything whose caption / hook_phrase is dominated by
 * Han or Hangul characters.
 *
 * Heuristic is conservative — we only skip a video when **more than 25%**
 * of the caption's non-space characters are CJK. This keeps borderline
 * bilingual captions ("vlog 東京 travel ngày 3") visible while reliably
 * catching pure-Chinese / pure-Korean content.
 */

// Unicode ranges covering Han (CJK Unified Ideographs) + Hangul + Hiragana
// + Katakana. Matches the overwhelming majority of non-VN TikTok captions
// that end up in a VN niche through a mis-tagging bug.
const CJK_PATTERN = /[぀-ゟ゠-ヿ一-鿿가-힯]/g;

export function countCjkCharacters(text: string | null | undefined): number {
  if (!text) return 0;
  return (text.match(CJK_PATTERN) ?? []).length;
}

/** Returns true when CJK chars dominate the caption (>25% by share). */
export function looksLikeNonVietnameseCaption(
  caption: string | null | undefined,
  threshold = 0.25,
): boolean {
  if (!caption) return false;
  const stripped = caption.replace(/\s+/g, "");
  if (stripped.length === 0) return false;
  const cjk = countCjkCharacters(stripped);
  return cjk / stripped.length > threshold;
}
