/**
 * CORS helpers for Supabase Edge Functions.
 *
 * Previously this module exported ``corsHeaders`` with
 * ``Access-Control-Allow-Origin: "*"``. Wildcard CORS is harmless
 * for our cron / webhook handlers (those are server-to-server and
 * never preflight) but still poor hygiene — defence-in-depth, and
 * a foot-gun if a future contributor copies the headers into a
 * browser-callable handler. We now echo origin only when it
 * matches the production / preview / localhost allowlist.
 *
 * Usage (browser-callable handler — e.g. ``create-payment``):
 *   const headers = buildCorsHeaders(req);
 *   return new Response("ok", { headers });
 *
 * Usage (server-to-server handler — e.g. PayOS webhook / cron):
 *   `corsHeaders` is still re-exported for backward compatibility
 *   but no longer contains a wildcard. CORS is a no-op there.
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

const ALLOWED_HEADERS =
  "authorization, x-client-info, apikey, content-type, x-payos-signature";

export function isAllowedOrigin(origin: string | null): boolean {
  if (!origin) return false;
  if (STATIC_ALLOWED_ORIGINS.includes(origin)) return true;
  return REGEX_ALLOWED_ORIGINS.some((re) => re.test(origin));
}

export function buildCorsHeaders(req: Request): Record<string, string> {
  const origin = req.headers.get("origin");
  const headers: Record<string, string> = {
    "Access-Control-Allow-Headers": ALLOWED_HEADERS,
    Vary: "Origin",
  };
  if (origin && isAllowedOrigin(origin)) {
    headers["Access-Control-Allow-Origin"] = origin;
  }
  return headers;
}

/**
 * Static fallback for handlers that never see a browser preflight
 * (server-to-server: PayOS webhook, pg_cron jobs). Includes the
 * allow-headers so a misconfigured caller still gets sensible
 * responses, but no longer hands out a wildcard origin.
 */
export const corsHeaders: Record<string, string> = {
  "Access-Control-Allow-Headers": ALLOWED_HEADERS,
  Vary: "Origin",
};
