import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { useQueryClient } from "@tanstack/react-query";
import { isSessionExpired } from "./authErrors";

/**
 * The supabase client (~185 KB raw / ~50 KB gzip) is dynamically
 * imported inside each effect / callback below so it does NOT ride
 * the critical-path entry chunk that every route preloads. Result:
 * the prerendered landing page no longer transfers + parses the
 * supabase bundle before first paint; auth-aware screens fetch it
 * during the first idle tick after mount instead.
 *
 * Type-only imports (``Session`` / ``User``) are erased at compile
 * time — no runtime cost.
 */

interface AuthContextValue {
  session: Session | null;
  user: User | null;
  loading: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  session: null,
  user: null,
  loading: true,
  signOut: async () => {},
});

/** OAuth redirect: `signInWithOAuth` in login route uses `redirectTo: origin + '/auth/callback'`. */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const queryClient = useQueryClient();

  useEffect(() => {
    let cancelled = false;
    let unsubscribe: (() => void) | null = null;
    void (async () => {
      const { supabase } = await import("./supabase");
      if (cancelled) return;
      const { data } = await supabase.auth.getSession();
      if (cancelled) return;
      setSession(data.session);
      setLoading(false);
      const { data: sub } = supabase.auth.onAuthStateChange((_event, s) => {
        setSession(s);
        setLoading(false);
      });
      unsubscribe = () => sub.subscription.unsubscribe();
    })();
    return () => {
      cancelled = true;
      unsubscribe?.();
    };
  }, []);

  // D.6 — global session-expired listener. Cloud Run rejects stale
  // JWTs with 401; the four analysis hooks (video / channel / script /
  // kol) translate that into a SessionExpired error. Catching it
  // here and running signOut() triggers onAuthStateChange → the
  // layout guard at src/routes/_app/layout.tsx redirects to /login.
  // Dedup via a local flag so five concurrent failing queries don't
  // fire five signOut calls back-to-back.
  useEffect(() => {
    let signingOut = false;
    const handleError = async (err: unknown) => {
      if (!isSessionExpired(err) || signingOut) return;
      signingOut = true;
      const { supabase } = await import("./supabase");
      void supabase.auth.signOut();
    };
    const unsubscribe = queryClient.getQueryCache().subscribe((event) => {
      if (event.type !== "updated") return;
      if (event.action.type !== "error") return;
      void handleError(event.action.error as unknown);
    });
    const unsubscribeMut = queryClient.getMutationCache().subscribe((event) => {
      if (event.type !== "updated") return;
      if (event.action.type !== "error") return;
      void handleError(event.action.error as unknown);
    });
    return () => {
      unsubscribe();
      unsubscribeMut();
    };
  }, [queryClient]);

  const signOut = useCallback(async () => {
    const { supabase } = await import("./supabase");
    await supabase.auth.signOut();
  }, []);

  const value = useMemo(
    () => ({
      session,
      user: session?.user ?? null,
      loading,
      signOut,
    }),
    [session, loading, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
