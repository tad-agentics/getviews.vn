import { throwSessionExpired } from "@/lib/authErrors";
import { readErrorDetail } from "@/lib/cloudRunErrors";
import { env } from "@/lib/env";
import { fetchWithTimeout } from "@/lib/fetchWithTimeout";
import { supabase } from "@/lib/supabase";

type NamedStatusError = {
  message: string;
  name?: string;
};

export function makeNamedError(message: string, name?: string): Error {
  const err = new Error(message);
  if (name) err.name = name;
  return err;
}

async function authTokenOrThrow(): Promise<string> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session?.access_token) throw new Error("Chưa đăng nhập");
  return session.access_token;
}

export async function cloudRunAuthedFetch(
  path: string,
  opts: {
    method?: "GET" | "POST" | "PATCH" | "DELETE";
    body?: string;
    timeoutMs?: number;
    headers?: Record<string, string>;
  } = {},
): Promise<Response> {
  const base = env.VITE_CLOUD_RUN_API_URL;
  if (!base) throw new Error("Cloud Run URL chưa cấu hình");
  const token = await authTokenOrThrow();
  const method = opts.method ?? "GET";
  return fetchWithTimeout(`${base}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(opts.body ? { "Content-Type": "application/json" } : {}),
      ...(opts.headers ?? {}),
    },
    body: opts.body,
    timeoutMs: opts.timeoutMs ?? 20_000,
  });
}

export async function throwCloudRunError(
  res: Response,
  namedStatuses: Partial<Record<number, NamedStatusError>> = {},
): Promise<never> {
  if (res.status === 401) {
    throwSessionExpired("401_from_cloud_run");
  }
  const mapped = namedStatuses[res.status];
  if (mapped) {
    throw makeNamedError(mapped.message, mapped.name);
  }
  throw new Error(await readErrorDetail(res));
}
