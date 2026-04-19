import { supabase } from "@/lib/supabase";
import type { Json } from "@/lib/database.types";

/**
 * Fire-and-forget product analytics (B.1 checkpoint + plan §Measurement).
 * Requires an authenticated session; no-ops if none.
 *
 * Common `action` values: `video_screen_load`, `flop_cta_click`, `video_to_script`,
 * `script_screen_load`, `script_generate`, `channel_to_script`, `kol_screen_load`,
 * `kol_pin` (plan §Measurement / B.2.5 / B.4).
 */
export function logUsage(action: string, metadata?: Record<string, unknown>): void {
  void (async () => {
    const { data } = await supabase.auth.getSession();
    const uid = data.session?.user?.id;
    if (!uid) return;
    const { error } = await supabase.from("usage_events").insert({
      user_id: uid,
      action,
      metadata: (metadata ?? {}) as Json,
    });
    if (error && import.meta.env.DEV) {
      console.warn("[logUsage]", action, error.message);
    }
  })();
}
