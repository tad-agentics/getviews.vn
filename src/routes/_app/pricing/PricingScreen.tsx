import { useState } from "react";
import { useNavigate } from "react-router";
import { motion, AnimatePresence } from "motion/react";
import { Check, Zap, Sparkles, Building2, Gift } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { pricingSavings } from "@/lib/mock-data";
import { useProfile } from "@/hooks/useProfile";
import { useSubscription } from "@/hooks/useSubscription";

type Period = "monthly" | "biannual" | "annual";

const plans = {
  monthly: [
    {
      name: "Free",
      priceDisplay: "Miễn phí",
      tagline: "Khám phá GetViews",
      icon: Gift,
      popular: false,
      cta: "Bắt đầu ngay",
      features: [
        "10 lần phân tích video (lifetime)",
        "Xem xu hướng cơ bản",
        "Chat AI không giới hạn",
        "Hỗ trợ qua email",
      ],
    },
    {
      name: "Starter",
      priceDisplay: "249.000đ",
      tagline: "Creator solo",
      icon: Zap,
      popular: true,
      cta: "Chọn gói",
      features: [
        "30 lần phân tích sâu / tháng",
        "Xu hướng không giới hạn",
        "Chat AI không giới hạn",
        "Corpus data 7 ngày gần nhất",
        "Hỗ trợ ưu tiên",
      ],
    },
    {
      name: "Pro",
      priceDisplay: "499.000đ",
      tagline: "Creator nghiêm túc",
      icon: Sparkles,
      popular: false,
      cta: "Nâng cấp Pro",
      features: [
        "80 lần phân tích sâu / tháng",
        "Xu hướng không giới hạn",
        "Corpus data 30 ngày gần nhất",
        "So sánh niche đa chiều",
        "Export báo cáo PDF",
        "Hỗ trợ ưu tiên cao",
      ],
    },
    {
      name: "Agency",
      priceDisplay: "1.490.000đ",
      tagline: "Đội nhóm & Agency",
      icon: Building2,
      popular: false,
      cta: "Liên hệ Agency",
      features: [
        "250 lần phân tích sâu / tháng",
        "Tối đa 10 tài khoản thành viên",
        "Tất cả tính năng Pro",
        "Corpus data realtime",
        "Dashboard quản lý team",
        "Hỗ trợ dedicated",
      ],
    },
  ],
  biannual: [
    {
      name: "Free",
      priceDisplay: "Miễn phí",
      tagline: "Khám phá GetViews",
      icon: Gift,
      popular: false,
      cta: "Bắt đầu ngay",
      features: [
        "10 lần phân tích video (lifetime)",
        "Xem xu hướng cơ bản",
        "Chat AI không giới hạn",
        "Hỗ trợ qua email",
      ],
    },
    {
      name: "Starter",
      priceDisplay: "199.000đ",
      tagline: "Creator solo",
      icon: Zap,
      popular: true,
      cta: "Chọn gói",
      features: [
        "30 lần phân tích sâu / tháng",
        "Xu hướng không giới hạn",
        "Chat AI không giới hạn",
        "Corpus data 7 ngày gần nhất",
        "Hỗ trợ ưu tiên",
      ],
    },
    {
      name: "Pro",
      priceDisplay: "449.000đ",
      tagline: "Creator nghiêm túc",
      icon: Sparkles,
      popular: false,
      cta: "Nâng cấp Pro",
      features: [
        "80 lần phân tích sâu / tháng",
        "Xu hướng không giới hạn",
        "Corpus data 30 ngày gần nhất",
        "So sánh niche đa chiều",
        "Export báo cáo PDF",
        "Hỗ trợ ưu tiên cao",
      ],
    },
    {
      name: "Agency",
      priceDisplay: "1.350.000đ",
      tagline: "Đội nhóm & Agency",
      icon: Building2,
      popular: false,
      cta: "Liên hệ Agency",
      features: [
        "250 lần phân tích sâu / tháng",
        "Tối đa 10 tài khoản thành viên",
        "Tất cả tính năng Pro",
        "Corpus data realtime",
        "Dashboard quản lý team",
        "Hỗ trợ dedicated",
      ],
    },
  ],
  annual: [
    {
      name: "Free",
      priceDisplay: "Miễn phí",
      tagline: "Khám phá GetViews",
      icon: Gift,
      popular: false,
      cta: "Bắt đầu ngay",
      features: [
        "10 lần phân tích video (lifetime)",
        "Xem xu hướng cơ bản",
        "Chat AI không giới hạn",
        "Hỗ trợ qua email",
      ],
    },
    {
      name: "Starter",
      priceDisplay: "199.000đ",
      tagline: "Creator solo",
      icon: Zap,
      popular: true,
      cta: "Chọn gói",
      features: [
        "30 lần phân tích sâu / tháng",
        "Xu hướng không giới hạn",
        "Chat AI không giới hạn",
        "Corpus data 7 ngày gần nhất",
        "Hỗ trợ ưu tiên",
      ],
    },
    {
      name: "Pro",
      priceDisplay: "399.000đ",
      tagline: "Creator nghiêm túc",
      icon: Sparkles,
      popular: false,
      cta: "Nâng cấp Pro",
      features: [
        "80 lần phân tích sâu / tháng",
        "Xu hướng không giới hạn",
        "Corpus data 30 ngày gần nhất",
        "So sánh niche đa chiều",
        "Export báo cáo PDF",
        "Hỗ trợ ưu tiên cao",
      ],
    },
    {
      name: "Agency",
      priceDisplay: "1.190.000đ",
      tagline: "Đội nhóm & Agency",
      icon: Building2,
      popular: false,
      cta: "Liên hệ Agency",
      features: [
        "250 lần phân tích sâu / tháng",
        "Tối đa 10 tài khoản thành viên",
        "Tất cả tính năng Pro",
        "Corpus data realtime",
        "Dashboard quản lý team",
        "Hỗ trợ dedicated",
      ],
    },
  ],
};

const periodLabels: Record<Period, string> = {
  monthly: "Tháng",
  biannual: "6 tháng",
  annual: "Năm",
};

const topupCopy = [
  { pack: "pack_10" as const, line: "10 lần phân tích sâu — 130.000đ (13.000đ/lần)", highlight: false },
  { pack: "pack_30" as const, line: "30 lần phân tích sâu — 350.000đ (11.700đ/lần)", highlight: false },
  { pack: "pack_50" as const, line: "50 lần phân tích sâu — 550.000đ (11.000đ/lần) · Phổ biến", highlight: true },
];

const paymentMethodsBase = [
  { label: "MoMo", color: "#a9135d", bg: "#fff0f7" },
  { label: "VNPay", color: "#0b3f99", bg: "#eef3ff" },
  { label: "ZaloPay", color: "#006af5", bg: "#e8f1ff" },
  { label: "Visa", color: "#1a1f71", bg: "#eeeffe" },
  { label: "Bank", color: "#2d7d46", bg: "#edf7f1" },
];

const zaloPayEnabled = import.meta.env.VITE_ZALOPAY_ENABLED === "true";

function PeriodToggle({ value, onChange }: { value: Period; onChange: (p: Period) => void }) {
  const periods: Period[] = ["monthly", "biannual", "annual"];
  return (
    <div className="inline-flex bg-[var(--surface)] border border-[var(--border)] rounded-xl p-1 relative">
      {periods.map((p) => (
        <button
          key={p}
          type="button"
          onClick={() => onChange(p)}
          className={`relative px-4 py-2 rounded-lg text-sm transition-colors duration-[120ms] z-10 ${
            value === p ? "text-white font-semibold" : "text-[var(--ink-soft)] hover:text-[var(--ink)]"
          }`}
        >
          {value === p && (
            <motion.div
              layoutId="period-pill"
              className="absolute inset-0 rounded-lg"
              style={{ background: "var(--gradient-primary)" }}
              transition={{ type: "spring", stiffness: 400, damping: 30 }}
            />
          )}
          <span className="relative z-10 flex items-center gap-1.5">
            {periodLabels[p]}
            {p === "annual" && value !== "annual" && (
              <span className="text-[9px] font-mono bg-[var(--purple)]/15 text-[var(--purple)] px-1.5 py-0.5 rounded-full">
                -20%
              </span>
            )}
          </span>
        </button>
      ))}
    </div>
  );
}

function starterPriceVerbatim(period: Period): string {
  if (period === "monthly") return "249.000đ/tháng";
  if (period === "biannual") return "199.000đ/tháng · thanh toán 6 tháng";
  return "199.000đ/tháng · thanh toán cả năm";
}

type SubRow = {
  tier: string;
  billing_period: string;
} | null;

function isStarterCurrentPeriod(sub: SubRow, period: Period): boolean {
  if (!sub || sub.tier !== "starter") return false;
  const bp = sub.billing_period;
  if (period === "monthly" && bp === "monthly") return true;
  if (period === "biannual" && bp === "biannual") return true;
  if (period === "annual" && bp === "annual") return true;
  return false;
}

function PlanCard({
  plan,
  period,
  index,
  subscription,
}: {
  plan: (typeof plans.monthly)[number];
  period: Period;
  index: number;
  subscription: SubRow;
}) {
  const navigate = useNavigate();
  const Icon = plan.icon;
  const isFree = plan.name === "Free";
  const isStarter = plan.name === "Starter";
  const starterLine = isStarter ? starterPriceVerbatim(period) : "";
  const showCurrentBadge = isStarter && isStarterCurrentPeriod(subscription, period);

  const goCheckoutStarter = () => {
    const planKey =
      period === "monthly" ? "starter_monthly" : period === "biannual" ? "starter_biannual" : "starter_annual";
    navigate("/app/checkout", { state: { plan: planKey, billingPeriod: period } });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: index * 0.06, ease: "easeOut" }}
      className={`relative rounded-xl overflow-hidden flex flex-col ${
        plan.popular ? "border-2 border-[var(--purple)] shadow-lg" : "border border-[var(--border)]"
      } bg-[var(--surface)]`}
    >
      {plan.popular && (
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: "var(--gradient-purple-wash)" }}
        />
      )}
      {plan.popular && (
        <div className="absolute top-0 right-4">
          <div
            className="px-3 py-1 text-white font-semibold rounded-b-lg"
            style={{ background: "var(--gradient-primary)", fontSize: "11px" }}
          >
            Phổ biến nhất
          </div>
        </div>
      )}
      {showCurrentBadge && (
        <div className="absolute top-0 left-4 z-20">
          <div
            className="px-2 py-1 text-white font-semibold rounded-b-lg"
            style={{ background: "var(--gradient-primary)", fontSize: "10px" }}
          >
            Gói hiện tại
          </div>
        </div>
      )}

      <div className="relative z-10 p-5 flex flex-col flex-1">
        <div className="flex items-start gap-3 mb-4">
          <div
            className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
              plan.popular ? "text-white" : "bg-[var(--surface-alt)] text-[var(--muted)]"
            }`}
            style={plan.popular ? { background: "var(--gradient-primary)" } : {}}
          >
            <Icon className="w-4 h-4" strokeWidth={1.8} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-extrabold text-[var(--ink)] text-sm">{plan.name}</p>
            <p className="text-xs text-[var(--muted)]">{plan.tagline}</p>
          </div>
        </div>

        <div className="mb-5">
          {isFree ? (
            <p className="font-extrabold text-[var(--ink)] font-mono" style={{ fontSize: "1.5rem" }}>
              Miễn phí
            </p>
          ) : isStarter ? (
            <p
              className={`font-extrabold font-mono ${plan.popular ? "gradient-text" : "text-[var(--ink)]"}`}
              style={{ fontSize: "1rem", lineHeight: 1.35 }}
            >
              {starterLine}
            </p>
          ) : (
            <div className="flex items-baseline gap-1">
              <p
                className={`font-extrabold font-mono ${plan.popular ? "gradient-text" : "text-[var(--ink)]"}`}
                style={{ fontSize: "1.5rem" }}
              >
                {plan.priceDisplay}
              </p>
              <span className="text-xs text-[var(--muted)]">/tháng</span>
            </div>
          )}
          {!isFree && !isStarter && period !== "monthly" && (
            <p className="text-[11px] text-[var(--muted)] mt-0.5 font-mono">
              Thanh toán {period === "biannual" ? "6 tháng" : "1 năm"} một lần
            </p>
          )}
        </div>

        <ul className="space-y-2 mb-5 flex-1">
          {plan.features.map((feat) => (
            <li key={feat} className="flex items-start gap-2">
              <span
                className={`w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
                  plan.popular ? "text-white" : "bg-[var(--surface-alt)] text-[var(--muted)]"
                }`}
                style={plan.popular ? { background: "var(--gradient-primary)" } : {}}
              >
                <Check className="w-2.5 h-2.5" strokeWidth={2.5} />
              </span>
              <span className="text-xs text-[var(--ink-soft)]">{feat}</span>
            </li>
          ))}
        </ul>

        {isFree ? (
          <button
            type="button"
            onClick={() => navigate("/app")}
            className="w-full py-2.5 rounded-lg border border-[var(--border)] text-sm text-[var(--ink-soft)] font-semibold hover:bg-[var(--surface-alt)] hover:text-[var(--ink)] transition-colors duration-[120ms]"
          >
            {plan.cta}
          </button>
        ) : isStarter ? (
          plan.popular ? (
            <button
              type="button"
              onClick={goCheckoutStarter}
              className="w-full py-2.5 rounded-lg text-sm text-white font-semibold transition-opacity duration-[120ms] hover:opacity-90"
              style={{ background: "var(--gradient-primary)" }}
            >
              {plan.cta}
            </button>
          ) : (
            <button
              type="button"
              onClick={goCheckoutStarter}
              className="w-full py-2.5 rounded-lg border border-[var(--purple)]/40 text-sm text-[var(--purple)] font-semibold hover:bg-[var(--purple)]/5 transition-colors duration-[120ms]"
            >
              {plan.cta}
            </button>
          )
        ) : (
          <button
            type="button"
            disabled
            title="Gói đang được cập nhật"
            className="w-full py-2.5 rounded-lg border border-[var(--border)] text-sm text-[var(--muted)] font-semibold opacity-60 cursor-not-allowed"
          >
            {plan.cta}
          </button>
        )}
      </div>
    </motion.div>
  );
}

function PricingSkeleton() {
  return (
    <div className="flex-1 overflow-y-auto animate-pulse" style={{ scrollbarWidth: "thin" }}>
      <div className="max-w-2xl mx-auto px-4 lg:px-6 pt-14 lg:pt-6 pb-8">
        <div className="h-8 w-48 mx-auto rounded-lg bg-[var(--border)] mb-2" />
        <div className="h-4 w-64 mx-auto rounded bg-[var(--border)] mb-6" />
        <div className="mb-6 h-20 rounded-xl bg-[var(--border)]" />
        <div className="flex justify-center mb-4 h-10 w-64 mx-auto rounded-xl bg-[var(--border)]" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-64 rounded-xl bg-[var(--border)]" />
          ))}
        </div>
      </div>
    </div>
  );
}

function PricingContent() {
  const navigate = useNavigate();
  const [period, setPeriod] = useState<Period>("annual");
  const currentPlans = plans[period];
  const savingsMsg = pricingSavings[period];
  const { data: profile, isPending: profileLoading } = useProfile();
  const { data: subscription } = useSubscription();

  const paymentMethods = paymentMethodsBase.filter((pm) => (pm.label === "ZaloPay" ? zaloPayEnabled : true));

  const subRow: SubRow = subscription
    ? { tier: String(subscription.tier), billing_period: String(subscription.billing_period) }
    : null;

  const cap = (profile as { deep_credits_total?: number } | null)?.deep_credits_total ?? 50;
  const remaining = profile?.deep_credits_remaining ?? 0;

  if (profileLoading) {
    return <PricingSkeleton />;
  }

  return (
    <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
      <div className="max-w-2xl mx-auto px-4 lg:px-6 pt-14 lg:pt-6 pb-8">
        <div className="text-center mb-6">
          <h1 className="font-extrabold text-[var(--ink)] mb-1" style={{ fontSize: "1.5rem" }}>
            Chọn gói phù hợp
          </h1>
          <p className="text-sm text-[var(--muted)]">Không ràng buộc hợp đồng · Huỷ bất cứ lúc nào</p>
        </div>

        <div className="mb-6 bg-[var(--surface)] border border-[var(--border)] rounded-xl px-4 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div
              className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-white"
              style={{ background: "var(--gradient-primary)" }}
            >
              <Zap className="w-3.5 h-3.5" strokeWidth={2} />
            </div>
            <div>
              <p className="text-xs text-[var(--muted)]">Credits còn lại</p>
              <p className="font-extrabold font-mono text-[var(--ink)] text-sm">
                {remaining}
                <span className="font-normal text-[var(--muted)]"> / {cap}</span>
              </p>
            </div>
          </div>
          <div className="flex-1 max-w-32">
            <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.min(100, Math.round((remaining / Math.max(cap, 1)) * 100))}%`,
                  background: "var(--gradient-primary)",
                }}
              />
            </div>
          </div>
        </div>

        <div className="flex justify-center mb-2">
          <PeriodToggle value={period} onChange={setPeriod} />
        </div>

        <div className="h-8 flex items-center justify-center mb-4">
          <AnimatePresence mode="wait">
            {savingsMsg ? (
              <motion.p
                key={period}
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 4 }}
                transition={{ duration: 0.15 }}
                className="text-xs font-semibold text-[var(--purple)] text-center"
              >
                ✦ {savingsMsg}
              </motion.p>
            ) : (
              <motion.span key="empty" initial={{ opacity: 0 }} animate={{ opacity: 0 }} />
            )}
          </AnimatePresence>
        </div>

        <AnimatePresence mode="wait">
          <div key={period} className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8">
            {currentPlans.map((plan, i) => (
              <PlanCard key={plan.name} plan={plan} period={period} index={i} subscription={subRow} />
            ))}
          </div>
        </AnimatePresence>

        <div className="border-t border-[var(--border)] mb-6" />

        <div className="mb-6">
          <p className="text-xs font-semibold uppercase tracking-widest text-[var(--faint)] mb-3">Mua thêm credits</p>
          <div className="grid grid-cols-3 gap-2">
            {topupCopy.map((pack) => (
              <button
                key={pack.pack}
                type="button"
                onClick={() => navigate("/app/checkout", { state: { plan: pack.pack } })}
                className={`relative flex flex-col items-center justify-center text-center p-4 rounded-xl border transition-all duration-[120ms] ${
                  pack.highlight
                    ? "border-[var(--purple)] bg-[var(--surface)]"
                    : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--border-active)]"
                }`}
              >
                {pack.highlight && (
                  <span
                    className="absolute -top-2.5 left-1/2 -translate-x-1/2 text-white px-2 py-0.5 rounded-full font-semibold whitespace-nowrap"
                    style={{ background: "var(--gradient-primary)", fontSize: "9px" }}
                  >
                    Phổ biến
                  </span>
                )}
                <p className="text-[10px] sm:text-xs text-[var(--ink-soft)] leading-snug px-0.5 sm:px-1">
                  {pack.line}
                </p>
              </button>
            ))}
          </div>
        </div>

        <div>
          <p className="text-[11px] text-[var(--faint)] mb-2">Thanh toán qua</p>
          <div className="flex flex-wrap gap-2">
            {paymentMethods.map((pm) => (
              <div
                key={pm.label}
                className="px-3 py-1.5 rounded-lg border border-[var(--border)] flex items-center justify-center"
                style={{ background: pm.bg, minWidth: 56 }}
              >
                <span className="font-bold text-xs" style={{ color: pm.color }}>
                  {pm.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function PricingScreen() {
  return (
    <AppLayout enableMobileSidebar>
      <PricingContent />
    </AppLayout>
  );
}
