import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { useQueryClient } from "@tanstack/react-query";
import { isSessionExpired } from "./authErrors";
import { supabase } from "./supabase";

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
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
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
    const unsubscribe = queryClient.getQueryCache().subscribe((event) => {
      if (event.type !== "updated") return;
      if (event.action.type !== "error") return;
      const err = event.action.error as unknown;
      if (!isSessionExpired(err) || signingOut) return;
      signingOut = true;
      void supabase.auth.signOut();
    });
    // Also watch mutations (useScriptGenerate etc. are mutations).
    const unsubscribeMut = queryClient.getMutationCache().subscribe((event) => {
      if (event.type !== "updated") return;
      if (event.action.type !== "error") return;
      const err = event.action.error as unknown;
      if (!isSessionExpired(err) || signingOut) return;
      signingOut = true;
      void supabase.auth.signOut();
    });
    return () => {
      unsubscribe();
      unsubscribeMut();
    };
  }, [queryClient]);

  const signOut = useCallback(async () => {
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
