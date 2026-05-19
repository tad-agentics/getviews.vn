/**
 * Cloud Run ``/answer/*`` helpers — base URL, auth header, shared error
 * handling. Every call goes through ``fetchWithTimeout`` + ``readErrorDetail``
 * so a cold-boot / 500 / 401 path surfaces as a named error the screen can
 * render through ``analysisErrorCopy`` — not as ``"answer/sessions 500"``.
 *
 * Previous shape used bare ``fetch`` + ``throw new Error(\`answer/sessions ${status}\`)``
 * which (a) hung forever if Cloud Run was starting and (b) rendered English
 * codes directly to users. The Cloud Run DB writes were happening but no
 * ``answer_sessions`` rows appeared — tracing the failure required a server
 * round-trip because the client had no detail to show.
 */
import { throwSessionExpired } from "@/lib/authErrors";
import { readErrorDetail } from "@/lib/cloudRunErrors";
import { env } from "@/lib/env";
import { fetchWithTimeout } from "@/lib/fetchWithTimeout";
import type { AnswerSessionFormat, AnswerSessionRow, AnswerTurnRow } from "@/lib/api-types";

export const answerApiBase = () => env.VITE_CLOUD_RUN_API_URL ?? "";

async function throwFromResponse(res: Response, route: string): Promise<never> {
  const detail = await readErrorDetail(res);
  const err = new Error(detail || `${route} ${res.status}`);
  // Tag with status so dev-tools / Sentry can filter.
  (err as Error & { status?: number }).status = res.status;
  (err as Error & { route?: string }).route = route;
  throw err;
}

export type CreateAnswerSessionBody = {
  initial_q: string;
  intent_type: string;
  niche_id: number | null;
  format: AnswerSessionFormat;
};

/** ``POST /answer/sessions`` — Idempotency-Key optional (120s server-side cache). */
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
  const res = await fetchWithTimeout(`${base}/answer/sessions`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    timeoutMs: 20_000,
  });
  if (res.status === 401) {
    throwSessionExpired("401_from_cloud_run");
  }
  if (!res.ok) {
    await throwFromResponse(res, "answer/sessions");
  }
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
  const res = await fetchWithTimeout(`${base}/answer/sessions?${params.toString()}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    timeoutMs: 15_000,
  });
  if (res.status === 401) {
    throwSessionExpired("401_from_cloud_run");
  }
  if (!res.ok) {
    await throwFromResponse(res, "answer/sessions");
  }
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
  const res = await fetchWithTimeout(`${base}/answer/sessions/${sessionId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    timeoutMs: 20_000,
  });
  if (res.status === 401) {
    throwSessionExpired("401_from_cloud_run");
  }
  if (res.status === 404) {
    const err = new Error("session_not_found");
    err.name = "SessionNotFound";
    throw err;
  }
  if (!res.ok) {
    await throwFromResponse(res, "answer/session");
  }
  return (await res.json()) as {
    session: AnswerSessionRow & { title: string | null; initial_q: string };
    turns: AnswerTurnRow[];
  };
}

/** ``DELETE /answer/sessions/:id`` — permanently remove session + turns (cascade). */
export async function deleteAnswerSession(
  accessToken: string,
  sessionId: string,
): Promise<void> {
  const base = answerApiBase();
  if (!base) throw new Error("no_cloud_run");
  const res = await fetchWithTimeout(`${base}/answer/sessions/${sessionId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${accessToken}` },
    timeoutMs: 15_000,
  });
  if (res.status === 401) {
    throwSessionExpired("401_from_cloud_run");
  }
  if (res.status === 404) throw new Error("session_not_found");
  if (!res.ok) {
    await throwFromResponse(res, "answer/session DELETE");
  }
}

/**
 * ``PATCH /answer/sessions/:id`` — update title and/or archived_at.
 *
 * ``archived_at`` remains for admin/legacy paths; user-facing delete uses
 * ``deleteAnswerSession`` (hard delete).
 */
export async function patchAnswerSession(
  accessToken: string,
  sessionId: string,
  patch: { title?: string | null; archived_at?: string | null },
): Promise<AnswerSessionRow> {
  const base = answerApiBase();
  if (!base) throw new Error("no_cloud_run");
  const res = await fetchWithTimeout(`${base}/answer/sessions/${sessionId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(patch),
    timeoutMs: 15_000,
  });
  if (res.status === 401) {
    throwSessionExpired("401_from_cloud_run");
  }
  if (res.status === 404) throw new Error("session_not_found");
  if (!res.ok) {
    await throwFromResponse(res, "answer/session PATCH");
  }
  return (await res.json()) as AnswerSessionRow;
}
