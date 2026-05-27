import { formatVN } from "@/lib/formatters";

export type BillingPeriod = "monthly" | "biannual" | "annual";

type PaidPlan = "Starter" | "Pro";

/** List price (tháng) — baseline for strikethrough on longer plans. */
const MONTHLY_LIST_VND: Record<PaidPlan, number> = {
  Starter: 249_000,
  Pro: 499_000,
};

/** Equivalent per month when on 6-month / annual (matches PayOS + CheckoutScreen). */
const PER_MONTH_VND: Record<BillingPeriod, Record<PaidPlan, number>> = {
  monthly: { Starter: 249_000, Pro: 499_000 },
  biannual: { Starter: 199_000, Pro: 449_000 },
  annual: { Starter: 199_000, Pro: 399_000 },
};

const TOTAL_DUE_VND: Record<
  Exclude<BillingPeriod, "monthly">,
  Record<PaidPlan, { amount: number; cadence: string }>
> = {
  biannual: {
    Starter: { amount: 1_194_000, cadence: "mỗi 6 tháng" },
    Pro: { amount: 2_694_000, cadence: "mỗi 6 tháng" },
  },
  annual: {
    Starter: { amount: 2_388_000, cadence: "mỗi năm" },
    Pro: { amount: 4_788_000, cadence: "mỗi năm" },
  },
};

function formatVnd(amount: number): string {
  return `${formatVN(amount)}đ`;
}

export type PlanPricePresentation = {
  mainPrice: string;
  showPerMonthSuffix: boolean;
  strikePrice: string | null;
  billingLine: string | null;
  savingsLine: string | null;
};

/** Landing + marketing cards — per-month + total due so toggles are comparable in one viewport. */
export function planPricePresentation(
  planName: string,
  period: BillingPeriod,
): PlanPricePresentation {
  if (planName === "Free") {
    return {
      mainPrice: "Miễn phí",
      showPerMonthSuffix: false,
      strikePrice: null,
      billingLine: null,
      savingsLine: null,
    };
  }

  const plan = planName as PaidPlan;
  const perMonth = PER_MONTH_VND[period][plan];
  const mainPrice = formatVnd(perMonth);

  if (period === "monthly") {
    return {
      mainPrice,
      showPerMonthSuffix: true,
      strikePrice: null,
      billingLine: "Thanh toán mỗi tháng",
      savingsLine: null,
    };
  }

  const list = MONTHLY_LIST_VND[plan];
  const months = period === "biannual" ? 6 : 12;
  const total = TOTAL_DUE_VND[period][plan];
  const savings = (list - perMonth) * months;

  return {
    mainPrice,
    showPerMonthSuffix: true,
    strikePrice: formatVnd(list),
    billingLine: `Thanh toán ${formatVnd(total.amount)} ${total.cadence}`,
    savingsLine:
      savings > 0 ? `Tiết kiệm ${formatVnd(savings)} so với trả gói tháng` : null,
  };
}
