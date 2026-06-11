import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate, useLocation, Navigate } from "react-router";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { AppLayout } from "@/components/AppLayout";
import { MobileShellStandalone } from "@/components/MobileShellStandalone";
import { supabase } from "@/lib/supabase";

type CheckoutState = {
  plan?: string;
  billingPeriod?: "monthly" | "biannual" | "annual";
};

/** PayOS bank transfer — sole production payment rail. */
const PAYOS_PAYMENT_METHOD = "bank_transfer" as const;

const ORDER_COPY: Record<
  string,
  {
    title: string;
    subtitle: string;
    amount: string;
  }
> = {
  starter_monthly: { title: "Starter", subtitle: "Thanh toán hàng tháng", amount: "249.000đ" },
  starter_biannual: { title: "Starter", subtitle: "Thanh toán 6 tháng", amount: "1.194.000đ" },
  starter_annual: { title: "Starter", subtitle: "Thanh toán cả năm", amount: "2.388.000đ" },
  pack_10: { title: "10 phân tích", subtitle: "Mua thêm", amount: "130.000đ" },
  pack_30: { title: "30 phân tích", subtitle: "Mua thêm", amount: "350.000đ" },
  pack_50: { title: "50 phân tích", subtitle: "Mua thêm", amount: "550.000đ" },
};

export default function CheckoutScreen() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as CheckoutState | null;
  const plan = state?.plan;

  const [submitting, setSubmitting] = useState(true);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const payosStartedRef = useRef(false);

  const startPayosCheckout = useCallback(async () => {
    if (!plan) return;
    setSubmitError(null);
    setSubmitting(true);
    let redirected = false;
    try {
      const { data, error } = await supabase.functions.invoke("create-payment", {
        body: { plan, payment_method: PAYOS_PAYMENT_METHOD },
      });
      if (error) {
        setSubmitError("Thanh toán không thành công — thử lại.");
        toast.error("Thanh toán không thành công — thử lại.");
        return;
      }
      const payload = data as { checkoutUrl?: string; error?: { message?: string } };
      if (payload?.error) {
        setSubmitError("Thanh toán không thành công — thử lại.");
        toast.error("Thanh toán không thành công — thử lại.");
        return;
      }
      const checkoutUrl = payload?.checkoutUrl?.trim();
      if (checkoutUrl) {
        redirected = true;
        window.location.href = checkoutUrl;
        return;
      }
      setSubmitError("Thanh toán không thành công — thử lại.");
      toast.error("Thanh toán không thành công — thử lại.");
    } catch {
      setSubmitError("Thanh toán không thành công — thử lại.");
      toast.error("Thanh toán không thành công — thử lại.");
    } finally {
      if (!redirected) setSubmitting(false);
    }
  }, [plan]);

  useEffect(() => {
    if (!plan || !ORDER_COPY[plan]) return;
    if (payosStartedRef.current) return;
    payosStartedRef.current = true;
    void startPayosCheckout();
  }, [plan, startPayosCheckout]);

  if (!plan || !ORDER_COPY[plan]) {
    return <Navigate to="/app/settings?section=billing&pricing=1" replace />;
  }

  const order = ORDER_COPY[plan];

  return (
    <AppLayout enableMobileSidebar>
      <MobileShellStandalone />
      <div className="flex flex-col h-full bg-[var(--surface-alt)]">
        <div className="flex-1 overflow-y-auto pb-6">
          <div className="max-w-xl mx-auto p-4 lg:p-6 space-y-6">
            <button
              type="button"
              onClick={() => navigate("/app/settings?section=billing&pricing=1")}
              className="mt-14 lg:mt-0 inline-flex min-h-[44px] min-w-[44px] items-center text-sm text-[var(--muted)] hover:text-[var(--ink)] transition-colors duration-[120ms]"
              disabled={submitting && !submitError}
            >
              ← Quay lại
            </button>

            <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-5">
              <h3 className="text-xs font-medium text-[var(--muted)] uppercase tracking-wide mb-3">Đơn hàng</h3>
              <div className="flex justify-between items-start gap-3">
                <div>
                  <p className="font-medium text-[var(--ink)]">{order.title}</p>
                  <p className="text-sm text-[var(--muted)]">{order.subtitle}</p>
                </div>
                <p className="font-mono font-bold text-[var(--gv-accent)] shrink-0" style={{ fontSize: "1.25rem" }}>
                  {order.amount}
                </p>
              </div>
            </div>

            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5">
              <p className="text-xs font-medium text-[var(--muted)] uppercase tracking-wide mb-2">
                Phương thức thanh toán
              </p>
              <p className="font-mono text-sm font-semibold text-[var(--ink)]">PayOS Chuyển khoản</p>
              {submitting && !submitError ? (
                <p className="mt-3 flex items-center gap-2 text-sm text-[var(--muted)]">
                  <Loader2 className="h-4 w-4 shrink-0 animate-spin text-[var(--gv-accent)]" aria-hidden />
                  Đang chuyển đến cổng thanh toán PayOS…
                </p>
              ) : null}
            </div>

            {submitError ? (
              <Button fullWidth className="h-12 text-sm" onClick={() => void startPayosCheckout()} disabled={submitting}>
                {submitting ? (
                  <span className="inline-flex items-center justify-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    Đang xử lý...
                  </span>
                ) : (
                  "Thử lại thanh toán PayOS"
                )}
              </Button>
            ) : null}
            {submitError ? <p className="text-sm text-destructive text-center">{submitError}</p> : null}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
