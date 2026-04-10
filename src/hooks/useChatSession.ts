import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export const chatKeys = {
  sessions: () => ["chat_sessions"] as const,
  session: (id: string) => ["chat_sessions", id] as const,
  messages: (sessionId: string) => ["chat_messages", sessionId] as const,
};

export function useChatSession(sessionId: string | null) {
  return useQuery({
    queryKey: chatKeys.session(sessionId ?? ""),
    queryFn: async () => {
      const { data, error } = await supabase
        .from("chat_sessions")
        .select("*, chat_messages(*)")
        .eq("id", sessionId!)
        .order("created_at", { foreignTable: "chat_messages", ascending: true })
        .single();
      if (error) throw error;
      return data;
    },
    enabled: !!sessionId,
    staleTime: 30_000,
  });
}

export function useCreateSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ userId, nicheId }: { userId: string; nicheId: number | null }) => {
      const { data, error } = await supabase
        .from("chat_sessions")
        .insert({
          user_id: userId,
          niche_id: nicheId,
          first_message: "",
        })
        .select()
        .single();
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: chatKeys.sessions() });
    },
  });
}

export function useInsertUserMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      sessionId,
      userId,
      content,
      intentType,
      isFree,
    }: {
      sessionId: string;
      userId: string;
      content: string;
      intentType: string | null;
      isFree: boolean;
    }) => {
      const { data, error } = await supabase
        .from("chat_messages")
        .insert({
          session_id: sessionId,
          user_id: userId,
          role: "user",
          content,
          intent_type: intentType,
          credits_used: 0,
          is_free: isFree,
        })
        .select()
        .single();
      if (error) throw error;
      return data;
    },
    onSuccess: (_, vars) => {
      void qc.invalidateQueries({ queryKey: chatKeys.messages(vars.sessionId) });
      void qc.invalidateQueries({ queryKey: chatKeys.sessions() });
    },
  });
}
