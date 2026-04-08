import { z } from "zod";

const clientEnvSchema = z.object({
  VITE_SUPABASE_URL: z.string().url(),
  VITE_SUPABASE_PUBLISHABLE_KEY: z.string().min(1),
  VITE_CLOUD_RUN_URL: z.string().url().optional(),
  VITE_R2_PUBLIC_URL: z.string().url().optional(),
});

export type ClientEnv = z.infer<typeof clientEnvSchema>;

function loadClientEnv(): ClientEnv {
  const parsed = clientEnvSchema.safeParse({
    VITE_SUPABASE_URL: import.meta.env.VITE_SUPABASE_URL,
    VITE_SUPABASE_PUBLISHABLE_KEY: import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
    VITE_CLOUD_RUN_URL: import.meta.env.VITE_CLOUD_RUN_URL,
    VITE_R2_PUBLIC_URL: import.meta.env.VITE_R2_PUBLIC_URL,
  });

  if (!parsed.success) {
    const fields = parsed.error.flatten().fieldErrors;
    throw new Error(
      `[RAD client env] Invalid or missing VITE_* variables (validation runs on first import of this module — stack may point here, not your route). Details: ${JSON.stringify(fields)}. Fix: copy .env.example → .env.local and set valid VITE_SUPABASE_URL (URL) and VITE_SUPABASE_PUBLISHABLE_KEY.`,
    );
  }

  return parsed.data;
}

/**
 * Parsed once when this module is first imported (usually during Vite dev/build, before React runs).
 * Intentionally throws at import time so bad env never reaches Supabase calls — expect the stack to
 * highlight `src/lib/env.ts` if `.env.local` is empty or wrong.
 */
export const env = loadClientEnv();
