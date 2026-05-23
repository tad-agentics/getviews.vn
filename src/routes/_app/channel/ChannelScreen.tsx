import { Navigate, useSearchParams } from "react-router";

import { channelRouteRedirectPath } from "@/lib/channelStudioHandoff";

/**
 * Legacy shim — ``/app/channel`` redirects to Studio Home with the same
 * query params (``?handle=&depth=&video_url=``).
 */
export default function ChannelScreen() {
  const [searchParams] = useSearchParams();
  return <Navigate to={channelRouteRedirectPath(searchParams)} replace />;
}
