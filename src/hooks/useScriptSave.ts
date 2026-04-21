import { useMutation, useQuery } from "@tanstack/react-query";

import type {
  ScriptDraftResponse,
  ScriptDraftsListResponse,
  ScriptSaveRequest,
  ScriptSaveResponse,
} from "@/lib/api-types";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

/**
 * D.1.1 — Wrappers for the four draft-script endpoints on Cloud Run.
 * Shares a single base URL + auth helper so the ScriptScreen wiring
 * stays declarative.
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
      const res = await fetch(`${base}/script/save`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || `HTTP ${res.status}`);
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
      const res = await fetch(`${base}/script/drafts`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(await res.text());
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
      const res = await fetch(
        `${base}/script/drafts/${encodeURIComponent(draftId ?? "")}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (res.status === 404) throw new Error("Không tìm thấy kịch bản");
      if (!res.ok) throw new Error(await res.text());
      return (await res.json()) as ScriptDraftResponse;
    },
    enabled: Boolean(draftId) && Boolean(env.VITE_CLOUD_RUN_API_URL),
  });
}

export interface ScriptExportCopyResult {
  format: "copy";
  text: string;
}

export interface ScriptExportPdfResult {
  format: "pdf";
  blob: Blob;
  filename: string;
}

/**
 * Invoke `POST /script/drafts/:id/export`. Copy path returns the plain text
 * for clipboard; PDF path returns a Blob ready for `URL.createObjectURL` +
 * click-to-download. 503 maps to a distinctive error so the UI can surface
 * "PDF tạm thời không khả dụng" without treating it like a transient fail.
 */
export function useScriptExport() {
  return useMutation<
    ScriptExportCopyResult | ScriptExportPdfResult,
    Error,
    { draftId: string; format: "copy" | "pdf"; filenameHint?: string }
  >({
    mutationFn: async ({ draftId, format, filenameHint }) => {
      const base = baseOrThrow();
      const token = await authToken();
      const res = await fetch(
        `${base}/script/drafts/${encodeURIComponent(draftId)}/export`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ format }),
        },
      );
      if (res.status === 503) {
        const err = new Error("pdf_unavailable");
        err.name = "PdfUnavailable";
        throw err;
      }
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || `HTTP ${res.status}`);
      }
      if (format === "copy") {
        return { format: "copy", text: await res.text() };
      }
      const blob = await res.blob();
      const disposition = res.headers.get("Content-Disposition") ?? "";
      const match = /filename="([^"]+)"/.exec(disposition);
      const filename = match?.[1] ?? `${filenameHint ?? "kich-ban"}.pdf`;
      return { format: "pdf", blob, filename };
    },
  });
}
