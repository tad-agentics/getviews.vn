import { useMutation, useQuery } from "@tanstack/react-query";

import type {
  ScriptDraftResponse,
  ScriptDraftsListResponse,
  ScriptSaveRequest,
  ScriptSaveResponse,
} from "@/lib/api-types";
import { throwSessionExpired } from "@/lib/authErrors";
import { readErrorDetail } from "@/lib/cloudRunErrors";
import { env } from "@/lib/env";
import { fetchWithTimeout } from "@/lib/fetchWithTimeout";
import { supabase } from "@/lib/supabase";

/**
 * D.1.1 — Wrappers for the four draft-script endpoints on Cloud Run.
 * Shares a single base URL + auth helper so the ScriptScreen wiring
 * stays declarative. Every fetch runs through `fetchWithTimeout` and
 * branches on 401 so a stale JWT auto-signs the user out instead of
 * bubbling an opaque "HTTP 500" that strands the draft.
 */

async function authToken(): Promise<string> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session?.access_token) throw new Error("Chưa đăng nhập");
  return session.access_token;
}

function baseOrThrow(): string {
  const base = env.VITE_CLOUD_RUN_API_URL;
  if (!base) throw new Error("Cloud Run URL chưa cấu hình");
  return base;
}

export function useScriptSave() {
  return useMutation<ScriptSaveResponse, Error, ScriptSaveRequest>({
    mutationFn: async (body) => {
      const base = baseOrThrow();
      const token = await authToken();
      const res = await fetchWithTimeout(`${base}/script/save`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
        timeoutMs: 30_000,
      });
      if (res.status === 401) {
        throwSessionExpired("401_from_cloud_run");
      }
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return (await res.json()) as ScriptSaveResponse;
    },
  });
}

export const scriptDraftsListKey = ["script-drafts"] as const;

export function useScriptDrafts(enabled: boolean = true) {
  return useQuery<ScriptDraftsListResponse>({
    queryKey: scriptDraftsListKey,
    queryFn: async () => {
      const base = baseOrThrow();
      const token = await authToken();
      const res = await fetchWithTimeout(`${base}/script/drafts`, {
        headers: { Authorization: `Bearer ${token}` },
        timeoutMs: 15_000,
      });
      if (res.status === 401) {
        throwSessionExpired("401_from_cloud_run");
      }
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return (await res.json()) as ScriptDraftsListResponse;
    },
    enabled: enabled && Boolean(env.VITE_CLOUD_RUN_API_URL),
    staleTime: 30_000,
  });
}

export function scriptDraftKey(draftId: string | null | undefined) {
  return ["script-draft", draftId] as const;
}

export function useScriptDraft(draftId: string | null | undefined) {
  return useQuery<ScriptDraftResponse>({
    queryKey: scriptDraftKey(draftId),
    queryFn: async () => {
      const base = baseOrThrow();
      const token = await authToken();
      const res = await fetchWithTimeout(
        `${base}/script/drafts/${encodeURIComponent(draftId ?? "")}`,
        { headers: { Authorization: `Bearer ${token}` }, timeoutMs: 15_000 },
      );
      if (res.status === 401) {
        throwSessionExpired("401_from_cloud_run");
      }
      if (res.status === 404) throw new Error("Không tìm thấy kịch bản");
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return (await res.json()) as ScriptDraftResponse;
    },
    enabled: Boolean(draftId) && Boolean(env.VITE_CLOUD_RUN_API_URL),
  });
}

export interface ScriptExportCopyResult {
  format: "copy";
  text: string;
}

/**
 * Invoke `POST /script/drafts/:id/export`. Returns the plain text for
 * clipboard paste (Zalo / notes apps).
 */
export function useScriptExport() {
  return useMutation<
    ScriptExportCopyResult,
    Error,
    { draftId: string }
  >({
    mutationFn: async ({ draftId }) => {
      const base = baseOrThrow();
      const token = await authToken();
      const res = await fetchWithTimeout(
        `${base}/script/drafts/${encodeURIComponent(draftId)}/export`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ format: "copy" }),
          timeoutMs: 30_000,
        },
      );
      if (res.status === 401) {
        throwSessionExpired("401_from_cloud_run");
      }
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return { format: "copy", text: await res.text() };
    },
  });
}
