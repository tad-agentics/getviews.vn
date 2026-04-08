import { Outlet, Navigate } from "react-router";
import { useAuth } from "@/lib/auth";

export default function AppLayout() {
  const { session, loading } = useAuth();

  if (loading) {
    return (
      <div
        role="status"
        aria-label="Loading"
        className="min-h-screen bg-[#EDEDEE] animate-pulse"
      />
    );
  }

  if (!session) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
