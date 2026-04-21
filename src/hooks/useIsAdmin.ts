import { useProfile } from "@/hooks/useProfile";

/**
 * Returns ``true`` when the signed-in user has ``profiles.is_admin = true``.
 *
 * The profile row is served by ``useProfile`` which already cures auth state
 * and subscribes to realtime updates, so there's no extra fetch here — the
 * admin gate is a pure selector. Unauthenticated users and callers still
 * loading the profile both get ``false`` so the default-deny stance is
 * "hide the admin surface until we're sure".
 *
 * Server-side checks remain the source of truth: the Cloud Run
 * `require_admin` dependency re-queries `profiles.is_admin` on every admin
 * endpoint. This hook only controls what the SPA *shows*.
 */
export function useIsAdmin(): { isAdmin: boolean; isLoading: boolean } {
  const profile = useProfile();
  const isLoading = profile.isLoading;
  const isAdmin = Boolean(profile.data?.is_admin);
  return { isAdmin, isLoading };
}
