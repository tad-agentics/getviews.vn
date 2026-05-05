import { useMutation, useQueryClient } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { fetchWithTimeout } from "@/lib/fetchWithTimeout";
import { supabase } from "@/lib/supabase";

export type RegenerateRitualResponse =
  | { status: "queued"; niche_id: number }
  | { status: "already_in_flight" };

/**
 * POST `/home/regenerate-ritual`. Queues a daily-ritual refresh for the
 * caller's current niche so Settings → niche change can hand the user a
 * fresh Home content bundle without waiting for the nightly morning-ritual
 * cron. Returns immediately (202 + queued); the FE polls
 * ``GET /home/daily-ritual`` to detect completion.
 *
 * Idempotent server-side via an in-flight set keyed by user_id, so spamming
 * the trigger only enqueues one regen.
 */
export function useRegenerateRitual() {
  const queryClient = useQueryClient();
  return useMutation<RegenerateRitualResponse>({
    mutationFn: async () => {
      const base = env.VITE_CLOUD_RUN_API_URL;
      if (!base) throw new Error("cloud_run_url_unset");
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error("no_session");

      const res = await fetchWithTimeout(`${base}/home/regenerate-ritual`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: "{}",
        timeoutMs: 15_000,
      });
      if (!res.ok) throw new Error(`http_${res.status}`);
      return (await res.json()) as RegenerateRitualResponse;
    },
    onSuccess: () => {
      // Invalidate the surfaces a fresh ritual will populate. The actual
      // generation is async (BackgroundTask on Cloud Run, ~30-60s), so the
      // first refetch will likely still see the previous bundle or 404
      // — TanStack will then keep retrying via the staleTime on
      // useDailyRitual + useHomePulse + useTopPatterns.
      void queryClient.invalidateQueries({ queryKey: ["daily_ritual"] });
      void queryClient.invalidateQueries({ queryKey: ["home", "pulse"] });
      void queryClient.invalidateQueries({ queryKey: ["trends"] });
    },
  });
}
