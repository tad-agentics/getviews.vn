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
const EXPLORE_HANDLE_RE = /(?:tiktok\.com\/@|^@)([A-Za-z0-9._]+)/;

/** Parse @handle, bare handle, or tiktok.com/@… for Khám kênh / channel explore. */
export function parseChannelExploreHandle(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const match = trimmed.match(EXPLORE_HANDLE_RE);
  if (match) return `@${match[1]}`;
  if (trimmed.startsWith("@")) return trimmed;
  if (/^[A-Za-z0-9._]+$/.test(trimmed)) return `@${trimmed}`;
  return null;
}

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
