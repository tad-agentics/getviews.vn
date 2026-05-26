import { Navigate } from "react-router";
import type { MetaFunction } from "react-router";
import { pageMeta } from "@/lib/pageTitle";

export const meta: MetaFunction = () => pageMeta("Bảng giá");

/** Legacy URL — pricing lives in Settings → Gói & Giao dịch. */
export default function PricingRoute() {
  return <Navigate to="/app/settings?section=billing&pricing=1" replace />;
}
