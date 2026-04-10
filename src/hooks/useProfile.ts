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
    const channel = supabase
      .channel(`profile:${userId}`)
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

  return useQuery({
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
  });
}
