import { Navigate, useParams, useSearchParams } from "react-router";

import { scriptShootRedirectPath } from "@/lib/answerHandoff";

/**
 * Wave 2 — deprecated shoot route. Redirects to Answer in-session shoot panel.
 */
export default function AppScriptShootRoute() {
  const { draftId } = useParams<{ draftId: string }>();
  const [searchParams] = useSearchParams();
  if (!draftId?.trim()) {
    return <Navigate to="/app/answer" replace />;
  }
  return <Navigate to={scriptShootRedirectPath(draftId, searchParams)} replace />;
}
