import { useEffect } from "react";
import { useNavigate } from "react-router";
import { supabase } from "@/lib/supabase";

export default function AuthCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      navigate(session ? "/app" : "/login", { replace: true });
    });
  }, [navigate]);

  return (
    <div
      role="status"
      aria-label="Authenticating"
      className="min-h-screen animate-pulse bg-[#EDEDEE]"
    />
  );
}
