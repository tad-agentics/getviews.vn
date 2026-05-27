/** Creator handle from a TikTok URL in paste/query text. */
export function extractTikTokHandleFromText(text: string): string | null {
  const raw = (text || "").trim();
  if (!raw) return null;
  const m = raw.match(/tiktok\.com\/@([^/?#\s]+)/i);
  return m?.[1] ?? null;
}

/** Compact sidebar/history label: ``@creator · …123456`` when URL is present. */
export function formatTikTokSidebarHint(text: string): string | null {
  const handle = extractTikTokHandleFromText(text);
  const vid = extractTikTokVideoIdFromText(text);
  const tail = vid && vid.length >= 6 ? `…${vid.slice(-6)}` : null;
  if (handle && tail) return `@${handle} · ${tail}`;
  if (handle) return `@${handle}`;
  if (tail) return `Video · ${tail}`;
  return null;
}

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

/** Mirror ``intent-router.ts`` / ``url_patterns.py`` — TikTok-only HTTP(S) links. */
const TIKTOK_HTTP_URL_RE =
  /https?:\/\/(?:(?:www\.)?tiktok\.com|(?:vm|vt|m)\.tiktok\.com)\/\S+/gi;

const HTTP_URL_RE = /https?:\/\/\S+/gi;

/** Hosts that must never enter the video analysis pipeline (with or without ``https://``). */
const NON_TIKTOK_VIDEO_HOST_RE =
  /\b(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be|instagram\.com|facebook\.com|fb\.watch)\b/i;

/** TikTok host in paste text — includes bare ``tiktok.com/...`` without a scheme. */
const TIKTOK_HOST_IN_TEXT_RE =
  /\b(?:https?:\/\/)?(?:(?:www\.)?(?:tiktok\.com)|(?:vm|vt|m)\.tiktok\.com)\b/i;

/**
 * Non-TikTok sites pasted like a video link (e.g. ``linhbeauty.vn/video/74012…``)
 * without ``https://`` — would bypass ``HTTP_URL_RE``-only checks.
 */
const EXTERNAL_VIDEO_PAGE_RE =
  /\b(?:https?:\/\/)?(?:www\.)?(?!(?:(?:vm|vt|m)\.)?tiktok\.com\b)[a-z0-9][-a-z0-9.]*\.[a-z]{2,}\/video\/\d/i;

/** TikTok video paths — strip before external-domain scan so dotted handles (e.g. @curnon.official) are not matched as ``handle.tld/video/…``. */
const TIKTOK_VIDEO_PATH_SEGMENT_RE =
  /\b(?:https?:\/\/)?(?:(?:www\.)?(?:tiktok\.com)|(?:vm|vt|m)\.tiktok\.com)\/@[^/\s]+\/video\/\d+/gi;

function stripTikTokVideoPathSegments(text: string): string {
  TIKTOK_VIDEO_PATH_SEGMENT_RE.lastIndex = 0;
  return text.replace(TIKTOK_VIDEO_PATH_SEGMENT_RE, " ");
}

/** User-facing copy (EDS + copy-rules). */
export const NON_TIKTOK_URL_MESSAGE =
  "Link không hợp lệ — cần link TikTok (tiktok.com hoặc vm/vt.tiktok.com).";

export function extractHttpUrlsFromText(text: string): string[] {
  return text.match(HTTP_URL_RE) ?? [];
}

export function isTikTokHttpUrl(url: string): boolean {
  return /https?:\/\/(?:(?:www\.)?tiktok\.com|(?:vm|vt|m)\.tiktok\.com)\//i.test(
    url.trim(),
  );
}

/** Returns Vietnamese error when any URL-like token is not TikTok; otherwise ``null``. */
export function nonTikTokUrlValidationMessage(text: string): string | null {
  if (NON_TIKTOK_VIDEO_HOST_RE.test(text)) {
    return NON_TIKTOK_URL_MESSAGE;
  }
  if (EXTERNAL_VIDEO_PAGE_RE.test(stripTikTokVideoPathSegments(text))) {
    return NON_TIKTOK_URL_MESSAGE;
  }
  const urls = extractHttpUrlsFromText(text);
  if (urls.length === 0) return null;
  if (urls.every(isTikTokHttpUrl)) return null;
  return NON_TIKTOK_URL_MESSAGE;
}

export function hasTikTokUrlInText(text: string): boolean {
  TIKTOK_HTTP_URL_RE.lastIndex = 0;
  if (TIKTOK_HTTP_URL_RE.test(text)) return true;
  return TIKTOK_HOST_IN_TEXT_RE.test(text);
}

export type QueryUrlChipState =
  | { kind: "none" }
  | { kind: "tiktok" }
  | { kind: "invalid"; message: string };

export function queryUrlChipState(text: string): QueryUrlChipState {
  const invalid = nonTikTokUrlValidationMessage(text);
  if (invalid) return { kind: "invalid", message: invalid };
  if (hasTikTokUrlInText(text)) return { kind: "tiktok" };
  return { kind: "none" };
}
