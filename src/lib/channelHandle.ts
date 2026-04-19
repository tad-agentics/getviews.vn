/**
 * TikTok handle helpers for `/app/channel` and chat handoff (B.3.4).
 */

export function normalizeChannelHandleInput(raw: string | null | undefined): string | null {
  const h = (raw ?? "").trim().replace(/^@+/, "");
  return h || null;
}

/**
 * Parse a profile URL or first @handle from free text. Skips `/video/` and
 * `/photo/` URLs so video links are not mistaken for channel profiles.
 */
export function extractChannelHandleFromMessage(text: string): string | null {
  const q = text.trim();
  // Video / photo permalinks contain `@handle` in the path — do not treat as profile.
  if (/tiktok\.com\/@[^/\s]+\/(video|photo)\//i.test(q)) {
    return null;
  }
  const urlMatch = q.match(/https?:\/\/(?:www\.)?tiktok\.com\/@([^\s/?#]+)/i);
  if (urlMatch) {
    return normalizeChannelHandleInput(urlMatch[1]);
  }
  const atMatch = q.match(/@([\w.]+)/);
  if (atMatch) return normalizeChannelHandleInput(atMatch[1]);
  return null;
}
