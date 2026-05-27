/**
 * Shared helpers for answer-turn SSE success + TD-4 resume args.
 */
import type { QueryClient } from "@tanstack/react-query";

import {
  answerSessionKeys,
  injectOptimisticTurn,
  type AnswerDetailCache,
} from "@/hooks/useAnswerSessionQueries";
import type { StreamArgs } from "@/hooks/useSessionStream";
import type { AnswerTurnRow } from "@/lib/api-types";
import type { ParsedAnswerHandoff } from "@/lib/answerHandoff";
import type { PendingAnswerStream } from "@/lib/sseResume";

export function applyOptimisticAnswerTurn(
  queryClient: QueryClient,
  sessionId: string,
  fallbackSession: AnswerDetailCache["session"],
  turn: AnswerTurnRow,
): void {
  queryClient.setQueryData<AnswerDetailCache>(
    answerSessionKeys.detail(sessionId),
    (prev) => injectOptimisticTurn(prev, fallbackSession, turn),
  );
}

/** Resume stream args, or null when no replay handles (caller must not stream). */
export function buildResumeAnswerStreamArgs(input: {
  sessionId: string;
  query: string;
  pending: PendingAnswerStream | null;
  sessionFormat?: string | null;
  handoff: ParsedAnswerHandoff;
  hookStreamId: string | null;
  hookLastSeq: number;
}): StreamArgs | null {
  const {
    sessionId,
    query,
    pending,
    sessionFormat,
    handoff,
    hookStreamId,
    hookLastSeq,
  } = input;
  const turnKind = pending?.turnKind ?? "primary";
  const fmt = pending?.sessionFormat ?? sessionFormat ?? null;
  const depth = pending?.analysisDepth ?? handoff.depth;
  const videoMode = pending?.videoMode ?? handoff.mode ?? undefined;
  const base: StreamArgs = {
    mode: "answer_turn",
    answerSessionId: sessionId,
    query,
    turnKind,
    sessionFormat: fmt,
    analysisDepth: depth,
    videoMode: fmt === "video" ? videoMode : undefined,
    sourceEntry: handoff.from ?? undefined,
  };
  if (pending) {
    return {
      ...base,
      resumeStreamId: pending.streamId,
      lastSeq: pending.seq,
      startedAt: pending.startedAt,
    };
  }
  if (hookStreamId && hookLastSeq > 0) {
    return { ...base, resumeStreamId: hookStreamId, lastSeq: hookLastSeq };
  }
  return null;
}
