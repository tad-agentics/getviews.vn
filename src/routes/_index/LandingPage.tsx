import { useState, useEffect } from "react";
import { Link } from "react-router";
import { r2FrameUrl } from "@/lib/services/corpus-service";
import * as Accordion from "@radix-ui/react-accordion";
import { ChevronDown, Database, Play, Globe, Zap, Search, MessageCircle, ExternalLink, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { motion, AnimatePresence } from "motion/react";
import { pricingPlans, pricingSavings } from "@/lib/mock-data";

const faqs = [
  {
    q: "Cái này khác gì ChatGPT?",
    a: "ChatGPT không có data TikTok thực và không xem được video. Hỏi \"hook nào đang hot trong skincare\" — ChatGPT sẽ bịa một câu trả lời nghe hợp lý nhưng không dựa trên video nào thật. GetViews trả lời từ 1.500+ video thật, view thật — bạn có thể bấm vào xem để kiểm chứng ngay.",
  },
  {
    q: "Tôi không rành AI, dùng có khó không?",
    a: "Không cần biết AI. Bạn chỉ cần gõ câu hỏi như nhắn tin — \"hook nào đang hot trong niche ẩm thực?\" hay \"phân tích kênh @tenkenhdoithu\" — GetViews tự xử lý phần còn lại và trả về kết quả cụ thể, có dẫn chứng video.",
  },
  {
    q: "Tôi mua khóa học rồi, có cần dùng thêm cái này không?",
    a: "Khóa học dạy tư duy nền tảng: thuật toán, cách quay, cách edit. Rất tốt. Nhưng không thể nói tuần này mẫu video nào đang \"cắn\" đề xuất trong đúng niche của bạn. GetViews lấp đúng chỗ đó: data tươi, cập nhật liên tục, không đoán mò.",
  },
  {
    q: "Khác gì Kalodata hay Shoplus?",
    a: "Kalodata và Shoplus tập trung vào bán hàng — sản phẩm nào chạy, doanh số bao nhiêu. GetViews tập trung vào nội dung — TẠI SAO video đó viral, hook mở đầu như thế nào, nhịp cắt và format ra sao. Hai loại công cụ bổ trợ nhau, không thay thế nhau.",
  },
  {
    q: "1 credit tính như thế nào?",
    a: "Lướt xu hướng, tìm KOL, hỏi đáp thông thường — miễn phí hoàn toàn, không giới hạn. 1 credit dùng cho phân tích sâu: soi video frame-by-frame, phân tích toàn bộ kênh đối thủ, hoặc viết brief chi tiết cho video tiếp theo.",
  },
  {
    q: "Thanh toán có phức tạp không?",
    a: "Không. MoMo, VNPay, chuyển khoản ngân hàng hoặc thẻ Visa/Mastercard. Thanh toán xong là dùng được ngay — không cần chờ duyệt, không cần xác minh thêm.",
  },
];

const testimonials = [
  {
    initials: "MK",
    handle: "@minhk.review",
    niche: "Review đồ gia dụng",
    followers: "~50K",
    quote:
      "Quăng link video bị flop vào, 1 phút sau biết ngay lỗi: hook chậm 2.3 giây, không có mặt người ở đầu. Sửa lại đúng theo gợi ý — video sau lên thẳng 89K view.",
    stat: "89K view",
  },
  {
    initials: "LH",
    handle: "@linhbeauty.vn",
    niche: "Làm đẹp / Skincare",
    followers: "~120K",
    quote:
      "Trước đây toàn phải screenshot thủ công rồi quên sạch. Giờ chỉ cần hỏi \"hook nào hot tuần này\" — AI lọc ra luôn 5 mẫu đang viral nhất, kèm link video gốc để học theo.",
    stat: "3.2x avg views",
  },
  {
    initials: "TN",
    handle: "@techvn.review",
    niche: "Công nghệ / Tech",
    followers: "~30K",
    quote:
      "Phân tích strategy của 3 đối thủ lớn chỉ trong 2 câu lệnh. Đỡ mất công ngồi \"soi\" tay cả buổi. Tiết kiệm được ít nhất 4-5 tiếng nghiên cứu mỗi tuần.",
    stat: "−4h/tuần",
  },
];

const hookTicker = [
  '"Cảnh Báo: Đừng mua trước khi xem" · 2.4M view · Skincare',
  '"3 sai lầm khiến da sạm đi buổi sáng" · 1.8M view · Làm đẹp',
  '"Tôi đã mua thử để bạn không mất tiền" · 1.2M view · Review',
  '"So sánh công tâm giữa hai siêu phẩm" · 610K view · Tech',
  '"Sự thật về sản phẩm này không ai nói..." · 890K view · Food',
  '"Thử nghiệm thực tế sau 30 ngày dùng:" · 750K view · Gia dụng',
  '"Đừng làm điều này nếu bạn đang dùng..." · 3.1M view · Skincare',
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
    body: "Đầu tư quay dựng cả ngày, đăng lên lẹt đẹt 500 view. Không biết lỗi ở hook, nội dung hay format. Nhìn video đối thủ lên xu hướng mà không biết họ làm gì khác mình.",
  },
];

const nicheList = [
  "Thời trang / Outfit", "Làm đẹp / Skincare", "Review đồ Shopee",
  "Review đồ ăn / F&B", "Nấu ăn / Công thức", "Mẹ bỉm sữa",
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

function VideoThumb({ id, className = "" }: { id: string; className?: string }) {
  const [failed, setFailed] = useState(false);
  const url = r2FrameUrl(id);
  useEffect(() => { setFailed(false); }, [url]);
  if (!url || failed) {
    return <div className={`bg-[color:var(--gv-canvas-2)] ${className}`} />;
  }
  return (
    <img
      src={url}
      alt=""
      className={`object-cover ${className}`}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}

function SolutionCardsSection() {
  return (
    <section className="px-4 py-16 md:py-20 bg-[color:var(--gv-canvas)]">
      <div className="max-w-4xl mx-auto">
        <p className="text-center text-sm text-[color:var(--gv-ink-3)] mb-2">Giải pháp</p>
        <h2 className="text-center font-extrabold text-[color:var(--gv-ink)] mb-3" style={{ fontSize: "clamp(1.75rem, 4vw, 2.25rem)" }}>
          Công Cụ Nghiên Cứu TikTok Của Bạn
        </h2>
        <p className="text-center text-sm text-[color:var(--gv-ink-3)] mb-12 max-w-2xl mx-auto leading-relaxed">
          GetViews xem hàng nghìn video TikTok và trả lời mọi câu hỏi bạn cần — từ nghiên cứu đối thủ, tìm hook viral, đến viết brief cho KOL. Dựa trên data thực, không đoán mò.
        </p>
        <div className="grid md:grid-cols-2 gap-4">

          {/* ── Card 1: Competitor Intel ──────────────────────────────── */}
          <motion.div
            initial={false} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.4, delay: 0 }}
            whileHover={{ y: -4 }}
            className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-5 flex flex-col gap-4 transition-shadow duration-200 hover:shadow-lg cursor-pointer"
          >
            <p className="text-lg font-bold text-[color:var(--gv-ink)]">"Đối thủ đang đăng gì?"</p>
            <div className="flex gap-2 overflow-hidden">
              {COMPETITOR_IDS.slice(0, 4).map((id) => (
                <div
                  key={id}
                  className="relative flex-shrink-0 overflow-hidden rounded-xl bg-[color:var(--gv-canvas-2)]"
                  style={{ width: "22%", paddingBottom: "39%" }}
                >
                  <VideoThumb id={id} className="absolute inset-0 w-full h-full" />
                </div>
              ))}
              {/* Faded peek of a 5th card — signals volume / scrollability */}
              <div
                className="relative flex-shrink-0 overflow-hidden rounded-xl bg-[color:var(--gv-canvas-2)] opacity-40"
                style={{ width: "10%", paddingBottom: "39%" }}
              />
            </div>
            <p className="text-xs text-[color:var(--gv-ink-3)]">Xem toàn bộ nội dung, format và hook của đối thủ trong 1 màn hình</p>
          </motion.div>

          {/* ── Card 2: Creator Avatars (scattered float) ─────────────── */}
          <motion.div
            initial={false} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.4, delay: 0.1 }}
            whileHover={{ y: -4 }}
            className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-5 flex flex-col gap-3 transition-shadow duration-200 hover:shadow-lg cursor-pointer"
            style={{ minHeight: 220 }}
          >
            <p className="text-lg font-bold text-[color:var(--gv-ink)]">"Creator nào nên hire?"</p>
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
            <p className="text-xs text-[color:var(--gv-ink-3)]">Lọc KOL theo niche, view trung bình và tỉ lệ engagement</p>
          </motion.div>

          {/* ── Card 3: Hook Showcase — chat bubble + sparkline ──────── */}
          <motion.div
            initial={false} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.4, delay: 0.2 }}
            whileHover={{ y: -4 }}
            className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-5 flex flex-col gap-4 transition-shadow duration-200 hover:shadow-lg cursor-pointer"
          >
            <p className="text-lg font-bold text-[color:var(--gv-ink)]">"Hook nào viral nhất tuần này?"</p>
            <div className="flex gap-3 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] p-3">
              <div className="flex-shrink-0 overflow-hidden rounded-lg bg-[color:var(--gv-canvas-2)]" style={{ width: 48, height: 64 }}>
                <VideoThumb id={HOOK_EXAMPLE.id} className="h-full w-full" />
              </div>
              <div className="flex flex-col justify-center gap-1 min-w-0">
                <p className="text-sm font-semibold text-[color:var(--gv-ink)] line-clamp-2">"{HOOK_EXAMPLE.phrase}"</p>
                <p className="text-xs text-[color:var(--gv-accent)] font-mono font-semibold">{HOOK_EXAMPLE.views} views</p>
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
            className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-5 flex flex-col gap-3 transition-shadow duration-200 hover:shadow-lg cursor-pointer"
          >
            <p className="text-lg font-bold text-[color:var(--gv-ink)]">"Video nào nên làm?"</p>
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

function formatViewsShort(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return String(v);
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

// 4 confirmed R2-frame IDs per niche for the scroll strip (5 niches)
const NICHE_STRIP: { label: string; ids: string[] }[] = [
  { label: "Ẩm thực",   ids: ["7619285253022125333","7624842569465220368","7621904918978252039","7626756818085203207"] },
  { label: "Thời trang", ids: ["7622669408665652488","7624501870622444821","7620112412523433237","7627444741767974152"] },
  { label: "Công nghệ", ids: ["7627432133937679624","7627069060844457233","7620672683994402069","7627665640186268948"] },
  { label: "Sức khỏe",  ids: ["7621463359350656277","7625973407997267221","7627068868820864276","7622902141807578389"] },
  { label: "Giải trí",  ids: ["7615811534962330901","7616572388544695573","7620342789313776917","7617676901603101973"] },
];

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

function LiveDemoSection({ stats }: { stats: { hooks: { hook_type: string; avg_views: number; sample_size: number }[]; thumb_ids: string[] } }) {

  return (
    <section className="px-4 py-16 md:py-20 bg-[color:var(--gv-paper)]">
      <div className="max-w-6xl mx-auto">
        <p className="text-center text-sm text-[color:var(--gv-ink-3)] mb-2">Số liệu thực tế</p>
        <h2 className="text-center font-extrabold text-[color:var(--gv-ink)] mb-3" style={{ fontSize: "clamp(1.75rem, 4vw, 2.25rem)" }}>
          Nắm bắt xu hướng,<br />cập nhật theo từng giờ
        </h2>
        <p className="text-center text-sm text-[color:var(--gv-ink-3)] mb-12 max-w-xl mx-auto leading-relaxed">
          Đừng đoán mò nội dung. Hãy xem chiến lược nào đang đẩy view ổn định cho đối thủ.
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
              <h3 className="font-bold text-[color:var(--gv-ink)]">Tín Hiệu Trend</h3>
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

            <p className="text-xs text-[color:var(--gv-ink-3)] mt-2">Cập nhật mỗi tuần từ 1.500+ video thực</p>
          </motion.div>

          <motion.div
            initial={false}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-5 flex flex-col gap-1"
          >
            <p className="font-bold text-[color:var(--gv-ink)] mb-3">Mẫu Hook "Ăn" Tiền</p>

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
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-[color:var(--gv-ink)]">Database 1.500+ Video Creator Việt</h3>
            <Link to="/app/trends" className="text-xs text-[color:var(--gv-ink-3)] hover:text-[color:var(--gv-ink)] transition-colors duration-200">Tìm đối thủ →</Link>
          </div>

          <div className="flex gap-4 overflow-x-auto pb-1">
            {NICHE_STRIP.map((niche) => (
              <div key={niche.label} className="flex-shrink-0 flex flex-col gap-1.5">
                <p className="text-[10px] font-semibold text-[color:var(--gv-ink-3)] uppercase tracking-wide">{niche.label}</p>
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

          <p className="text-xs text-[color:var(--gv-ink-3)] mt-3 text-center">Đầy đủ 21 niche thịnh hành nhất tại Việt Nam</p>
        </motion.div>
      </div>
    </section>
  );
}

const INFRA_FEATURES = [
  { icon: Database,      label: "1.500+ Video Thực",      sub: "Corpus TikTok Việt Nam, kiểm chứng được" },
  { icon: Play,          label: "Phân Tích Video Thật",    sub: "AI xem frame thực, không đoán mò" },
  { icon: Globe,         label: "20 Niche Việt Nam",       sub: "Làm đẹp, ẩm thực, tài chính, công nghệ..." },
  { icon: Zap,           label: "Hook Pattern Thực Tế",    sub: "Từ video đã viral, không phải lý thuyết" },
  { icon: Search,        label: "Tìm Đối Thủ Ngay",       sub: "Tra @handle, ra ngay chiến lược của họ" },
  { icon: MessageCircle, label: "AI Hiểu Tiếng Việt",     sub: "Hỏi tiếng Việt, trả lời tiếng Việt" },
  { icon: ExternalLink,  label: "Cite Có Thể Kiểm Chứng", sub: "Mọi gợi ý đều kèm video thật, bấm xem được" },
  { icon: RefreshCw,     label: "Cập Nhật Hàng Tuần",     sub: "Data mới mỗi tuần, không dùng data cũ" },
] as const;

function InfraGrid() {
  return (
    <section className="px-4 py-16 bg-[color:var(--gv-canvas)]">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-10">
          <p className="text-xs font-semibold uppercase tracking-widest text-[color:var(--gv-ink-3)] mb-3">
            Hạ tầng
          </p>
          <h2
            className="font-extrabold text-[color:var(--gv-ink)] mb-3"
            style={{ fontSize: "clamp(1.5rem, 4vw, 2rem)" }}
          >
            Câu trả lời dựa trên{" "}
            <span className="text-[color:var(--gv-accent)]">data thực, không đoán mò</span>
          </h2>
          <p className="text-sm text-[color:var(--gv-ink-3)] max-w-xl mx-auto">
            GetViews không phải ChatGPT biết về TikTok — hệ thống thu thập và phân tích video TikTok Việt Nam liên tục, mỗi câu trả lời đều có nguồn gốc.
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {INFRA_FEATURES.map(({ icon: Icon, label, sub }) => (
            <motion.div
              key={label}
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
          ))}
        </div>
      </div>
    </section>
  );
}

const SAMPLE_QUERIES = [
  "Hook nào đang top view trong niche làm đẹp?",
  "Soi kênh @đối_thủ — họ đang làm gì?",
  "Tại sao video này chỉ 500 view?",
  "Viết brief KOL cho chiến dịch skincare",
];

function CredibilitySection() {
  return (
    <section className="px-4 py-16 bg-[color:var(--gv-paper)]">
      <div className="max-w-5xl mx-auto grid md:grid-cols-2 gap-12 items-center">

        {/* Left — credibility copy */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-[color:var(--gv-ink-3)] mb-4">
            Tại sao chúng tôi xây GetViews
          </p>
          <h2
            className="font-extrabold text-[color:var(--gv-ink)] mb-5 leading-tight"
            style={{ fontSize: "clamp(1.5rem, 3.5vw, 2rem)" }}
          >
            Bắt đầu tăng view{" "}
            <span className="text-[color:var(--gv-accent)]">ngay hôm nay</span>
          </h2>
          <p className="text-sm text-[color:var(--gv-ink-3)] leading-relaxed mb-6">
            Chúng tôi là những creator đã tự xây kênh TikTok từ 0 — và nhận ra rằng mọi quyết định nội dung đều đang được đưa ra dựa trên cảm tính. GetViews được xây để thay đổi điều đó: mỗi gợi ý đều có video thật làm bằng chứng, bạn bấm vào kiểm chứng được luôn.
          </p>
          <Link to="/login">
            <button
              type="button"
              className="rounded-lg bg-[color:var(--gv-accent)] px-6 py-3 text-sm font-medium text-white transition-all duration-[120ms] hover:bg-[color:var(--gv-accent-deep)] active:scale-95"
            >
              Thử miễn phí — không cần thẻ
            </button>
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
            <p className="text-[10px] text-[color:var(--gv-ink-3)] text-center mt-2">
              1.500+ video · 21 niche · Cập nhật hàng tuần
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
      title: "Quăng link TikTok vào",
      body: "Dán link video của bạn hoặc bất kỳ đối thủ nào. GetViews tự động \"xem\" và trích xuất dữ liệu.",
    },
    {
      num: "02",
      title: "Đối chiếu với Data thực",
      body: "AI so sánh video đó với hàng nghìn video viral khác trong cùng niche ngay tại thời điểm hiện tại.",
    },
    {
      num: "03",
      title: "Nhận \"đề bài\" để viral",
      body: "Biết ngay vì sao video flop, cần sửa hook ở giây thứ mấy, hay chuyển sang format nào để lên xu hướng.",
    },
  ];

  return (
    <section className="px-4 py-16 md:py-20 bg-[color:var(--gv-canvas)]">
      <div className="max-w-5xl mx-auto">
        <p className="mb-3 text-center text-sm uppercase tracking-wider text-[color:var(--gv-ink-3)]">Quy trình</p>
        <h2 className="text-center font-extrabold text-[color:var(--gv-ink)] mb-10 md:mb-14" style={{ fontSize: "clamp(1.75rem, 4vw, 2.25rem)" }}>
          3 bước đơn giản, dưới 2 phút
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
}

export default function LandingPage({ stats }: { stats: LandingStats }) {
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "biannual" | "annual">("annual");
  const [stickyVisible, setStickyVisible] = useState(false);

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
            className="fixed bottom-0 left-0 right-0 z-50 bg-[color:var(--gv-ink)] border-t border-[color:var(--gv-rule)]"
          >
            <div className="max-w-3xl mx-auto flex items-center justify-between px-4 py-3">
              <span className="font-extrabold text-white text-sm">
                GetViews<span className="text-[color:var(--brand-red)]">.vn</span>
              </span>
              <div className="flex items-center gap-4">
                <span className="text-xs text-white/60 hidden sm:block">Không cần thẻ tín dụng</span>
                <Link to="/login">
                  <button className="bg-[color:var(--gv-paper)] text-[color:var(--gv-ink)] hover:bg-[color:var(--gv-canvas-2)] text-sm font-medium px-5 py-2 rounded-lg transition-colors duration-[120ms] active:scale-95">
                    Soi Video Miễn Phí
                  </button>
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
                transition={{ duration: 0.5 }}
              >
                <div className="inline-flex items-center gap-2 bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-full px-4 py-2 mb-6">
                  <span className="text-sm font-medium text-[color:var(--gv-ink-3)]">Trợ lý AI số 1 cho TikTok Creator Việt</span>
                </div>

                <h1 className="font-extrabold leading-[1.2] mb-6" style={{ fontSize: "clamp(1.75rem, 4.5vw, 3rem)" }}>
                  <span className="text-[color:var(--gv-ink)]">Lướt TikTok cả&nbsp;ngày?</span>
                  <br />
                  <span className="text-[color:var(--gv-accent)]">Để GetViews "cày"&nbsp;thay.</span>
                </h1>

                <p className="text-lg text-[color:var(--gv-ink-3)] mb-8 max-w-lg leading-relaxed">
                  Quăng link video → Nhận phân tích sau 1 phút. Biết ngay{" "}
                  <span className="font-semibold text-[color:var(--gv-ink)]">lỗi ở đâu</span>,{" "}
                  <span className="font-semibold text-[color:var(--gv-ink)]">hook nào hot</span>,{" "}
                  <span className="font-semibold text-[color:var(--gv-ink)]">format nào cắn đề xuất</span>. Dựa trên số liệu thực, không đoán mò.
                </p>

                {/* CTA Input */}
                <div className="mb-4">
                  <div className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-1.5 shadow-sm mb-3 transition-all duration-200 hover:border-[color:var(--gv-ink)]/30 hover:shadow-md">
                    <div className="flex items-center gap-2 px-3 py-2">
                      <Input
                        placeholder="https://tiktok.com/@..."
                        className="flex-1 border-0 bg-transparent text-base focus:outline-none focus:ring-0 placeholder:text-[color:var(--gv-ink-4)]"
                      />
                    </div>
                  </div>
                  <Link to="/login">
                    <button className="w-full rounded-xl bg-[color:var(--gv-ink)] px-8 py-4 text-base font-semibold text-white transition-all duration-[120ms] hover:bg-[color:var(--gv-ink-2)] active:scale-[0.98]">
                      Soi Video Miễn Phí →
                    </button>
                  </Link>
                </div>

                <div className="flex items-center gap-4 text-xs text-[color:var(--gv-ink-3)]">
                  {["10 lượt dùng thử", "Không cần thẻ", "Dùng được ngay"].map((label) => (
                    <div key={label} className="flex items-center gap-1">
                      <svg className="h-4 w-4 text-[color:var(--success)]" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span>{label}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            </div>

            {/* Right: Visual Proof */}
            <motion.div
              initial={false}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="relative hidden lg:block"
            >
              {/* Floating Stats Card */}
              <div className="absolute top-8 -left-8 bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-4 shadow-lg z-10">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded bg-[color:var(--gv-ink)] flex items-center justify-center">
                    <span className="text-white font-mono font-bold text-sm">↑</span>
                  </div>
                  <div>
                    <p className="text-xs text-[color:var(--gv-ink-3)] mb-0.5">Hiệu quả trung bình</p>
                    <p className="font-mono font-bold text-lg text-[color:var(--gv-ink)]">+312%</p>
                  </div>
                </div>
              </div>

              {/* Main Mock Chat */}
              <div className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-6 shadow-lg">
                <div className="flex items-center gap-3 mb-4 pb-4 border-b border-[color:var(--gv-rule)]">
                  <div className="w-10 h-10 rounded bg-[color:var(--gv-ink)] flex items-center justify-center text-white font-bold text-xs">GV</div>
                  <div>
                    <p className="font-semibold text-sm text-[color:var(--gv-ink)]">GetViews AI</p>
                    <p className="text-xs text-[color:var(--gv-ink-3)] flex items-center gap-1">
                      <span className="w-1.5 h-1.5 bg-[color:var(--gv-ink)] rounded-full" />
                      Đang soi dữ liệu video...
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="bg-[color:var(--gv-paper)] rounded-xl p-3">
                    <div className="flex items-start gap-2 mb-2">
                      <span className="font-bold text-[color:var(--danger)]">✕</span>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-[color:var(--gv-ink)] mb-1">Hook vào quá chậm (2.3s)</p>
                        <p className="text-xs text-[color:var(--gv-ink-3)]">Top video viral thường mở màn ở 0.5s</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-[color:var(--gv-paper)] rounded-xl p-3">
                    <div className="flex items-start gap-2 mb-2">
                      <span className="font-bold text-[color:var(--danger)]">✕</span>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-[color:var(--gv-ink)] mb-1">Thiếu "mặt người" ở đầu</p>
                        <p className="text-xs text-[color:var(--gv-ink-3)]">89% video top view mở bằng mặt chính chủ</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-[color:var(--gv-paper)] rounded-xl p-3 border border-[color:var(--gv-rule)]">
                    <div className="flex items-start gap-2">
                      <span className="font-bold text-[color:var(--success)]">✓</span>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-[color:var(--gv-ink)] mb-1">Dùng Hook "Cảnh Báo" là chuẩn</p>
                        <p className="text-xs text-[color:var(--gv-ink-3)]">Mẫu này tăng 340% view so với "Kể Chuyện"</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-[color:var(--gv-rule)]">
                  <p className="text-xs font-mono text-[color:var(--gv-ink-4)]">So khớp với 1.247 video skincare · 7 ngày qua</p>
                </div>
              </div>

              {/* Floating Niche Badge */}
              <div className="absolute -bottom-4 -right-4 bg-[color:var(--gv-ink)] text-white rounded-xl px-5 py-3 shadow-lg">
                <p className="text-xs opacity-70 mb-0.5">Phủ sóng 21 niche creator</p>
                <p className="font-bold text-sm">Skincare · Review · Food · Affiliate...</p>
              </div>
            </motion.div>
          </div>

          {/* Trust Badges */}
          <motion.div
            initial={false}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="mt-16 flex flex-wrap items-center justify-center gap-6 text-sm text-[color:var(--gv-ink-3)]"
          >
            <div className="flex items-center gap-2"><span>Data 100% từ TikTok Việt</span></div>
            <div className="hidden sm:block w-px h-4 bg-[color:var(--gv-rule)]" />
            <div className="flex items-center gap-2"><span>Cập nhật hàng giờ</span></div>
            <div className="hidden sm:block w-px h-4 bg-[color:var(--gv-rule)]" />
            <div className="flex items-center gap-2"><span>Chuyên biệt cho 21 niche creator</span></div>
          </motion.div>

          {/* Hook Ticker */}
          <motion.div
            initial={false}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.6 }}
            className="mt-10 overflow-hidden border-t border-[color:var(--gv-rule)] pt-5"
          >
            <p className="text-xs text-[color:var(--gv-ink-3)] mb-3 text-center">Các mẫu Hook đang "lên ngôi" tuần này</p>
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
          <h2 className="font-extrabold text-[color:var(--gv-ink)] leading-[1.4]" style={{ fontSize: "clamp(1.75rem, 4.5vw, 2.75rem)" }}>
            Công cụ duy nhất tự động "soi" hàng nghìn video mỗi&nbsp;ngày để tìm ra công&nbsp;thức viral cho bạn
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
          <h2 className="text-center font-extrabold text-[color:var(--gv-ink)] mb-10 md:mb-16" style={{ fontSize: "clamp(1.75rem, 4vw, 2.25rem)" }}>
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
      <LiveDemoSection stats={stats} />

      {/* ── Infrastructure + Credibility ─────────────────────────── */}
      <InfraGrid />
      <CredibilitySection />

      {/* ── Results ─────────────────────────────────────────────── */}
      <section className="px-4 py-16 md:py-20 bg-[color:var(--gv-paper)]">
        <div className="max-w-5xl mx-auto">
          <p className="text-center text-sm text-[color:var(--gv-ink-3)] mb-3">Kết quả thực</p>
          <h2 className="text-center font-extrabold text-[color:var(--gv-ink)] mb-3" style={{ fontSize: "clamp(1.75rem, 4vw, 2.25rem)" }}>
            Số liệu nói thay lời
          </h2>
          <p className="text-center text-sm text-[color:var(--gv-ink-3)] mb-12 max-w-xl mx-auto leading-relaxed">
            Creator thật, kết quả đo được — không phải lời hứa.
          </p>

          <motion.div
            initial={false}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4 }}
            className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl p-6 md:p-8 mb-6"
          >
            <div className="grid md:grid-cols-[1fr_80px_1fr] gap-6 items-center">
              <div>
                <p className="text-xs text-[color:var(--gv-ink-3)] mb-4 uppercase tracking-wide">Trước</p>
                <div className="font-mono font-bold text-[color:var(--gv-ink-3)] mb-1" style={{ fontSize: "clamp(2rem, 5vw, 2.75rem)" }}>2.000</div>
                <p className="text-sm text-[color:var(--gv-ink-3)] mb-5">view · video review nồi chiên</p>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-[color:var(--danger)]">✕</span>
                    <span className="text-sm text-[color:var(--gv-ink-3)]">Hook chậm 2.3 giây</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-[color:var(--danger)]">✕</span>
                    <span className="text-sm text-[color:var(--gv-ink-3)]">Không có mặt người 3 giây đầu</span>
                  </div>
                </div>
              </div>
              <div className="flex flex-col items-center gap-2">
                <div className="w-10 h-10 border border-[color:var(--gv-rule)] rounded flex items-center justify-center bg-[color:var(--gv-paper)]">
                  <span className="font-mono font-bold text-sm text-[color:var(--gv-ink)] hidden md:inline">→</span>
                  <span className="font-mono font-bold text-sm text-[color:var(--gv-ink)] md:hidden">↓</span>
                </div>
                <p className="text-xs text-[color:var(--gv-ink-3)] font-mono text-center">GetViews</p>
              </div>
              <div>
                <p className="text-xs text-[color:var(--gv-ink-3)] mb-4 uppercase tracking-wide">Sau khi fix</p>
                <div className="font-mono font-bold text-[color:var(--gv-ink)] mb-1" style={{ fontSize: "clamp(2rem, 5vw, 2.75rem)" }}>45.000</div>
                <p className="text-sm text-[color:var(--gv-ink-3)] mb-5">view · quay lại theo gợi ý</p>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-[color:var(--success)]">✓</span>
                    <span className="text-sm text-[color:var(--gv-ink-3)]">Mặt nhìn camera từ frame 0</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-[color:var(--success)]">✓</span>
                    <span className="text-sm text-[color:var(--gv-ink-3)]">Hook &ldquo;Cảnh Báo&rdquo; đúng pattern niche</span>
                  </div>
                </div>
              </div>
            </div>
            <p className="text-xs font-mono text-[color:var(--gv-ink-4)] mt-6 pt-4 border-t border-[color:var(--gv-rule)]">
              412 video review đồ gia dụng · 7 ngày · Updated 4h ago
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
            Chọn gói phù hợp
          </h2>
          <p className="text-sm text-[color:var(--gv-ink-3)] text-center mb-8">
            Thanh toán qua MoMo, VNPay, chuyển khoản, hoặc thẻ quốc tế.
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
                    <span className="absolute -top-2 -right-2 bg-[color:var(--gv-ink)] text-white text-[9px] px-1.5 py-0.5 rounded-full font-medium whitespace-nowrap">
                      Save 20%
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 mb-4">
            {plans.map((plan, idx) => (
              <motion.div
                key={plan.name}
                initial={false}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: idx * 0.05 }}
                whileHover={{ y: -4 }}
                className={`border rounded-xl p-5 relative bg-[color:var(--gv-paper)] transition-shadow duration-200 hover:shadow-lg ${
                  plan.popular ? "border-[color:var(--gv-ink)] border-2" : "border-[color:var(--gv-rule)]"
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="bg-[color:var(--gv-ink)] text-white text-xs px-3 py-1 rounded-full font-medium">Phổ biến</span>
                  </div>
                )}
                <h3 className="font-bold text-[color:var(--gv-ink)] mb-1">{plan.label}</h3>
                <div className="mb-3">
                  <span className="font-mono font-bold text-[color:var(--gv-ink)]" style={{ fontSize: "1.25rem" }}>{plan.price}</span>
                  {plan.name !== "Free" && billingPeriod !== "monthly" && (
                    <span className="text-xs text-[color:var(--gv-ink-3)]">/tháng</span>
                  )}
                </div>
                <p className="text-xs text-[color:var(--gv-ink-3)] mb-5" style={{ lineHeight: "1.5" }}>{plan.credits}</p>
                <Link to="/login">
                  <Button fullWidth variant={plan.popular ? "primary" : "outlined"} className="text-sm py-2">
                    {plan.name === "Free" ? "Bắt đầu miễn phí" : `Nâng cấp ${plan.name}`}
                  </Button>
                </Link>
              </motion.div>
            ))}
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
          <h2 className="font-extrabold text-white mb-6 leading-tight" style={{ fontSize: "clamp(1.75rem, 4vw, 2.5rem)" }}>
            Dán 1 link. Xem GetViews nói gì.
          </h2>
          <Link to="/login">
            <button className="bg-[color:var(--gv-paper)] text-[color:var(--gv-ink)] hover:bg-[color:var(--gv-canvas-2)] font-semibold px-10 py-4 rounded-xl text-base transition-all duration-[120ms] active:scale-95">
              Soi Video Miễn Phí
            </button>
          </Link>
          <p className="text-sm text-white/60 mt-4">10 lần miễn phí · Không cần thẻ</p>
        </div>
      </section>

      {stickyVisible && <div className="h-14" />}
    </div>
  );
}
