/**
 * TikTok aweme id for the official embed player: ``/embed/v2/{id}``.
 * Prefer id parsed from ``tiktok_url`` when ``video_id`` is not numeric.
 */
export function tiktokAwemeIdForEmbed(
  videoId: string,
  tiktokUrl?: string | null,
): string | null {
  const fromUrl = tiktokUrl?.match(/video\/(\d+)/)?.[1];
  if (fromUrl && /^\d+$/.test(fromUrl)) return fromUrl;
  const id = videoId.trim();
  if (/^\d{10,22}$/.test(id)) return id;
  return null;
}
