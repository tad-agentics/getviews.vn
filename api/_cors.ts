/**
 * CORS helpers for Vercel Edge handlers under ``api/``.
 *
 * Mirrors ``supabase/functions/_shared/cors.ts`` so both edge
 * surfaces echo the same allowlist. Production + the production
 * www host are matched by exact string; Vercel preview deploys and
 * localhost dev are matched by regex. Anything else (and any
 * cross-origin request from an attacker-controlled domain) gets
 * no ``Access-Control-Allow-Origin`` header — the browser will
 * then block the response.
 */

const STATIC_ALLOWED_ORIGINS = [
  "https://getviews.vn",
  "https://www.getviews.vn",
];

const REGEX_ALLOWED_ORIGINS = [
  /^https:\/\/[a-z0-9-]+\.vercel\.app$/,
  /^http:\/\/localhost:\d+$/,
  /^http:\/\/127\.0\.0\.1:\d+$/,
];

export function isAllowedOrigin(origin: string | null): boolean {
  if (!origin) return false;
  if (STATIC_ALLOWED_ORIGINS.includes(origin)) return true;
  return REGEX_ALLOWED_ORIGINS.some((re) => re.test(origin));
}

export function buildCorsHeaders(req: Request): Record<string, string> {
  const origin = req.headers.get("origin");
  const headers: Record<string, string> = {
    Vary: "Origin",
  };
  if (origin && isAllowedOrigin(origin)) {
    headers["Access-Control-Allow-Origin"] = origin;
  }
  return headers;
}
