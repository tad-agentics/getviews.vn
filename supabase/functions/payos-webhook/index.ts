import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { corsHeaders } from "../_shared/cors.ts";

async function hmacSha256Hex(secret: string, payload: string): Promise<string> {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(payload));
  const bytes = new Uint8Array(sig);
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let x = 0;
  for (let i = 0; i < a.length; i++) x |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return x === 0;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const checksumKey = Deno.env.get("PAYOS_CHECKSUM_KEY");
  const url = Deno.env.get("SUPABASE_URL")!;
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

  if (!checksumKey) {
    return new Response(JSON.stringify({ error: "PAYOS_CHECKSUM_KEY missing" }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const supabase = createClient(url, serviceKey);

  try {
    const rawBody = await req.text();
    const headerSig =
      req.headers.get("x-payos-signature") ??
      req.headers.get("X-PayOS-Signature") ??
      "";

    const expected = await hmacSha256Hex(checksumKey, rawBody);
    if (!headerSig || !timingSafeEqual(headerSig.toLowerCase(), expected.toLowerCase())) {
      return new Response(JSON.stringify({ error: "Invalid signature" }), {
        status: 401,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const payload = JSON.parse(rawBody) as {
      code?: string;
      data?: {
        orderCode?: string;
        paymentLinkId?: string;
        desc?: string;
        amount?: number;
      };
    };

    const orderCode = payload.data?.orderCode != null ? String(payload.data.orderCode) : "";
    if (!orderCode) {
      return new Response(JSON.stringify({ error: "Missing orderCode" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const success = payload.code === "00" || payload.data?.desc === "success";
    const eventType = success ? "PAID" : "CANCELLED";

    const { error: insErr } = await supabase.from("processed_webhook_events").insert({
      payos_order_code: orderCode,
      event_type: eventType,
    });

    if (insErr?.code === "23505") {
      return new Response(JSON.stringify({ success: true, duplicate: true }), {
        status: 200,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
    if (insErr) throw insErr;

    const paymentId = payload.data?.paymentLinkId ?? "";

    const { data: grantResult, error: rpcErr } = await supabase.rpc("decrement_and_grant_credits", {
      p_payos_order_code: orderCode,
      p_payos_payment_id: paymentId,
      p_event_type: eventType,
    });

    if (rpcErr) throw rpcErr;

    const grant = grantResult as Record<string, unknown> | null;

    if (success && grant && grant.user_id && typeof grant.user_id === "string") {
      const uid = grant.user_id;
      const { data: profile } = await supabase.from("profiles").select("display_name, email").eq("id", uid).single();

      const { data: sub } = await supabase
        .from("subscriptions")
        .select("tier, deep_credits_granted, expires_at, amount_vnd")
        .eq("payos_order_code", orderCode)
        .single();

      if (profile?.email && sub) {
        await fetch(`${url}/functions/v1/send-email`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${serviceKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            template: "receipt",
            to: profile.email,
            data: {
              count: sub.deep_credits_granted,
              display_name: profile.display_name ?? "",
              tier: sub.tier,
              expires_at: sub.expires_at,
              amount_vnd: sub.amount_vnd,
            },
          }),
        });
      }
    }

    return new Response(JSON.stringify({ success: true }), {
      status: 200,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "webhook_error";
    console.error("payos-webhook", e);
    return new Response(JSON.stringify({ error: msg }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
