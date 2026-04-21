/**
 * TikTok URL recognition — shared between the interactive input capture
 * (`VideoUrlCapture`) and the query-param deep-link path on `/app/video`.
 *
 * Deliberately lenient: we accept any hostname ending in `tiktok.com`
 * (including the `vm.tiktok.com` / `vt.tiktok.com` / `m.tiktok.com`
 * subdomains users paste from share buttons) and tolerate missing
 * `https://` prefixes. A strict video-path regex is handled server-side
 * — getting past this gate just means the request reaches Cloud Run,
 * which will 404 if the URL doesn't resolve to a corpus row.
 */
export function looksLikeTikTokUrl(raw: string): boolean {
  const s = raw.trim();
  if (!s || s.startsWith("@")) return false;
  const candidate = s.includes("://") ? s : `https://${s}`;
  try {
    return new URL(candidate).hostname.toLowerCase().endsWith("tiktok.com");
  } catch {
    return false;
  }
}
