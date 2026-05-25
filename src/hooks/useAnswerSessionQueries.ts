/**
 * Phase C.1 — TanStack Query keys + fetchers for `/answer` sessions.
 * staleTime: list 60s, detail 2min. Short enough that a second tab picks
 * up follow-up turns appended from another tab on the next focus refetch,
 * and cheap enough that cache churn doesn't hit the cold-start path — the
 * optimistic injection in AnswerScreen already keeps the active tab warm.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import {
  deleteAnswerSession,
  fetchAnswerSessionDetail,
  fetchAnswerSessions,
  patchAnswerSession,
} from "@/lib/answerApi";
import type { AnswerSessionRow, AnswerTurnRow, ReportV1 } from "@/lib/api-types";

export const answerSessionKeys = {
  all: ["answer-sessions"] as const,
  /** Includes ``scope`` so 30d vs all caches stay separate. */
  list: (userId: string, scope: "30d" | "all" = "30d") =>
    [...answerSessionKeys.all, "list", userId, scope] as const,
  /** Prefix for invalidating every list variant for a user. */
  listsForUser: (userId: string) => [...answerSessionKeys.all, "list", userId] as const,
  detail: (sessionId: string) => [...answerSessionKeys.all, "detail", sessionId] as const,
};

async function getToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

export function useAnswerSessionsList(
  userId: string | undefined,
  enabled: boolean,
  scope: "30d" | "all" = "30d",
  /** Sidebar / drawer may request more rows than the default Answer screen cap. */
  limit = 40,
) {
  return useQuery({
    queryKey: userId
      ? [...answerSessionKeys.list(userId, scope), limit]
      : ["answer-sessions", "list", "none"],
    queryFn: async () => {
      const t = await getToken();
      if (!t) throw new Error("auth");
      return fetchAnswerSessions(t, { limit, scope });
    },
    enabled: Boolean(userId && enabled),
    staleTime: 60_000,
  });
}

export function useAnswerSessionDetail(sessionId: string | null | undefined, userId: string | undefined) {
  return useQuery({
    queryKey: sessionId ? answerSessionKeys.detail(sessionId) : ["answer-session", "detail", "none"],
    queryFn: async () => {
      const t = await getToken();
      if (!t || !sessionId) throw new Error("auth");
      return fetchAnswerSessionDetail(t, sessionId);
    },
    enabled: Boolean(sessionId && userId),
    staleTime: 2 * 60_000,
  });
}

/** Permanently delete an answer session (``DELETE /answer/sessions/:id``). */
export function useDeleteAnswerSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (sessionId: string) => {
      const t = await getToken();
      if (!t) throw new Error("auth");
      await deleteAnswerSession(t, sessionId);
    },
    onSuccess: (_void, sessionId) => {
      qc.removeQueries({ queryKey: answerSessionKeys.detail(sessionId) });
      void qc.invalidateQueries({ queryKey: answerSessionKeys.all });
      void qc.invalidateQueries({ queryKey: ["history_union"] });
      void qc.invalidateQueries({ queryKey: ["search_history_union"] });
    },
  });
}

/**
 * Rename an answer session via the same PATCH endpoint.
 * Trims the title on the client so a whitespace-only rename is a no-op
 * instead of a silent wipe of the title.
 */
export function useRenameAnswerSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ sessionId, title }: { sessionId: string; title: string }) => {
      const t = await getToken();
      if (!t) throw new Error("auth");
      const trimmed = title.trim();
      if (!trimmed) throw new Error("empty_title");
      return patchAnswerSession(t, sessionId, { title: trimmed });
    },
    onSuccess: (_row, { sessionId }) => {
      void qc.invalidateQueries({ queryKey: answerSessionKeys.all });
      void qc.invalidateQueries({ queryKey: answerSessionKeys.detail(sessionId) });
      void qc.invalidateQueries({ queryKey: ["history_union"] });
      void qc.invalidateQueries({ queryKey: ["search_history_union"] });
    },
  });
}

export function lastPayloadFromTurns(
  turns: Array<{ payload: ReportV1 }> | undefined,
): ReportV1 | null {
  const last = turns?.at(-1);
  return last?.payload ?? null;
}

export type AnswerDetailCache = {
  session: AnswerSessionRow & { title: string | null; initial_q: string };
  turns: AnswerTurnRow[];
};

/**
 * Writes a just-streamed turn directly into the detail-query cache so the UI
 * renders immediately, without waiting on a `GET /answer/sessions/:id` refetch
 * that can race Supabase read-replica lag. Dedups by `turn_index` so the real
 * server row replaces this synthesized one naturally when the cache is later
 * refreshed.
 */
export function injectOptimisticTurn(
  current: AnswerDetailCache | undefined,
  fallbackSession: AnswerDetailCache["session"],
  turn: AnswerTurnRow,
): AnswerDetailCache {
  if (!current) return { session: fallbackSession, turns: [turn] };
  const existing = current.turns.findIndex((t) => t.turn_index === turn.turn_index);
  if (existing >= 0) {
    const next = current.turns.slice();
    next[existing] = turn;
    return { ...current, turns: next };
  }
  return { ...current, turns: [...current.turns, turn] };
}

export type { AnswerSessionRow };
