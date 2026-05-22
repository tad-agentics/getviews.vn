import { Navigate, useSearchParams } from "react-router";

import { scriptRouteRedirectPath } from "@/lib/answerHandoff";

/**
 * Wave 2 — deprecated route shell. All script entry flows redirect to
 * ``/app/answer`` with composer ``?q=`` prefill (intent-router SSOT).
 */
export default function ScriptScreen() {
  const [searchParams] = useSearchParams();
  return <Navigate to={scriptRouteRedirectPath(searchParams)} replace />;
}
