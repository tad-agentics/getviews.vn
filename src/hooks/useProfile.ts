import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { queryKeys } from "@/lib/query-keys";
import { useAuth } from "@/lib/auth";
import type { Database } from "@/lib/database.types";

export type ProfileRow = Database["public"]["Tables"]["profiles"]["Row"];

export function useProfile() {
  const { session } = useAuth();
  const userId = session?.user.id ?? "";
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!userId) return;
    // Use a unique channel name per mount to avoid "cannot add callbacks after subscribe()"
    // when React strict mode or re-mounts create a second instance before cleanup runs.
    const channelName = `realtime:profile:${userId}:${Math.random().toString(36).slice(2)}`;
    const channel = supabase
      .channel(channelName)
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "profiles", filter: `id=eq.${userId}` },
        () => {
          void queryClient.invalidateQueries({ queryKey: queryKeys.profile(userId) });
        },
      )
      .subscribe();
    return () => {
      void supabase.removeChannel(channel);
    };
  }, [userId, queryClient]);

  const query = useQuery({
    queryKey: queryKeys.profile(userId),
    queryFn: async () => {
      const { data, error } = await supabase.from("profiles").select("*").eq("id", userId).maybeSingle();
      if (error) throw error;
      // maybeSingle() returns null when the row doesn't exist yet (e.g. trigger lag after OAuth)
      // returning null here lets callers distinguish "loading" from "row missing" gracefully
      return data as ProfileRow | null;
    },
    enabled: Boolean(userId),
    staleTime: Number.POSITIVE_INFINITY,
    // Poll every 4s when is_processing is stuck true — realtime can miss updates on network blips.
    // Once is_processing clears, refetchInterval returns false and polling stops.
    refetchInterval: (query) => {
      const data = query.state.data as ProfileRow | null | undefined;
      return data?.is_processing ? 4_000 : false;
    },
  });

  return query;
}
