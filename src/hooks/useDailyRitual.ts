import { useQuery } from "@tanstack/react-query";
import { fetchDailyRitual } from "shared/api/ritual";
import type { DailyRitual, RitualEmptyReason } from "shared/types/ritual";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

export type { DailyRitual, RitualEmptyReason, RitualScript } from "shared/types/ritual";

type RitualQueryPayload = {
  data: DailyRitual | null;
  emptyReason: RitualEmptyReason | null;
};

export const ritualKeys = {
  /** Include ``primaryNicheId`` so changing ngách in Cài đặt invalidates cache. */
  today: (primaryNicheId: number | null) => ["daily_ritual", "today", primaryNicheId] as const,
};

/**
 * Today's 3 pre-generated scripts for the creator.
 *
 * Returns paired `data` + `emptyReason` so the UI can branch copy (no row vs niche-stale).
 * When `emptyReason` is null and `data` is null, the fetch was skipped (no Cloud Run URL / no session).
 */
export function useDailyRitual(enabled: boolean = true, primaryNicheId: number | null = null) {
  const query = useQuery<RitualQueryPayload>({
    queryKey: ritualKeys.today(primaryNicheId),
    queryFn: async ({ queryKey }): Promise<RitualQueryPayload> => {
      const expectedNicheId = queryKey[2];
      if (typeof expectedNicheId !== "number") {
        return { data: null, emptyReason: null };
      }

      const cloudRunUrl = env.VITE_CLOUD_RUN_API_URL;
      if (!cloudRunUrl) {
        return { data: null, emptyReason: null };
      }

      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        return { data: null, emptyReason: null };
      }

      const result = await fetchDailyRitual({
        baseUrl: cloudRunUrl,
        accessToken: session.access_token,
        expectedNicheId,
      });
      return { data: result.data, emptyReason: result.emptyReason };
    },
    enabled: enabled && primaryNicheId != null,
    staleTime: 10 * 60 * 1000, // 10 min; rituals regenerate nightly
    retry: false,
  });

  return {
    data: query.data?.data ?? null,
    emptyReason: query.data?.emptyReason ?? null,
    isPending: query.isPending,
    isFetching: query.isFetching,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
