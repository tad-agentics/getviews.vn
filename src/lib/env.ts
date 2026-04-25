import { z } from "zod";

/** Matches `supabase start` defaults so `npm run dev` works before `.env.local` exists. */
const DEV_DEFAULT_SUPABASE_URL = "http://127.0.0.1:54321";
/** Public demo anon JWT from Supabase local stack (not a secret). */
const DEV_DEFAULT_SUPABASE_PUBLISHABLE_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0";

// Vite injects all VITE_* env values as strings (or undefined). The
// transform pattern below normalises optional URL strings ("" → undefined)
// + boolean feature flags ("true" → true, anything else → false) so
// callers can read them via the typed ``env`` export instead of touching
// ``import.meta.env`` directly.
const VITE_BOOL = z
  .string()
  .optional()
  .transform((v) => v === "true");

const clientEnvSchema = z.object({
  VITE_SUPABASE_URL: z.string().url(),
  VITE_SUPABASE_PUBLISHABLE_KEY: z.string().min(1),
  VITE_CLOUD_RUN_API_URL: z.string().url().optional().or(z.literal("").transform(() => undefined)),
  VITE_R2_PUBLIC_URL: z.string().url().optional().or(z.literal("").transform(() => undefined)),
  /** Feature flag: shows the ZaloPay pricing option in PricingScreen.
   *  Off by default (PayOS is the live payment gateway). Set to ``"true"``
   *  in ``.env.local`` to surface ZaloPay alongside PayOS. */
  VITE_ZALOPAY_ENABLED: VITE_BOOL,
});

export type ClientEnv = z.infer<typeof clientEnvSchema>;

function emptyToUndefined(v: unknown): unknown {
  return v === "" ? undefined : v;
}

function loadClientEnv(): ClientEnv {
  let url = emptyToUndefined(import.meta.env.VITE_SUPABASE_URL);
  let publishable = emptyToUndefined(import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY);

  if (import.meta.env.DEV && (url == null || publishable == null)) {
    if (url == null) url = DEV_DEFAULT_SUPABASE_URL;
    if (publishable == null) publishable = DEV_DEFAULT_SUPABASE_PUBLISHABLE_KEY;
    if (
      emptyToUndefined(import.meta.env.VITE_SUPABASE_URL) == null &&
      emptyToUndefined(import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY) == null
    ) {
      console.warn(
        "[RAD client env] Dev fallback: using local Supabase defaults (127.0.0.1:54321). " +
          "Copy .env.example → .env.local and set VITE_SUPABASE_* for a hosted project or after `supabase start`.",
      );
    }
  }

  const parsed = clientEnvSchema.safeParse({
    VITE_SUPABASE_URL: url,
    VITE_SUPABASE_PUBLISHABLE_KEY: publishable,
    VITE_CLOUD_RUN_API_URL: import.meta.env.VITE_CLOUD_RUN_API_URL,
    VITE_R2_PUBLIC_URL: import.meta.env.VITE_R2_PUBLIC_URL,
    VITE_ZALOPAY_ENABLED: import.meta.env.VITE_ZALOPAY_ENABLED,
  });

  if (!parsed.success) {
    const fields = parsed.error.flatten().fieldErrors;
    throw new Error(
      `[RAD client env] Invalid or missing VITE_* variables (validation runs on first import of this module — stack may point here, not your route). Details: ${JSON.stringify(fields)}. Fix: copy .env.example → .env.local and set valid VITE_SUPABASE_URL (URL) and VITE_SUPABASE_PUBLISHABLE_KEY.`,
    );
  }

  const d = parsed.data;
  const cloud = d.VITE_CLOUD_RUN_API_URL;
  return {
    ...d,
    VITE_CLOUD_RUN_API_URL:
      cloud != null && cloud !== "" ? cloud.replace(/\/+$/, "") : undefined,
  };
}

/**
 * Parsed once when this module is first imported (usually during Vite dev/build, before React runs).
 * Intentionally throws at import time so bad env never reaches Supabase calls — expect the stack to
 * highlight `src/lib/env.ts` if `.env.local` is empty or wrong.
 */
export const env = loadClientEnv();
