import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { z } from "https://esm.sh/zod@3.24.2";
import { corsHeaders } from "../_shared/cors.ts";

const PlanSchema = z.enum([
  "starter_monthly",
  "starter_biannual",
  "starter_annual",
  "pack_10",
  "pack_30",
  "pack_50",
]);

const PaymentMethodSchema = z.enum(["momo", "bank_transfer", "vietqr"]);

const BodySchema = z.object({
  plan: PlanSchema,
  payment_method: PaymentMethodSchema,
});

type DbBillingPeriod = "monthly" | "biannual" | "annual" | "overage_10" | "overage_30" | "overage_50";

const PLAN_CONFIG: Record<
  z.infer<typeof PlanSchema>,
  {
    amount_vnd: number;
    deep_credits_granted: number;
    tier: "starter";
    db_billing_period: DbBillingPeriod;
    billing_period: "monthly" | "biannual" | "annual" | "pack";
  }
> = {
  starter_monthly: {
    amount_vnd: 249_000,
    deep_credits_granted: 30,
    tier: "starter",
    db_billing_period: "monthly",
    billing_period: "monthly",
  },
  starter_biannual: {
    amount_vnd: 199_000 * 6,
    deep_credits_granted: 30 * 6,
    tier: "starter",
    db_billing_period: "biannual",
    billing_period: "biannual",
  },
  starter_annual: {
    amount_vnd: 199_000 * 12,
    deep_credits_granted: 30 * 12,
    tier: "starter",
    db_billing_period: "annual",
    billing_period: "annual",
  },
  pack_10: {
    amount_vnd: 130_000,
    deep_credits_granted: 10,
    tier: "starter",
    db_billing_period: "overage_10",
    billing_period: "pack",
  },
  pack_30: {
    amount_vnd: 350_000,
    deep_credits_granted: 30,
    tier: "starter",
    db_billing_period: "overage_30",
    billing_period: "pack",
  },
  pack_50: {
    amount_vnd: 550_000,
    deep_credits_granted: 50,
    tier: "starter",
    db_billing_period: "overage_50",
    billing_period: "pack",
  },
};

function computeExpiresAt(dbBilling: DbBillingPeriod): Date {
  const starts = new Date();
  const expires = new Date(starts);
  if (dbBilling === "monthly" || dbBilling.startsWith("overage_")) {
    expires.setMonth(expires.getMonth() + 1);
  } else if (dbBilling === "biannual") {
    expires.setMonth(expires.getMonth() + 6);
  } else if (dbBilling === "annual") {
    expires.setFullYear(expires.getFullYear() + 1);
  }
  return expires;
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

    const { plan, payment_method } = parsed.data;
    const cfg = PLAN_CONFIG[plan];
    const orderCode = Date.now();
    const starts = new Date();
    const expires = computeExpiresAt(cfg.db_billing_period);

    const siteBase =
      Deno.env.get("SITE_URL") ?? Deno.env.get("PUBLIC_APP_URL") ?? "https://getviews.vn";
    const siteUrl = siteBase.replace(/\/$/, "");

    if (!payosClientId || !payosApiKey) {
      return new Response(
        JSON.stringify({
          error: { code: "SERVER_ERROR", message: "PayOS not configured" },
        }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    const admin = createClient(url, serviceKey);

    const { error: subErr } = await admin.from("subscriptions").insert({
      user_id: user.id,
      tier: cfg.tier,
      billing_period: cfg.db_billing_period,
      amount_vnd: cfg.amount_vnd,
      deep_credits_granted: cfg.deep_credits_granted,
      starts_at: starts.toISOString(),
      expires_at: expires.toISOString(),
      payos_order_code: String(orderCode),
      status: "pending",
    });

    if (subErr) throw subErr;

    const description = `GetViews ${plan} · ${payment_method}`;

    const payosRes = await fetch("https://api-merchant.payos.vn/v2/payment-requests", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-client-id": payosClientId,
        "x-api-key": payosApiKey,
      },
      body: JSON.stringify({
        orderCode,
        amount: cfg.amount_vnd,
        description,
        cancelUrl: `${siteUrl}/app/pricing`,
        returnUrl: `${siteUrl}/app/payment-success`,
      }),
    });

    const payosJson = (await payosRes.json()) as Record<string, unknown>;
    if (!payosRes.ok) {
      console.error("PayOS error", payosJson);
      throw new Error("payos_create_failed");
    }

    const data = payosJson.data as Record<string, unknown> | undefined;
    const checkoutUrl = (data?.checkoutUrl ?? data?.checkout_url) as string | undefined;
    const qrCode = (data?.qrCode ?? data?.qr_code) as string | undefined;

    return new Response(
      JSON.stringify({
        checkoutUrl: checkoutUrl ?? "",
        qrCode: qrCode ?? "",
        orderCode,
        amount_vnd: cfg.amount_vnd,
        deep_credits_granted: cfg.deep_credits_granted,
        billing_period: cfg.billing_period,
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
