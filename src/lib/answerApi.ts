/**
 * Cloud Run `/answer/*` helpers (Phase C.1.2) — single place for base URL + auth header.
 */
import { env } from "@/lib/env";
import type { AnswerSessionRow, ReportV1 } from "@/lib/api-types";

export const answerApiBase = () => env.VITE_CLOUD_RUN_API_URL ?? "";

export type AnswerSessionsListResponse = {
  sessions: AnswerSessionRow[];
  next_cursor: string | null;
};

export async function fetchAnswerSessions(
  accessToken: string,
  options?: {
    limit?: number;
    includeArchived?: boolean;
    /** Drawer default ``30d``; ``all`` for unbounded lists. */
    scope?: "30d" | "all";
    cursor?: string | null;
  },
): Promise<AnswerSessionsListResponse> {
  const base = answerApiBase();
  if (!base) return { sessions: [], next_cursor: null };
  const limit = options?.limit ?? 30;
  const inc = options?.includeArchived ?? false;
  const scope = options?.scope ?? "30d";
  const cursor = options?.cursor;
  const params = new URLSearchParams({
    limit: String(limit),
    include_archived: String(inc),
    scope,
  });
  if (cursor) params.set("cursor", cursor);
  const res = await fetch(`${base}/answer/sessions?${params.toString()}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new Error(`answer/sessions ${res.status}`);
  const data = (await res.json()) as {
    sessions?: AnswerSessionRow[];
    next_cursor?: string | null;
  };
  return {
    sessions: data.sessions ?? [],
    next_cursor: data.next_cursor ?? null,
  };
}

export async function fetchAnswerSessionDetail(accessToken: string, sessionId: string) {
  const base = answerApiBase();
  if (!base) throw new Error("no_cloud_run");
  const res = await fetch(`${base}/answer/sessions/${sessionId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new Error(`answer/session ${res.status}`);
  return (await res.json()) as {
    session: AnswerSessionRow & { title: string | null; initial_q: string };
    turns: Array<{ payload: ReportV1 }>;
  };
}
