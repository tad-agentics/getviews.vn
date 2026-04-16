// Vercel Edge — text intents ⑤⑥⑦ + follow-ups (Gemini 3.x only)
export const config = { runtime: "edge" };

import { createClient } from "@supabase/supabase-js";

// Vercel Edge Runtime receives all env vars (including VITE_-prefixed ones).
// VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY are the canonical names
// in this project (set in .env.local and Vercel project settings).
// SUPABASE_URL / SUPABASE_ANON_KEY are accepted as aliases for CI/CD environments
// that prefer non-VITE_ names.
const SUPABASE_URL =
  process.env.SUPABASE_URL ?? process.env.VITE_SUPABASE_URL ?? "";
const SUPABASE_ANON_KEY =
  process.env.SUPABASE_ANON_KEY ??
  process.env.VITE_SUPABASE_PUBLISHABLE_KEY ??
  "";
const GEMINI_API_KEY = process.env.GEMINI_API_KEY!;
const GEMINI_MODEL =
  process.env.GEMINI_SYNTHESIS_MODEL ?? "gemini-3.1-flash-lite-preview";

const FREE_INTENTS = new Set([
  "format_lifecycle",
  "follow_up",
]);

// §13: max 100 free queries per user per day — matches Cloud Run FREE_DAILY_LIMIT
const FREE_DAILY_LIMIT = 100;

function userSupabase(accessToken: string) {
  return createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: { persistSession: false, autoRefreshToken: false },
    global: { headers: { Authorization: `Bearer ${accessToken}` } },
  });
}

export default async function handler(req: Request): Promise<Response> {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Authorization, Content-Type",
      },
    });
  }

  if (req.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405 });
  }

  const authHeader = req.headers.get("Authorization");
  if (!authHeader?.startsWith("Bearer ")) {
    return new Response("Unauthorized", { status: 401 });
  }
  const token = authHeader.slice(7);

  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    return new Response("Server misconfigured", { status: 500 });
  }

  const supabase = userSupabase(token);
  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser(token);
  if (authError || !user) {
    return new Response("Unauthorized", { status: 401 });
  }

  let body: {
    session_id: string;
    query: string;
    intent_type: string;
    stream_id?: string;
    last_seq?: number;
  };
  try {
    body = (await req.json()) as typeof body;
  } catch {
    return new Response("Bad Request", { status: 400 });
  }

  const { session_id, query, intent_type, stream_id, last_seq } = body;
  if (!session_id || !query || !intent_type) {
    return new Response("Bad Request: missing session_id, query, or intent_type", {
      status: 400,
    });
  }

  const isFree = FREE_INTENTS.has(intent_type);

  if (isFree) {
    // Enforce daily free query limit (§13) — matches Cloud Run FREE_DAILY_LIMIT
    const { data: gateResult, error: gateError } = await supabase.rpc(
      "increment_free_query_count",
      { p_user_id: user.id },
    );
    if (!gateError && gateResult) {
      const newCount = (gateResult as { new_count?: number }).new_count ?? 0;
      if (newCount > FREE_DAILY_LIMIT) {
        return new Response(
          JSON.stringify({ error: "daily_limit_exceeded" }),
          { status: 429, headers: { "Content-Type": "application/json" } },
        );
      }
    }
  } else {
    await supabase.from("profiles").update({ is_processing: true }).eq("id", user.id);

    const { data: balanceAfter, error: rpcError } = await supabase.rpc("decrement_credit", {
      p_user_id: user.id,
    });

    if (rpcError || balanceAfter == null) {
      await supabase.from("profiles").update({ is_processing: false }).eq("id", user.id);
      return new Response(JSON.stringify({ error: "insufficient_credits" }), {
        status: 402,
        headers: { "Content-Type": "application/json" },
      });
    }
  }

  const systemPrompt = buildSystemPrompt(intent_type);
  const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:streamGenerateContent?alt=sse&key=${GEMINI_API_KEY}`;

  // For conversational intents, fetch recent message history so Gemini has
  // context for pronouns like "video đó", "format này", "kênh đó", etc.
  // Cap at 12 turns to stay within Edge CPU/memory budget.
  let contents: Array<{ role: string; parts: Array<{ text: string }> }> = [
    { role: "user", parts: [{ text: query }] },
  ];
  if (intent_type === "follow_up" || intent_type === "format_lifecycle") {
    const { data: history } = await supabase
      .from("chat_messages")
      .select("role, content")
      .eq("session_id", session_id)
      .order("created_at", { ascending: true })
      .limit(12);
    if (history && history.length > 0) {
      const historyContents = history
        .filter((m) => m.content && (m.role === "user" || m.role === "assistant"))
        .map((m) => ({
          role: m.role === "assistant" ? "model" : "user",
          parts: [{ text: (m.content as string).slice(0, 2000) }],
        }));
      contents = [...historyContents, { role: "user", parts: [{ text: query }] }];
    }
  }

  const geminiRes = await fetch(geminiUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      system_instruction: { parts: [{ text: systemPrompt }] },
      contents,
      generationConfig: { temperature: 0.7, maxOutputTokens: 2048 },
    }),
  });

  if (!geminiRes.ok) {
    if (!isFree) await supabase.from("profiles").update({ is_processing: false }).eq("id", user.id);
    return new Response("Upstream error", { status: 502 });
  }

  const newStreamId = stream_id ?? crypto.randomUUID();
  let seq = last_seq ?? 0;
  let fullText = "";

  const stream = new ReadableStream({
    async start(controller) {
      const reader = geminiRes.body!.getReader();
      const decoder = new TextDecoder();

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const data = line.slice(6);
            if (data === "[DONE]") continue;

            try {
              const parsed = JSON.parse(data) as {
                candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>;
              };
              const delta = parsed.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
              if (!delta) continue;

              fullText += delta;
              seq += 1;

              const token = JSON.stringify({
                stream_id: newStreamId,
                seq,
                delta,
                done: false,
              });
              controller.enqueue(new TextEncoder().encode(`data: ${token}\n\n`));
            } catch {
              /* skip malformed chunks */
            }
          }
        }

        const doneToken = JSON.stringify({
          stream_id: newStreamId,
          seq,
          delta: "",
          done: true,
        });
        controller.enqueue(new TextEncoder().encode(`data: ${doneToken}\n\n`));

        await supabase.from("chat_messages").insert({
          session_id,
          user_id: user.id,
          role: "assistant",
          content: fullText,
          intent_type,
          credits_used: isFree ? 0 : 1,
          is_free: isFree,
          stream_id: newStreamId,
        });

        if (!isFree) {
          await supabase.from("profiles").update({ is_processing: false }).eq("id", user.id);
        }
      } catch {
        if (!isFree) await supabase.from("profiles").update({ is_processing: false }).eq("id", user.id);
        const errToken = JSON.stringify({
          stream_id: newStreamId,
          seq,
          delta: "",
          done: true,
          error: "stream_failed",
        });
        controller.enqueue(new TextEncoder().encode(`data: ${errToken}\n\n`));
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

function buildSystemPrompt(intentType: string): string {
  const style = `Ngôn ngữ: tiếng Việt, thân thiện nhưng súc tích.
Định dạng: không dùng markdown heading (#). Dùng bullet (–) khi liệt kê nhiều điểm.
Độ dài: tối đa 4–5 bullet hoặc 2–3 đoạn ngắn. Không dài dòng.
Khi không chắc: nói thẳng, không bịa số liệu.`;

  switch (intentType) {
    case "follow_up":
      return `Bạn là GetViews AI — trợ lý phân tích TikTok thông minh dành cho creator Việt Nam.

KIẾN THỨC:
– Thuật toán TikTok: FYP, completion rate, rewatch, engagement signals, watch time
– Chiến lược nội dung: hook 3 giây đầu, CTR thumbnail, cấu trúc video, storytelling
– Xu hướng & niche: cách đọc tín hiệu trend sớm, chọn niche, content pillars
– Kỹ thuật sản xuất: caption, hashtag, thời điểm đăng, A/B test thumbnail
– Thị trường Việt Nam: hành vi người dùng TikTok VN, niche phổ biến, creator economy

CÁC TÍNH NĂNG CỦA GETVIEWS (chủ động gợi ý khi phù hợp):
– Phân tích video cụ thể → "Dán link TikTok vào đây để tôi soi chi tiết tại sao video đó lên hoặc không lên"
– Soi kênh đối thủ → "Gửi @handle hoặc link profile TikTok để tôi phân tích toàn bộ kênh"
– Xu hướng đang nổi → "Hỏi 'xu hướng tuần này trong niche X' để xem data thực tế"
– Tìm creator/KOL → "Hỏi 'tìm creator trong niche X' để tôi gợi ý danh sách"
– Lên kịch bản quay → "Hỏi 'lên kịch bản cho video về X' để tôi tạo shot list chi tiết"

HƯỚNG DẪN:
${style}
Dựa vào lịch sử hội thoại để trả lời đúng ngữ cảnh. Nếu câu hỏi cần data thực tế (số liệu view, trend corpus), gợi ý dùng tính năng phân tích chuyên sâu thay vì bịa số.`;

    case "format_lifecycle":
      return `Bạn là GetViews AI, trợ lý phân tích TikTok cho creator Việt Nam.
Phân tích vòng đời format video: xác định đang ở giai đoạn nào (mới nổi / đỉnh / bão hòa / tàn) và đưa ra lời khuyên thực tế.
${style}`;

    default:
      return `Bạn là GetViews AI, trợ lý phân tích TikTok cho creator Việt Nam.
${style}`;
  }
}
