import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { AppLayout } from "@/components/AppLayout";
import { useProfile } from "@/hooks/useProfile";

type SuccessState = {
  planName?: string;
  creditsDelta?: number;
};

export default function PaymentSuccessScreen() {
  const location = useLocation();
  const navigate = useNavigate();
  const st = location.state as SuccessState | null;
  const hasRouterState =
    st != null && typeof st === "object" && (st.creditsDelta != null || Boolean(st.planName));

  const { data: profile, isPending } = useProfile();
  const remaining = profile?.deep_credits_remaining ?? 0;
  const delta = st?.creditsDelta;

  const headingCount = delta ?? remaining;

  const startVal = delta != null ? Math.max(0, remaining - delta) : remaining;
  const [displayCredits, setDisplayCredits] = useState(startVal);

  useEffect(() => {
    if (isPending || !profile) return;
    if (delta == null) {
      setDisplayCredits(remaining);
      return;
    }
    const start = Math.max(0, remaining - delta);
    const end = remaining;
    let raf = 0;
    const t0 = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - t0) / 800);
      setDisplayCredits(Math.round(start + (end - start) * t));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [isPending, profile, remaining, delta]);

  if (isPending) {
    return (
      <AppLayout enableMobileSidebar>
        <div className="flex-1 flex items-center justify-center px-4 bg-[var(--surface-alt)] animate-pulse">
          <div className="max-w-sm w-full rounded-xl bg-[var(--border)] h-64" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout enableMobileSidebar>
      <div className="flex-1 flex items-center justify-center px-4 bg-[var(--surface-alt)]">
        <div className="max-w-sm w-full text-center">
          <div
            className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-6 border border-[var(--border)]"
            style={{ background: "color-mix(in oklch, var(--success) 10%, transparent)" }}
          >
            <Check className="w-7 h-7" style={{ color: "var(--success)" }} strokeWidth={2.5} />
          </div>

          {hasRouterState ? (
            <h1 className="font-extrabold text-[var(--ink)] mb-2" style={{ fontSize: "1.5rem" }}>
              Đã thêm {headingCount} deep credits.
            </h1>
          ) : (
            <h1 className="font-extrabold text-[var(--ink)] mb-2" style={{ fontSize: "1.5rem" }}>
              Credits đã được cập nhật.
            </h1>
          )}

          {hasRouterState && st?.planName ? (
            <p className="text-sm text-[var(--ink-soft)] mb-8" style={{ lineHeight: "1.6" }}>
              {st.planName}
            </p>
          ) : (
            <div className="mb-8" />
          )}

          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-8 mb-8">
            <div
              className="font-mono font-extrabold text-[var(--purple)] mb-1"
              style={{ fontSize: "3.5rem", lineHeight: "1" }}
            >
              {displayCredits}
            </div>
            <p className="text-sm text-[var(--muted)]">deep credits còn lại</p>
          </div>

          <Button fullWidth className="h-12 text-sm" onClick={() => navigate("/app")}>
            Bắt đầu phân tích ngay
          </Button>
        </div>
      </div>
    </AppLayout>
  );
}
