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
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) throw new Error("Not authenticated");
      const { data, error } = await supabase
        .from("chat_sessions")
        .update({ deleted_at: new Date().toISOString() })
        .eq("id", sessionId)
        .eq("user_id", user.id)
        .select("id");
      if (error) throw error;
      // If 0 rows updated, the session didn't exist or RLS blocked it
      if (!data || data.length === 0) throw new Error("Delete failed: session not found or access denied");
    },
    onMutate: async (sessionId: string) => {
      // Cancel any in-flight refetches so they don't overwrite the optimistic update
      await qc.cancelQueries({ queryKey: chatKeys.sessions() });
      // Snapshot the previous value for rollback
      const previous = qc.getQueryData(chatKeys.sessions());
      // Optimistically remove from cache immediately
      qc.setQueryData(chatKeys.sessions(), (old: unknown[] | undefined) =>
        old ? old.filter((s: { id: string }) => s.id !== sessionId) : [],
      );
      return { previous };
    },
    onError: (_err, _sessionId, context) => {
      // Rollback to previous cache state on failure
      if (context?.previous !== undefined) {
        qc.setQueryData(chatKeys.sessions(), context.previous);
      }
    },
    onSettled: () => {
      // Always sync with server after mutation completes or fails
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
