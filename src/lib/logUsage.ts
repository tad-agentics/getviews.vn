import { supabase } from "@/lib/supabase";

/**
 * Fire-and-forget product analytics (B.1 checkpoint + plan §Measurement).
 * Requires an authenticated session; no-ops if none.
 *
 * Common `action` values: `video_screen_load`, `flop_cta_click`, `kol_screen_load`,
 * `kol_pin` (plan §Measurement / B.2.5).
 */
export function logUsage(action: string, metadata?: Record<string, unknown>): void {
  void (async () => {
    const { data } = await supabase.auth.getSession();
    const uid = data.session?.user?.id;
    if (!uid) return;
    const { error } = await supabase.from("usage_events").insert({
      user_id: uid,
      action,
      metadata: metadata ?? {},
    });
    if (error && import.meta.env.DEV) {
      console.warn("[logUsage]", action, error.message);
    }
  })();
}
