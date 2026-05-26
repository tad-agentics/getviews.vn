import { useState } from "react";
import { useNavigate } from "react-router";
import { motion, AnimatePresence } from "motion/react";
import { Check, Zap, Sparkles, Building2, Gift } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { MobileShellStandalone } from "@/components/MobileShellStandalone";
import { Btn } from "@/components/v2/Btn";
import { env } from "@/lib/env";
import { pricingSavings } from "@/lib/mock-data";
import { useProfile } from "@/hooks/useProfile";
import { useSubscription } from "@/hooks/useSubscription";

type Period = "monthly" | "biannual" | "annual";

const plans = {
  monthly: [
    {
      name: "Free",
      priceDisplay: "Miễn phí",
      tagline: "Trải nghiệm GetViews",
      icon: Gift,
      popular: false,
      cta: "Bắt đầu miễn phí",
      features: [
        "10 lượt phân tích chuyên sâu",
        "Xem ý tưởng & xu hướng cơ bản",
        "Tư vấn chatbot AI không giới hạn",
        "Hỗ trợ qua email nhanh chóng",
      ],
    },
    {
      name: "Starter",
      priceDisplay: "249.000đ",
      tagline: "Nhà sáng tạo tự do",
      icon: Zap,
      popular: true,
      cta: "Chọn gói Starter",
      features: [
        "30 lượt phân tích chuyên sâu/tháng",
        "Xem đầy đủ bảng xếp hạng xu hướng",
        "Tư vấn chatbot AI không giới hạn",
        "Thư viện video TikTok 7 ngày gần nhất",
        "Hỗ trợ kỹ thuật ưu tiên",
      ],
    },
    {
      name: "Pro",
      priceDisplay: "499.000đ",
      tagline: "Nhà sáng tạo chuyên nghiệp",
      icon: Sparkles,
      popular: false,
      cta: "Đăng ký Pro",
      features: [
        "80 lượt phân tích chuyên sâu/tháng",
        "Xem đầy đủ bảng xếp hạng xu hướng",
        "Thư viện video TikTok 30 ngày gần nhất",
        "So sánh đối chiếu ngách đa chiều",
        "Hỗ trợ kỹ thuật ưu tiên cao",
      ],
    },
    {
      name: "Agency",
      priceDisplay: "1.490.000đ",
      tagline: "Doanh nghiệp & Đội nhóm",
      icon: Building2,
      popular: false,
      cta: "Liên hệ Agency",
      features: [
        "250 lượt phân tích chuyên sâu/tháng",
        "Hỗ trợ tối đa 10 tài khoản thành viên",
        "Bao gồm toàn bộ đặc quyền gói Pro",
        "Dữ liệu TikTok cập nhật liên tục",
        "Trang tổng quan quản lý nhóm",
        "Hỗ trợ kỹ thuật riêng biệt 24/7",
      ],
    },
  ],
  biannual: [
    {
      name: "Free",
      priceDisplay: "Miễn phí",
      tagline: "Trải nghiệm GetViews",
      icon: Gift,
      popular: false,
      cta: "Bắt đầu miễn phí",
      features: [
        "10 lượt phân tích chuyên sâu",
        "Xem ý tưởng & xu hướng cơ bản",
        "Tư vấn chatbot AI không giới hạn",
        "Hỗ trợ qua email nhanh chóng",
      ],
    },
    {
      name: "Starter",
      priceDisplay: "199.000đ",
      tagline: "Nhà sáng tạo tự do",
      icon: Zap,
      popular: true,
      cta: "Chọn gói Starter",
      features: [
        "30 lượt phân tích chuyên sâu/tháng",
        "Xem đầy đủ bảng xếp hạng xu hướng",
        "Tư vấn chatbot AI không giới hạn",
        "Thư viện video TikTok 7 ngày gần nhất",
        "Hỗ trợ kỹ thuật ưu tiên",
      ],
    },
    {
      name: "Pro",
      priceDisplay: "449.000đ",
      tagline: "Nhà sáng tạo chuyên nghiệp",
      icon: Sparkles,
      popular: false,
      cta: "Đăng ký Pro",
      features: [
        "80 lượt phân tích chuyên sâu/tháng",
        "Xem đầy đủ bảng xếp hạng xu hướng",
        "Thư viện video TikTok 30 ngày gần nhất",
        "So sánh đối chiếu ngách đa chiều",
        "Hỗ trợ kỹ thuật ưu tiên cao",
      ],
    },
    {
      name: "Agency",
      priceDisplay: "1.350.000đ",
      tagline: "Doanh nghiệp & Đội nhóm",
      icon: Building2,
      popular: false,
      cta: "Liên hệ Agency",
      features: [
        "250 lượt phân tích chuyên sâu/tháng",
        "Hỗ trợ tối đa 10 tài khoản thành viên",
        "Bao gồm toàn bộ đặc quyền gói Pro",
        "Dữ liệu TikTok cập nhật liên tục",
        "Trang tổng quan quản lý nhóm",
        "Hỗ trợ kỹ thuật riêng biệt 24/7",
      ],
    },
  ],
  annual: [
    {
      name: "Free",
      priceDisplay: "Miễn phí",
      tagline: "Trải nghiệm GetViews",
      icon: Gift,
      popular: false,
      cta: "Bắt đầu miễn phí",
      features: [
        "10 lượt phân tích chuyên sâu",
        "Xem ý tưởng & xu hướng cơ bản",
        "Tư vấn chatbot AI không giới hạn",
        "Hỗ trợ qua email nhanh chóng",
      ],
    },
    {
      name: "Starter",
      priceDisplay: "199.000đ",
      tagline: "Nhà sáng tạo tự do",
      icon: Zap,
      popular: true,
      cta: "Chọn gói Starter",
      features: [
        "30 lượt phân tích chuyên sâu/tháng",
        "Xem đầy đủ bảng xếp hạng xu hướng",
        "Tư vấn chatbot AI không giới hạn",
        "Thư viện video TikTok 7 ngày gần nhất",
        "Hỗ trợ kỹ thuật ưu tiên",
      ],
    },
    {
      name: "Pro",
      priceDisplay: "399.000đ",
      tagline: "Nhà sáng tạo chuyên nghiệp",
      icon: Sparkles,
      popular: false,
      cta: "Đăng ký Pro",
      features: [
        "80 lượt phân tích chuyên sâu/tháng",
        "Xem đầy đủ bảng xếp hạng xu hướng",
        "Thư viện video TikTok 30 ngày gần nhất",
        "So sánh đối chiếu ngách đa chiều",
        "Hỗ trợ kỹ thuật ưu tiên cao",
      ],
    },
    {
      name: "Agency",
      priceDisplay: "1.190.000đ",
      tagline: "Doanh nghiệp & Đội nhóm",
      icon: Building2,
      popular: false,
      cta: "Liên hệ Agency",
      features: [
        "250 lượt phân tích chuyên sâu/tháng",
        "Hỗ trợ tối đa 10 tài khoản thành viên",
        "Bao gồm toàn bộ đặc quyền gói Pro",
        "Dữ liệu TikTok cập nhật liên tục",
        "Trang tổng quan quản lý nhóm",
        "Hỗ trợ kỹ thuật riêng biệt 24/7",
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
  { pack: "pack_10" as const, line: "10 phân tích — 130.000đ (13.000đ/lần)", highlight: false },
  { pack: "pack_30" as const, line: "30 phân tích — 350.000đ (11.700đ/lần)", highlight: false },
  { pack: "pack_50" as const, line: "50 phân tích — 550.000đ (11.000đ/lần) · Phổ biến", highlight: true },
];

const paymentMethodLabels = ["MoMo", "VNPay", "ZaloPay", "Visa", "Bank"] as const;

const zaloPayEnabled = env.VITE_ZALOPAY_ENABLED;

function PeriodToggle({ value, onChange }: { value: Period; onChange: (p: Period) => void }) {
  const periods: Period[] = ["monthly", "biannual", "annual"];
  return (
    <div className="inline-flex rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-1">
      {periods.map((p) => (
        <button
          key={p}
          type="button"
          onClick={() => onChange(p)}
          className={`relative min-h-[44px] rounded-md px-5 py-2 text-sm font-medium transition-colors duration-[120ms] ${
            value === p
              ? "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
              : "text-[color:var(--gv-ink-3)] hover:text-[color:var(--gv-ink)]"
          }`}
        >
          {periodLabels[p]}
          {p === "annual" && value !== "annual" ? (
            <span className="absolute -top-2 -right-2 whitespace-nowrap rounded-full bg-[color:var(--gv-ink)] px-1.5 py-0.5 text-[11px] font-medium text-white">
              Tiết kiệm 20%
            </span>
          ) : null}
        </button>
      ))}
    </div>
  );
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
  userTier,
}: {
  plan: (typeof plans.monthly)[number];
  period: Period;
  index: number;
  subscription: SubRow;
  userTier: string;
}) {
  const navigate = useNavigate();
  const Icon = plan.icon;
  const isFree = plan.name === "Free";
  const isStarter = plan.name === "Starter";
  const showCurrentBadge =
    (isFree && userTier === "free" && !subscription) ||
    (isStarter && isStarterCurrentPeriod(subscription, period));

  const goCheckoutStarter = () => {
    const planKey =
      period === "monthly" ? "starter_monthly" : period === "biannual" ? "starter_biannual" : "starter_annual";
    navigate("/app/checkout", { state: { plan: planKey, billingPeriod: period } });
  };

  const subtextPrice = () => {
    if (isFree) return "";
    if (period === "monthly") return "Gia hạn hàng tháng";
    if (isStarter) {
      if (period === "biannual") return "Thanh toán 1.194.000đ mỗi 6 tháng";
      return "Thanh toán 2.388.000đ mỗi năm";
    }
    if (plan.name === "Pro") {
      if (period === "biannual") return "Thanh toán 2.694.000đ mỗi 6 tháng";
      return "Thanh toán 4.788.000đ mỗi năm";
    }
    if (plan.name === "Agency") {
      if (period === "biannual") return "Thanh toán 8.100.000đ mỗi 6 tháng";
      return "Thanh toán 14.280.000đ mỗi năm";
    }
    return "";
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: index * 0.06, ease: [0.16, 1, 0.3, 1] }}
      className={`relative flex flex-col rounded-xl border bg-[color:var(--gv-paper)] p-5 transition-colors duration-[120ms] ${
        plan.popular
          ? "border-2 border-[color:var(--gv-ink)]"
          : "border-[color:var(--gv-rule)] hover:border-[color:var(--gv-ink-3)]"
      }`}
    >
      {plan.popular ? (
        <div className="absolute -top-3 left-1/2 z-10 -translate-x-1/2">
          <span className="rounded-full bg-[color:var(--gv-ink)] px-3 py-1 text-xs font-medium text-white">
            Phổ biến nhất
          </span>
        </div>
      ) : null}
      {showCurrentBadge ? (
        <div className="absolute -top-3 right-4 z-10">
          <span className="rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-2.5 py-1 text-[11px] font-medium text-[color:var(--gv-ink-2)]">
            Gói hiện tại
          </span>
        </div>
      ) : null}

      <div className="flex flex-1 flex-col pt-1">
        <div className="mb-4 flex items-start gap-3">
          <div
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
              plan.popular
                ? "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
                : "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-3)]"
            }`}
          >
            <Icon className="h-4 w-4" strokeWidth={2} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-base font-bold leading-none text-[color:var(--gv-ink)]">{plan.name}</p>
            <p className="mt-0.5 text-xs leading-tight text-[color:var(--gv-ink-3)]">{plan.tagline}</p>
          </div>
        </div>

        <div className="mb-4 flex min-h-[52px] flex-col justify-center">
          {isFree ? (
            <p className="font-mono text-2xl font-bold text-[color:var(--gv-ink)]">Miễn phí</p>
          ) : (
            <div className="flex items-baseline gap-1">
              <p className="font-mono text-[1.75rem] font-bold leading-none text-[color:var(--gv-ink)]">
                {plan.priceDisplay}
              </p>
              <span className="text-xs font-medium text-[color:var(--gv-ink-3)]">/tháng</span>
            </div>
          )}
          {!isFree ? (
            <p className="mt-1 font-mono text-[10px] font-medium uppercase tracking-wider text-[color:var(--gv-ink-4)]">
              {subtextPrice()}
            </p>
          ) : null}
        </div>

        <ul className="mb-5 flex-1 space-y-2">
          {plan.features.map((feat) => (
            <li key={feat} className="flex items-start gap-2">
              <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-3)]">
                <Check className="h-2.5 w-2.5" strokeWidth={2.5} />
              </span>
              <span className="text-xs leading-relaxed text-[color:var(--gv-ink-3)]">{feat}</span>
            </li>
          ))}
        </ul>

        {isFree ? (
          <Btn
            variant="ghost"
            className="w-full"
            disabled={showCurrentBadge}
            onClick={() => navigate("/app")}
          >
            {showCurrentBadge ? "Gói hiện tại" : plan.cta}
          </Btn>
        ) : isStarter ? (
          <Btn
            variant={plan.popular ? "accent" : "ghost"}
            className="w-full"
            disabled={showCurrentBadge}
            onClick={goCheckoutStarter}
          >
            {showCurrentBadge ? "Gói hiện tại" : plan.cta}
          </Btn>
        ) : (
          <Btn
            variant="ghost"
            disabled
            className="w-full"
            title="Gói dịch vụ đang được cập nhật — Hãy chọn gói Starter để sử dụng đầy đủ tính năng"
          >
            Gói sắp ra mắt
          </Btn>
        )}
      </div>
    </motion.div>
  );
}

function PricingSkeleton() {
  return (
    <div className="w-full animate-pulse space-y-6">
      <div className="h-4 w-64 rounded bg-[color:var(--gv-canvas-2)]" />
      <div className="h-20 rounded-lg bg-[color:var(--gv-canvas-2)]" />
      <div className="mx-auto h-10 w-64 rounded-lg bg-[color:var(--gv-canvas-2)]" />
      <div className="grid grid-cols-1 gap-4 min-[700px]:grid-cols-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-64 rounded-xl bg-[color:var(--gv-canvas-2)]" />
        ))}
      </div>
    </div>
  );
}

export type PricingContentProps = {
  /** Render inside Settings billing tab — tighter top spacing, optional back control. */
  embedded?: boolean;
  onBack?: () => void;
};

export function PricingContent({ embedded = false, onBack }: PricingContentProps = {}) {
  const navigate = useNavigate();
  const [period, setPeriod] = useState<Period>("annual");
  const currentPlans = plans[period];
  const savingsMsg = pricingSavings[period];
  const { data: profile, isPending: profileLoading } = useProfile();
  const { data: subscription } = useSubscription();

  const paymentMethods = paymentMethodLabels.filter((label) => (label === "ZaloPay" ? zaloPayEnabled : true));

  const userTier = profile?.subscription_tier ?? "free";
  const subRow: SubRow = subscription
    ? { tier: String(subscription.tier), billing_period: String(subscription.billing_period) }
    : null;

  const cap = (profile as { credits_total?: number } | null)?.credits_total ?? 50;
  const remaining = profile?.credits_remaining ?? 0;

  if (profileLoading) {
    return <PricingSkeleton />;
  }

  return (
    <div className={embedded ? "w-full" : "flex-1 overflow-y-auto"} style={{ scrollbarWidth: "thin" }}>
      <div className={`max-w-4xl mx-auto px-0 sm:px-2 pb-8 ${embedded ? "pt-0" : "px-4 lg:px-6 pt-14 lg:pt-6"}`}>
        {onBack ? (
          <button
            type="button"
            onClick={onBack}
            className="mb-6 min-h-[44px] text-sm font-medium text-[color:var(--gv-ink-2)] transition-colors duration-[120ms] hover:text-[color:var(--gv-ink)]"
          >
            ← Quay lại gói & giao dịch
          </button>
        ) : null}

        {embedded ? (
          <p className="mb-6 text-sm text-[color:var(--gv-ink-3)]">
            Thanh toán qua MoMo, VNPay, chuyển khoản hoặc thẻ quốc tế. Không ràng buộc hợp đồng.
          </p>
        ) : (
          <div className="mb-10 text-center">
            <p className="gv-kicker mb-1 text-[color:var(--gv-ink-3)]">Bảng giá dịch vụ</p>
            <h1 className="gv-tight mb-2 text-[clamp(24px,4vw,32px)] font-bold leading-tight text-[color:var(--gv-ink)]">
              Lựa chọn gói phân tích phù hợp
            </h1>
            <p className="text-sm text-[color:var(--gv-ink-3)]">
              Thanh toán qua MoMo, VNPay, chuyển khoản hoặc thẻ quốc tế.
            </p>
          </div>
        )}

        <div className="mb-8 overflow-hidden rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
          <p className="gv-kicker mb-3 text-[color:var(--gv-ink-3)]">Lượt phân tích còn lại</p>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)]">
                <Zap className="h-4 w-4 text-[color:var(--gv-ink-2)]" strokeWidth={2} />
              </div>
              <p className="font-mono text-sm font-bold text-[color:var(--gv-ink)]">
                {remaining}
                <span className="font-normal text-[color:var(--gv-ink-4)]"> / {cap}</span>
              </p>
            </div>
            <div className="h-2 min-w-[128px] flex-1 max-w-[200px] overflow-hidden rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)]">
              <div
                className="h-full rounded-full bg-[color:var(--gv-accent)] transition-[width] duration-[400ms] ease-[cubic-bezier(0.16,1,0.3,1)]"
                style={{ width: `${Math.min(100, Math.round((remaining / Math.max(cap, 1)) * 100))}%` }}
              />
            </div>
          </div>
        </div>

        <div className="flex justify-center mb-2">
          <PeriodToggle value={period} onChange={setPeriod} />
        </div>

        <div className="mb-6 flex h-6 items-center justify-center">
          <AnimatePresence mode="wait">
            {savingsMsg ? (
              <motion.p
                key={period}
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 4 }}
                transition={{ duration: 0.15 }}
                className="text-center text-sm text-[color:var(--gv-ink-3)]"
              >
                {savingsMsg}
              </motion.p>
            ) : (
              <motion.span key="empty" initial={{ opacity: 0 }} animate={{ opacity: 0 }} />
            )}
          </AnimatePresence>
        </div>

        <AnimatePresence mode="wait">
          <div key={period} className="mb-10 grid grid-cols-1 gap-4 min-[700px]:grid-cols-2">
            {currentPlans.map((plan, i) => (
              <PlanCard
                key={plan.name}
                plan={plan}
                period={period}
                index={i}
                subscription={subRow}
                userTier={userTier}
              />
            ))}
          </div>
        </AnimatePresence>

        <hr className="mb-8 border-0 border-t border-[color:var(--gv-rule)]" />

        <div className="mb-10">
          <p className="gv-kicker mb-1 text-[color:var(--gv-ink-3)]">Mua thêm lượt phân tích</p>
          <h2 className="gv-tight mb-0.5 text-lg font-bold text-[color:var(--gv-ink)]">
            Mua thêm theo lượt (không gia hạn)
          </h2>
          <p className="mb-4 text-xs text-[color:var(--gv-ink-3)]">
            Dành cho creator cần phân tích gấp — lượt dùng không hết hạn theo chu kỳ gói.
          </p>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {topupCopy.map((pack) => {
              const count = pack.pack === "pack_10" ? 10 : pack.pack === "pack_30" ? 30 : 50;
              const price = pack.pack === "pack_10" ? "130.000đ" : pack.pack === "pack_30" ? "350.000đ" : "550.000đ";
              const perUnit =
                pack.pack === "pack_10" ? "13.000đ/lần" : pack.pack === "pack_30" ? "11.600đ/lần" : "11.000đ/lần";

              return (
                <button
                  key={pack.pack}
                  type="button"
                  onClick={() => navigate("/app/checkout", { state: { plan: pack.pack } })}
                  className={`group relative flex min-h-[44px] flex-col rounded-lg border bg-[color:var(--gv-paper)] p-5 text-center transition-colors duration-[120ms] ${
                    pack.highlight
                      ? "border-2 border-[color:var(--gv-ink)]"
                      : "border-[color:var(--gv-rule)] hover:border-[color:var(--gv-ink-3)]"
                  }`}
                >
                  {pack.highlight ? (
                    <span className="absolute -top-2.5 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-full bg-[color:var(--gv-ink)] px-2.5 py-0.5 text-[11px] font-medium text-white">
                      Phổ biến nhất
                    </span>
                  ) : null}
                  <p className="mb-2 font-mono text-lg font-bold text-[color:var(--gv-ink)]">
                    +{count} <span className="text-xs font-normal text-[color:var(--gv-ink-3)]">lượt</span>
                  </p>
                  <p className="font-mono text-sm font-bold text-[color:var(--gv-ink)]">{price}</p>
                  <p className="mt-0.5 font-mono text-[10px] text-[color:var(--gv-ink-4)]">{perUnit}</p>
                  <p className="mt-4 border-t border-[color:var(--gv-rule)] pt-3 text-[11px] font-semibold text-[color:var(--gv-ink-3)] group-hover:text-[color:var(--gv-ink)]">
                    Mua ngay
                  </p>
                </button>
              );
            })}
          </div>
        </div>

        <div className="border-t border-[color:var(--gv-rule)] pt-6">
          <p className="gv-kicker mb-3 text-[color:var(--gv-ink-3)]">Phương thức thanh toán</p>
          <div className="flex flex-wrap gap-2">
            {paymentMethods.map((label) => (
              <div
                key={label}
                className="flex min-w-[64px] items-center justify-center rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-4 py-2"
              >
                <span className="font-mono text-xs font-semibold tracking-wide text-[color:var(--gv-ink-2)]">
                  {label}
                </span>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs leading-relaxed text-[color:var(--gv-ink-4)]">
            Cổng thanh toán PayOS — lượt phân tích được cộng ngay sau khi giao dịch thành công.
          </p>
        </div>
      </div>
    </div>
  );
}

export default function PricingScreen() {
  return (
    <AppLayout enableMobileSidebar>
      <MobileShellStandalone />
      <PricingContent />
    </AppLayout>
  );
}
