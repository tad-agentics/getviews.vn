/**
 * Cloud Run analysis hooks can surface two distinct auth-error
 * shapes: a pre-flight "no session" when Supabase already dropped
 * the client-side session, and a post-flight 401 when Cloud Run
 * rejected the Bearer token as expired. Both map to the same
 * user-visible outcome — the session is gone, we should sign out
 * and bounce to /login.
 *
 * Centralising the classification keeps every hook honest and lets
 * the global AuthErrorListener (mounted in AuthProvider) detect it
 * via `err.name === "SessionExpired"` without having to regex
 * Vietnamese messages.
 */
export function throwSessionExpired(reason: string): never {
  const err = new Error(reason || "session_expired");
  err.name = "SessionExpired";
  throw err;
}

export function isSessionExpired(err: unknown): boolean {
  return err instanceof Error && err.name === "SessionExpired";
}
