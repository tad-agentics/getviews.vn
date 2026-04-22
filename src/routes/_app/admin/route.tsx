import { lazy, Suspense } from "react";
import type { MetaFunction } from "react-router";
import { pageMeta } from "@/lib/pageTitle";

export const meta: MetaFunction = () => pageMeta("Admin");

const AdminScreen = lazy(() => import("./AdminScreen"));

/** `/app/admin` — operator dashboard (Phase D.6). Gated client-side by
 *  `useIsAdmin`; the server re-checks via `require_admin` on every data
 *  endpoint so a manual URL visit by a non-admin still hits 403. */
export default function AppAdminRoute() {
  return (
    <Suspense
      fallback={
        <div
          role="status"
          aria-label="Đang tải"
          className="min-h-[40vh] flex-1 animate-pulse rounded-lg bg-[color:var(--gv-canvas-2)]"
        />
      }
    >
      <AdminScreen />
    </Suspense>
  );
}
