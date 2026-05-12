import { useMutation } from "@tanstack/react-query";
import type { ScriptGenerateRequest, ScriptGenerateResponse } from "@/lib/api-types";
import { cloudRunAuthedFetch, throwCloudRunError } from "@/lib/cloudRunClient";
import { env } from "@/lib/env";

/**
 * POST ``/script/generate`` (Cloud Run, JWT). v1 returns a deterministic scaffold;
 * one credit deducted per successful call.
 */
export function useScriptGenerate() {
  const base = env.VITE_CLOUD_RUN_API_URL;

  return useMutation<ScriptGenerateResponse, Error, ScriptGenerateRequest>({
    mutationFn: async (body) => {
      if (!base) throw new Error("Cloud Run URL chưa cấu hình");
      const res = await cloudRunAuthedFetch("/script/generate", {
        method: "POST",
        body: JSON.stringify(body),
        timeoutMs: 45_000,
      });
      if (res.status === 402) {
        await throwCloudRunError(res, {
          402: { message: "insufficient_credits", name: "InsufficientCredits" },
        });
      }
      if (res.status === 429) {
        await throwCloudRunError(res, {
          429: { message: "daily_free_limit", name: "DailyFreeLimit" },
        });
      }
      if (!res.ok) {
        await throwCloudRunError(res);
      }
      return (await res.json()) as ScriptGenerateResponse;
    },
  });
}
