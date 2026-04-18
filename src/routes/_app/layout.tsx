import { Navigate, Outlet } from "react-router";
import { useAuth } from "@/lib/auth";
import { Toaster } from "@/components/ui/sonner";

function Spinner() {
  return (
    <svg className="h-8 w-8 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

export default function AppLayout() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div
        className="gv-studio-type flex min-h-screen items-center justify-center bg-[color:var(--gv-canvas)] text-[color:var(--gv-ink-2)]"
        role="status"
        aria-label="Đang tải"
      >
        <Spinner />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <>
      <div className="gv-studio-type min-h-screen bg-[color:var(--gv-canvas)]">
        <Outlet />
      </div>
      <Toaster />
    </>
  );
}
