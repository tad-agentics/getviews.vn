import { QueryClient } from "@tanstack/react-query";

/**
 * Retry policy.
 *
 * - **Queries:** ``retry: 1`` keeps cheap reads resilient against
 *   transient network blips. Credit-burning queries
 *   (``useVideoAnalysis``, ``useChannelAnalyze``, ``useScriptGenerate``)
 *   already override with ``retry: false`` per-hook.
 *
 * - **Mutations:** ``retry: 0`` is explicit because TanStack v5's
 *   default already happens to be 0 — but the policy must stay
 *   explicit. A retried mutation against any of our Cloud Run
 *   endpoints is potentially a duplicate ``decrement_credit`` call.
 *   Hooks that genuinely need a retry should opt in per-mutation.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,
      gcTime: 5 * 60 * 1000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
});
