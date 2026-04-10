import { z } from "https://esm.sh/zod@3.24.2";
import { corsHeaders } from "../_shared/cors.ts";

const ReceiptDataSchema = z.object({
  count: z.number().int().nonnegative(),
  display_name: z.string().optional(),
  tier: z.string().optional(),
  expires_at: z.string().optional(),
  amount_vnd: z.number().optional(),
});

const ExpiryReminderDataSchema = z.object({
  name: z.string(),
  expiry_date: z.string(),
  site_url: z.string().min(1),
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
    data: ExpiryReminderDataSchema,
  }),
  z.object({
    to: z.string().email(),
    subject: z.string().min(1).optional(),
    template: z.literal("expiry_reminder_3d"),
    data: ExpiryReminderDataSchema,
  }),
  z.object({
    to: z.string().email(),
    subject: z.string().min(1).optional(),
    template: z.literal("expiry_reminder_1d"),
    data: ExpiryReminderDataSchema,
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

function ctaPricingHref(siteUrl: string): string {
  return `${siteUrl.replace(/\/$/, "")}/app/pricing`;
}

function renderExpiryReminder(
  window: "7d" | "3d" | "1d",
  data: z.infer<typeof ExpiryReminderDataSchema>,
): { subject: string; html: string } {
  const subjects = {
    "7d": "Gói GetViews của bạn hết hạn trong 7 ngày",
    "3d": "Gói GetViews của bạn hết hạn trong 3 ngày",
    "1d": "Gói GetViews của bạn hết hạn ngày mai",
  } as const;
  const subject = subjects[window];
  const href = ctaPricingHref(data.site_url);

  const bodyByWindow = {
    "7d": `<p>Xin chào ${data.name}, gói Starter của bạn sẽ hết hạn vào ${data.expiry_date}. Gia hạn ngay để không bị gián đoạn phân tích content.</p>`,
    "3d": `<p>Xin chào ${data.name}, chỉ còn 3 ngày — gói Starter hết hạn vào ${data.expiry_date}. Đừng để mất đà phân tích.</p>`,
    "1d": `<p>Xin chào ${data.name}, gói Starter của bạn hết hạn vào ngày mai (${data.expiry_date}). Gia hạn ngay để tiếp tục phân tích.</p>`,
  } as const;

  const html = `<h2>GetViews</h2>
${bodyByWindow[window]}
<p><a href="${href}">Gia hạn ngay</a></p>`;

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
        const r = renderExpiryReminder("7d", body.data);
        subject = body.subject ?? r.subject;
        html = r.html;
        break;
      }
      case "expiry_reminder_3d": {
        const r = renderExpiryReminder("3d", body.data);
        subject = body.subject ?? r.subject;
        html = r.html;
        break;
      }
      case "expiry_reminder_1d": {
        const r = renderExpiryReminder("1d", body.data);
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
