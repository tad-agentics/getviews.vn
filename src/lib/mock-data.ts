// Dev / marketing mock data — mirrors Figma Make `mockData.ts`; swap with live data per feature.

export const mockProfile = {
  display_name: "Nguyễn Minh",
  email: "minh.nguyen@example.com",
  primary_niche: "Review đồ gia dụng",
  deep_credits_remaining: 27,
  subscription_tier: "starter",
  credits_reset_at: "2026-05-01",
};

export const mockMessages = [
  {
    role: "user" as const,
    content:
      "Tại sao video này chỉ 2.000 view? https://www.tiktok.com/@minhreview/video/7123456789",
    intent_type: "video_diagnosis",
    credits_used: 1,
    is_free: false,
  },
  {
    role: "assistant" as const,
    content: null,
    diagnosis_rows: [
      {
        type: "fail",
        finding: "Không mặt trong 3 giây đầu",
        benchmark: "92% top video trong niche mở bằng mặt trong 0.5 giây đầu",
        fix: "Quay lại mở bằng mặt nhìn camera trong 0.5 giây đầu",
      },
      {
        type: "fail",
        finding: "Text overlay ở giây 3.2",
        benchmark: "Top video: text xuất hiện trước giây 1",
        fix: "Chuyển text lên frame đầu tiên",
      },
      {
        type: "pass",
        finding: "Hook 'Cảnh Báo' đúng pattern",
        benchmark: "Trung bình 3.2x views so với 'Kể Chuyện' trong niche",
      },
    ],
    corpus_cite: {
      count: 412,
      niche: "review đồ gia dụng",
      timeframe: "7 ngày",
      updated_hours_ago: 4,
    },
    thumbnails: [
      { handle: "@topniche1", views: "1,2M", url: "https://tiktok.com/1" },
      { handle: "@topniche2", views: "890K", url: "https://tiktok.com/2" },
      { handle: "@topniche3", views: "450K", url: "https://tiktok.com/3" },
      { handle: "@topniche4", views: "320K", url: "https://tiktok.com/4" },
    ],
  },
];

export const mockSessions = [
  {
    id: "s1",
    first_message: "Tại sao video review nồi chiên không dầu chỉ 2.000 view?",
    intent_type: "video_diagnosis",
    created_at: "2026-04-08T08:14:00",
    credits_used: 1,
  },
  {
    id: "s2",
    first_message: "Hook nào đang hot trong review đồ gia dụng tuần này?",
    intent_type: "trend_spike",
    created_at: "2026-04-08T07:52:00",
    credits_used: 0,
  },
  {
    id: "s3",
    first_message: "Soi kênh @reviewer_top1 — họ đang làm gì?",
    intent_type: "competitor_profile",
    created_at: "2026-04-07T15:30:00",
    credits_used: 1,
  },
  {
    id: "s4",
    first_message: "Viết brief cho KOL quay video nồi chiên không dầu",
    intent_type: "brief_generation",
    created_at: "2026-04-07T10:15:00",
    credits_used: 1,
  },
  {
    id: "s5",
    first_message: "Format nào đang lên trong niche của tôi?",
    intent_type: "format_lifecycle",
    created_at: "2026-04-06T14:22:00",
    credits_used: 0,
  },
  {
    id: "s6",
    first_message: "Tìm KOL micro trong niche làm đẹp để hợp tác",
    intent_type: "find_creators",
    created_at: "2026-04-05T09:10:00",
    credits_used: 1,
  },
];

export const pricingPlans = {
  monthly: [
    {
      name: "Free",
      label: "Dùng thử",
      price: "Miễn phí",
      credits: "10 lần phân tích sâu (lifetime)",
      popular: false,
    },
    {
      name: "Starter",
      label: "Starter",
      price: "249.000đ",
      credits: "30 lần phân tích sâu/tháng + lướt xu hướng không giới hạn",
      popular: true,
    },
    {
      name: "Pro",
      label: "Pro",
      price: "499.000đ",
      credits: "80 lần phân tích sâu/tháng + không giới hạn browse",
      popular: false,
    },
    {
      name: "Agency",
      label: "Agency",
      price: "1.490.000đ",
      credits: "250 lần phân tích sâu + 10 tài khoản",
      popular: false,
    },
  ],
  biannual: [
    {
      name: "Free",
      label: "Dùng thử",
      price: "Miễn phí",
      credits: "10 lần phân tích sâu (lifetime)",
      popular: false,
    },
    {
      name: "Starter",
      label: "Starter",
      price: "219.000đ",
      credits: "30 lần phân tích sâu/tháng + lướt xu hướng không giới hạn",
      popular: true,
    },
    {
      name: "Pro",
      label: "Pro",
      price: "449.000đ",
      credits: "80 lần phân tích sâu/tháng + không giới hạn browse",
      popular: false,
    },
    {
      name: "Agency",
      label: "Agency",
      price: "1.350.000đ",
      credits: "250 lần phân tích sâu + 10 tài khoản",
      popular: false,
    },
  ],
  annual: [
    {
      name: "Free",
      label: "Dùng thử",
      price: "Miễn phí",
      credits: "10 lần phân tích sâu (lifetime)",
      popular: false,
    },
    {
      name: "Starter",
      label: "Starter",
      price: "199.000đ",
      credits: "30 lần phân tích sâu/tháng + lướt xu hướng không giới hạn",
      popular: true,
    },
    {
      name: "Pro",
      label: "Pro",
      price: "399.000đ",
      credits: "80 lần phân tích sâu/tháng + không giới hạn browse",
      popular: false,
    },
    {
      name: "Agency",
      label: "Agency",
      price: "1.190.000đ",
      credits: "250 lần phân tích sâu + 10 tài khoản",
      popular: false,
    },
  ],
};

/** Screen-spec `screen-specs-getviews-vn-v1.md` — pricing_sixmo_callout + pricing_annual_callout */
export const pricingSavings = {
  monthly: "",
  biannual: "Tặng 1 tháng miễn phí khi mua 6 tháng",
  annual: "Tiết kiệm 600.000đ khi mua cả năm",
};
