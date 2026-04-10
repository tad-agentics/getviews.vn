import { useEffect } from "react";
import { useNavigate } from "react-router";
import { supabase } from "@/lib/supabase";

export default function AuthCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;

    const finish = async () => {
      const params = new URLSearchParams(window.location.search);
      const oauthError = params.get("error");
      if (oauthError) {
        if (!cancelled) navigate("/login?error=oauth", { replace: true });
        return;
      }

      const code = params.get("code");
      if (code) {
        const { error } = await supabase.auth.exchangeCodeForSession(code);
        if (cancelled) return;
        if (error) {
          navigate("/login?error=oauth", { replace: true });
          return;
        }
        navigate("/app", { replace: true });
        return;
      }

      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (cancelled) return;
      navigate(session ? "/app" : "/login", { replace: true });
    };

    void finish();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  return (
    <div
      className="flex min-h-screen items-center justify-center"
      style={{ background: "var(--background)", color: "var(--ink-soft)" }}
    >
      <p>Đang xác thực...</p>
    </div>
  );
}
