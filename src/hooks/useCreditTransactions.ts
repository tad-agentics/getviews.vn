import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { queryKeys } from "@/lib/query-keys";
import { useAuth } from "@/lib/auth";

export function useCreditTransactions(limit = 20) {
  const { session } = useAuth();
  const userId = session?.user.id ?? "";

  return useQuery({
    queryKey: queryKeys.creditTransactions(userId, limit),
    queryFn: async () => {
      const { data, error } = await supabase
        .from("credit_transactions")
        .select("*")
        .eq("user_id", userId)
        .order("created_at", { ascending: false })
        .limit(limit);
      if (error) throw error;
      return data ?? [];
    },
    enabled: Boolean(userId),
    staleTime: 30_000,
  });
}
