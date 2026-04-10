import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { chatKeys } from "./useChatSession";

export function useChatSessions() {
  return useQuery({
    queryKey: chatKeys.sessions(),
    queryFn: async () => {
      const { data, error } = await supabase
        .from("chat_sessions")
        .select("id, title, first_message, created_at, niche_id, niche_taxonomy(name)")
        .is("deleted_at", null)
        .order("created_at", { ascending: false })
        .limit(50);
      if (error) throw error;
      return data;
    },
    staleTime: 30_000,
  });
}

export function useDeleteSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (sessionId: string) => {
      const { error } = await supabase
        .from("chat_sessions")
        .update({ deleted_at: new Date().toISOString() })
        .eq("id", sessionId);
      if (error) throw error;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: chatKeys.sessions() });
    },
  });
}
