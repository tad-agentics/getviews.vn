/**
 * Marketing Corpus Pick — thin proxy to Cloud Run batch.
 *
 * Auth: Supabase service_role JWT (requireServiceRole).
 * Env: CLOUD_RUN_BATCH_URL, BATCH_SECRET, optional R2_PUBLIC_URL.
 *
 * Do NOT call from the browser — use server-side scripts only.
 */

import { corsHeaders } from "../_shared/cors.ts";
import { requireServiceRole } from "../_shared/auth.ts";

// Vault/pg_cron uses ``cloud_run_api_url``; Edge secrets may use either name.
const BATCH_URL = (
  Deno.env.get("CLOUD_RUN_BATCH_URL") ??
  Deno.env.get("cloud_run_api_url") ??
  ""
).replace(/\/$/, "");
const BATCH_SECRET =
  Deno.env.get("BATCH_SECRET") ?? Deno.env.get("cloud_run_batch_secret") ?? "";

function jsonResponse(body: unknown, status: number, extraHeaders?: Record<string, string>): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...corsHeaders,
      "Content-Type": "application/json",
      ...extraHeaders,
    },
  });
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  const authFail = requireServiceRole(req);
  if (authFail) return authFail;

  if (req.method !== "POST") {
    return jsonResponse({ error: "method_not_allowed" }, 405);
  }

  if (!BATCH_URL || !BATCH_SECRET) {
    console.error("[marketing-corpus-pick] missing CLOUD_RUN_BATCH_URL or BATCH_SECRET");
    return jsonResponse({ error: "server_misconfigured" }, 500);
  }

  const batchEndpoint = `${BATCH_URL}/batch/marketing-corpus-pick`;
  let batchRes: Response;
  try {
    batchRes = await fetch(batchEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Batch-Secret": BATCH_SECRET,
      },
      body: "{}",
      signal: AbortSignal.timeout(120_000),
    });
  } catch (e) {
    console.error("[marketing-corpus-pick] batch fetch failed", e);
    return jsonResponse({ error: "batch_unreachable" }, 502);
  }

  const text = await batchRes.text();
  let parsed: Record<string, unknown> = {};
  try {
    parsed = text ? (JSON.parse(text) as Record<string, unknown>) : {};
  } catch {
    parsed = { raw: text };
  }

  if (!batchRes.ok) {
    const detail = parsed.detail ?? parsed.error ?? parsed;
    if (batchRes.status === 404) {
      return jsonResponse(
        { error: "marketing_pool_exhausted", detail },
        404,
      );
    }
    if (batchRes.status === 502) {
      return jsonResponse({ error: "analysis_failed", detail }, 502);
    }
    return jsonResponse(
      { error: "batch_error", status: batchRes.status, detail },
      batchRes.status >= 400 && batchRes.status < 600 ? batchRes.status : 502,
    );
  }

  // Batch wraps payload as { ok: true, ...fields }
  const { ok: _ok, ...payload } = parsed;
  return jsonResponse(payload, 200);
});
