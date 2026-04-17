/** App-wide constants for GetViews.vn */

export const APP_NAME = "GetViews.vn";
export const APP_TAGLINE = "Bạn lướt TikTok cả ngày để tìm ý tưởng. GetViews làm việc đó thay bạn.";
export const APP_TRUST_LINE = "Không guru. Không screenshot. Chỉ data thực từ video thực.";

/** Free query limit per day for unlimited intents (⑥⑦) */
export const DAILY_FREE_QUERY_LIMIT = 100;

/** Credit packs pricing (VND) */
export const CREDIT_PACKS = {
  pack_10: { queries: 10, price_vnd: 130_000 },
  pack_50: { queries: 50, price_vnd: 600_000 },
} as const;

/** Subscription tiers (VND/month, monthly base rate) */
export const TIERS = {
  free: { deep_queries_lifetime: 10, price_vnd: 0 },
  starter: { deep_queries_monthly: 30, price_monthly: 249_000, price_annual_per_month: 199_000 },
  pro: { deep_queries_monthly: 80, price_monthly: 499_000, price_annual_per_month: 399_000 },
  agency: { deep_queries_monthly: 250, price_monthly: 1_490_000, price_annual_per_month: 1_190_000, seats: 10 },
} as const;

/** Vietnamese niche IDs (mapped from §7 taxonomy) */
export const NICHE_IDS = {
  review_shopee: 1,
  lam_dep: 2,
  thoi_trang: 3,
  review_an: 4,
  kiem_tien_online: 5,
  chi_dep: 6,
  me_bim_sua: 7,
  gym: 8,
  cong_nghe: 9,
  bat_dong_san: 10,
  edutok: 11,
  shopee_live: 12,
  hai_giai_tri: 13,
  oto_xe_may: 14,
  tai_chinh: 15,
  du_lich: 16,
  gaming: 17,
  nauan: 18,
  thu_cung: 19,
  nha_cua: 20,
} as const;
