import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { z } from "https://esm.sh/zod@3.24.2";
import { corsHeaders } from "../_shared/cors.ts";

const BodySchema = z.object({
  tier: z.enum(["starter", "pro", "agency"]),
  billing_period: z.enum(["monthly", "biannual", "annual"]),
  is_overage: z.boolean(),
  overage_pack_size: z.union([z.literal(10), z.literal(30), z.literal(50), z.null()]),
});

/** PayOS orderCode is numeric in API; we keep a stable string id for our DB + description. */
function orderCodes(): { numeric: number; label: string } {
  const numeric = Number(`${Date.now()}`.slice(-12));
  return { numeric, label: `GV-${numeric}` };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const url = Deno.env.get("SUPABASE_URL")!;
  const anon = Deno.env.get("SUPABASE_ANON_KEY")!;
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const payosClientId = Deno.env.get("PAYOS_CLIENT_ID");
  const payosApiKey = Deno.env.get("PAYOS_API_KEY");

  const authHeader = req.headers.get("Authorization");
  if (!authHeader?.startsWith("Bearer ")) {
    return new Response(JSON.stringify({ error: { code: "UNAUTHORIZED", message: "Missing JWT" } }), {
      status: 401,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const userClient = createClient(url, anon, {
    global: { headers: { Authorization: authHeader } },
  });

  const {
    data: { user },
    error: userErr,
  } = await userClient.auth.getUser();
  if (userErr || !user) {
    return new Response(JSON.stringify({ error: { code: "UNAUTHORIZED", message: "Invalid session" } }), {
      status: 401,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  try {
    const json = await req.json();
    const parsed = BodySchema.safeParse(json);
    if (!parsed.success) {
      return new Response(JSON.stringify({ error: { code: "VALIDATION_ERROR", message: parsed.error.message } }), {
        status: 422,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const { tier, billing_period, is_overage, overage_pack_size } = parsed.data;
    if (is_overage && overage_pack_size === null) {
      return new Response(JSON.stringify({ error: { code: "VALIDATION_ERROR", message: "overage_pack_size required" } }), {
        status: 422,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
    if (!is_overage && overage_pack_size !== null) {
      return new Response(JSON.stringify({ error: { code: "VALIDATION_ERROR", message: "unexpected overage_pack_size" } }), {
        status: 422,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // Placeholder pricing — replace with pricing table / env in production
    const amountTable: Record<string, Record<string, number>> = {
      starter: { monthly: 249_000, biannual: 1_290_000, annual: 2_388_000 },
      pro: { monthly: 499_000, biannual: 2_590_000, annual: 4_788_000 },
      agency: { monthly: 999_000, biannual: 5_190_000, annual: 9_588_000 },
    };

    let billingPeriod: "monthly" | "biannual" | "annual" | "overage_10" | "overage_30" | "overage_50" = billing_period;
    let amountVnd = amountTable[tier][billing_period];
    let credits = tier === "starter" ? 30 : tier === "pro" ? 80 : 200;

    if (is_overage && overage_pack_size) {
      billingPeriod =
        overage_pack_size === 10 ? "overage_10" : overage_pack_size === 30 ? "overage_30" : "overage_50";
      const overagePrices = { 10: 79_000, 30: 199_000, 50: 299_000 };
      const overageCredits = { 10: 10, 30: 30, 50: 50 };
      amountVnd = overagePrices[overage_pack_size];
      credits = overageCredits[overage_pack_size];
    }

    const { numeric: orderNum, label: code } = orderCodes();
    const starts = new Date();
    const expires = new Date(starts);
    if (billingPeriod === "monthly") expires.setMonth(expires.getMonth() + 1);
    else if (billingPeriod === "biannual") expires.setMonth(expires.getMonth() + 6);
    else if (billingPeriod === "annual") expires.setFullYear(expires.getFullYear() + 1);
    else expires.setMonth(expires.getMonth() + 1);

    const admin = createClient(url, serviceKey);

    const { error: subErr } = await admin.from("subscriptions").insert({
      user_id: user.id,
      tier,
      billing_period: billingPeriod,
      amount_vnd: amountVnd,
      deep_credits_granted: credits,
      starts_at: starts.toISOString(),
      expires_at: expires.toISOString(),
      payos_order_code: String(orderNum),
      status: "pending",
    });

    if (subErr) throw subErr;

    if (!payosClientId || !payosApiKey) {
      return new Response(
        JSON.stringify({
          error: { code: "SERVER_ERROR", message: "PayOS not configured" },
        }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    const appUrl = Deno.env.get("PUBLIC_APP_URL") ?? "https://getviews.vn";
    const payosRes = await fetch("https://api-merchant.payos.vn/v2/payment-requests", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-client-id": payosClientId,
        "x-api-key": payosApiKey,
      },
      body: JSON.stringify({
        orderCode: orderNum,
        amount: amountVnd,
        description: `GetViews ${tier} ${code}`,
        cancelUrl: `${appUrl}/app/settings`,
        returnUrl: `${appUrl}/app/settings`,
      }),
    });

    const payosJson = (await payosRes.json()) as Record<string, unknown>;
    if (!payosRes.ok) {
      console.error("PayOS error", payosJson);
      throw new Error("payos_create_failed");
    }

    const data = payosJson.data as Record<string, unknown> | undefined;
    const checkoutUrl = (data?.checkoutUrl ?? data?.checkout_url) as string | undefined;
    const qr = (data?.qrCode ?? data?.qr_code) as string | undefined;

    return new Response(
      JSON.stringify({
        order_code: String(orderNum),
        payment_url: checkoutUrl ?? "",
        qr_code_url: qr ?? "",
        bank_details: {
          bank_name: "PayOS",
          account_number: "",
          account_name: "GETVIEWS",
          reference_code: String(orderNum),
        },
        amount_vnd: amountVnd,
        expires_at: expires.toISOString(),
      }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  } catch (e) {
    const msg = e instanceof Error ? e.message : "create_payment_failed";
    return new Response(JSON.stringify({ error: { code: "SERVER_ERROR", message: msg } }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
