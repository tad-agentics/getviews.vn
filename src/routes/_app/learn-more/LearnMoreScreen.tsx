import { useNavigate } from "react-router";
import { ExternalLink, ChevronLeft } from "lucide-react";
import { motion } from "motion/react";
import { AppLayout } from "@/components/AppLayout";

interface LearnMoreItem {
  title: string;
  summary: string;
  url: string;
}

const sections: { heading: string; items: LearnMoreItem[] }[] = [
  {
    heading: "GetViews.vn",
    items: [
      {
        title: "Về GetViews.vn",
        summary:
          "Tìm hiểu GetViews là gì, ai xây dựng, tại sao được tạo ra, và vision dài hạn cho creator Việt Nam.",
        url: "https://getviews.vn/about",
      },
      {
        title: "Hướng dẫn sử dụng",
        summary:
          "Cách dán link TikTok, đọc báo cáo chẩn đoán, lướt xu hướng và tận dụng tối đa Deep Credits.",
        url: "https://getviews.vn/docs",
      },
      {
        title: "Changelog",
        summary: "Lịch sử cập nhật tính năng, cải tiến và sửa lỗi theo từng phiên bản.",
        url: "https://getviews.vn/changelog",
      },
    ],
  },
  {
    heading: "Tài nguyên từ TikTok",
    items: [
      {
        title: "TikTok Creator Academy",
        summary:
          "Khóa học chính thức từ TikTok về cách tối ưu nội dung, hiểu thuật toán và phát triển kênh bền vững.",
        url: "https://www.tiktok.com/creator-academy",
      },
      {
        title: "TikTok Trends Hub",
        summary:
          "Bảng xu hướng toàn cầu của TikTok — theo dõi hashtag, âm nhạc và nội dung đang viral mỗi tuần.",
        url: "https://www.tiktok.com/trending",
      },
    ],
  },
  {
    heading: "Pháp lý",
    items: [
      {
        title: "Điều khoản dịch vụ",
        summary: "Quy định sử dụng nền tảng, quyền và nghĩa vụ của người dùng và GetViews.vn.",
        url: "https://getviews.vn/terms",
      },
      {
        title: "Chính sách bảo mật",
        summary: "Cách GetViews thu thập, lưu trữ và bảo vệ dữ liệu cá nhân của bạn.",
        url: "https://getviews.vn/privacy",
      },
      {
        title: "Chính sách hoàn tiền",
        summary: "Điều kiện hoàn tiền, thời hạn xử lý và quy trình yêu cầu hoàn tiền.",
        url: "https://getviews.vn/refund",
      },
    ],
  },
];

function LearnMoreRow({ item, index }: { item: LearnMoreItem; index: number }) {
  return (
    <motion.a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2, delay: index * 0.04, ease: "easeOut" }}
      className="flex items-start justify-between gap-3 px-4 py-4 border-b border-[var(--border)] last:border-0 hover:bg-[var(--surface-alt)] transition-colors duration-[120ms] group"
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm text-[var(--ink)] font-semibold mb-0.5 group-hover:text-[var(--purple)] transition-colors duration-[120ms]">
          {item.title}
        </p>
        <p className="text-xs text-[var(--muted)]">{item.summary}</p>
      </div>
      <ExternalLink
        className="w-3.5 h-3.5 text-[var(--faint)] group-hover:text-[var(--purple)] flex-shrink-0 mt-0.5 transition-colors duration-[120ms]"
        strokeWidth={1.8}
      />
    </motion.a>
  );
}

function LearnMoreContent() {
  let rowIndex = 0;
  return (
    <div className="max-w-xl mx-auto space-y-6">
      {sections.map((section) => (
        <div key={section.heading}>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-[var(--faint)] px-4 mb-2">
            {section.heading}
          </p>
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl overflow-hidden">
            {section.items.map((item) => {
              const idx = rowIndex++;
              return <LearnMoreRow key={item.title} item={item} index={idx} />;
            })}
          </div>
        </div>
      ))}
      <p className="text-center text-[11px] font-mono text-[var(--faint)] mt-10 pb-2">getviews.vn · v1.0.0</p>
    </div>
  );
}

export default function LearnMoreScreen() {
  const navigate = useNavigate();

  return (
    <AppLayout enableMobileSidebar>
      <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
        <div className="px-4 lg:px-8 pt-16 lg:pt-8 pb-8">
          <div className="max-w-xl mx-auto mb-6 flex items-start gap-2">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="mt-1 w-10 h-10 flex items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--ink-soft)] hover:bg-[var(--surface-alt)] transition-colors duration-[120ms] flex-shrink-0"
              aria-label="Quay lại"
            >
              <ChevronLeft className="w-5 h-5" strokeWidth={2} />
            </button>
            <div className="min-w-0 flex-1">
              <h1 className="font-extrabold text-[var(--ink)] mb-1" style={{ fontSize: "1.75rem" }}>
                Tìm hiểu thêm
              </h1>
              <p className="text-sm text-[var(--muted)]">Tài liệu, khóa học và thông tin pháp lý về GetViews.vn</p>
            </div>
          </div>
          <LearnMoreContent />
        </div>
      </div>
    </AppLayout>
  );
}
