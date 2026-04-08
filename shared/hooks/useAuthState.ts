import { useState, useEffect } from "react";
import { useSupabase } from "../api/supabase-context";

/**
 * Platform-agnostic auth state hook.
 * Uses SupabaseProvider context — works on both web and mobile.
 * Returns { isLoggedIn, userId, isLoading } for auth guards.
 */
export function useAuthState() {
  const supabase = useSupabase();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check current session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setIsLoggedIn(!!session);
      setUserId(session?.user?.id ?? null);
      setIsLoading(false);
    });

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setIsLoggedIn(!!session);
      setUserId(session?.user?.id ?? null);
      setIsLoading(false);
    });

    return () => subscription.unsubscribe();
  }, [supabase]);

  return { isLoggedIn, userId, isLoading };
}
