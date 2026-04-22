import { useNavigate } from "react-router";
import { ExternalLink, ChevronLeft } from "lucide-react";
import { motion } from "motion/react";
import { AppLayout } from "@/components/AppLayout";

interface LearnMoreItem {
  title: string;
  summary: string;
  url: string;
}

// Links below point either at real third-party pages (TikTok resources) or
// at ``mailto:support@getviews.vn``. The earlier iteration shipped with
// ``https://getviews.vn/{about,docs,changelog,terms,privacy,refund}`` links,
// but routes.ts only declares ``/``, ``/login``, ``/signup``, ``/auth/callback``
// and ``/app/*`` — those marketing/legal URLs 404. Until the real pages
// exist, legal queries route to the support inbox referenced in the spec
// (``artifacts/docs/screen-specs-getviews-vn-v1.md:859``).
const SUPPORT_EMAIL = "support@getviews.vn";

function supportMailto(subject: string): string {
  return `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(subject)}`;
}

const sections: { heading: string; items: LearnMoreItem[] }[] = [
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
    heading: "Pháp lý · Hỗ trợ",
    items: [
      {
        title: "Điều khoản dịch vụ",
        summary: `Gửi email cho ${SUPPORT_EMAIL} để nhận bản điều khoản hiện hành.`,
        url: supportMailto("Hỏi về điều khoản dịch vụ"),
      },
      {
        title: "Chính sách bảo mật",
        summary: `Gửi email cho ${SUPPORT_EMAIL} để biết cách GetViews xử lý dữ liệu cá nhân.`,
        url: supportMailto("Hỏi về chính sách bảo mật"),
      },
      {
        title: "Chính sách hoàn tiền",
        summary: `Gửi email cho ${SUPPORT_EMAIL} kèm mã giao dịch PayOS để yêu cầu hoàn tiền.`,
        url: supportMailto("Yêu cầu hoàn tiền"),
      },
      {
        title: "Liên hệ hỗ trợ chung",
        summary: `Gửi bất kỳ câu hỏi nào về GetViews tới ${SUPPORT_EMAIL}.`,
        url: supportMailto("Hỗ trợ GetViews.vn"),
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
        <p className="text-sm text-[var(--ink)] font-semibold mb-0.5 group-hover:text-[var(--gv-accent)] transition-colors duration-[120ms]">
          {item.title}
        </p>
        <p className="text-xs text-[var(--muted)]">{item.summary}</p>
      </div>
      <ExternalLink
        className="w-3.5 h-3.5 text-[var(--faint)] group-hover:text-[var(--gv-accent)] flex-shrink-0 mt-0.5 transition-colors duration-[120ms]"
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
              className="mt-1 w-10 h-10 flex items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--gv-ink-3)] hover:bg-[var(--surface-alt)] transition-colors duration-[120ms] flex-shrink-0"
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
