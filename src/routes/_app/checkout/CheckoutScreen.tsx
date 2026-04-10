import { useState, useEffect, useMemo } from "react";
import { useNavigate, useLocation, Navigate } from "react-router";
import * as RadioGroup from "@radix-ui/react-radio-group";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { AppLayout } from "@/components/AppLayout";
import { supabase } from "@/lib/supabase";

type PaymentMethod = "momo" | "bank_transfer" | "vietqr";

type CheckoutState = {
  plan?: string;
  billingPeriod?: "monthly" | "biannual" | "annual";
};

const paymentOptions: { value: PaymentMethod; label: string }[] = [
  { value: "momo", label: "MoMo" },
  { value: "vietqr", label: "VietQR" },
  { value: "bank_transfer", label: "Chuyển khoản ngân hàng" },
];

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
  pack_10: { title: "Gói 10 deep credits", subtitle: "Mua thêm", amount: "130.000đ" },
  pack_30: { title: "Gói 30 deep credits", subtitle: "Mua thêm", amount: "350.000đ" },
  pack_50: { title: "Gói 50 deep credits", subtitle: "Mua thêm", amount: "550.000đ" },
};

function PaymentMethodIcon({ method }: { method: PaymentMethod }) {
  const config = {
    momo: { label: "MM", bg: "#fce4f0", color: "#a9135d" },
    vietqr: { label: "QR", bg: "#deeaff", color: "#0b3f99" },
    bank_transfer: { label: "Bank", bg: "#d4edda", color: "#2d7d46" },
  }[method];

  return (
    <div
      className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
      style={{ background: config.bg }}
    >
      <span className="text-[10px] font-bold" style={{ color: config.color }}>
        {config.label}
      </span>
    </div>
  );
}

export default function CheckoutScreen() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as CheckoutState | null;
  const plan = state?.plan;

  const defaultMethod = useMemo((): PaymentMethod => {
    const bp = state?.billingPeriod;
    if (bp === "annual" || bp === "biannual") return "bank_transfer";
    return "momo";
  }, [state?.billingPeriod]);

  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>(defaultMethod);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    setPaymentMethod(defaultMethod);
  }, [defaultMethod]);

  if (!plan || !ORDER_COPY[plan]) {
    return <Navigate to="/app/pricing" replace />;
  }

  const order = ORDER_COPY[plan];

  async function handlePay() {
    setSubmitError(null);
    setSubmitting(true);
    try {
      const { data, error } = await supabase.functions.invoke("create-payment", {
        body: { plan, payment_method: paymentMethod },
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
        window.location.href = checkoutUrl;
        return;
      }
      setSubmitError("Thanh toán không thành công — thử lại.");
      toast.error("Thanh toán không thành công — thử lại.");
    } catch {
      setSubmitError("Thanh toán không thành công — thử lại.");
      toast.error("Thanh toán không thành công — thử lại.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppLayout enableMobileSidebar>
      <div className="flex flex-col h-full bg-[var(--surface-alt)]">
        <div className="flex-1 overflow-y-auto pb-6">
          <div className="max-w-xl mx-auto p-4 lg:p-6 space-y-6">
            <button
              type="button"
              onClick={() => navigate("/app/pricing")}
              className="mt-14 lg:mt-0 text-sm text-[var(--muted)] hover:text-[var(--ink)] transition-colors duration-[120ms]"
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
                <p className="font-mono font-bold text-[var(--purple)] shrink-0" style={{ fontSize: "1.25rem" }}>
                  {order.amount}
                </p>
              </div>
            </div>

            <div>
              <h3 className="text-xs font-medium text-[var(--muted)] uppercase tracking-wide mb-3">
                Phương thức thanh toán
              </h3>
              <RadioGroup.Root
                value={paymentMethod}
                onValueChange={(v) => setPaymentMethod(v as PaymentMethod)}
              >
                <div className="space-y-2">
                  {paymentOptions.map(({ value, label }) => (
                    <RadioGroup.Item
                      key={value}
                      value={value}
                      className="w-full flex items-center gap-3 p-4 bg-[var(--surface)] border rounded-xl cursor-pointer transition-all duration-[120ms] data-[state=checked]:border-[var(--purple)] data-[state=checked]:bg-[var(--purple-light)] hover:border-[var(--border-active)]"
                    >
                      <div
                        className={`w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors duration-[120ms] ${
                          paymentMethod === value ? "border-[var(--purple)]" : "border-[var(--border)]"
                        }`}
                      >
                        {paymentMethod === value && <div className="w-2 h-2 rounded-full bg-[var(--purple)]" />}
                      </div>
                      <PaymentMethodIcon method={value} />
                      <span className="font-medium text-sm text-[var(--ink)]">{label}</span>
                    </RadioGroup.Item>
                  ))}
                </div>
              </RadioGroup.Root>
            </div>

            <Button
              fullWidth
              className="h-12 text-sm"
              onClick={() => void handlePay()}
              disabled={submitting}
            >
              {submitting ? (
                <span className="inline-flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  Đang xử lý...
                </span>
              ) : (
                "Thanh toán"
              )}
            </Button>
            {submitError ? <p className="text-sm text-destructive text-center">{submitError}</p> : null}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
