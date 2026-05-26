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

const paymentMethodsBase = [
  { label: "MoMo", color: "#a9135d", bg: "#fff0f7" },
  { label: "VNPay", color: "#0b3f99", bg: "#eef3ff" },
  { label: "ZaloPay", color: "#006af5", bg: "#e8f1ff" },
  { label: "Visa", color: "#1a1f71", bg: "#eeeffe" },
  { label: "Bank", color: "#2d7d46", bg: "#edf7f1" },
];

const zaloPayEnabled = env.VITE_ZALOPAY_ENABLED;

function PeriodToggle({ value, onChange }: { value: Period; onChange: (p: Period) => void }) {
  const periods: Period[] = ["monthly", "biannual", "annual"];
  return (
    <div className="inline-flex bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-[12px] p-1 relative shadow-sm">
      {periods.map((p) => (
        <button
          key={p}
          type="button"
          onClick={() => onChange(p)}
          className={`relative px-5 py-2 min-h-[44px] rounded-[8px] text-xs font-semibold tracking-wide uppercase transition-colors duration-[120ms] z-10 cursor-pointer ${
            value === p ? "text-white font-bold" : "text-[color:var(--gv-ink-3)] hover:text-[color:var(--gv-ink)]"
          }`}
        >
          {value === p && (
            <motion.div
              layoutId="period-pill"
              className="absolute inset-0 rounded-[8px]"
              style={{ background: "var(--gradient-primary)" }}
              transition={{ type: "tween", ease: [0.2, 0.8, 0.2, 1], duration: 0.24 }}
            />
          )}
          <span className="relative z-10 flex items-center gap-1.5">
            {periodLabels[p]}
            {p === "annual" && value !== "annual" && (
              <span className="gv-mono text-[9px] font-bold bg-[color:var(--gv-accent)]/15 text-[color:var(--gv-accent)] px-1.5 py-0.5 rounded-full leading-none tracking-normal normal-case">
                Tiết kiệm 20%
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
  const showCurrentBadge = isStarter && isStarterCurrentPeriod(subscription, period);

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
      transition={{ duration: 0.2, delay: index * 0.06, ease: "easeOut" }}
      className={`relative rounded-[18px] overflow-hidden flex flex-col transition-all duration-150 ${
        plan.popular
          ? "border-2 border-[color:var(--gv-accent)] shadow-[0_4px_24px_-4px_rgba(254,44,85,0.12)]"
          : "border border-[color:var(--gv-rule)]"
      } bg-[color:var(--gv-paper)]`}
    >
      {plan.popular && (
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: "var(--gradient-purple-wash)" }}
        />
      )}
      {plan.popular && (
        <div className="absolute top-0 right-4 z-20">
          <div
            className="px-3 py-1 text-white font-bold uppercase tracking-wider rounded-b-lg"
            style={{ background: "var(--gradient-primary)", fontSize: "10px" }}
          >
            Khuyên dùng
          </div>
        </div>
      )}
      {showCurrentBadge && (
        <div className="absolute top-0 left-4 z-20">
          <div
            className="px-2.5 py-1 text-white font-bold uppercase tracking-wider rounded-b-lg"
            style={{ background: "var(--gradient-primary)", fontSize: "9px" }}
          >
            Đang hoạt động
          </div>
        </div>
      )}

      <div className="relative z-10 p-6 flex flex-col flex-1">
        <div className="flex items-start gap-3 mb-5">
          <div
            className={`w-10 h-10 rounded-[10px] flex items-center justify-center flex-shrink-0 ${
              plan.popular ? "text-white" : "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-3)]"
            }`}
            style={plan.popular ? { background: "var(--gradient-primary)" } : {}}
          >
            <Icon className="w-5 h-4" strokeWidth={2} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-extrabold text-[color:var(--gv-ink)] text-base mb-0.5 leading-none">{plan.name}</p>
            <p className="text-xs text-[color:var(--gv-ink-4)] leading-tight">{plan.tagline}</p>
          </div>
        </div>

        <div className="mb-5 min-h-[52px] flex flex-col justify-center">
          {isFree ? (
            <p className="font-extrabold text-[color:var(--gv-ink)] font-mono text-2xl">
              Miễn phí
            </p>
          ) : (
            <div className="flex items-baseline gap-1">
              <p
                className={`font-extrabold font-mono ${plan.popular ? "gradient-text" : "text-[color:var(--gv-ink)]"}`}
                style={{ fontSize: "1.75rem", lineHeight: 1 }}
              >
                {plan.priceDisplay}
              </p>
              <span className="text-xs text-[color:var(--gv-ink-3)] font-semibold">/tháng</span>
            </div>
          )}
          {!isFree && (
            <p className="text-[10px] text-[color:var(--gv-ink-4)] mt-1 font-semibold uppercase tracking-wider font-mono">
              {subtextPrice()}
            </p>
          )}
        </div>

        <ul className="space-y-2.5 mb-6 flex-1">
          {plan.features.map((feat) => (
            <li key={feat} className="flex items-start gap-2">
              <span
                className={`w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
                  plan.popular ? "text-white" : "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-3)]"
                }`}
                style={plan.popular ? { background: "var(--gradient-primary)" } : {}}
              >
                <Check className="w-2.5 h-2.5" strokeWidth={2.5} />
              </span>
              <span className="text-xs text-[color:var(--gv-ink-3)] leading-relaxed">{feat}</span>
            </li>
          ))}
        </ul>

        {isFree ? (
          <Btn
            variant="ghost"
            className="w-full"
            onClick={() => navigate("/app")}
          >
            {plan.cta}
          </Btn>
        ) : isStarter ? (
          <Btn
            variant={plan.popular ? "ink" : "ghost"}
            className="w-full"
            style={plan.popular ? { background: "var(--gradient-primary)" } : {}}
            onClick={goCheckoutStarter}
          >
            {plan.cta}
          </Btn>
        ) : (
          <Btn
            variant="ghost"
            disabled
            className="w-full opacity-50 cursor-not-allowed text-[color:var(--gv-ink-4)] border-[color:var(--gv-rule)]"
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
    <div className="flex-1 overflow-y-auto animate-pulse" style={{ scrollbarWidth: "thin" }}>
      <div className="max-w-4xl mx-auto px-4 lg:px-6 pt-14 lg:pt-6 pb-8">
        <div className="h-8 w-48 mx-auto rounded-lg bg-[color:var(--gv-rule)] mb-2" />
        <div className="h-4 w-64 mx-auto rounded bg-[color:var(--gv-rule)] mb-6" />
        <div className="mb-6 h-20 rounded-xl bg-[color:var(--gv-rule)]" />
        <div className="flex justify-center mb-4 h-10 w-64 mx-auto rounded-xl bg-[color:var(--gv-rule)]" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-64 rounded-xl bg-[color:var(--gv-rule)]" />
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

  const cap = (profile as { credits_total?: number } | null)?.credits_total ?? 50;
  const remaining = profile?.credits_remaining ?? 0;

  if (profileLoading) {
    return <PricingSkeleton />;
  }

  return (
    <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
      <div className="max-w-4xl mx-auto px-4 lg:px-6 pt-14 lg:pt-6 pb-8">
        <div className="text-center mb-10">
          <p className="gv-mono text-[10px] font-semibold gv-kicker tracking-[0.16em] text-[color:var(--gv-accent-deep)] mb-1">
            BẢNG GIÁ DỊCH VỤ
          </p>
          <h1 className="gv-tight text-[clamp(24px,4vw,32px)] font-bold text-[color:var(--gv-ink)] leading-tight mb-2">
            Lựa chọn gói phân tích phù hợp
          </h1>
          <p className="text-sm text-[color:var(--gv-ink-3)]">
            Không ràng buộc hợp đồng · Hủy bất kỳ lúc nào bạn muốn
          </p>
        </div>

        <div className="mb-8 bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-[12px] px-5 py-4 flex items-center justify-between gap-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-white"
              style={{ background: "var(--gradient-primary)" }}
            >
              <Zap className="w-4 h-4" strokeWidth={2} />
            </div>
            <div>
              <p className="gv-mono text-[10px] font-semibold gv-kicker tracking-[0.08em] text-[color:var(--gv-ink-4)] mb-0.5">
                LƯỢT PHÂN TÍCH CÒN LẠI
              </p>
              <p className="font-extrabold font-mono text-[color:var(--gv-ink)] text-sm">
                {remaining}
                <span className="font-normal text-[color:var(--gv-ink-4)]"> / {cap}</span>
              </p>
            </div>
          </div>
          <div className="flex-1 max-w-[128px]">
            <div className="h-1.5 bg-[color:var(--gv-canvas-2)] rounded-full overflow-hidden">
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

        <div className="h-8 flex items-center justify-center mb-6">
          <AnimatePresence mode="wait">
            {savingsMsg ? (
              <motion.p
                key={period}
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 4 }}
                transition={{ duration: 0.15 }}
                className="text-xs font-semibold text-[color:var(--gv-accent)] text-center inline-flex items-center justify-center gap-1.5"
              >
                <Sparkles className="h-3.5 w-3.5 shrink-0" aria-hidden />
                {savingsMsg}
              </motion.p>
            ) : (
              <motion.span key="empty" initial={{ opacity: 0 }} animate={{ opacity: 0 }} />
            )}
          </AnimatePresence>
        </div>

        <AnimatePresence mode="wait">
          <div key={period} className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-10">
            {currentPlans.map((plan, i) => (
              <PlanCard key={plan.name} plan={plan} period={period} index={i} subscription={subRow} />
            ))}
          </div>
        </AnimatePresence>

        <div className="border-t border-[color:var(--gv-rule-2)] mb-8" />

        <div className="mb-10">
          <div className="mb-4">
            <span className="gv-kicker gv-kicker--dot text-[color:var(--gv-accent-deep)] mb-1 block">
              MỞ THÊM LƯỢT PHÂN TÍCH CHUYÊN SÂU
            </span>
            <h3 className="gv-tight text-lg font-bold text-[color:var(--gv-ink)]">
              Mua thêm theo lượt (Không gia hạn)
            </h3>
            <p className="text-xs text-[color:var(--gv-ink-3)] mt-0.5">
              Dành cho creator cần phân tích gấp, lượt dùng không bao giờ hết hạn.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {topupCopy.map((pack) => {
              const count = pack.pack === "pack_10" ? 10 : pack.pack === "pack_30" ? 30 : 50;
              const price = pack.pack === "pack_10" ? "130.000đ" : pack.pack === "pack_30" ? "350.000đ" : "550.000đ";
              const perUnit = pack.pack === "pack_10" ? "13.000đ/lần" : pack.pack === "pack_30" ? "11.600đ/lần" : "11.000đ/lần";
              
              return (
                <button
                  key={pack.pack}
                  type="button"
                  onClick={() => navigate("/app/checkout", { state: { plan: pack.pack } })}
                  className={`group relative flex flex-col items-center justify-between text-center p-5 rounded-[12px] border transition-all duration-150 cursor-pointer ${
                    pack.highlight
                      ? "border-[color:var(--gv-accent)] bg-[color:var(--gv-paper)] shadow-[0_4px_16px_-4px_rgba(254,44,85,0.12)] hover:shadow-[0_6px_20px_-4px_rgba(254,44,85,0.18)]"
                      : "border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] hover:border-[color:var(--gv-ink)] hover:shadow-md"
                  }`}
                >
                  {pack.highlight && (
                    <span
                      className="absolute -top-2.5 left-1/2 -translate-x-1/2 text-white px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider whitespace-nowrap z-10"
                      style={{ background: "var(--gradient-primary)", fontSize: "9px" }}
                    >
                      Phổ biến nhất
                    </span>
                  )}
                  <div className="mb-2">
                    <p className="font-extrabold text-[color:var(--gv-ink)] text-lg font-mono">
                      +{count} <span className="text-xs font-normal text-[color:var(--gv-ink-3)]">lượt</span>
                    </p>
                  </div>
                  <div>
                    <p className="font-bold text-[color:var(--gv-ink)] text-sm font-mono">{price}</p>
                    <p className="text-[10px] text-[color:var(--gv-ink-4)] mt-0.5 font-mono">{perUnit}</p>
                  </div>
                  <div className="w-full mt-4 pt-3 border-t border-[color:var(--gv-rule-2)] group-hover:border-[color:var(--gv-ink)]/10 transition-colors">
                    <span className={`text-[11px] font-bold uppercase tracking-wider ${
                      pack.highlight ? "text-[color:var(--gv-accent-deep)]" : "text-[color:var(--gv-ink-3)] group-hover:text-[color:var(--gv-ink)]"
                    }`}>
                      Mua ngay ➔
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-[color:var(--gv-rule-2)]">
          <p className="gv-mono text-[10px] font-semibold gv-kicker tracking-[0.08em] text-[color:var(--gv-ink-4)] mb-3">
            PHƯƠNG THỨC THANH TOÁN ĐƯỢC CHẤP NHẬN
          </p>
          <div className="flex flex-wrap gap-2">
            {paymentMethods.map((pm) => (
              <div
                key={pm.label}
                className="px-4 py-2 rounded-[8px] border border-[color:var(--gv-rule)] flex items-center justify-center shadow-sm select-none"
                style={{ background: pm.bg, minWidth: 64 }}
              >
                <span className="font-extrabold text-xs font-mono tracking-wider" style={{ color: pm.color }}>
                  {pm.label}
                </span>
              </div>
            ))}
          </div>
          <p className="text-[11px] text-[color:var(--gv-ink-4)] mt-3 leading-relaxed">
            Hệ thống GetViews.vn tích hợp cổng thanh toán an toàn, bảo mật thông tin tuyệt đối. Lượt phân tích sẽ được cộng ngay lập tức sau khi giao dịch thành công.
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
