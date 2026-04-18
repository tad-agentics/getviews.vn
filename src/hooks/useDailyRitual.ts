import { useQuery } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

export type RitualScript = {
  hook_type_en: string;
  hook_type_vi: string;
  title_vi: string;
  why_works: string;
  retention_est_pct: number;
  shot_count: number;
  length_sec: number;
};

export type DailyRitual = {
  generated_for_date: string;
  niche_id: number;
  adequacy:
    | "none"
    | "reference_pool"
    | "basic_citation"
    | "niche_norms"
    | "hook_effectiveness"
    | "trend_delta";
  scripts: RitualScript[];
  generated_at: string;
};

export const ritualKeys = {
  today: () => ["daily_ritual", "today"] as const,
};

/**
 * Today's 3 pre-generated scripts for the creator.
 *
 * Phase A · A2 — rendered as a banner on the current ChatScreen empty state
 * so we can validate the feature before investing in the Home shell (A3).
 *
 * Returns `null` (not an error) when no ritual exists yet — the nightly
 * cron runs at 07:00 ICT and new creators won't have a row on day one.
 * The UI should render a "sắp có" state for both null and error cases.
 */
export function useDailyRitual(enabled: boolean = true) {
  return useQuery<DailyRitual | null>({
    queryKey: ritualKeys.today(),
    queryFn: async () => {
      const cloudRunUrl = env.VITE_CLOUD_RUN_API_URL;
      if (!cloudRunUrl) return null; // local dev without cloud-run = no ritual

      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) return null;

      const res = await fetch(`${cloudRunUrl}/home/daily-ritual`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.status === 404) return null; // no ritual yet today
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return (await res.json()) as DailyRitual;
    },
    enabled,
    staleTime: 10 * 60 * 1000, // 10 min; rituals regenerate nightly
    retry: false,
  });
}
