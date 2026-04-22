import { lazy, Suspense } from "react";
import type { MetaFunction } from "react-router";
import { pageMeta } from "@/lib/pageTitle";

export const meta: MetaFunction = () => pageMeta("Kênh tham chiếu");

const KolScreen = lazy(() => import("./KolScreen"));

/**
 * `/app/kol` — Phase B · B.2.2 Kênh Tham Chiếu (browse + pin) via Cloud Run
 * `GET /kol/browse`, `POST /kol/toggle-pin`.
 * Query: `?tab=pinned|discover`, `?page=`, `?followers=10k-100k|100k-1m|1m-5m`, `?growth=1`.
 */
export default function AppKolRoute() {
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
      <KolScreen />
    </Suspense>
  );
}
