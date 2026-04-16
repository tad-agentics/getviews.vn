import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { chatKeys } from "./useChatSession";

export function useChatSessions() {
  return useQuery({
    queryKey: chatKeys.sessions(),
    queryFn: async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return [];
      const { data, error } = await supabase
        .from("chat_sessions")
        .select(
          "id, title, first_message, created_at, niche_id, intent_type, credits_used, niche_taxonomy(name_vn)",
        )
        .eq("user_id", user.id)
        .is("deleted_at", null)
        .order("created_at", { ascending: false })
        .limit(50);
      if (error) throw error;
      return data;
    },
    staleTime: 0,
  });
}

export function useDeleteSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (sessionId: string) => {
      const { error } = await supabase
        .from("chat_sessions")
        .delete()
        .eq("id", sessionId);
      if (error) {
        console.error("[useDeleteSession] Supabase DELETE error:", error.message, error.code, error.details);
        throw error;
      }
    },
    onMutate: async (sessionId: string) => {
      await qc.cancelQueries({ queryKey: chatKeys.sessions() });
      const previous = qc.getQueryData(chatKeys.sessions());
      qc.setQueryData(chatKeys.sessions(), (old: unknown[] | undefined) =>
        old ? old.filter((s: { id: string }) => s.id !== sessionId) : [],
      );
      return { previous };
    },
    onError: (err, _sessionId, context) => {
      const e = err as { message?: string; code?: string };
      console.error("[useDeleteSession] onError — rolling back:", e?.message ?? err, e?.code ?? "");
      if (context?.previous !== undefined) {
        qc.setQueryData(chatKeys.sessions(), context.previous);
      }
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: chatKeys.sessions() });
    },
  });
}

export function useUpdateSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ sessionId, title }: { sessionId: string; title: string }) => {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) throw new Error("Not authenticated");
      const { error } = await supabase
        .from("chat_sessions")
        .update({ title: title.trim() })
        .eq("id", sessionId)
        .eq("user_id", user.id);
      if (error) throw error;
    },
    onSuccess: (_, vars) => {
      void qc.invalidateQueries({ queryKey: chatKeys.sessions() });
      void qc.invalidateQueries({ queryKey: chatKeys.session(vars.sessionId) });
    },
  });
}

export function useSearchSessions(query: string) {
  return useQuery({
    queryKey: [...chatKeys.sessions(), "search", query] as const,
    queryFn: async () => {
      const q = query.trim();
      if (!q) return [];
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) return [];
      const { data, error } = await supabase.rpc("search_sessions", {
        search_query: q,
        p_user_id: user.id,
      });
      if (error) throw error;
      return data ?? [];
    },
    enabled: query.trim().length > 0,
    staleTime: 10_000,
  });
}
