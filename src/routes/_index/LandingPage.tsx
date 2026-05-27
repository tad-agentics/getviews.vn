import {
  useCallback,
  useMemo,
  useState,
  useEffect,
  type FormEvent,
  type ReactNode,
} from "react";
import { Link, useNavigate } from "react-router";
import { r2FrameUrl, r2ThumbnailUrl } from "@/lib/r2";
import { formatCorpusMarketingCount } from "@/lib/formatters";
import { resolveLandingHeroSubmit } from "@/lib/landingHeroCta";
import { persistPostLoginNextFromSearch } from "@/lib/postLoginRedirect";
import { formatTikTokSidebarHint, queryUrlChipState } from "@/lib/tiktokUrl";
import * as Accordion from "@radix-ui/react-accordion";
import { ChevronDown, Database, Play, Globe, Zap, Search, MessageCircle, ExternalLink, RefreshCw } from "lucide-react";
import { pricingPlans, pricingSavings } from "@/lib/mock-data";
import { planPricePresentation } from "@/lib/pricingDisplay";

/**
 * Landing page is prerendered at build time and is the entry point for
 * unauthenticated visitors. Every kilobyte preloaded here is a
 * kilobyte the user pays for before first paint, so we keep this
 * route deliberately library-light.
 *
 * ``motion/react`` (~125 KB raw / ~45 KB gzip) was on the critical
 * path purely for decorative ``whileInView`` fade-ups (mostly no-ops
 * because ``initial={false}`` left elements at their final state)
 * and a hover-lift that the cards' border emphasis already
 * implies. The local ``motion`` and ``AnimatePresence`` shims below
 * silently strip animation props and render plain DOM, so the
 * bundle no longer includes the library while the JSX shape stays
 * identical to the rest of the app.
 */
type MotionDivProps = React.HTMLAttributes<HTMLDivElement> & {
  initial?: unknown;
  animate?: unknown;
  exit?: unknown;
  transition?: unknown;
  whileHover?: unknown;
  whileInView?: unknown;
  viewport?: unknown;
  layout?: unknown;
};
function MotionDivStub({
  initial: _i,
  animate: _a,
  exit: _e,
  transition: _t,
  whileHover: _h,
  whileInView: _v,
  viewport: _vp,
  layout: _l,
  ...rest
}: MotionDivProps) {
  return <div {...rest} />;
}
const motion = { div: MotionDivStub };
const AnimatePresence = ({ children }: { children: ReactNode }) => <>{children}</>;

function buildFaqs(corpusLabel: string) {
  return [
  {
    q: "Cái này khác gì ChatGPT?",
    a: `ChatGPT là một công cụ AI tổng quát, không được huấn luyện trên dữ liệu video TikTok chuyên biệt và không thể trực tiếp phân tích nội dung hình ảnh/âm thanh. GetViews được xây dựng riêng để phân tích chuyên sâu từ ${corpusLabel} video TikTok thực tế, cung cấp các insight và dẫn chứng trực quan, giúp bạn đưa ra quyết định dựa trên số liệu, không phải phỏng đoán.`,
  },
  {
    q: "Tôi không rành về AI, dùng có khó không?",
    a: "GetViews được thiết kế với giao diện trực quan và dễ sử dụng, không yêu cầu kiến thức chuyên sâu về AI. Bạn chỉ cần nhập câu hỏi hoặc dán đường dẫn video TikTok. Hệ thống sẽ tự động xử lý và cung cấp báo cáo phân tích chi tiết, dễ hiểu, kèm theo các video dẫn chứng cụ thể để bạn áp dụng ngay.",
  },
  {
    q: "Tôi đã mua khóa học rồi, có cần dùng thêm GetViews không?",
    a: "Các khóa học cung cấp nền tảng kiến thức và tư duy chiến lược quý giá. Tuy nhiên, thị trường TikTok biến đổi liên tục. GetViews bổ trợ bằng cách cung cấp dữ liệu thực tế cập nhật hàng tuần, chỉ ra chính xác định dạng video, các loại hook và nội dung nào đang hiệu quả nhất trong niche của bạn, giúp bạn tối ưu hóa chiến lược theo thời gian thực.",
  },
  {
    q: "Khác gì các nền tảng như Kalodata hay Shoplus?",
    a: "Trong khi Kalodata và Shoplus tập trung vào hiệu suất thương mại điện tử (sản phẩm, doanh số), GetViews chuyên sâu vào phân tích nội dung sáng tạo. Chúng tôi đi sâu vào cấu trúc video, hiệu quả của hook, nhịp độ dựng phim và định dạng để giải mã thành công của video. GetViews bổ trợ tốt cho bán hàng: insight về nội dung giúp bạn tối ưu video trước khi đăng.",
  },
  {
    q: "Một lượt phân tích được tính như thế nào?",
    a: "Các công cụ khám phá xu hướng, tìm kiếm Creator và AI Chat hỏi đáp cơ bản là miễn phí và không giới hạn. Lượt phân tích chuyên sâu được tính khi bạn yêu cầu hệ thống thực hiện phân tích chi tiết một video (frame-by-frame), chẩn đoán kênh đối thủ toàn diện hoặc tạo kịch bản video AI tùy chỉnh.",
  },
  {
    q: "Thanh toán có phức tạp không?",
    a: "Chúng tôi cung cấp nhiều phương thức thanh toán linh hoạt và an toàn như MoMo, VNPay, chuyển khoản ngân hàng tự động và thẻ quốc tế Visa/Mastercard. Quá trình thanh toán nhanh chóng, và số lượt phân tích sẽ được cộng tức thì vào tài khoản của bạn ngay sau khi giao dịch hoàn tất.",
  },
];
}

const testimonials = [
  {
    initials: "MK",
    handle: "@minhk.review",
    niche: "Review đồ gia dụng",
    followers: "~50K",
    quote:
      "Dán link video flop, ~1 phút có 3 lỗi cụ thể: hook 2,3 giây, không mặt ở frame đầu. Biết sửa gì trước khi quay lại — không phải đoán cảm tính.",
    stat: "3 lỗi có số",
  },
  {
    initials: "LH",
    handle: "@linhbeauty.vn",
    niche: "Làm đẹp · Skincare",
    followers: "~120K",
    quote:
      "Hỏi hook hot tuần này — ra top 5 kèm link video gốc trong ngách. Không còn lưu TikTok rồi quên mất.",
    stat: "Top 5 + link",
  },
  {
    initials: "TN",
    handle: "@techvn.review",
    niche: "Công nghệ / Tech",
    followers: "~30K",
    quote:
      "Soi 3 kênh đối thủ bằng @handle, không phải ngồi lướt cả tối. Tiết kiệm ~4–5 giờ research mỗi tuần.",
    stat: "~4h/tuần",
  },
];

/** Minh họa hook ranking — hệ số TB ngách + khung thời gian, không hứa view. */
const hookTicker = [
  '"Cảnh Báo: Đừng mua trước khi xem" · 2,4× TB ngách · Skincare · 7 ngày',
  '"3 sai lầm khiến da sạm đi buổi sáng" · 1,9× TB ngách · Làm đẹp · 7 ngày',
  '"Tôi đã mua thử để bạn không mất tiền" · 1,6× TB ngách · Review · 7 ngày',
  '"So sánh công tâm giữa hai siêu phẩm" · 1,4× TB ngách · Tech · 7 ngày',
  '"Sự thật về sản phẩm này không ai nói..." · 1,7× TB ngách · Food · 7 ngày',
  '"Thử nghiệm thực tế sau 30 ngày dùng:" · 1,5× TB ngách · Gia dụng · 7 ngày',
  '"Đừng làm điều này nếu bạn đang dùng..." · 2,1× TB ngách · Skincare · 7 ngày',
];

const painPoints = [
  {
    title: 'Lướt TikTok \u201cvô tri\u201d cả buổi',
    body: "Sáng mở app định \"nghiên cứu đối thủ\". 2 tiếng sau nhận ra mình vẫn đang lướt trong vô định. Lưu hàng chục video vào mục yêu thích rồi... để đó, chẳng bao giờ xem lại.",
  },
  {
    title: 'Học đủ khóa vẫn \u201cbí\u201d ý tưởng',
    body: "Bỏ 3-5 triệu mua khóa học. Nắm chắc lý thuyết nhưng sáng ngủ dậy đứng trước camera vẫn không biết quay gì. Thuật toán đổi liên tục, kiến thức tháng trước giờ đã lỗi thời.",
  },
  {
    title: "Video flop không rõ nguyên nhân",
    body: "Đầu tư quay dựng cả ngày, đăng lên lẹt đẹt 500 lượt xem. Không biết lỗi ở hook, nội dung hay định dạng video. Nhìn video đối thủ lên xu hướng mà không biết họ làm gì khác mình.",
  },
];

const nicheList = [
  "Thời trang / Outfit", "Làm đẹp · Skincare", "Review đồ Shopee",
  "Ẩm thực & Ăn uống", "Mẹ bỉm sữa",
  "Gym / Fitness & Sức khoẻ", "Thể thao & Ngoài trời", "Gaming",
  "Công nghệ / Tech", "EduTok VN", "Tài chính / Đầu tư",
  "Du lịch / Travel", "Ô tô / Xe máy", "Bất động sản",
  "Hài / Giải trí", "Shopee Live", "Kiếm tiền online",
  "Chị đẹp", "Thú cưng", "Nhà cửa / Nội thất",
];

// ─── Hardcoded real video IDs from corpus (selected 2026-04-09) ──────────────

// Card 1: Competitor intel — yeah1.giaitri (7 confirmed R2 frames + 1 fill)
// All probed live 2026-04-09 — only IDs with HTTP 200 on /frames/{id}/0.png
const COMPETITOR_IDS = [
  "7615811534962330901", // 1.5M · ✓ frame
  "7616572388544695573", // 612K · ✓ frame
  "7620342789313776917", // 381K · ✓ frame
  "7617676901603101973", // 313K · ✓ frame
  "7616570339660713237", // 219K · ✓ frame
  "7620352506454920469", // 160K · ✓ frame
  "7615201094343396628", // 156K · ✓ frame
  "7626372581448371464", // 220K · ✓ frame (fill — niche 4, same era)
];

// Card 2: Creator avatars — scattered float layout (LightReel style)
// All confirmed R2 frames
const CREATOR_AVATAR_IDS: { id: string; handle: string; views: string }[] = [
  { id: "7622669408665652488", handle: "@lynguyn.2002",    views: "7.3M" },
  { id: "7619285253022125333", handle: "@_ttqueen",        views: "4.6M" },
  { id: "7616957249201638677", handle: "@emhoangnhapho",   views: "3.8M" },
  { id: "7621463359350656277", handle: "@monkeyjuniorvn",  views: "2.4M" },
];

const AVATAR_POSITIONS = [
  { top: "10%", left: "30%" },
  { top: "5%",  left: "62%" },
  { top: "45%", left: "18%" },
  { top: "50%", left: "58%" },
];

// Card 3: Hook showcase — confirmed R2 frame, strong Vietnamese hook phrase
const HOOK_EXAMPLE = {
  id: "7619285253022125333",
  phrase: "Hôm nay mời mọi người mukbang combo mì cay và trà sữa với mình nhé",
  views: "4.6M",
  handle: "@_ttqueen",
};

// Card 4: Dense video grid — 15 confirmed R2 frames, diverse niches (5 cols × 3 rows)
const GRID_VIDEO_IDS = [
  "7622669408665652488", // niche 3  · 7.3M  · ✓
  "7619285253022125333", // niche 4  · 4.6M  · ✓
  "7616957249201638677", // niche 10 · 3.8M  · ✓
  "7621463359350656277", // niche 11 · 2.4M  · ✓
  "7626242462796778773", // niche 2  · 1.7M  · ✓
  "7615811534962330901", // niche 6  · 1.5M  · ✓
  "7626724853504068884", // niche 7  · 1.0M  · ✓
  "7627432133937679624", // niche 8  · 746K  · ✓
  "7626349423580204295", // niche 9  · 335K  · ✓
  "7625661777463872788", // niche 1  · 271K  · ✓
  "7627166762894740757", // niche 12 · 92K   · ✓
  "7624842569465220368", // niche 4  · 2.2M  · ✓
  "7625973407997267221", // niche 11 · 2.0M  · ✓
  "7624501870622444821", // niche 3  · 1.8M  · ✓
  "7616572388544695573", // niche 6  · 612K  · ✓
];

function VideoThumb({
  id,
  className = "",
  priority = false,
}: {
  id: string;
  className?: string;
  /** Above-fold thumbnails set ``priority`` so the browser starts the
   *  fetch eagerly instead of waiting for the IntersectionObserver
   *  ``loading="lazy"`` heuristic. The hero card thumbs in the very
   *  first SolutionCardsSection are the only sites that need this —
   *  every thumbnail below the fold keeps the lazy default. */
  priority?: boolean;
}) {
  const candidates = useMemo(() => landingThumbSrcCandidates(id), [id]);
  const [srcIndex, setSrcIndex] = useState(0);
  useEffect(() => {
    setSrcIndex(0);
  }, [id]);
  const src = candidates[srcIndex];
  if (!src || srcIndex >= candidates.length) {
    return (
      <div
        className={`flex items-center justify-center bg-[color:var(--gv-canvas-2)] ${className}`}
        aria-hidden
      >
        <Play className="h-4 w-4 text-[color:var(--gv-ink-4)] opacity-40" strokeWidth={1.5} />
      </div>
    );
  }
  return (
    <img
      src={src}
      alt=""
      className={`object-cover ${className}`}
      loading={priority ? "eager" : "lazy"}
      fetchPriority={priority ? "high" : "auto"}
      onError={() => {
        setSrcIndex((i) => (i + 1 < candidates.length ? i + 1 : candidates.length));
      }}
    />
  );
}

function SolutionCardsSection() {
  return (
    <section className="px-4 py-16 md:py-20 bg-[color:var(--gv-canvas)]">
      <div className="max-w-4xl mx-auto">
        <p className="text-center text-sm text-[color:var(--gv-ink-3)] mb-2">Tăng tốc hiệu suất</p>
        <h2 className="gv-landing-h2-sm text-center font-extrabold text-[color:var(--gv-ink)] mb-3">
          Nâng tầm nội dung, dẫn đầu xu hướng
        </h2>
        <p className="text-center text-sm text-[color:var(--gv-ink-3)] mb-12 max-w-2xl mx-auto leading-relaxed">
          GetViews không chỉ xem hàng nghìn video TikTok, mà còn phân tích chuyên sâu để bạn
          <span className="font-semibold text-[color:var(--gv-ink)]">hiểu rõ chiến lược đối thủ</span>,
          <span className="font-semibold text-[color:var(--gv-ink)]">khám phá hook viral</span>,
          và <span className="font-semibold text-[color:var(--gv-ink)]">tối ưu định dạng viral</span>. Tất cả dựa trên dữ liệu thực tế.
        </p>
        <div className="grid md:grid-cols-2 gap-4">

          {/* ── Card 1: Competitor Intel ──────────────────────────────── */}
          <motion.div
            initial={false} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.4, delay: 0 }}
            whileHover={{ y: -4 }}
            className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-5 flex flex-col gap-4 transition-colors duration-200 hover:border-[color:var(--gv-ink-3)] cursor-pointer"
          >
            <p className="text-lg font-bold text-[color:var(--gv-ink)]">"Chiến lược của đối thủ là gì?"</p>
            <div className="flex gap-2 overflow-hidden">
              {COMPETITOR_IDS.slice(0, 4).map((id, i) => (
                <div
                  key={id}
                  className="relative flex-shrink-0 overflow-hidden rounded-xl bg-[color:var(--gv-canvas-2)]"
                  style={{ width: "22%", paddingBottom: "39%" }}
                >
                  <VideoThumb
                    id={id}
                    priority={i < 2}
                    className="absolute inset-0 w-full h-full"
                  />
                </div>
              ))}
              {/* Faded peek of a 5th card — signals volume / scrollability */}
              <div
                className="relative flex-shrink-0 overflow-hidden rounded-xl bg-[color:var(--gv-canvas-2)] opacity-40"
                style={{ width: "10%", paddingBottom: "39%" }}
              />
            </div>
            <p className="text-xs text-[color:var(--gv-ink-3)]">Phân tích sâu nội dung, format và các hook hiệu quả nhất của đối thủ trực tiếp</p>
          </motion.div>

          {/* ── Card 2: Creator Avatars (scattered float) ─────────────── */}
          <motion.div
            initial={false} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.4, delay: 0.1 }}
            whileHover={{ y: -4 }}
            className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-5 flex flex-col gap-3 transition-colors duration-200 hover:border-[color:var(--gv-ink-3)] cursor-pointer"
            style={{ minHeight: 220 }}
          >
            <p className="text-lg font-bold text-[color:var(--gv-ink)]">"Hợp tác với Creator nào để tối ưu chiến dịch?"</p>
            <div className="relative flex-1">
              {CREATOR_AVATAR_IDS.map((c, i) => {
                const pos = AVATAR_POSITIONS[i];
                return (
                  <div
                    key={c.id}
                    className="absolute overflow-hidden rounded-full border-2 border-white shadow-md bg-[color:var(--gv-canvas-2)]"
                    style={{ width: 64, height: 64, ...pos }}
                  >
                    <VideoThumb id={c.id} className="h-full w-full" />
                  </div>
                );
              })}
            </div>
            <p className="text-xs text-[color:var(--gv-ink-3)]">Tìm kiếm và lọc Creator (KOL/KOC) tiềm năng dựa trên hiệu suất thực tế: mảng nội dung, lượt xem trung bình và tỷ lệ tương tác</p>
          </motion.div>

          {/* ── Card 3: Hook Showcase — chat bubble + sparkline ──────── */}
          <motion.div
            initial={false} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.4, delay: 0.2 }}
            whileHover={{ y: -4 }}
            className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-5 flex flex-col gap-4 transition-colors duration-200 hover:border-[color:var(--gv-ink-3)] cursor-pointer"
          >
            <p className="text-lg font-bold text-[color:var(--gv-ink)]">"Hook nào đang \"cắn\" đề xuất nhiều nhất tuần này?"</p>
            <div className="flex gap-3 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] p-3">
              <div className="flex-shrink-0 overflow-hidden rounded-lg bg-[color:var(--gv-canvas-2)]" style={{ width: 48, height: 64 }}>
                <VideoThumb id={HOOK_EXAMPLE.id} className="h-full w-full" />
              </div>
              <div className="flex flex-col justify-center gap-1 min-w-0">
                <p className="text-sm font-semibold text-[color:var(--gv-ink)] line-clamp-2">"{HOOK_EXAMPLE.phrase}"</p>
                <p className="text-xs text-[color:var(--gv-accent)] font-mono font-semibold">{HOOK_EXAMPLE.views} lượt xem</p>
              </div>
            </div>
            {/* Sparkline — pure SVG, no chart lib */}
            <svg viewBox="0 0 200 40" className="w-full opacity-40" fill="none">
              <polyline
                points="0,38 40,30 80,20 120,12 160,6 200,2"
                className="stroke-[color:var(--gv-accent)]"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </motion.div>

          {/* ── Card 4: Dense Video Grid (5-col) ─────────────────────── */}
          <motion.div
            initial={false} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.4, delay: 0.3 }}
            whileHover={{ y: -4 }}
            className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-5 flex flex-col gap-3 transition-colors duration-200 hover:border-[color:var(--gv-ink-3)] cursor-pointer"
          >
            <p className="text-lg font-bold text-[color:var(--gv-ink)]">"Video tiếp theo nên làm gì để viral?"</p>
            {/* Responsive grid: at 360px baseline 5 cells = 72px each
                (cramped); step up via 3 → 4 → 5 cols matching Tailwind's
                sm (640px) and md (768px) breakpoints. */}
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-1">
              {GRID_VIDEO_IDS.map((id) => (
                <div
                  key={id}
                  className="relative overflow-hidden rounded-md bg-[color:var(--gv-canvas-2)]"
                  style={{ paddingBottom: "177%" }}
                >
                  <VideoThumb id={id} className="absolute inset-0 w-full h-full" />
                </div>
              ))}
            </div>
          </motion.div>

        </div>
      </div>
    </section>
  );
}

const SIGNALS: { key: keyof typeof SIGNAL_VIDEOS; dot: string; label: string; sub: string }[] = [
  { key: "rising", dot: "bg-[color:var(--gv-accent)]", label: "Hook số liệu shock", sub: "Top pattern tuần này" },
  { key: "early",  dot: "bg-[color:var(--gv-warn)]",   label: "Cảnh báo + reveal",  sub: "Mới nổi, vào sớm" },
  { key: "stable", dot: "bg-[color:var(--gv-ink-4)]",  label: "Before / After",     sub: "Ổn định, cạnh tranh cao" },
];

// Confirmed R2 frames (probed 2026-04-09) — used for the scroll strip
// Diverse niches: 2,3,4,6,7,8,9,10,11,12
const STRIP_FRAME_IDS = [
  "7622669408665652488", // niche 3  · 7.3M
  "7619285253022125333", // niche 4  · 4.6M
  "7616957249201638677", // niche 10 · 3.8M
  "7621463359350656277", // niche 11 · 2.4M
  "7624842569465220368", // niche 4  · 2.2M
  "7625973407997267221", // niche 11 · 2.0M
  "7624501870622444821", // niche 3  · 1.8M
  "7626242462796778773", // niche 2  · 1.7M
  "7621904918978252039", // niche 4  · 1.6M
  "7615811534962330901", // niche 6  · 1.6M
  "7627854030705839380", // niche 2  · 1.2M
  "7626756818085203207", // niche 4  · 1.1M
  "7626724853504068884", // niche 7  · 1.0M
  "7624064318136536328", // niche 2  · 840K
  "7627475293153905941", // niche 7  · 830K
  "7627432133937679624", // niche 8  · 750K
  "7626727359231675669", // niche 2  · 750K
  "7627069060844457233", // niche 8  · 740K
  "7624108179890228496", // niche 4  · 730K
  "7620672683994402069", // niche 8  · 660K
  "7625901708295671048", // niche 2  · 640K
  "7616572388544695573", // niche 6  · 610K
  "7627068868820864276", // niche 11 · 560K
  "7626349423580204295", // niche 9  · 330K
  "7617676901603101973", // niche 6  · 310K
  "7625661777463872788", // niche 1  · 270K
  "7620112412523433237", // niche 3  · 260K
  "7624873937884826900", // niche 11 · 250K
  "7616570339660713237", // niche 6  · 220K
  "7626372581448371464", // niche 4  · 220K
];

// 3 confirmed R2-frame IDs per signal type (probed 2026-04-09)
// rising = bold_claim / shock_stat hooks · early = curiosity_gap / pain_point · stable = how_to / story_open
const SIGNAL_VIDEOS: Record<string, string[]> = {
  rising: ["7616957249201638677", "7624842569465220368", "7626242462796778773"],
  early:  ["7625973407997267221", "7621904918978252039", "7626756818085203207"],
  stable: ["7622669408665652488", "7621463359350656277", "7615811534962330901"],
};

// 5 hook examples — real phrases from corpus, confirmed R2 frames
const HOOK_EXAMPLES: { id: string; phrase: string; hookType: string; views: string }[] = [
  { id: "7622669408665652488", phrase: "My height outfit >>",                                           hookType: "how_to",     views: "7.3M" },
  { id: "7616957249201638677", phrase: "Nhà 25 tỷ view mặt hồ Hoàn Kiếm",                              hookType: "bold_claim", views: "3.8M" },
  { id: "7619285253022125333", phrase: "Hôm nay mời mọi người mukbang combo mì cay và trà sữa",        hookType: "other",      views: "4.6M" },
  { id: "7625973407997267221", phrase: "Đũa bị mốc cực kỳ nguy hiểm mà bạn không để ý",               hookType: "pain_point", views: "2.0M" },
  { id: "7624842569465220368", phrase: "Mai mốt mà em có mở quán cơm á thì em sẽ bán món ba rọi chao", hookType: "bold_claim", views: "2.2M" },
];

// 4× R2-confirmed frame IDs per showcase column (probed 2026-04-09 — see STRIP_FRAME_IDS)
const NICHE_STRIP: { label: string; ids: string[] }[] = [
  { label: "Ẩm thực", ids: ["7619285253022125333", "7624842569465220368", "7621904918978252039", "7626756818085203207"] },
  { label: "Thời trang", ids: ["7622669408665652488", "7624501870622444821", "7620112412523433237", "7627166762894740757"] },
  { label: "Công nghệ", ids: ["7627432133937679624", "7627069060844457233", "7620672683994402069", "7627475293153905941"] },
  { label: "Sức khỏe", ids: ["7621463359350656277", "7625973407997267221", "7627068868820864276", "7624873937884826900"] },
  { label: "Giải trí", ids: ["7615811534962330901", "7616572388544695573", "7620342789313776917", "7617676901603101973"] },
];

function landingThumbSrcCandidates(videoId: string): string[] {
  const out: string[] = [];
  const push = (url: string | null) => {
    if (url && !out.includes(url)) out.push(url);
  };
  push(r2ThumbnailUrl(videoId, "webp"));
  push(r2ThumbnailUrl(videoId, "png"));
  push(r2FrameUrl(videoId));
  push(r2ThumbnailUrl(videoId, "jpg"));
  return out;
}

const HOOK_TYPE_LABELS: Record<string, string> = {
  warning: "Cảnh báo",
  number_shock: "Số liệu gây shock",
  question: "Câu hỏi kích tò mò",
  before_after: "Trước / sau",
  reveal: "Tiết lộ sự thật",
  challenge: "Thử thách",
  story: "Kể chuyện ngắn",
  comparison: "So sánh trực diện",
  tutorial: "Hướng dẫn nhanh",
};

function LiveDemoSection({
  stats,
  corpusLabel,
}: {
  stats: { hooks: { hook_type: string; avg_views: number; sample_size: number }[]; thumb_ids: string[] };
  corpusLabel: string;
}) {

  return (
    <section className="px-4 py-16 md:py-20 bg-[color:var(--gv-paper)]">
      <div className="max-w-6xl mx-auto">
        <p className="text-center text-sm text-[color:var(--gv-ink-3)] mb-2">Dữ liệu dẫn dắt mọi quyết định</p>
        <h2 className="gv-landing-h2-sm text-center font-extrabold text-[color:var(--gv-ink)] mb-3">
          Khám phá xu hướng viral,<br />phân tích insight chuyên sâu
        </h2>
        <p className="text-center text-sm text-[color:var(--gv-ink-3)] mb-12 max-w-xl mx-auto leading-relaxed">
          Loại bỏ mọi phỏng đoán. GetViews cung cấp cái nhìn sâu sắc về cấu trúc nội dung và chiến lược đang giúp các kênh đối thủ đạt được tăng trưởng vượt trội.
        </p>

        <div className="grid lg:grid-cols-[2fr_1fr] gap-6 mb-6">
          <motion.div
            initial={false}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4 }}
            className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-5 flex flex-col gap-1"
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-[color:var(--gv-ink)]">Phân tích tín hiệu xu hướng</h3>
              <Link to="/app/trends" className="text-xs text-[color:var(--gv-ink-3)] hover:text-[color:var(--gv-ink)] transition-colors duration-200">Xem tất cả →</Link>
            </div>

            {SIGNALS.map((s) => (
              <div key={s.key} className="flex items-center justify-between py-2.5 border-b border-[color:var(--gv-rule)] last:border-0">
                <div className="flex items-center gap-2.5">
                  <div className={`h-2.5 w-2.5 rounded-full flex-shrink-0 ${s.dot}`} />
                  <div>
                    <p className="text-sm font-medium text-[color:var(--gv-ink)]">{s.label}</p>
                    <p className="text-xs text-[color:var(--gv-ink-3)]">{s.sub}</p>
                  </div>
                </div>
                {/* Overlapping thumbnail circles */}
                <div className="flex -space-x-2 flex-shrink-0">
                  {SIGNAL_VIDEOS[s.key].map((id, i) => (
                    <div
                      key={id}
                      className="h-8 w-8 rounded-full overflow-hidden border-2 border-[color:var(--gv-paper)] bg-[color:var(--gv-canvas-2)]"
                      style={{ zIndex: 3 - i }}
                    >
                      <VideoThumb id={id} className="h-full w-full" />
                    </div>
                  ))}
                </div>
              </div>
            ))}

            <p className="text-xs text-[color:var(--gv-ink-3)] mt-2">Cập nhật mỗi tuần từ {corpusLabel} video thực</p>
          </motion.div>

          <motion.div
            initial={false}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-5 flex flex-col gap-1"
          >
            <p className="font-bold text-[color:var(--gv-ink)] mb-3">Top Hook dẫn đầu hiệu suất trong ngành</p>

            {HOOK_EXAMPLES.map((h, i) => (
              <div key={h.id} className="flex items-center gap-3 py-2 border-b border-[color:var(--gv-rule)] last:border-0">
                <span className="text-xs text-[color:var(--gv-ink-3)] w-4 flex-shrink-0 font-mono">{i + 1}</span>
                <div className="flex-shrink-0 overflow-hidden rounded-md bg-[color:var(--gv-canvas-2)]" style={{ width: 32, height: 44 }}>
                  <VideoThumb id={h.id} className="h-full w-full" />
                </div>
                <p className="flex-1 text-xs text-[color:var(--gv-ink)] line-clamp-2 leading-snug">{h.phrase}</p>
                <p className="flex-shrink-0 font-mono text-xs font-semibold text-[color:var(--gv-accent)] tabular-nums">{h.views}</p>
              </div>
            ))}
          </motion.div>
        </div>

        <motion.div
          initial={false}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-5"
        >
          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <h3 className="text-balance font-bold text-[color:var(--gv-ink)]">
                Kho dữ liệu TikTok Việt Nam
              </h3>
              <p className="mt-1 font-[family-name:var(--gv-font-mono)] text-sm font-semibold tabular-nums text-[color:var(--gv-ink-3)]">
                {corpusLabel} video được lập chỉ mục liên tục
              </p>
            </div>
            <Link
              to="/app/trends"
              className="shrink-0 text-xs text-[color:var(--gv-ink-3)] transition-colors duration-200 hover:text-[color:var(--gv-ink)]"
            >
              Tìm đối thủ →
            </Link>
          </div>

          <div className="flex gap-4 overflow-x-auto pb-1">
            {NICHE_STRIP.map((niche) => (
              <div key={niche.label} className="flex-shrink-0 flex flex-col gap-1.5">
                <p className="text-[11px] font-semibold text-[color:var(--gv-ink-3)] gv-kicker tracking-wide">{niche.label}</p>
                <div className="flex gap-1">
                  {niche.ids.map((id) => (
                    <div
                      key={id}
                      className="overflow-hidden rounded-lg bg-[color:var(--gv-canvas-2)] flex-shrink-0"
                      style={{ width: 52, height: 72 }}
                    >
                      <VideoThumb id={id} className="h-full w-full" />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <p className="text-xs text-[color:var(--gv-ink-3)] mt-3 text-center">Phân tích sâu rộng trên 21 niche creator thịnh hành nhất Việt Nam</p>
        </motion.div>
      </div>
    </section>
  );
}

const INFRA_FEATURE_TEMPLATES = [
  { icon: Database,      labelKey: "corpus" as const,      sub: "Kho dữ liệu TikTok Việt Nam, kiểm chứng được" },
  { icon: Play,          labelKey: "analyze" as const,    sub: "AI xem frame thực, không đoán mò" },
  { icon: Globe,         labelKey: "niche" as const,      sub: "Làm đẹp, ẩm thực, tài chính, công nghệ..." },
  { icon: Zap,           labelKey: "hook" as const,       sub: "Từ video breakout thực tế, không phải lý thuyết" },
  { icon: Search,        labelKey: "rival" as const,      sub: "Tra @handle, ra ngay chiến lược của họ" },
  { icon: MessageCircle, labelKey: "vi" as const,         sub: "Hỏi tiếng Việt, trả lời tiếng Việt" },
  { icon: ExternalLink,  labelKey: "cite" as const,       sub: "Mọi gợi ý đều kèm video thật, bấm xem được" },
  { icon: RefreshCw,     labelKey: "refresh" as const,    sub: "Data mới mỗi tuần, không dùng data cũ" },
] as const;

function infraFeatureLabel(key: (typeof INFRA_FEATURE_TEMPLATES)[number]["labelKey"], corpusLabel: string): string {
  switch (key) {
    case "corpus":
      return `Hơn ${corpusLabel} video thực tế`;
    case "analyze":
      return "Phân tích video chuyên sâu";
    case "niche":
      return "Hỗ trợ 21 niche creator";
    case "hook":
      return "Mẫu hook hiệu suất cao";
    case "rival":
      return "Phân tích đối thủ trực diện";
    case "vi":
      return "AI tối ưu cho tiếng Việt";
    case "cite":
      return "Dữ liệu có dẫn chứng";
    case "refresh":
      return "Cập nhật dữ liệu liên tục";
  }
}

function InfraGrid({ corpusLabel }: { corpusLabel: string }) {
  return (
    <section className="px-4 py-16 bg-[color:var(--gv-canvas)]">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-10">
          <p className="text-xs font-semibold uppercase tracking-widest text-[color:var(--gv-ink-3)] mb-3">
            Nền tảng công nghệ
          </p>
          <h2
            className="gv-landing-h3 font-extrabold text-[color:var(--gv-ink)] mb-3"
          >
            Câu trả lời dựa trên{" "}
            <span className="text-[color:var(--gv-accent)]">dữ liệu TikTok xác thực</span>
          </h2>
          <p className="text-sm text-[color:var(--gv-ink-3)] max-w-xl mx-auto">
            GetViews vượt xa các công cụ AI tổng quát. Chúng tôi xây dựng hệ thống thu thập, phân tích và lập chỉ mục video TikTok Việt Nam liên tục, đảm bảo mọi insight đều có nguồn gốc rõ ràng và có thể kiểm chứng.
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {INFRA_FEATURE_TEMPLATES.map(({ icon: Icon, labelKey, sub }) => {
            const label = infraFeatureLabel(labelKey, corpusLabel);
            return (
            <motion.div
              key={labelKey}
              initial={false}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.35 }}
              className="rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5 flex flex-col gap-3"
            >
              <Icon className="h-6 w-6 text-[color:var(--gv-ink-3)]" strokeWidth={1.5} />
              <div>
                <p className="text-sm font-bold text-[color:var(--gv-ink)] leading-snug mb-1">{label}</p>
                <p className="text-xs text-[color:var(--gv-ink-3)] leading-snug">{sub}</p>
              </div>
            </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

const SAMPLE_QUERIES = [
  "Công thức hook nào đang dẫn đầu lượt xem trong mảng làm đẹp?",
  "Phân tích kênh @đối_thủ — họ đang làm gì hiệu quả?",
  "Tại sao video này chỉ đạt 500 lượt xem?",
  "Viết kịch bản KOL chi tiết cho mảng skincare",
];

function CredibilitySection({
  corpusLabel,
  loginPath,
}: {
  corpusLabel: string;
  loginPath: string;
}) {
  return (
    <section className="px-4 py-16 bg-[color:var(--gv-paper)]">
      <div className="max-w-5xl mx-auto grid md:grid-cols-2 gap-12 items-center">

        {/* Left — credibility copy */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-[color:var(--gv-ink-3)] mb-4">
            Tại sao chúng tôi xây dựng GetViews
          </p>
          <h2
            className="gv-landing-h3-tight font-extrabold text-[color:var(--gv-ink)] mb-5 leading-tight"
          >
            Nâng tầm video với{" "}
            <span className="text-[color:var(--gv-accent)]">quyết định dựa trên dữ liệu</span>
          </h2>
          <p className="text-sm text-[color:var(--gv-ink-3)] leading-relaxed mb-6">
            Là những người trực tiếp sáng tạo và phát triển kênh TikTok, chúng tôi hiểu rõ thách thức khi phải đưa ra quyết định nội dung dựa vào cảm tính. GetViews được tạo ra để thay đổi điều đó: mọi phân tích và gợi ý đều đi kèm bằng chứng từ hàng triệu video TikTok thực tế, giúp bạn tự tin đưa ra chiến lược tối ưu.
          </p>
          <Link
            to={loginPath}
            className="inline-flex items-center justify-center rounded-lg bg-[color:var(--gv-accent)] px-6 py-3 text-sm font-medium text-white transition-all duration-[120ms] hover:bg-[color:var(--gv-accent-deep)] active:scale-95"
          >
            Phân tích ngay — miễn phí
          </Link>
        </div>

        {/* Right — product UI mock */}
        <div className="rounded-2xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] overflow-hidden shadow-sm">
          <div className="px-4 py-3 border-b border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]">
            <p className="text-xs font-semibold text-[color:var(--gv-ink)] text-center">GetViews AI</p>
          </div>
          <div className="p-4">
            <p className="text-xs text-[color:var(--gv-ink-3)] mb-3">Bắt đầu với</p>
            <div className="flex flex-col gap-2">
              {SAMPLE_QUERIES.map((q) => (
                <div
                  key={q}
                  className="rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2.5 text-xs text-[color:var(--gv-ink-3)]"
                >
                  {q}
                </div>
              ))}
            </div>
          </div>
          <div className="px-4 pb-4">
            <div className="flex items-center gap-2 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2.5">
              <p className="flex-1 text-xs text-[color:var(--gv-ink-3)]">Dán link TikTok hoặc đặt câu hỏi...</p>
              <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-[color:var(--gv-accent)]">
                <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none">
                  <path d="M3 8h10M9 4l4 4-4 4" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            </div>
            <p className="text-[11px] text-[color:var(--gv-ink-3)] text-center mt-2">
              {corpusLabel} video · 21 niche · Cập nhật hàng tuần
            </p>
          </div>
        </div>

      </div>
    </section>
  );
}

function HowItWorksSection() {
  const steps = [
    {
      num: "01",
      title: "Dán liên kết video TikTok",
      body: "Đơn giản chỉ cần dán đường dẫn video TikTok của bạn hoặc đối thủ. Hệ thống AI của GetViews sẽ tự động quét, trích xuất dữ liệu hình ảnh, âm thanh và văn bản chuyên sâu.",
    },
    {
      num: "02",
      title: "Đối chiếu với kho dữ liệu Big Data",
      body: "GetViews sẽ đối chiếu video của bạn với hàng chục nghìn video TikTok đã được lập chỉ mục trong kho dữ liệu (corpus) khổng lồ, để tìm ra các điểm tương đồng và khác biệt về cấu trúc nội dung, hook, và định dạng.",
    },
    {
      num: "03",
      title: "Nhận phân tích chi tiết & gợi ý hành động",
      body: "Nhận báo cáo chi tiết về lý do video của bạn (hoặc đối thủ) chưa hiệu quả. Biết chính xác hook cần cải thiện ở giây nào, dạng nội dung nào đang lên xu hướng trong ngách của bạn, kèm video mẫu tham khảo để bạn dễ dàng hành động.",
    },
  ];

  return (
    <section className="px-4 py-16 md:py-20 bg-[color:var(--gv-canvas)]">
      <div className="max-w-5xl mx-auto">
        <p className="mb-3 text-center text-sm uppercase tracking-wider text-[color:var(--gv-ink-3)]">Tăng trưởng hiệu quả</p>
        <h2 className="gv-landing-h2-sm text-center font-extrabold text-[color:var(--gv-ink)] mb-10 md:mb-14">
          Quy trình phân tích chuyên sâu, tối ưu nội dung của bạn
        </h2>

        <div className="relative">
          <div className="hidden md:block absolute top-8 left-[calc(16.67%+1.5rem)] right-[calc(16.67%+1.5rem)] h-px bg-[color:var(--gv-rule)] z-0" />
          <div className="grid md:grid-cols-3 gap-10 md:gap-8">
            {steps.map((step, i) => (
              <motion.div
                key={step.num}
                initial={false}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.4, delay: i * 0.12 }}
                className="flex items-center gap-4 md:flex-col md:items-center md:text-center md:gap-0"
              >
                <div className="relative z-10 flex-shrink-0">
                  <div className="w-16 h-16 bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded flex items-center justify-center md:mb-6">
                    <span className="font-mono font-bold text-lg text-[color:var(--gv-ink)]">{step.num}</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-[color:var(--gv-ink)] mb-2 text-base">{step.title}</h3>
                  <p className="text-sm text-[color:var(--gv-ink-3)] leading-relaxed">{step.body}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

interface LandingStats {
  hooks: { hook_type: string; avg_views: number; sample_size: number }[];
  thumb_ids: string[];
  corpus_indexed_count: number | null;
}

function loginPathFromHeroPaste(pasted: string): string {
  const result = resolveLandingHeroSubmit(pasted);
  return result.ok ? result.loginPath : "/login";
}

export default function LandingPage({ stats }: { stats: LandingStats }) {
  const navigate = useNavigate();
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "biannual" | "annual">("annual");
  const [stickyVisible, setStickyVisible] = useState(false);
  const [heroUrl, setHeroUrl] = useState("");
  const [heroUrlError, setHeroUrlError] = useState<string | null>(null);
  const corpusLabel = formatCorpusMarketingCount(stats.corpus_indexed_count);
  const faqs = buildFaqs(corpusLabel);
  const heroUrlChip = queryUrlChipState(heroUrl);
  const loginPath = useMemo(() => loginPathFromHeroPaste(heroUrl), [heroUrl]);

  const submitHeroCta = useCallback(() => {
    const result = resolveLandingHeroSubmit(heroUrl);
    if (!result.ok) {
      setHeroUrlError(result.error);
      return;
    }
    setHeroUrlError(null);
    const q = result.loginPath.split("?")[1];
    if (q) {
      persistPostLoginNextFromSearch(new URLSearchParams(q));
    }
    navigate(result.loginPath);
  }, [heroUrl, navigate]);

  const handleHeroFormSubmit = useCallback(
    (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      submitHeroCta();
    },
    [submitHeroCta],
  );

  useEffect(() => {
    const handleScroll = () => setStickyVisible(window.scrollY > 480);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const plans = pricingPlans[billingPeriod];

  return (
    <div className="gv-studio-type min-h-dvh bg-[linear-gradient(180deg,var(--gv-paper)_0%,var(--gv-canvas-2)_100%)] text-[color:var(--gv-ink)]">
      {/* Top accent — same language as /login card chrome (visible Studio signal) */}
      <div className="h-1 w-full bg-[color:var(--gv-accent)]" aria-hidden />
      {/* ── Sticky Bar ─────────────────────────────────────────── */}
      <AnimatePresence>
        {stickyVisible && (
          <motion.div
            initial={{ y: 64 }}
            animate={{ y: 0 }}
            exit={{ y: 64 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="fixed bottom-0 left-0 right-0 z-50 border-t border-[color:var(--gv-rule)] bg-[color:var(--gv-ink)] pb-[env(safe-area-inset-bottom)]"
          >
            <div className="max-w-3xl mx-auto flex items-center justify-between px-4 py-3">
              <span className="font-extrabold text-white text-sm">
                GetViews<span className="text-[color:var(--brand-red)]">.vn</span>
              </span>
              <div className="flex items-center gap-4">
                <span className="text-xs text-white/60 hidden sm:block">Không cần thẻ tín dụng</span>
                <Link
                  to={loginPath}
                  className="inline-flex items-center justify-center rounded-lg bg-[color:var(--gv-paper)] px-5 py-2 text-sm font-medium text-[color:var(--gv-ink)] transition-colors duration-[120ms] hover:bg-[color:var(--gv-canvas-2)] active:scale-95"
                >
                  Phân tích miễn phí
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Hero (transparent so the page shell gradient shows through) ── */}
      <section className="relative bg-transparent px-4 pt-6 pb-20 md:pb-32">
        <div className="max-w-6xl mx-auto">
          {/* Top Nav */}
          <div className="flex items-center justify-center mb-16">
            <span className="font-extrabold text-xl text-[color:var(--gv-ink)]">
              GetViews<span className="text-[color:var(--brand-red)]">.vn</span>
            </span>
          </div>

          {/* Hero Grid */}
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left: Copy + CTA */}
            <div>
              <motion.div
                initial={false}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.32 }}
              >
                <div className="inline-flex items-center gap-2 bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-full px-4 py-2 mb-6">
                  <span className="text-sm font-medium text-[color:var(--gv-ink-3)]">Chẩn đoán TikTok · corpus video thật · Việt Nam</span>
                </div>

                <h1 className="gv-landing-h1 font-extrabold leading-[1.2] mb-6">
  <span className="text-[color:var(--gv-ink)]">Phân tích TikTok</span>
  <br />
  <span className="text-[color:var(--gv-accent)]">Đừng chạy theo trend, hãy tạo trend.</span>
                </h1>

                <p className="text-lg text-[color:var(--gv-ink-3)] mb-8 max-w-lg leading-relaxed">
                  Dán link video đối thủ hoặc của bạn → Nhận ngay chẩn đoán chuyên sâu sau 1 phút.
                  Nắm bắt <span className="font-semibold text-[color:var(--gv-ink)]">chiến lược nội dung thành công</span>,
                  phát hiện <span className="font-semibold text-[color:var(--gv-ink)]">hook đang chạy tốt</span>,
                  và <span className="font-semibold text-[color:var(--gv-ink)]">tối ưu định dạng viral</span>. Tất cả dựa trên dữ liệu thực, không cảm tính.
                </p>

                {/* CTA — one form so Enter and button share the same submit path */}
                <form
                  className="mb-0"
                  onSubmit={handleHeroFormSubmit}
                  aria-label="Dán link TikTok và bắt đầu phân tích"
                >
                  <div
                    className={`flex flex-col gap-2 rounded-xl border bg-[color:var(--gv-paper)] p-1.5 shadow-sm transition-all duration-200 sm:flex-row sm:items-stretch ${
                      heroUrlError
                        ? "border-[color:var(--destructive)]"
                        : "border-[color:var(--gv-rule)] hover:border-[color:var(--gv-ink)]/30 hover:shadow-md"
                    }`}
                  >
                    <div className="flex min-h-[44px] flex-1 items-center gap-2 px-3 py-2">
                      <input
                        type="url"
                        inputMode="url"
                        autoComplete="url"
                        name="tiktok_url"
                        aria-label="Link video hoặc kênh TikTok"
                        aria-invalid={heroUrlError ? true : undefined}
                        aria-describedby={
                          heroUrlError
                            ? "hero-url-error"
                            : heroUrlChip.kind === "tiktok"
                              ? "hero-url-ok"
                              : undefined
                        }
                        placeholder="https://tiktok.com/@..."
                        value={heroUrl}
                        onChange={(e) => {
                          setHeroUrl(e.target.value);
                          if (heroUrlError) setHeroUrlError(null);
                        }}
                        className="min-w-0 flex-1 border-0 bg-transparent text-base text-[color:var(--gv-ink)] placeholder:text-[color:var(--gv-ink-4)] focus:outline-none focus:ring-0"
                      />
                    </div>
                    <button
                      type="submit"
                      className="inline-flex min-h-[44px] shrink-0 items-center justify-center rounded-lg bg-[color:var(--gv-accent)] px-6 py-3 text-base font-semibold text-white transition-all duration-[120ms] hover:bg-[color:var(--gv-accent-deep)] active:scale-[0.98] sm:rounded-lg"
                    >
                      Phân tích →
                    </button>
                  </div>
                  {heroUrlChip.kind === "tiktok" ? (
                    <p
                      id="hero-url-ok"
                      className="mt-2 text-sm text-[color:var(--gv-ink-3)]"
                    >
                      {formatTikTokSidebarHint(heroUrl) ? (
                        <>
                          Đã nhận link TikTok{" "}
                          <span className="font-[family-name:var(--gv-font-mono)] text-[color:var(--gv-ink)]">
                            {formatTikTokSidebarHint(heroUrl)}
                          </span>
                          {" "}
                          — bấm Phân tích hoặc Enter để tiếp tục.
                        </>
                      ) : (
                        "Đã nhận link TikTok — bấm Phân tích hoặc Enter để tiếp tục."
                      )}
                    </p>
                  ) : null}
                  {heroUrlError ? (
                    <p
                      id="hero-url-error"
                      className="mt-2 text-sm text-[color:var(--destructive)]"
                      role="alert"
                    >
                      {heroUrlError}
                    </p>
                  ) : null}
                </form>

                <p className="mt-3 max-w-lg border-t border-[color:var(--gv-rule-2)] pt-3 text-[11px] leading-relaxed text-[color:var(--gv-ink-4)]">
  <span className="font-medium text-[color:var(--gv-ink-3)]">Bắt đầu ngay —</span>{" "}
  10 lượt phân tích miễn phí · không cần thẻ tín dụng · trải nghiệm tức thì
                </p>
              </motion.div>
            </div>

            {/* Right: demo diagnosis card (no absolute overlays — avoids collision at ~1558px) */}
            <motion.div
              initial={false}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: 0.2 }}
              className="hidden min-w-0 lg:block"
            >
              <div className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-6">
                <div className="mb-4 flex flex-wrap items-start justify-between gap-3 border-b border-[color:var(--gv-rule)] pb-4">
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-[color:var(--gv-ink)] text-xs font-bold text-white">
                      GV
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-[color:var(--gv-ink)]">GetViews AI</p>
                      <p className="flex items-center gap-1 text-xs text-[color:var(--gv-ink-3)]">
                        <span className="h-1.5 w-1.5 rounded-full bg-[color:var(--gv-ink)]" />
                        Đang phân tích chuyên sâu...
                      </p>
                    </div>
                  </div>
                  <div className="shrink-0 rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-3 py-2 text-right">
                    <p className="text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
                      Video trong corpus
                    </p>
                    <p className="font-[family-name:var(--gv-font-mono)] text-base font-bold tabular-nums text-[color:var(--gv-ink)]">
                      {corpusLabel}
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="bg-[color:var(--gv-paper)] rounded-xl p-3">
                    <div className="flex items-start gap-2 mb-2">
                      <span className="font-bold text-[color:var(--danger)]">✕</span>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-[color:var(--gv-ink)] mb-1">Hook vào quá chậm (2.3s)</p>
                        <p className="text-xs text-[color:var(--gv-ink-3)]">Top video nhiều lượt xem thường mở màn ở 0.5s</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-[color:var(--gv-paper)] rounded-xl p-3">
                    <div className="flex items-start gap-2 mb-2">
                      <span className="font-bold text-[color:var(--danger)]">✕</span>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-[color:var(--gv-ink)] mb-1">Thiếu "mặt người" ở đầu</p>
                        <p className="text-xs text-[color:var(--gv-ink-3)]">92% video nhiều view trong ngách mở mặt trong 0,5 giây</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-[color:var(--gv-paper)] rounded-xl p-3 border border-[color:var(--gv-rule)]">
                    <div className="flex items-start gap-2">
                      <span className="font-bold text-[color:var(--success)]">✓</span>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-[color:var(--gv-ink)] mb-1">Dùng Hook "Cảnh Báo" là chuẩn</p>
                        <p className="text-xs text-[color:var(--gv-ink-3)]">Cảnh Báo · 3,4× lượt xem TB ngách so với Kể Chuyện</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-4 flex flex-col gap-2 border-t border-[color:var(--gv-rule)] pt-4 sm:flex-row sm:items-end sm:justify-between sm:gap-4">
                  <p className="min-w-0 text-xs font-[family-name:var(--gv-font-mono)] text-[color:var(--gv-ink-3)]">
                    Minh họa · so khớp corpus skincare · 7 ngày qua
                  </p>
                  <p className="shrink-0 text-[10px] leading-snug text-[color:var(--gv-ink-4)]">
                    <span className="font-medium text-[color:var(--gv-ink-3)]">21 niche creator</span>
                    <span className="hidden sm:inline"> · </span>
                    <span className="block sm:inline">Skincare · Review · Food · Affiliate…</span>
                  </p>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Trust Badges */}
          <motion.div
            initial={false}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.32, delay: 0.4 }}
            className="mt-16 flex flex-wrap items-center justify-center gap-6 text-sm text-[color:var(--gv-ink-3)]"
          >
            <div className="flex items-center gap-2"><span>Data 100% từ TikTok Việt</span></div>
            <div className="hidden sm:block w-px h-4 bg-[color:var(--gv-rule)]" />
            <div className="flex items-center gap-2"><span>Cập nhật hàng tuần</span></div>
            <div className="hidden sm:block w-px h-4 bg-[color:var(--gv-rule)]" />
            <div className="flex items-center gap-2"><span>Chuyên biệt cho 21 niche creator</span></div>
          </motion.div>

          {/* Hook Ticker */}
          <motion.div
            initial={false}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.32, delay: 0.4 }}
            className="mt-10 overflow-hidden border-t border-[color:var(--gv-rule)] pt-5"
          >
            <p className="text-xs text-[color:var(--gv-ink-3)] mb-3 text-center">
              Ví dụ hook trong corpus (hệ số TB ngách · 7 ngày — không phải lời hứa view)
            </p>
            <div className="flex gap-3 animate-scroll-ticker">
              {[...hookTicker, ...hookTicker].map((hook, i) => (
                <div key={i} className="flex-shrink-0 border border-[color:var(--gv-rule)] rounded bg-[color:var(--gv-paper)] px-4 py-2">
                  <span className="text-xs text-[color:var(--gv-ink-3)] whitespace-nowrap">{hook}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── Statement ───────────────────────────────────────────── */}
      <section className="px-4 py-20 md:py-28 bg-[color:var(--gv-paper)]">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="gv-landing-h2-lg font-extrabold text-[color:var(--gv-ink)] leading-[1.4]">
            Corpus TikTok Việt được lập chỉ mục liên tục — so sánh video của bạn với mẫu đang chạy trong từng&nbsp;ngách
          </h2>
        </div>
      </section>

      {/* ── Niche Chips ─────────────────────────────────────────── */}
      <div className="px-4 pb-16 bg-[color:var(--gv-paper)]">
        <div className="max-w-4xl mx-auto">
          <p className="text-xs text-center text-[color:var(--gv-ink-3)] mb-4">Dành cho 21 nhóm creator thịnh hành tại Việt Nam</p>
          <div className="flex flex-wrap justify-center gap-2">
            {nicheList.map((niche) => (
              <span
                key={niche}
                className="text-xs text-[color:var(--gv-ink-3)] border border-[color:var(--gv-rule)] rounded-full px-3 py-1.5 bg-[color:var(--gv-paper)] transition-colors duration-[120ms] hover:border-[color:var(--gv-ink)] hover:text-[color:var(--gv-ink)] cursor-default"
              >
                {niche}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ── Pain Points ─────────────────────────────────────────── */}
      <section className="px-4 py-16 md:py-20 bg-[color:var(--gv-paper)]">
        <div className="max-w-5xl mx-auto">
          <p className="text-center text-sm text-[color:var(--gv-ink-3)] mb-3 uppercase tracking-wide">Thực tế phũ phàng</p>
          <h2 className="gv-landing-h2-sm text-center font-extrabold text-[color:var(--gv-ink)] mb-10 md:mb-16">
            Đa số creator Việt đang làm như thế nào?
          </h2>
          <div className="grid md:grid-cols-3 gap-8 md:gap-16">
            {painPoints.map((p, idx) => (
              <motion.div
                key={p.title}
                initial={false}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.4, delay: idx * 0.1 }}
                className="text-center"
              >
                <div className="mb-6 flex justify-center">
                  <div className="w-16 h-16 border-2 border-[color:var(--gv-rule)] rounded flex items-center justify-center transition-transform duration-200 hover:scale-110">
                    <span className="font-mono font-bold text-2xl text-[color:var(--gv-ink-3)]">{idx + 1}</span>
                  </div>
                </div>
                <h3 className="font-bold text-[color:var(--gv-ink)] mb-4 text-base">{p.title}</h3>
                <p className="text-sm text-[color:var(--gv-ink-3)] leading-relaxed max-w-xs mx-auto">{p.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ────────────────────────────────────────── */}
      <HowItWorksSection />

      {/* ── Solutions ───────────────────────────────────────────── */}
      <SolutionCardsSection />

      {/* ── Live Demo ───────────────────────────────────────────── */}
      <LiveDemoSection stats={stats} corpusLabel={corpusLabel} />

      {/* ── Infrastructure + Credibility ─────────────────────────── */}
      <InfraGrid corpusLabel={corpusLabel} />
      <CredibilitySection corpusLabel={corpusLabel} loginPath={loginPath} />

      {/* ── Results ─────────────────────────────────────────────── */}
      <section className="px-4 py-16 md:py-20 bg-[color:var(--gv-paper)]">
        <div className="max-w-5xl mx-auto">
          <p className="text-center text-sm text-[color:var(--gv-ink-3)] mb-3">Kết quả chuyên sâu</p>
          <h2 className="gv-landing-h2-sm text-center font-extrabold text-[color:var(--gv-ink)] mb-3">
            Insight có số liệu, không phỏng đoán
          </h2>
          <p className="text-center text-sm text-[color:var(--gv-ink-3)] mb-12 max-w-xl mx-auto leading-relaxed">
            GetViews cung cấp phân tích cấu trúc video chi tiết và đối chiếu với các mẫu thành công trong cùng niche, trao quyền cho bạn đưa ra các quyết định sáng tạo hiệu quả.
          </p>

          <motion.div
            initial={false}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4 }}
            className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-6 md:p-8 mb-6"
            aria-label="Ví dụ chẩn đoán video flop — lỗi hook và so sánh ngách"
          >
            <p className="text-xs text-[color:var(--gv-ink-3)] mb-4 uppercase tracking-wide">
              Ví dụ · video review đồ gia dụng
            </p>
            <div className="space-y-3">
              <div className="flex items-start gap-2">
                <span className="text-sm font-bold text-[color:var(--danger)]">✕</span>
                <div>
                  <p className="text-sm font-medium text-[color:var(--gv-ink)]">Hook vào chậm 2,3 giây</p>
                  <p className="text-xs text-[color:var(--gv-ink-3)]">92% video nhiều view trong ngách mở mặt trong 0,5 giây</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-sm font-bold text-[color:var(--danger)]">✕</span>
                <div>
                  <p className="text-sm font-medium text-[color:var(--gv-ink)]">Không có mặt người ở 3 giây đầu</p>
                  <p className="text-xs text-[color:var(--gv-ink-3)]">So với mẫu top trong corpus cùng ngách</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-sm font-bold text-[color:var(--success)]">✓</span>
                <div>
                  <p className="text-sm font-medium text-[color:var(--gv-ink)]">Hook &ldquo;Cảnh Báo&rdquo; đang dẫn trong ngách</p>
                  <p className="text-xs text-[color:var(--gv-ink-3)]">3,4× lượt xem TB so với &ldquo;Kể Chuyện&rdquo; · 7 ngày qua</p>
                </div>
              </div>
            </div>
            <p className="text-xs font-mono text-[color:var(--gv-ink-3)] mt-6 pt-4 border-t border-[color:var(--gv-rule)]">
              Minh họa · so khớp corpus review đồ gia dụng · 7 ngày qua — không cam kết kết quả view
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-4">
            {testimonials.map((t, i) => (
              <motion.div
                key={t.handle}
                initial={false}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-5"
              >
                <p className="text-sm text-[color:var(--gv-ink-3)] leading-relaxed mb-5">&ldquo;{t.quote}&rdquo;</p>
                <div className="flex items-center gap-3 pt-4 border-t border-[color:var(--gv-rule)]">
                  <div className="w-8 h-8 rounded bg-[color:var(--gv-ink)] flex items-center justify-center flex-shrink-0">
                    <span className="text-white text-xs font-bold">{t.initials}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-[color:var(--gv-ink)] truncate">{t.handle}</p>
                    <p className="text-xs text-[color:var(--gv-ink-3)] truncate">{t.niche} · {t.followers}</p>
                  </div>
                  <div className="flex-shrink-0">
                    <span className="font-mono text-xs font-bold text-[color:var(--gv-ink)]">{t.stat}</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ─────────────────────────────────────────────── */}
      <section className="px-4 py-16 bg-[color:var(--gv-paper)]" id="pricing">
        <div className="max-w-5xl mx-auto">
          <h2 className="font-extrabold text-[color:var(--gv-ink)] mb-2 text-center" style={{ fontSize: "1.75rem" }}>
            Chọn gói nâng cấp, tối ưu chiến lược
          </h2>
          <p className="text-sm text-[color:var(--gv-ink-3)] text-center mb-8">
            Thanh toán linh hoạt qua MoMo, VNPay, chuyển khoản ngân hàng hoặc thẻ quốc tế.
          </p>

          <div className="flex justify-center mb-8">
            <div className="inline-flex bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-lg p-1">
              {(["monthly", "biannual", "annual"] as const).map((period) => (
                <button
                  key={period}
                  onClick={() => setBillingPeriod(period)}
                  className={`px-5 py-2 rounded-md text-sm font-medium transition-all duration-[120ms] relative ${
                    billingPeriod === period
                      ? "bg-[color:var(--gv-ink)] text-white"
                      : "text-[color:var(--gv-ink-3)] hover:text-[color:var(--gv-ink)]"
                  }`}
                >
                  {period === "monthly" ? "Tháng" : period === "biannual" ? "6 tháng" : "Năm"}
                  {period === "annual" && billingPeriod !== "annual" && (
                    <span className="absolute -top-2 -right-2 bg-[color:var(--gv-ink)] text-white text-[11px] px-1.5 py-0.5 rounded-full font-medium whitespace-nowrap">
                      Tiết kiệm 20%
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          <div
            key={billingPeriod}
            className="grid grid-cols-1 sm:grid-cols-3 gap-3 md:gap-4 mb-4"
          >
            {plans.map((plan, idx) => {
              const price = planPricePresentation(plan.name, billingPeriod);
              return (
              <motion.div
                key={`${plan.name}-${billingPeriod}`}
                initial={false}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: idx * 0.05 }}
                whileHover={{ y: -4 }}
                className={`border rounded-xl p-5 relative bg-[color:var(--gv-paper)] transition-colors duration-200 hover:border-[color:var(--gv-ink-3)] ${
                  plan.popular ? "border-[color:var(--gv-ink)] border-2" : "border-[color:var(--gv-rule)]"
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="bg-[color:var(--gv-ink)] text-white text-xs px-3 py-1 rounded-full font-medium">Phổ biến</span>
                  </div>
                )}
                <h3 className="font-bold text-[color:var(--gv-ink)] mb-1">{plan.label}</h3>
                <div className="mb-3 min-h-[4.5rem]">
                  <div className="flex flex-wrap items-baseline gap-x-1.5 gap-y-0.5">
                    {price.strikePrice ? (
                      <span className="font-[family-name:var(--gv-font-mono)] text-sm text-[color:var(--gv-ink-4)] line-through tabular-nums">
                        {price.strikePrice}
                      </span>
                    ) : null}
                    <span
                      className="font-[family-name:var(--gv-font-mono)] font-bold tabular-nums text-[color:var(--gv-ink)]"
                      style={{ fontSize: "1.25rem" }}
                    >
                      {price.mainPrice}
                    </span>
                    {price.showPerMonthSuffix ? (
                      <span className="text-xs text-[color:var(--gv-ink-3)]">/tháng</span>
                    ) : null}
                  </div>
                  {price.billingLine ? (
                    <p className="mt-1 font-[family-name:var(--gv-font-mono)] text-[11px] leading-snug text-[color:var(--gv-ink-3)]">
                      {price.billingLine}
                    </p>
                  ) : null}
                  {price.savingsLine ? (
                    <p className="mt-0.5 text-[11px] font-medium leading-snug text-[color:var(--gv-accent-deep)]">
                      {price.savingsLine}
                    </p>
                  ) : null}
                </div>
                <p className="text-xs text-[color:var(--gv-ink-3)] mb-5" style={{ lineHeight: "1.5" }}>{plan.credits}</p>
                <Link
                  to={loginPath}
                  className={`inline-flex w-full items-center justify-center rounded-lg px-6 py-3 text-sm font-medium transition-all duration-[120ms] ease-out active:scale-95 ${
                    plan.popular
                      ? "bg-[color:var(--gv-accent)] text-white hover:bg-[color:var(--gv-accent-deep)] disabled:pointer-events-none disabled:cursor-not-allowed disabled:border-[color:var(--gv-rule)] disabled:bg-[color:var(--gv-faint)] disabled:text-[color:var(--gv-ink-4)] disabled:opacity-100"
                      : "border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink)] hover:bg-[color:var(--gv-rule-2)]"
                  } py-2`}
                >
                  {plan.name === "Free" ? "Bắt đầu miễn phí" : `Kích hoạt gói ${plan.name}`}
                </Link>
              </motion.div>
            );
            })}
          </div>

          {pricingSavings[billingPeriod] && (
            <p className="text-center text-sm text-[color:var(--gv-ink-3)]">{pricingSavings[billingPeriod]}</p>
          )}
        </div>
      </section>

      {/* ── FAQ ─────────────────────────────────────────────────── */}
      <section className="bg-[color:var(--gv-canvas)] px-4 py-16">
        <div className="mx-auto max-w-2xl">
          <h2 className="mb-8 text-center text-2xl font-extrabold text-[color:var(--gv-ink)]">
            Câu hỏi thường gặp
          </h2>
          <Accordion.Root type="single" collapsible className="space-y-3">
            {faqs.map((faq, idx) => (
              <motion.div
                key={idx}
                initial={false}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: idx * 0.05 }}
              >
                <Accordion.Item
                  value={`item-${idx}`}
                  className="border border-[color:var(--gv-rule)] rounded-xl overflow-hidden bg-[color:var(--gv-paper)]"
                >
                  <Accordion.Header>
                    <Accordion.Trigger className="w-full px-5 py-4 text-left font-medium text-[color:var(--gv-ink)] hover:bg-[color:var(--gv-canvas-2)] transition-colors duration-[200ms] flex items-center justify-between group">
                      <span className="text-sm">{faq.q}</span>
                      <ChevronDown className="w-4 h-4 text-[color:var(--gv-ink-3)] transition-transform duration-[200ms] group-data-[state=open]:rotate-180 flex-shrink-0 ml-3" />
                    </Accordion.Trigger>
                  </Accordion.Header>
                  <Accordion.Content
                    className="px-5 pb-4 text-sm text-[color:var(--gv-ink-3)] data-[state=open]:animate-accordion-down data-[state=closed]:animate-accordion-up"
                    style={{ lineHeight: "1.6" }}
                  >
                    {faq.a}
                  </Accordion.Content>
                </Accordion.Item>
              </motion.div>
            ))}
          </Accordion.Root>
        </div>
      </section>

      {/* ── Final CTA ───────────────────────────────────────────── */}
      <section className="px-4 py-20 md:py-24 bg-[color:var(--gv-ink)]">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="gv-landing-h2 font-extrabold text-white mb-6 leading-tight">
            Sẵn sàng để đưa kênh TikTok của bạn lên tầm cao mới?
          </h2>
          <Link
            to={loginPath}
            className="inline-flex items-center justify-center rounded-xl bg-[color:var(--gv-paper)] px-10 py-4 text-base font-semibold text-[color:var(--gv-ink)] transition-all duration-[120ms] hover:bg-[color:var(--gv-canvas-2)] active:scale-95"
          >
            Bắt đầu phân tích miễn phí
          </Link>
          <p className="text-sm text-white/60 mt-4">10 lượt phân tích chuyên sâu miễn phí · Không yêu cầu thẻ tín dụng</p>
        </div>
      </section>

      {stickyVisible && <div className="h-[calc(3.5rem+env(safe-area-inset-bottom))]" />}
    </div>
  );
}
