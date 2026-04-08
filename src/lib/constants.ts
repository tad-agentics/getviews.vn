// Vietnamese golden hours for TikTok posting
export const GOLDEN_HOURS = [
  { label: "Sáng", range: "6-9 AM" },
  { label: "Trưa", range: "11:30 AM - 1:30 PM" },
  { label: "Chiều tối", range: "6-8 PM" },
  { label: "Tối", range: "10 PM - 12 AM" },
];

export const PEAK_DAY = "Thứ 5"; // Thursday 7-9 PM = peak engagement

// Credit system
export const DEEP_INTENTS = [
  "video_diagnosis",
  "content_directions",
  "competitor_profile",
  "soi_kenh",
  "brief_generation",
] as const;

export const FREE_INTENTS = ["trend_spike", "find_creators", "followup"] as const;

// Pricing (VND)
export const PRICING = {
  starter: { monthly: 249_000, sixMonth: 209_000, annual: 199_000 },
  pro: { monthly: 499_000, sixMonth: 419_000, annual: 399_000 },
  agency: { monthly: 1_490_000, sixMonth: 1_249_000, annual: 1_190_000 },
  overage: { ten: 130_000, fifty: 600_000 },
} as const;

// Rate limiting for free intents
export const FREE_INTENT_DAILY_LIMIT = 100;

// Credit thresholds
export const CREDIT_LOW_THRESHOLD = 5;

// Input limits
export const MAX_INPUT_CHARS = 1000;
export const MAX_CHAT_HISTORY = 5; // messages sent to Gemini for context
