/** Extract TikTok aweme_id from a URL or bare-id string in user paste/query. */
export function extractTikTokVideoIdFromText(text: string): string | null {
  const raw = (text || "").trim();
  if (!raw) return null;
  const urlMatch =
    raw.match(/tiktok\.com\/@[^/\s]+\/video\/(\d{15,22})/i) ??
    raw.match(/tiktok\.com\/video\/(\d{15,22})/i);
  if (urlMatch?.[1]) return urlMatch[1];
  const bare = raw.match(/\b(\d{17,22})\b/);
  return bare?.[1] ?? null;
}
