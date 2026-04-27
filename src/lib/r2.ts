import { env } from "@/lib/env";

/**
 * Standalone R2 frame URL builder. Lives in its own module (no supabase
 * import) so that side-effect-free callers (like the prerendered landing
 * page's hook ticker) don't drag the supabase client chunk into their
 * critical-path bundle.
 *
 * ``corpus-service.ts`` re-exports this for back-compat with the existing
 * call sites that already import it from there.
 */

/** Derive a stable R2 frame URL for a video_id (frame 0 = ~0s thumbnail). */
export function r2FrameUrl(videoId: string): string | null {
  const base = env.VITE_R2_PUBLIC_URL;
  if (!base || !videoId) return null;
  return `${base.replace(/\/$/, "")}/frames/${videoId}/0.png`;
}
