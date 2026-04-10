import { z } from "https://esm.sh/zod@3.24.2";
import { corsHeaders } from "../_shared/cors.ts";

const ReceiptDataSchema = z.object({
  count: z.number().int().nonnegative(),
  display_name: z.string().optional(),
  tier: z.string().optional(),
  expires_at: z.string().optional(),
  amount_vnd: z.number().optional(),
});

const ExpiryDataSchema = z.object({
  display_name: z.string(),
  tier: z.string(),
  expires_at: z.string(),
  renewal_url: z.string(),
});

const BodySchema = z.discriminatedUnion("template", [
  z.object({
    to: z.string().email(),
    subject: z.string().min(1).optional(),
    template: z.literal("receipt"),
    data: ReceiptDataSchema,
  }),
  z.object({
    to: z.string().email(),
    subject: z.string().min(1).optional(),
    template: z.literal("expiry_reminder_7d"),
    data: ExpiryDataSchema,
  }),
  z.object({
    to: z.string().email(),
    subject: z.string().min(1).optional(),
    template: z.literal("expiry_reminder_3d"),
    data: ExpiryDataSchema,
  }),
  z.object({
    to: z.string().email(),
    subject: z.string().min(1).optional(),
    template: z.literal("expiry_reminder_1d"),
    data: ExpiryDataSchema,
  }),
]);

function requireServiceRole(req: Request): Response | null {
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const auth = req.headers.get("Authorization") ?? "";
  const token = auth.replace(/^Bearer\s+/i, "").trim();
  if (token !== serviceKey) {
    return new Response(JSON.stringify({ error: { code: "UNAUTHORIZED", message: "Invalid service token" } }), {
      status: 401,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
  return null;
}

function renderReceipt(data: z.infer<typeof ReceiptDataSchema>): { subject: string; html: string } {
  const subject = "Thanh toán thành công — GetViews";
  const lines: string[] = [];
  if (data.display_name) {
    lines.push(`<p>Xin chào ${data.display_name},</p>`);
  }
  lines.push(
    `<p>Thanh toán thành công — bạn đã nhận được <strong>${data.count}</strong> deep credits. Hẹn gặp lại trên GetViews!</p>`,
  );
  if (data.tier) {
    lines.push(`<p>Gói: <strong>${data.tier}</strong></p>`);
  }
  if (data.expires_at) {
    lines.push(`<p>Hết hạn: ${data.expires_at}</p>`);
  }
  if (data.amount_vnd != null) {
    lines.push(`<p>Số tiền: ${data.amount_vnd.toLocaleString("vi-VN")} VND</p>`);
  }
  return { subject, html: lines.join("\n") };
}

function renderExpiry(
  window: "7d" | "3d" | "1d",
  data: z.infer<typeof ExpiryDataSchema>,
): { subject: string; html: string } {
  const map = {
    "7d": "Gói GetViews của bạn hết hạn trong 7 ngày",
    "3d": "Gói GetViews của bạn hết hạn trong 3 ngày",
    "1d": "Gói GetViews của bạn hết hạn ngày mai",
  } as const;
  const subject = map[window];
  const html = `<p>Xin chào ${data.display_name},</p>
<p>Gói <strong>${data.tier}</strong> sẽ hết hạn vào <strong>${data.expires_at}</strong>.</p>
<p><a href="${data.renewal_url}">Gia hạn ngay</a></p>`;
  return { subject, html };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const denied = requireServiceRole(req);
  if (denied) return denied;

  try {
    const raw = await req.json();
    const parsed = BodySchema.safeParse(raw);
    if (!parsed.success) {
      return new Response(JSON.stringify({ error: { code: "VALIDATION_ERROR", message: parsed.error.message } }), {
        status: 422,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const body = parsed.data;
    const apiKey = Deno.env.get("RESEND_API_KEY");
    if (!apiKey) {
      throw new Error("RESEND_API_KEY not configured");
    }

    let subject: string;
    let html: string;

    switch (body.template) {
      case "receipt": {
        const r = renderReceipt(body.data);
        subject = body.subject ?? r.subject;
        html = r.html;
        break;
      }
      case "expiry_reminder_7d": {
        const r = renderExpiry("7d", body.data);
        subject = body.subject ?? r.subject;
        html = r.html;
        break;
      }
      case "expiry_reminder_3d": {
        const r = renderExpiry("3d", body.data);
        subject = body.subject ?? r.subject;
        html = r.html;
        break;
      }
      case "expiry_reminder_1d": {
        const r = renderExpiry("1d", body.data);
        subject = body.subject ?? r.subject;
        html = r.html;
        break;
      }
    }

    const fromAddr = Deno.env.get("RESEND_FROM") ?? "GetViews <noreply@getviews.vn>";

    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: fromAddr,
        to: [body.to],
        subject,
        html,
      }),
    });

    const json = await res.json();
    if (!res.ok) {
      console.error("Resend error", json);
      throw new Error("resend_failed");
    }

    return new Response(JSON.stringify({ message_id: (json as { id?: string }).id ?? "sent" }), {
      status: 200,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "send_email_failed";
    return new Response(JSON.stringify({ error: { code: "SERVER_ERROR", message: msg } }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
