import { useState, useEffect } from "react";
import { Link } from "react-router";
import { r2FrameUrl } from "@/lib/services/corpus-service";
import * as Accordion from "@radix-ui/react-accordion";
import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { motion, AnimatePresence } from "motion/react";
import { pricingPlans, pricingSavings } from "@/lib/mock-data";

const faqs = [
  {
    q: "Cái này khác gì ChatGPT?",
    a: "ChatGPT không có data TikTok realtime và không xem được video. Nếu bạn hỏi \"hook nào đang hot trong skincare\" — ChatGPT sẽ bịa ra một câu trả lời nghe có vẻ hợp lý nhưng không dựa trên bất kỳ video thực tế nào. GetViews trả lời dựa trên 100% video thật, view thật, bạn có thể bấm vào xem để kiểm chứng ngay lập tức.",
  },
  {
    q: "Tôi mua khóa học rồi, có cần dùng thêm cái này không?",
    a: "Khóa học dạy bạn tư duy nền tảng: thuật toán, cách quay, cách edit. Rất tốt. Nhưng nó không thể nói cho bạn biết tuần này, ngày hôm nay, mẫu video nào đang \"cắn\" đề xuất trong đúng niche của bạn. GetViews là công cụ thực chiến bổ sung đúng chỗ mà kiến thức lý thuyết không cover được: data tươi, cập nhật mỗi giờ.",
  },
  {
    q: "Khác gì Kalodata hay Shoplus?",
    a: "Kalodata tập trung vào bán hàng (sản phẩm nào chạy). GetViews tp trung vào nội dung (TẠI SAO video đó viral) — từ cách mở đầu, nhịp cắt đến tâm lý người xem. Hai công cụ này bổ trợ cho nhau hoàn hảo nếu bạn làm Affiliate.",
  },
  {
    q: "1 credit tính như thế nào?",
    a: "1 credit = 1 lần phân tích sâu (soi video, phân tích đối thủ, viết brief chi tiết). Còn việc lướt xem xu hướng, tìm KOL và chat hỏi đáp thông thường là hoàn toàn miễn phí, không giới hạn.",
  },
  {
    q: "Thanh toán có phức tạp không?",
    a: "Cực kỳ đơn giản qua MoMo, VNPay, chuyển khoản ngân hàng hoặc thẻ Visa/Mastercard. Thanh toán xong là tài khoản được kích hoạt để dùng ngay.",
  },
  {
    q: "Nếu dùng không hiệu quả thì sao?",
    a: "GetViews không bắt cam kết dài hạn, bạn có thể hủy bất cứ lúc nào. Lời khuyên là hãy dùng gói tháng để trải nghiệm độ \"nhạy\" của data, khi thấy video bắt đầu có chuyển biến thì hãy nâng cấp gói năm để tiết kiệm hơn.",
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
    body: "Đầu tư quay dựng cả ngày, đăng lên lẹt đẹt 500 view. Không biết lỗi ở hook, nội dung hay format. Nhìn video đối thủ triệu view mà không biết họ làm gì khác mình.",
  },
];

const nicheList = [
  "Skincare", "Review đồ gia dụng", "Hài hước", "Ẩm thực / Food",
  "Công nghệ", "Làm đẹp", "Affiliate Shopee", "Mẹ bỉm sữa",
  "Thời trang", "Du lịch", "Tài chính", "Vlog đời sống",
];

// ─── Hardcoded real video IDs from corpus (selected 2026-04-09) ──────────────

// Card 1: Competitor intel — yeah1.giaitri (12 videos · 5.1M total views)
const COMPETITOR_IDS = [
  "7615811534962330901", // 1.5M views
  "7616572388544695573", // 612K views
  "7620356499101011220", // 505K views
  "7620356501630192916", // 500K views
  "7616572382827973909", // 450K views
  "7620342789313776917", // 381K views
  "7617676901603101973", // 313K views
  "7616570339660713237", // 219K views
];

// Card 2: Creator roster — top 4 unique creators by views
const CREATOR_ROSTER: { id: string; handle: string; views: string }[] = [
  { id: "7625127374316784916", handle: "@kietfei",              views: "101M" },
  { id: "7621134771292245266", handle: "@maria.bui1",           views: "17.6M" },
  { id: "7622669408665652488", handle: "@lynguyn.2002",         views: "7.3M" },
  { id: "7623726538600877332", handle: "@blogtamsu.taichinh",   views: "5.8M" },
];

// Card 3: Hook showcase — high-view video with strong hook phrase
const HOOK_EXAMPLE = {
  id: "7623726538600877332",
  hook: "Đỉnh cao của sự phô trương kín đáo: Biển số xe đẹp chưa là gì...",
  views: "5.8M",
  handle: "@blogtamsu.taichinh",
};

// Card 4: Video grid — 16 diverse high-view videos across niches
const GRID_IDS = [
  "7625127374316784916", // niche 13 · 101M
  "7621134771292245266", // niche 4  · 17.6M
  "7622669408665652488", // niche 3  · 7.3M
  "7623726538600877332", // niche 15 · 5.8M
  "7625916587916152086", // niche 16 · 4.3M
  "7626043613700558087", // niche 7  · 3.9M
  "7616957249201638677", // niche 10 · 3.8M
  "7627893160542260500", // niche 2  · 3.4M
  "7627072266957884693", // niche 17 · 3.1M
  "7623076368741436693", // niche 11 · 3.0M
  "7619681088465571080", // niche 9  · 2.6M
  "7615811534962330901", // niche 6  · 1.5M
  "7618909735487835413", // niche 12 · 1.2M
  "7625204222585228566", // niche 1  · 1.0M
  "7624886649725504789", // niche 14 · 807K
  "7626680583250365697", // niche 8  · 758K
];

function VideoThumb({ id, className = "" }: { id: string; className?: string }) {
  const [failed, setFailed] = useState(false);
  const url = r2FrameUrl(id);
  useEffect(() => { setFailed(false); }, [url]);
  if (!url || failed) {
    return <div className={`bg-[var(--surface-alt)] ${className}`} />;
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
    <section className="px-4 py-16 md:py-20 bg-[var(--background)]">
      <div className="max-w-5xl mx-auto">
        <p className="text-center text-sm text-[var(--muted)] mb-2">Giải pháp</p>
        <h2 className="text-center font-extrabold text-[var(--ink)] mb-3" style={{ fontSize: "clamp(1.75rem, 4vw, 2.25rem)" }}>
          Công Cụ Nghiên Cứu TikTok Của Bạn
        </h2>
        <p className="text-center text-sm text-[var(--ink-soft)] mb-12 max-w-2xl mx-auto leading-relaxed">
          GetViews xem hàng nghìn video TikTok và trả lời mọi câu hỏi bạn cần — từ nghiên cứu đối thủ, tìm hook viral, đến viết brief cho KOL. Dựa trên data thực, không đoán mò.
        </p>
        <div className="grid md:grid-cols-2 gap-6">

          {/* ── Card 1: Competitor Intel ──────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.4, delay: 0 }}
            whileHover={{ y: -4 }}
            className="bg-white border border-[var(--border)] rounded-xl p-5 flex flex-col gap-4 transition-shadow duration-200 hover:shadow-lg cursor-pointer"
          >
            <p className="text-lg font-bold text-[var(--ink)]">"Đối thủ đang đăng gì?"</p>
            <div className="flex gap-2 overflow-hidden">
              {COMPETITOR_IDS.slice(0, 4).map((id) => (
                <div
                  key={id}
                  className="relative flex-shrink-0 overflow-hidden rounded-xl bg-[var(--surface-alt)]"
                  style={{ width: "22%", paddingBottom: "39%" }}
                >
                  <VideoThumb id={id} className="absolute inset-0 w-full h-full" />
                </div>
              ))}
              {/* Faded peek of a 5th card — signals volume / scrollability */}
              <div
                className="relative flex-shrink-0 overflow-hidden rounded-xl bg-[var(--surface-alt)] opacity-40"
                style={{ width: "10%", paddingBottom: "39%" }}
              />
            </div>
            <p className="text-xs text-[var(--muted)]">12 video trong corpus · 5.1M views tổng</p>
          </motion.div>

          {/* ── Card 2: Creator Roster ────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.4, delay: 0.1 }}
            whileHover={{ y: -4 }}
            className="bg-white border border-[var(--border)] rounded-xl p-6 transition-shadow duration-200 hover:shadow-lg cursor-pointer"
          >
            <p className="font-bold text-[var(--ink)] mb-1">"Creator nào nên hire?"</p>
            <p className="text-xs text-[var(--muted)] mb-4">Lọc KOL theo niche, view trung bình và tỉ lệ engagement</p>
            <div className="space-y-3">
              {CREATOR_ROSTER.map((c) => (
                <div key={c.id} className="flex items-center gap-3">
                  <div className="relative w-10 h-[71px] flex-shrink-0 overflow-hidden rounded">
                    <VideoThumb id={c.id} className="absolute inset-0 w-full h-full" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[var(--ink)] truncate">{c.handle}</p>
                    <p className="text-xs text-[var(--muted)]">{c.views} views</p>
                  </div>
                  <span className="text-xs font-mono text-[var(--purple)] font-semibold tabular-nums">{c.views}</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* ── Card 3: Hook Showcase ─────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.4, delay: 0.2 }}
            whileHover={{ y: -4 }}
            className="bg-white border border-[var(--border)] rounded-xl p-6 transition-shadow duration-200 hover:shadow-lg cursor-pointer"
          >
            <p className="font-bold text-[var(--ink)] mb-1">"Hook nào viral nhất?"</p>
            <p className="text-xs text-[var(--muted)] mb-4">Phân tích frame-by-frame để tìm khoảnh khắc "bắt view"</p>
            <div className="flex gap-4 items-start">
              <div className="relative flex-shrink-0 overflow-hidden rounded-lg" style={{ width: 80, height: 142 }}>
                <VideoThumb id={HOOK_EXAMPLE.id} className="absolute inset-0 w-full h-full" />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                <div className="absolute bottom-1.5 left-1.5 right-1.5">
                  <span className="text-[10px] font-mono text-white font-semibold">{HOOK_EXAMPLE.views}</span>
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="bg-[var(--surface)] rounded-lg p-3 mb-2">
                  <p className="text-xs font-medium text-[var(--ink)] leading-snug line-clamp-3">
                    "{HOOK_EXAMPLE.hook}"
                  </p>
                </div>
                <p className="text-xs text-[var(--muted)]">{HOOK_EXAMPLE.handle} · {HOOK_EXAMPLE.views} views</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {["Hook mạnh", "Số liệu shock", "Kéo tò mò"].map((tag) => (
                    <span key={tag} className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--surface)] border border-[var(--border)] text-[var(--ink-soft)]">{tag}</span>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>

          {/* ── Card 4: Video Grid ────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.4, delay: 0.3 }}
            whileHover={{ y: -4 }}
            className="bg-white border border-[var(--border)] rounded-xl p-6 transition-shadow duration-200 hover:shadow-lg cursor-pointer"
          >
            <p className="font-bold text-[var(--ink)] mb-1">"Tìm video viral theo niche"</p>
            <p className="text-xs text-[var(--muted)] mb-4">46.000+ video từ 17 niche — lọc, tìm, học theo</p>
            <div className="grid grid-cols-4 gap-1">
              {GRID_IDS.map((id) => (
                <div key={id} className="relative overflow-hidden rounded" style={{ paddingBottom: "177.78%" }}>
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

const SIGNAL_EXAMPLES = [
  { label: "Hook số liệu shock", signal: "rising", desc: "Top pattern tuần này" },
  { label: "Cảnh báo + reveal", signal: "early", desc: "Mới nổi, vào sớm" },
  { label: "Before / After", signal: "stable", desc: "Ổn định, cạnh tranh cao" },
];

const SIGNAL_DOT: Record<string, string> = {
  rising: "bg-[var(--purple)]",
  early: "bg-orange-400",
  stable: "bg-[var(--muted)]",
};

const HOOK_TYPE_LABELS: Record<string, string> = {
  warning: "Cảnh báo",
  number_shock: "Số liệu gây shock",
  question: "Câu hỏi kích tò mò",
  before_after: "Trước / sau",
  reveal: "Tiết lộ bí mật",
  challenge: "Thử thách",
  story: "Kể chuyện ngắn",
  comparison: "So sánh trực diện",
  tutorial: "Hướng dẫn nhanh",
};

function LiveDemoSection({ stats }: { stats: { hooks: { hook_type: string; avg_views: number; sample_size: number }[]; thumb_ids: string[] } }) {

  return (
    <section className="px-4 py-16 md:py-20 bg-white">
      <div className="max-w-6xl mx-auto">
        <p className="text-center text-sm text-[var(--muted)] mb-2">Số liệu thực tế</p>
        <h2 className="text-center font-extrabold text-[var(--ink)] mb-3" style={{ fontSize: "clamp(1.75rem, 4vw, 2.25rem)" }}>
          Nắm bắt xu hướng,<br />cập nhật theo từng giờ
        </h2>
        <p className="text-center text-sm text-[var(--ink-soft)] mb-12 max-w-xl mx-auto leading-relaxed">
          Đừng đoán mò nội dung. Hãy xem chiến lược nào thực sự đang mang lại triệu view cho đối thủ.
        </p>

        <div className="grid lg:grid-cols-[2fr_1fr] gap-6 mb-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4 }}
            className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-[var(--ink)]">Tín Hiệu Trend</h3>
              <Link to="/app/trends" className="text-xs text-[var(--ink)] font-medium hover:underline transition-colors duration-200 hover:text-[var(--purple)]">Xem tất cả →</Link>
            </div>
            <div className="space-y-3">
              {SIGNAL_EXAMPLES.map((item) => (
                <div key={item.signal} className="flex items-center gap-3 pb-3 border-b border-[var(--border)] last:border-0 last:pb-0">
                  <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${SIGNAL_DOT[item.signal] ?? "bg-[var(--muted)]"}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[var(--ink)] leading-snug">{item.label}</p>
                    <p className="text-xs text-[var(--muted)]">{item.desc}</p>
                  </div>
                </div>
              ))}
              <p className="text-xs text-[var(--ink-soft)] pt-1">Cập nhật mỗi tuần từ 46.000+ video thực</p>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6"
          >
            <h3 className="font-bold text-[var(--ink)] mb-4">Mẫu Hook "Ăn" Tiền</h3>
            <div className="divide-y divide-[var(--border)]">
              {stats.hooks.length > 0
                ? stats.hooks.slice(0, 5).map((h) => (
                    <div key={h.hook_type} className="flex items-center justify-between py-2 first:pt-0 last:pb-0">
                      <div>
                        <p className="text-sm font-medium text-[var(--ink)]">
                          {HOOK_TYPE_LABELS[h.hook_type] ?? h.hook_type}
                        </p>
                        <p className="text-xs text-[var(--muted)]">{h.sample_size.toLocaleString("vi-VN")} video mẫu</p>
                      </div>
                      <p className="font-mono text-xs font-semibold text-[var(--purple)] tabular-nums">
                        {(h.avg_views / 1_000_000).toFixed(1)}M avg
                      </p>
                    </div>
                  ))
                : Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="h-10 animate-pulse rounded bg-[var(--surface-alt)] my-1" />
                  ))
              }
            </div>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-[var(--ink)]">Database 10.000+ Video Creator Việt</h3>
            <button className="text-xs text-[var(--ink)] font-medium hover:underline transition-colors duration-200 hover:text-[var(--purple)]">Tìm đối thủ →</button>
          </div>
          <div className="overflow-hidden">
            <div className="flex gap-2 animate-scroll-infinite">
              {(stats.thumb_ids.length > 0 ? [...stats.thumb_ids, ...stats.thumb_ids] : Array(12).fill(null)).map((id, i) => {
                const url = id ? r2FrameUrl(id) : null;
                return (
                  <div
                    key={`${id ?? "sk"}-${i}`}
                    className="flex-shrink-0 overflow-hidden rounded border border-[var(--border)] bg-[var(--surface-alt)] transition-transform duration-200 hover:scale-105"
                    style={{ width: 48, height: 85 /* ~9:16 at w=48 */ }}
                  >
                    {url ? (
                      <img
                        src={url}
                        alt=""
                        className="h-full w-full object-cover"
                        loading="lazy"
                      />
                    ) : (
                      <div className="h-full w-full animate-pulse bg-[var(--surface-alt)]" />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
          <p className="text-xs text-center text-[var(--ink-soft)] mt-4">
            Đầy đủ 17 niche thịnh hành nhất tại Việt Nam
          </p>
        </motion.div>
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
    <section className="px-4 py-16 md:py-20 bg-[var(--background)]">
      <div className="max-w-5xl mx-auto">
        <p className="text-center text-sm text-[var(--muted)] mb-3 text-uppercase tracking-wider">Quy trình</p>
        <h2 className="text-center font-extrabold text-[var(--ink)] mb-10 md:mb-14" style={{ fontSize: "clamp(1.75rem, 4vw, 2.25rem)" }}>
          3 bước đơn giản, dưới 2 phút
        </h2>

        <div className="relative">
          <div className="hidden md:block absolute top-8 left-[calc(16.67%+1.5rem)] right-[calc(16.67%+1.5rem)] h-px bg-[var(--border)] z-0" />
          <div className="grid md:grid-cols-3 gap-10 md:gap-8">
            {steps.map((step, i) => (
              <motion.div
                key={step.num}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.4, delay: i * 0.12 }}
                className="flex items-center gap-4 md:flex-col md:items-center md:text-center md:gap-0"
              >
                <div className="relative z-10 flex-shrink-0">
                  <div className="w-16 h-16 bg-white border border-[var(--border)] rounded flex items-center justify-center md:mb-6">
                    <span className="font-mono font-bold text-lg text-[var(--ink)]">{step.num}</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-[var(--ink)] mb-2 text-base">{step.title}</h3>
                  <p className="text-sm text-[var(--ink-soft)] leading-relaxed">{step.body}</p>
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
    <div className="min-h-screen bg-[var(--background)]">
      {/* ── Sticky Bar ─────────────────────────────────────────── */}
      <AnimatePresence>
        {stickyVisible && (
          <motion.div
            initial={{ y: 64 }}
            animate={{ y: 0 }}
            exit={{ y: 64 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="fixed bottom-0 left-0 right-0 z-50 bg-[var(--ink)] border-t border-[var(--border)]"
          >
            <div className="max-w-3xl mx-auto flex items-center justify-between px-4 py-3">
              <span className="font-extrabold text-white text-sm">
                GetViews<span className="text-[var(--brand-red)]">.vn</span>
              </span>
              <div className="flex items-center gap-4">
                <span className="text-xs text-white/60 hidden sm:block">Không cần thẻ tín dụng</span>
                <Link to="/login">
                  <button className="bg-white text-[var(--ink)] hover:bg-[var(--surface-alt)] text-sm font-medium px-5 py-2 rounded-lg transition-colors duration-[120ms] active:scale-95">
                    Soi Video Miễn Phí
                  </button>
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Hero ───────────────────────────────────────────────── */}
      <section className="relative px-4 pt-6 pb-20 md:pb-32 bg-[var(--background)]">
        <div className="max-w-6xl mx-auto">
          {/* Top Nav */}
          <div className="flex items-center justify-center mb-16">
            <span className="font-extrabold text-xl text-[var(--ink)]">
              GetViews<span className="text-[var(--brand-red)]">.vn</span>
            </span>
          </div>

          {/* Hero Grid */}
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left: Copy + CTA */}
            <div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
              >
                <div className="inline-flex items-center gap-2 bg-[var(--surface)] border border-[var(--border)] rounded-full px-4 py-2 mb-6">
                  <span className="text-sm font-medium text-[var(--ink-soft)]">Trợ lý AI số 1 cho TikTok Creator Việt</span>
                </div>

                <h1 className="font-extrabold leading-[1.2] mb-6" style={{ fontSize: "clamp(1.75rem, 4.5vw, 3rem)" }}>
                  <span className="text-[var(--ink)]">Lướt TikTok cả&nbsp;ngày?</span>
                  <br />
                  <span className="gradient-text">Để GetViews "cày"&nbsp;thay.</span>
                </h1>

                <p className="text-lg text-[var(--ink-soft)] mb-8 max-w-lg leading-relaxed">
                  Quăng link video → Nhận phân tích sau 1 phút. Biết ngay{" "}
                  <span className="font-semibold text-[var(--ink)]">lỗi ở đâu</span>,{" "}
                  <span className="font-semibold text-[var(--ink)]">hook nào hot</span>,{" "}
                  <span className="font-semibold text-[var(--ink)]">format nào cắn đề xuất</span>. Dựa trên số liệu thực, không đoán mò.
                </p>

                {/* CTA Input */}
                <div className="mb-4">
                  <div className="bg-white border border-[var(--border)] rounded-xl p-1.5 shadow-sm mb-3 transition-all duration-200 hover:border-[var(--ink)]/30 hover:shadow-md">
                    <div className="flex items-center gap-2 px-3 py-2">
                      <Input
                        placeholder="https://tiktok.com/@..."
                        className="border-0 bg-transparent flex-1 text-base focus:outline-none focus:ring-0 placeholder:text-[var(--muted)]"
                        style={{ fontSize: "16px" }}
                      />
                    </div>
                  </div>
                  <Link to="/login">
                    <button className="w-full bg-[var(--ink)] hover:bg-[var(--ink-soft)] text-white font-semibold px-8 py-4 rounded-xl text-base transition-all duration-[120ms] active:scale-[0.98]">
                      Soi Video Miễn Phí →
                    </button>
                  </Link>
                </div>

                <div className="flex items-center gap-4 text-xs text-[var(--muted)]">
                  {["10 lượt dùng thử", "Không cần thẻ", "Dùng được ngay"].map((label) => (
                    <div key={label} className="flex items-center gap-1">
                      <svg className="w-4 h-4 text-[var(--success)]" fill="currentColor" viewBox="0 0 20 20">
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
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="relative hidden lg:block"
            >
              {/* Floating Stats Card */}
              <div className="absolute top-8 -left-8 bg-white border border-[var(--border)] rounded-xl p-4 shadow-lg z-10">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded bg-[var(--ink)] flex items-center justify-center">
                    <span className="text-white font-mono font-bold text-sm">↑</span>
                  </div>
                  <div>
                    <p className="text-xs text-[var(--muted)] mb-0.5">Hiệu quả trung bình</p>
                    <p className="font-mono font-bold text-lg text-[var(--ink)]">+312%</p>
                  </div>
                </div>
              </div>

              {/* Main Mock Chat */}
              <div className="bg-white border border-[var(--border)] rounded-xl p-6 shadow-lg">
                <div className="flex items-center gap-3 mb-4 pb-4 border-b border-[var(--border)]">
                  <div className="w-10 h-10 rounded bg-[var(--ink)] flex items-center justify-center text-white font-bold text-xs">GV</div>
                  <div>
                    <p className="font-semibold text-sm text-[var(--ink)]">GetViews AI</p>
                    <p className="text-xs text-[var(--muted)] flex items-center gap-1">
                      <span className="w-1.5 h-1.5 bg-[var(--ink)] rounded-full" />
                      Đang soi dữ liệu video...
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="bg-[var(--surface)] rounded-xl p-3">
                    <div className="flex items-start gap-2 mb-2">
                      <span className="text-[var(--danger)] font-bold">✕</span>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-[var(--ink)] mb-1">Hook vào quá chậm (2.3s)</p>
                        <p className="text-xs text-[var(--ink-soft)]">Top video viral thường mở màn ở 0.5s</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-[var(--surface)] rounded-xl p-3">
                    <div className="flex items-start gap-2 mb-2">
                      <span className="text-[var(--danger)] font-bold">✕</span>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-[var(--ink)] mb-1">Thiếu "mặt người" ở đầu</p>
                        <p className="text-xs text-[var(--ink-soft)]">89% video triệu view mở bằng mặt chính chủ</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-[var(--surface)] rounded-xl p-3 border border-[var(--border)]">
                    <div className="flex items-start gap-2">
                      <span className="text-[var(--success)] font-bold">✓</span>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-[var(--ink)] mb-1">Dùng Hook "Cảnh Báo" là chuẩn</p>
                        <p className="text-xs text-[var(--ink-soft)]">Mẫu này tăng 340% view so với "Kể Chuyện"</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-[var(--border)]">
                  <p className="text-xs font-mono text-[var(--faint)]">So khớp với 1.247 video skincare · 7 ngày qua</p>
                </div>
              </div>

              {/* Floating Niche Badge */}
              <div className="absolute -bottom-4 -right-4 bg-[var(--ink)] text-white rounded-xl px-5 py-3 shadow-lg">
                <p className="text-xs opacity-70 mb-0.5">Phủ sóng 17 niche creator</p>
                <p className="font-bold text-sm">Skincare · Review · Food · Affiliate...</p>
              </div>
            </motion.div>
          </div>

          {/* Trust Badges */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="mt-16 flex flex-wrap items-center justify-center gap-6 text-sm text-[var(--ink-soft)]"
          >
            <div className="flex items-center gap-2"><span>Data 100% từ TikTok Việt</span></div>
            <div className="hidden sm:block w-px h-4 bg-[var(--border)]" />
            <div className="flex items-center gap-2"><span>Cập nhật hàng giờ</span></div>
            <div className="hidden sm:block w-px h-4 bg-[var(--border)]" />
            <div className="flex items-center gap-2"><span>Chuyên biệt cho 17 niche creator</span></div>
          </motion.div>

          {/* Hook Ticker */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.6 }}
            className="mt-10 overflow-hidden border-t border-[var(--border)] pt-5"
          >
            <p className="text-xs text-[var(--muted)] mb-3 text-center">Các mẫu Hook đang "lên ngôi" tuần này</p>
            <div className="flex gap-3 animate-scroll-ticker">
              {[...hookTicker, ...hookTicker].map((hook, i) => (
                <div key={i} className="flex-shrink-0 border border-[var(--border)] rounded bg-white px-4 py-2">
                  <span className="text-xs text-[var(--ink-soft)] whitespace-nowrap">{hook}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── Statement ───────────────────────────────────────────── */}
      <section className="px-4 py-20 md:py-28 bg-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="font-extrabold text-[var(--ink)] leading-[1.4]" style={{ fontSize: "clamp(1.75rem, 4.5vw, 2.75rem)" }}>
            Công cụ duy nhất tự động "soi" hàng nghìn video mỗi&nbsp;ngày để tìm ra công&nbsp;thức viral cho bạn
          </h2>
        </div>
      </section>

      {/* ── Niche Chips ─────────────────────────────────────────── */}
      <div className="px-4 pb-16 bg-white">
        <div className="max-w-4xl mx-auto">
          <p className="text-xs text-center text-[var(--muted)] mb-4">Dành cho 17 nhóm creator thịnh hành tại Việt Nam</p>
          <div className="flex flex-wrap justify-center gap-2">
            {nicheList.map((niche) => (
              <span
                key={niche}
                className="text-xs text-[var(--ink-soft)] border border-[var(--border)] rounded-full px-3 py-1.5 bg-[var(--surface)] transition-colors duration-[120ms] hover:border-[var(--border-active)] hover:text-[var(--ink)] cursor-default"
              >
                {niche}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ── Pain Points ─────────────────────────────────────────── */}
      <section className="px-4 py-16 md:py-20 bg-white">
        <div className="max-w-5xl mx-auto">
          <p className="text-center text-sm text-[var(--muted)] mb-3 uppercase tracking-wide">Thực tế phũ phàng</p>
          <h2 className="text-center font-extrabold text-[var(--ink)] mb-10 md:mb-16" style={{ fontSize: "clamp(1.75rem, 4vw, 2.25rem)" }}>
            Đa số creator Việt đang làm như thế nào?
          </h2>
          <div className="grid md:grid-cols-3 gap-8 md:gap-16">
            {painPoints.map((p, idx) => (
              <motion.div
                key={p.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.4, delay: idx * 0.1 }}
                className="text-center"
              >
                <div className="mb-6 flex justify-center">
                  <div className="w-16 h-16 border-2 border-[var(--border)] rounded flex items-center justify-center transition-transform duration-200 hover:scale-110">
                    <span className="font-mono font-bold text-2xl text-[var(--muted)]">{idx + 1}</span>
                  </div>
                </div>
                <h3 className="font-bold text-[var(--ink)] mb-4 text-base">{p.title}</h3>
                <p className="text-sm text-[var(--ink-soft)] leading-relaxed max-w-xs mx-auto">{p.body}</p>
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

      {/* ── Results ─────────────────────────────────────────────── */}
      <section className="px-4 py-16 md:py-20 bg-white">
        <div className="max-w-5xl mx-auto">
          <p className="text-center text-sm text-[var(--muted)] mb-3">Kết quả thực</p>
          <h2 className="text-center font-extrabold text-[var(--ink)] mb-3" style={{ fontSize: "clamp(1.75rem, 4vw, 2.25rem)" }}>
            Số liệu nói thay lời
          </h2>
          <p className="text-center text-sm text-[var(--ink-soft)] mb-12 max-w-xl mx-auto leading-relaxed">
            Creator thật, kết quả đo được — không phải lời hứa.
          </p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4 }}
            className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6 md:p-8 mb-6"
          >
            <div className="grid md:grid-cols-[1fr_80px_1fr] gap-6 items-center">
              <div>
                <p className="text-xs text-[var(--muted)] mb-4 uppercase tracking-wide">Trước</p>
                <div className="font-mono font-bold text-[var(--ink-soft)] mb-1" style={{ fontSize: "clamp(2rem, 5vw, 2.75rem)" }}>2.000</div>
                <p className="text-sm text-[var(--ink-soft)] mb-5">view · video review nồi chiên</p>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[var(--danger)] font-bold text-sm">✕</span>
                    <span className="text-sm text-[var(--ink-soft)]">Hook chậm 2.3 giây</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[var(--danger)] font-bold text-sm">✕</span>
                    <span className="text-sm text-[var(--ink-soft)]">Không có mặt người 3 giây đầu</span>
                  </div>
                </div>
              </div>
              <div className="flex flex-col items-center gap-2">
                <div className="w-10 h-10 border border-[var(--border)] rounded flex items-center justify-center bg-white">
                  <span className="font-mono font-bold text-sm text-[var(--ink)] hidden md:inline">→</span>
                  <span className="font-mono font-bold text-sm text-[var(--ink)] md:hidden">↓</span>
                </div>
                <p className="text-xs text-[var(--muted)] font-mono text-center">GetViews</p>
              </div>
              <div>
                <p className="text-xs text-[var(--muted)] mb-4 uppercase tracking-wide">Sau khi fix</p>
                <div className="font-mono font-bold text-[var(--ink)] mb-1" style={{ fontSize: "clamp(2rem, 5vw, 2.75rem)" }}>45.000</div>
                <p className="text-sm text-[var(--ink-soft)] mb-5">view · quay lại theo gợi ý</p>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[var(--success)] font-bold text-sm">✓</span>
                    <span className="text-sm text-[var(--ink-soft)]">Mặt nhìn camera từ frame 0</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[var(--success)] font-bold text-sm">✓</span>
                    <span className="text-sm text-[var(--ink-soft)]">Hook &ldquo;Cảnh Báo&rdquo; đúng pattern niche</span>
                  </div>
                </div>
              </div>
            </div>
            <p className="text-xs font-mono text-[var(--faint)] mt-6 pt-4 border-t border-[var(--border)]">
              412 video review đồ gia dụng · 7 ngày · Updated 4h ago
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-4">
            {testimonials.map((t, i) => (
              <motion.div
                key={t.handle}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-5"
              >
                <p className="text-sm text-[var(--ink-soft)] leading-relaxed mb-5">&ldquo;{t.quote}&rdquo;</p>
                <div className="flex items-center gap-3 pt-4 border-t border-[var(--border)]">
                  <div className="w-8 h-8 rounded bg-[var(--ink)] flex items-center justify-center flex-shrink-0">
                    <span className="text-white text-xs font-bold">{t.initials}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-[var(--ink)] truncate">{t.handle}</p>
                    <p className="text-xs text-[var(--muted)] truncate">{t.niche} · {t.followers}</p>
                  </div>
                  <div className="flex-shrink-0">
                    <span className="font-mono text-xs font-bold text-[var(--ink)]">{t.stat}</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ─────────────────────────────────────────────── */}
      <section className="px-4 py-16 bg-[var(--surface)]" id="pricing">
        <div className="max-w-5xl mx-auto">
          <h2 className="font-extrabold text-[var(--ink)] mb-2 text-center" style={{ fontSize: "1.75rem" }}>
            Chọn gói phù hợp
          </h2>
          <p className="text-sm text-[var(--muted)] text-center mb-8">
            Thanh toán qua MoMo, VNPay, chuyển khoản, hoặc thẻ quốc tế.
          </p>

          <div className="flex justify-center mb-8">
            <div className="inline-flex bg-[var(--surface)] border border-[var(--border)] rounded-lg p-1">
              {(["monthly", "biannual", "annual"] as const).map((period) => (
                <button
                  key={period}
                  onClick={() => setBillingPeriod(period)}
                  className={`px-5 py-2 rounded-md text-sm font-medium transition-all duration-[120ms] relative ${
                    billingPeriod === period
                      ? "bg-[var(--ink)] text-white"
                      : "text-[var(--ink-soft)] hover:text-[var(--ink)]"
                  }`}
                >
                  {period === "monthly" ? "Tháng" : period === "biannual" ? "6 tháng" : "Năm"}
                  {period === "annual" && billingPeriod !== "annual" && (
                    <span className="absolute -top-2 -right-2 bg-[var(--ink)] text-white text-[9px] px-1.5 py-0.5 rounded-full font-medium whitespace-nowrap">
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
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: idx * 0.05 }}
                whileHover={{ y: -4 }}
                className={`border rounded-xl p-5 relative bg-[var(--surface)] transition-shadow duration-200 hover:shadow-lg ${
                  plan.popular ? "border-[var(--ink)] border-2" : "border-[var(--border)]"
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="bg-[var(--ink)] text-white text-xs px-3 py-1 rounded-full font-medium">Phổ biến</span>
                  </div>
                )}
                <h3 className="font-bold text-[var(--ink)] mb-1">{plan.label}</h3>
                <div className="mb-3">
                  <span className="font-mono font-bold text-[var(--ink)]" style={{ fontSize: "1.25rem" }}>{plan.price}</span>
                  {plan.name !== "Free" && billingPeriod !== "monthly" && (
                    <span className="text-xs text-[var(--muted)]">/tháng</span>
                  )}
                </div>
                <p className="text-xs text-[var(--ink-soft)] mb-5" style={{ lineHeight: "1.5" }}>{plan.credits}</p>
                <Link to="/login">
                  <Button fullWidth variant={plan.popular ? "primary" : "outlined"} className="text-sm py-2">
                    {plan.name === "Free" ? "Bắt đầu miễn phí" : `Nâng cấp ${plan.name}`}
                  </Button>
                </Link>
              </motion.div>
            ))}
          </div>

          {pricingSavings[billingPeriod] && (
            <p className="text-center text-sm text-[var(--ink-soft)]">{pricingSavings[billingPeriod]}</p>
          )}
        </div>
      </section>

      {/* ── FAQ ─────────────────────────────────────────────────── */}
      <section className="px-4 py-16">
        <div className="max-w-2xl mx-auto">
          <h2 className="font-extrabold text-[var(--ink)] mb-8 text-center" style={{ fontSize: "1.75rem" }}>
            Câu hỏi thường gặp
          </h2>
          <Accordion.Root type="single" collapsible className="space-y-3">
            {faqs.map((faq, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: idx * 0.05 }}
              >
                <Accordion.Item
                  value={`item-${idx}`}
                  className="border border-[var(--border)] rounded-xl overflow-hidden bg-[var(--surface)]"
                >
                  <Accordion.Header>
                    <Accordion.Trigger className="w-full px-5 py-4 text-left font-medium text-[var(--ink)] hover:bg-[var(--surface-alt)] transition-colors duration-[200ms] flex items-center justify-between group">
                      <span className="text-sm">{faq.q}</span>
                      <ChevronDown className="w-4 h-4 text-[var(--muted)] transition-transform duration-[200ms] group-data-[state=open]:rotate-180 flex-shrink-0 ml-3" />
                    </Accordion.Trigger>
                  </Accordion.Header>
                  <Accordion.Content
                    className="px-5 pb-4 text-sm text-[var(--ink-soft)] data-[state=open]:animate-accordion-down data-[state=closed]:animate-accordion-up"
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
      <section className="px-4 py-20 md:py-24 bg-[var(--ink)]">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="font-extrabold text-white mb-6 leading-tight" style={{ fontSize: "clamp(1.75rem, 4vw, 2.5rem)" }}>
            Dán 1 link. Xem GetViews nói gì.
          </h2>
          <Link to="/login">
            <button className="bg-white text-[var(--ink)] hover:bg-[var(--surface-alt)] font-semibold px-10 py-4 rounded-xl text-base transition-all duration-[120ms] active:scale-95">
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
