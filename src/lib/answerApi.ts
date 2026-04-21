/**
 * Cloud Run `/answer/*` helpers (Phase C.1.2) — single place for base URL + auth header.
 */
import { env } from "@/lib/env";
import type { AnswerSessionRow, AnswerTurnRow, ReportV1 } from "@/lib/api-types";

export const answerApiBase = () => env.VITE_CLOUD_RUN_API_URL ?? "";

export type CreateAnswerSessionBody = {
  initial_q: string;
  intent_type: string;
  niche_id: number | null;
  format: "pattern" | "ideas" | "timing" | "generic";
};

/** `POST /answer/sessions` — Idempotency-Key optional (120s server-side cache). */
export async function createAnswerSession(
  accessToken: string,
  body: CreateAnswerSessionBody,
  idempotencyKey?: string,
): Promise<AnswerSessionRow> {
  const base = answerApiBase();
  if (!base) throw new Error("no_cloud_run");
  const headers: Record<string, string> = {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  };
  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }
  const res = await fetch(`${base}/answer/sessions`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`answer/sessions ${res.status}`);
  return (await res.json()) as AnswerSessionRow;
}

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
    turns: AnswerTurnRow[];
  };
}

/**
 * `PATCH /answer/sessions/:id` — update title and/or archived_at.
 *
 * Answer sessions have an `archived_at` column (history_union filters
 * `archived_at IS NULL`, so setting it effectively hides the session from
 * /app/history). Distinct from chat sessions which hard-delete via RPC —
 * per phase-c-plan.md the soft-delete model stayed for answer because
 * turn rows carry irreversible cost (Gemini + EnsembleData spend).
 */
export async function patchAnswerSession(
  accessToken: string,
  sessionId: string,
  patch: { title?: string | null; archived_at?: string | null },
): Promise<AnswerSessionRow> {
  const base = answerApiBase();
  if (!base) throw new Error("no_cloud_run");
  const res = await fetch(`${base}/answer/sessions/${sessionId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(patch),
  });
  if (res.status === 404) throw new Error("session_not_found");
  if (!res.ok) throw new Error(`answer/session PATCH ${res.status}`);
  return (await res.json()) as AnswerSessionRow;
}
