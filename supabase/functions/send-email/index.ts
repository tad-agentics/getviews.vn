import { corsHeaders } from "../_shared/cors.ts";

type ReceiptPayload = {
  display_name: string;
  tier: string;
  credits_granted: number;
  expires_at: string;
  amount_vnd: number;
};

type ExpiryPayload = {
  display_name: string;
  tier: string;
  expires_at: string;
  renewal_url: string;
};

type Body = {
  template: "receipt" | "expiry_reminder_7d" | "expiry_reminder_3d" | "expiry_reminder_1d";
  to: string;
  data: ReceiptPayload | ExpiryPayload;
};

function requireServiceRole(req: Request): Response | null {
  const url = Deno.env.get("SUPABASE_URL")!;
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

function renderReceipt(data: ReceiptPayload): { subject: string; html: string } {
  const subject = `Thanh toán thành công — GetViews ${data.tier}`;
  const html = `<p>Xin chào ${data.display_name},</p>
<p>Gói <strong>${data.tier}</strong> đã được kích hoạt. Bạn nhận <strong>${data.credits_granted}</strong> deep credits.</p>
<p>Hết hạn: ${data.expires_at}</p>
<p>Số tiền: ${data.amount_vnd.toLocaleString("vi-VN")} VND</p>`;
  return { subject, html };
}

function renderExpiry(
  window: "7d" | "3d" | "1d",
  data: ExpiryPayload,
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
    const body = (await req.json()) as Body;
    const apiKey = Deno.env.get("RESEND_API_KEY");
    if (!apiKey) {
      throw new Error("RESEND_API_KEY not configured");
    }

    let subject: string;
    let html: string;

    switch (body.template) {
      case "receipt": {
        const r = renderReceipt(body.data as ReceiptPayload);
        subject = r.subject;
        html = r.html;
        break;
      }
      case "expiry_reminder_7d": {
        const r = renderExpiry("7d", body.data as ExpiryPayload);
        subject = r.subject;
        html = r.html;
        break;
      }
      case "expiry_reminder_3d": {
        const r = renderExpiry("3d", body.data as ExpiryPayload);
        subject = r.subject;
        html = r.html;
        break;
      }
      case "expiry_reminder_1d": {
        const r = renderExpiry("1d", body.data as ExpiryPayload);
        subject = r.subject;
        html = r.html;
        break;
      }
      default:
        return new Response(JSON.stringify({ error: { code: "VALIDATION_ERROR", message: "Unknown template" } }), {
          status: 422,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
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

    return new Response(JSON.stringify({ message_id: json.id ?? "sent" }), {
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
