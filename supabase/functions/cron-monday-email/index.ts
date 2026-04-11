import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { corsHeaders } from "../_shared/cors.ts";

type TrendSummary = {
  niche_name: string;
  top_signal: string;
  top_hook_type: string | null;
  card_count: number;
};

function requireService(req: Request): Response | null {
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const auth = req.headers.get("Authorization") ?? "";
  const token = auth.replace(/^Bearer\s+/i, "").trim();
  if (token !== serviceKey) {
    return new Response(JSON.stringify({ error: "Không được phép" }), {
      status: 401,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
  return null;
}

function isoDateDaysAgo(days: number): string {
  const t = new Date();
  const utc = new Date(Date.UTC(t.getFullYear(), t.getMonth(), t.getDate()));
  utc.setUTCDate(utc.getUTCDate() - days);
  return utc.toISOString().slice(0, 10);
}

function signalLabelVi(signal: string): string {
  const m: Record<string, string> = {
    rising: "tăng tốc",
    early: "sớm",
    stable: "ổn định",
    declining: "giảm",
  };
  return m[signal] ?? signal;
}

async function invokeSendDigest(
  functionsUrl: string,
  serviceKey: string,
  to: string,
  subject: string,
  html: string,
): Promise<boolean> {
  const res = await fetch(`${functionsUrl}/functions/v1/send-email`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${serviceKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      template: "monday_digest",
      to,
      subject,
      data: { html },
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    console.error("Gửi email thất bại", res.status, text);
    return false;
  }
  return true;
}

function bestCrossSignal(rows: TrendSummary[]): {
  signal: string;
  nicheCount: number;
  sampleHook: string;
} | null {
  const bySig = new Map<string, Set<string>>();
  for (const r of rows) {
    const s = r.top_signal;
    if (!bySig.has(s)) bySig.set(s, new Set());
    bySig.get(s)!.add(r.niche_name);
  }
  let best: { signal: string; nicheCount: number } | null = null;
  for (const [signal, set] of bySig) {
    const n = set.size;
    if (!best || n > best.nicheCount) best = { signal, nicheCount: n };
  }
  if (!best || best.nicheCount < 3) return null;
  const hookRow = rows
    .filter((r) => r.top_signal === best!.signal)
    .sort((a, b) => b.card_count - a.card_count)[0];
  return {
    signal: best.signal,
    nicheCount: best.nicheCount,
    sampleHook: hookRow?.top_hook_type?.trim() || "xu hướng",
  };
}

async function geminiMetaInsight(
  apiKey: string,
  summaries: TrendSummary[],
  cross: { signal: string; nicheCount: number; sampleHook: string },
): Promise<string | null> {
  const model = Deno.env.get("GEMINI_MONDAY_MODEL") ?? "gemini-3.1-flash-lite-preview";
  const url =
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
  const lines = summaries.map(
    (r) =>
      `- ${r.niche_name}: ${r.top_signal} · ${r.top_hook_type ?? "—"} (${r.card_count} thẻ)`,
  ).join("\n");
  const prompt =
    `Bạn là đồng hành creator TikTok Việt Nam. Dựa trên bảng tóm tắt xu hướng tuần trước, viết 2–3 câu tiếng Việt (giọng nói chuyện, không học thuật) về mẫu chung: tín hiệu "${
      signalLabelVi(cross.signal)
    }" xuất hiện trên ${cross.nicheCount} niche. Nhắc hook "${cross.sampleHook}" nếu hợp lý. Dùng "tuần này" hoặc "tuần vừa rồi". Không dùng số kiểu 1,200 — dùng dấu chấm ngàn kiểu Việt Nam. Chỉ trả về đoạn văn, không gạch đầu dòng, không tiêu đề.\n\nDữ liệu:\n${lines}`;

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contents: [{ role: "user", parts: [{ text: prompt }] }],
      generationConfig: {
        temperature: 0.7,
        maxOutputTokens: 400,
      },
    }),
  });
  const raw = await res.json();
  if (!res.ok) {
    console.error("Gemini lỗi", raw);
    return null;
  }
  const text = raw?.candidates?.[0]?.content?.parts?.[0]?.text;
  return typeof text === "string" && text.trim() ? text.trim() : null;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  const denied = requireService(req);
  if (denied) return denied;

  const functionsUrl = Deno.env.get("SUPABASE_URL")!.replace(/\/$/, "");
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const supabase = createClient(functionsUrl, serviceKey);
  const geminiKey = Deno.env.get("GEMINI_API_KEY");
  const recipientsRaw = (Deno.env.get("MONDAY_DIGEST_RECIPIENTS") ?? "").trim();

  const weekOf = isoDateDaysAgo(7);
  const cacheKey = `monday-digest-sent-${weekOf}`;

  try {
    const { data: cached } = await supabase
      .from("llm_cache")
      .select("input_hash")
      .eq("input_hash", cacheKey)
      .maybeSingle();
    if (cached) {
      return new Response(
        JSON.stringify({ ok: true, skipped: true, reason: "đã gửi tuần này" }),
        { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    const { data: summaries, error: rpcErr } = await supabase.rpc("get_weekly_trend_summaries", {
      p_week_of: weekOf,
    });
    if (rpcErr) throw rpcErr;

    const rows = (summaries ?? []) as TrendSummary[];
    if (rows.length === 0) {
      return new Response(
        JSON.stringify({ ok: true, skipped: true, reason: "không có dữ liệu trending_cards" }),
        { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    if (!recipientsRaw) {
      return new Response(
        JSON.stringify({ ok: true, skipped: true, reason: "chưa cấu hình MONDAY_DIGEST_RECIPIENTS" }),
        { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    const cross = bestCrossSignal(rows);
    let metaInsight: string | null = null;
    if (cross && geminiKey) {
      metaInsight = await geminiMetaInsight(geminiKey, rows, cross);
      if (metaInsight) {
        const { error: upErr } = await supabase
          .from("trending_cards")
          .update({ meta_insight: metaInsight })
          .eq("week_of", weekOf);
        if (upErr) console.error("Cập nhật meta_insight thất bại", upErr);
      }
    }

    const tableRows = rows.map(
      (r) =>
        `<tr><td>${escapeHtml(r.niche_name)}</td><td>${escapeHtml(r.top_signal)}</td><td>${escapeHtml(r.top_hook_type ?? "—")}</td><td>${r.card_count}</td></tr>`,
    ).join("");

    const metaBlock = metaInsight
      ? `<p><strong>Nhìn chung tuần này:</strong> ${escapeHtml(metaInsight)}</p>`
      : "";

    const html = `<h2>GetViews — Xu hướng tuần</h2>
<p>Tóm tắt từ dữ liệu corpus tuần vừa rồi (week_of ${escapeHtml(weekOf)}).</p>
${metaBlock}
<table border="1" cellpadding="6" cellspacing="0"><thead><tr><th>Niche</th><th>Tín hiệu</th><th>Hook</th><th>Số thẻ</th></tr></thead><tbody>${tableRows}</tbody></table>
<p><a href="https://getviews.vn/app">Mở GetViews</a></p>`;

    const hookShort = (cross?.sampleHook ?? rows[0]?.top_hook_type ?? "xu hướng").slice(0, 18);
    const subj = cross && cross.nicheCount >= 3
      ? `Tuần này: ${hookShort} · ${cross.nicheCount} niche`
      : "GetViews — Bản tin xu hướng tuần";
    const subject = subj.length > 42 ? subj.slice(0, 39) + "…" : subj;

    const emails = recipientsRaw.split(",").map((s) => s.trim()).filter(Boolean);
    let sent = 0;
    for (const to of emails) {
      const ok = await invokeSendDigest(functionsUrl, serviceKey, to, subject, html);
      if (ok) sent += 1;
    }

    if (sent > 0) {
      await supabase.from("llm_cache").insert({
        input_hash: cacheKey,
        response: { sent, week_of: weekOf },
      });
    }

    return new Response(
      JSON.stringify({ ok: true, week_of: weekOf, sent, meta: !!metaInsight }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  } catch (e) {
    console.error(e);
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
