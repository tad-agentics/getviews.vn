import { useQuery } from "@tanstack/react-query";
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
    retry: false,
  });
}

