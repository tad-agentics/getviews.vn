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

  const geminiRes = await fetch(geminiUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      system_instruction: { parts: [{ text: systemPrompt }] },
      contents: [{ role: "user", parts: [{ text: query }] }],
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
  const base = `Bạn là GetViews AI, trợ lý phân tích TikTok cho creator Việt Nam.
Trả lời bằng tiếng Việt, ngắn gọn, đi thẳng vào vấn đề.
Không dùng markdown heading. Dùng bullet points khi liệt kê.`;

  switch (intentType) {
    case "format_lifecycle":
      return `${base}\nPhân tích vòng đời format video: đang ở giai đoạn nào, nên làm gì.`;
    case "follow_up":
      return `${base}\nTrả lời câu hỏi tiếp theo dựa trên ngữ cảnh cuộc hội thoại.`;
    default:
      return base;
  }
}
