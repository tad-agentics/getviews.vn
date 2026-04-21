import { useMutation } from "@tanstack/react-query";
import type { ScriptGenerateRequest, ScriptGenerateResponse } from "@/lib/api-types";
import { env } from "@/lib/env";
import { fetchWithTimeout } from "@/lib/fetchWithTimeout";
import { supabase } from "@/lib/supabase";

/**
 * POST ``/script/generate`` (Cloud Run, JWT). v1 returns a deterministic scaffold;
 * one credit deducted per successful call.
 */
export function useScriptGenerate() {
  const base = env.VITE_CLOUD_RUN_API_URL;

  return useMutation<ScriptGenerateResponse, Error, ScriptGenerateRequest>({
    mutationFn: async (body) => {
      if (!base) throw new Error("Cloud Run URL chưa cấu hình");
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session?.access_token) throw new Error("Chưa đăng nhập");
      const res = await fetchWithTimeout(`${base}/script/generate`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
        timeoutMs: 45_000,
      });
      if (res.status === 402) {
        const err = new Error("insufficient_credits");
        err.name = "InsufficientCredits";
        throw err;
      }
      if (res.status === 429) {
        const err = new Error("daily_free_limit");
        err.name = "DailyFreeLimit";
        throw err;
      }
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || `HTTP ${res.status}`);
      }
      return (await res.json()) as ScriptGenerateResponse;
    },
  });
}
