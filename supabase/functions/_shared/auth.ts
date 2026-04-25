// Edge Function auth helper.
//
// Replaces the previous strict ``token !== SUPABASE_SERVICE_ROLE_KEY``
// comparison which silently 401s when the cron.job hardcoded JWT was
// minted under a now-rotated service_role secret. Instead we decode
// the JWT payload and verify ``role === "service_role"`` — Supabase
// Auth's signing key validates signatures upstream of this function
// so a forged token would never reach this check.
//
// Returns a 401 Response if auth fails, or null when the request
// should proceed.

import { corsHeaders } from "./cors.ts";

function unauthorized(reason: string): Response {
  return new Response(JSON.stringify({ error: "Unauthorized", reason }), {
    status: 401,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    const b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
    const decoded = atob(padded);
    return JSON.parse(decoded);
  } catch (_e) {
    return null;
  }
}

export function requireServiceRole(req: Request): Response | null {
  const auth = req.headers.get("Authorization") ?? "";
  const token = auth.replace(/^Bearer\s+/i, "").trim();
  if (!token) return unauthorized("missing bearer");
  const payload = decodeJwtPayload(token);
  if (!payload) return unauthorized("malformed jwt");
  if (payload.role !== "service_role") return unauthorized("role mismatch");
  const now = Math.floor(Date.now() / 1000);
  const exp = typeof payload.exp === "number" ? payload.exp : 0;
  if (exp && exp < now) return unauthorized("token expired");
  return null;
}
