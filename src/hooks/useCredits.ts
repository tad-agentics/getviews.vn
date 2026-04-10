import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { queryKeys } from "@/lib/query-keys";
import { supabase } from "@/lib/supabase";

/**
 * Shared credit balance for paywall / header — deduped via React Query.
 */
export function useCredits() {
  const { user } = useAuth();

  return useQuery({
    queryKey: queryKeys.credits(user?.id ?? ""),
    queryFn: async () => {
      const { data, error } = await supabase
        .from("profiles")
        .select("deep_credits_remaining")
        .eq("id", user!.id)
        .single();
      if (error) throw error;
      return data.deep_credits_remaining as number;
    },
    enabled: !!user,
    staleTime: 30 * 1000,
  });
}
