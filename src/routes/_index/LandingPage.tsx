import { useState, useEffect, useMemo } from "react";
import { Link, useNavigate } from "react-router";
import * as Accordion from "@radix-ui/react-accordion";
import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { motion, AnimatePresence } from "motion/react";
import { pricingPlans, pricingSavings } from "@/lib/mock-data";
import { useAuth } from "@/lib/auth";
import { useInstallPrompt } from "@/hooks/useInstallPrompt";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const faqs = [
  {
    q: "Khác gì ChatGPT?",
    a: 'ChatGPT không có data TikTok và không xem được video. Bạn hỏi "hook nào đang hot trong skincare" — ChatGPT bịa ra câu trả lời nghe hợp lý nhưng không dựa trên video nào cả. GetViews trả lời dựa trên video thật, view thật, bạn bấm vào xem kiểm chứng được.',
  },
  {
    q: "Tôi mua khóa học rồi, cần thêm cái này không?",
    a: "Khóa học dạy bạn nền tảng — algorithm, cách quay, cách edit. Tốt. Nhưng nó không nói cho bạn biết tuần này hook nào đang chạy trong đúng niche của bạn. GetViews bổ sung chỗ khóa học không cover được: data thực, cập nhật mỗi ngày, cho đúng niche.",
  },
  {
    q: "Khác gì Kalodata?",
    a: "Kalodata chỉ cho bạn biết sản phẩm nào bán chạy. GetViews chỉ cho bạn biết TẠI SAO cái video bán được chạy — hook kiểu gì, mở đầu ra sao, nhịp cắt thế nào. Hai cái khác nhau, dùng song song được.",
  },
  {
    q: "1 credit là gì?",
    a: "Phân tích sâu (soi video, phân tích đối thủ, viết brief) = 1 credit. Lướt xu hướng, tìm KOL, và hỏi thêm trong cùng phiên — miễn phí, không giới hạn.",
  },
  {
    q: "Thanh toán sao?",
    a: "MoMo, VNPay, chuyển khoản, hoặc thẻ Visa/Mastercard. Mua xong dùng được ngay.",
  },
  {
    q: "Lỡ không hiệu quả thì sao?",
    a: "Không hợp đồng, hủy lúc nào cũng được. Mua gói tháng thử trước, thấy ổn thì chuyển gói dài hơn.",
  },
];

const painPoints = [
  {
    title: "Lướt TikTok Cả Ngày",
    body: 'Sáng mở TikTok "nghiên cứu" — 2 tiếng sau vẫn đang lướt. Screenshot mấy video hay, quăng vô Google Sheet rồi quên luôn. Hôm sau lại lướt lại từ đầu. Quen không?',
  },
  {
    title: "Học Rồi Vẫn Không Biết Quay Gì",
    body: "Mua khóa học 3-5 triệu xong cũng nắm được lý thuyết. Nhưng mở app lên vẫn không biết hôm nay nên quay cái gì. Algorithm thay đổi liên tục — kiến thức tháng trước tháng này đã khác.",
  },
  {
    title: "Video Flop Mà Không Biết Tại Sao",
    body: "Quay xong đăng lên, ngồi chờ. 500 view. Không biết lỗi ở hook, ở nhịp, hay ở format. Video đối thủ triệu view — cũng không biết họ làm gì khác mình.",
  },
];

const solutions = [
  {
    title: "Xem Video Thật, Nói Cho Bạn Thật",
    body: "GetViews không đoán. Nó xem thật video của bạn — mặt xuất hiện giây nào, text overlay ở đâu, nhịp cắt cảnh ra sao — rồi so với video đang chạy tốt nhất trong niche của bạn. Mọi gợi ý đều kèm video thật có view thật, bạn bấm vào xem được luôn.",
  },
  {
    title: "Hôm Nay Hỏi, Hôm Nay Có",
    body: "Khóa học dạy bạn tháng 1, tháng 4 đã cũ. GetViews biết hook nào đang chạy tuần này, trong đúng niche của bạn. Hỏi lúc nào cũng được, data luôn mới.",
  },
  {
    title: "Làm Cho Creator Việt Nam",
    body: "Đây không phải tool Tây dịch ra tiếng Việt. GetViews hiểu review đồ gia dụng, làm đẹp, Shopee affiliate, hài phương ngữ — 17 niche của creator Việt. Hỏi bằng tiếng Việt, trả lời bằng tiếng Việt, data từ TikTok Việt Nam.",
  },
];

const SITE_URL = "https://getviews.vn";

/* ─── LiveDemoSection ──────────────────────────────────────────── */
function LiveDemoSection() {
  const prompts = [
    "Tại sao video này ít view — lỗi ở đâu?",
    "Hook nào đang hot trong review đồ gia dụng?",
    "Soi kênh @đối_thủ — họ đang làm gì?",
    "Viết brief cho KOL quay video skincare",
    "Format nào đang lên tuần này?",
  ];

  const diagnosisRows = [
    {
      type: "fail" as const,
      finding: "Không mặt trong 3 giây đầu",
      benchmark:
        "92% top video trong niche mở bằng mặt. Fix: Quay lại, mở bằng mặt nhìn camera trong 0.5s đầu.",
    },
    {
      type: "fail" as const,
      finding: "Text overlay xuất hiện ở giây 3.2",
      benchmark: "Top video: 0.8 giây. Fix: Chuyển text lên frame đầu tiên.",
    },
    {
      type: "pass" as const,
      finding: "Hook 'Cảnh Báo' — đúng pattern",
      benchmark: "Trung bình 3.2x views so với 'Kể Chuyện'.",
    },
  ];

  return (
    <section className="px-4 py-16 bg-[var(--surface)]">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl font-extrabold mb-2">
          <span className="gradient-text">GetViews hoạt động thế nào</span>
        </h2>
        <p className="text-sm text-[var(--muted)] mb-8">Dán link → GetViews xem video → trả lời bằng data thực.</p>

        <div className="border border-[var(--border)] rounded-xl overflow-hidden bg-[var(--background)]">
          <div className="flex flex-wrap gap-2 p-4 bg-[var(--surface)] border-b border-[var(--border)]">
            {prompts.map((p, i) => (
              <span
                key={i}
                className="px-3 py-1.5 bg-[var(--surface-alt)] border border-[var(--border)] rounded-lg text-xs text-[var(--ink-soft)]"
              >
                {p}
              </span>
            ))}
          </div>

          <div className="p-4 space-y-4">
            <div className="flex justify-end">
              <div className="max-w-[80%] bg-[var(--purple-light)] rounded-xl px-4 py-3">
                <p className="text-sm text-[var(--ink)]">
                  Tại sao video này chỉ 2.000 view? https://tiktok.com/@minhreview/video/...
                </p>
              </div>
            </div>

            <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-4">
              <p className="text-xs text-[var(--muted)] mb-3">Đã so sánh với 412 video trong niche —</p>
              <div className="space-y-3">
                {diagnosisRows.map((row, i) => (
                  <div
                    key={i}
                    className={`flex gap-3 py-2 ${i === 0 ? "border-l-2 border-[var(--purple)] pl-3" : ""}`}
                  >
                    <span
                      className={`flex-shrink-0 font-bold text-sm ${row.type === "fail" ? "text-[var(--danger)]" : "text-[var(--success)]"}`}
                    >
                      {row.type === "fail" ? "✕" : "✓"}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-[var(--ink)]">{row.finding}</p>
                      <p className="text-xs text-[var(--ink-soft)]">{row.benchmark}</p>
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-xs font-mono text-[var(--faint)] mt-3">
                412 video review đồ gia dụng · 7 ngày · Cập nhật 4h trước
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function LandingPage() {
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "biannual" | "annual">("annual");
  const [stickyVisible, setStickyVisible] = useState(false);
  const [iosOpen, setIosOpen] = useState(false);
  const [online, setOnline] = useState(true);

  const { session, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const { canInstall, isIOS, isInstalled, prompt } = useInstallPrompt();

  useEffect(() => {
    const handleScroll = () => setStickyVisible(window.scrollY > 480);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  const plans = pricingPlans[billingPeriod];

  const handlePrimaryCta = () => {
    if (authLoading) return;
    if (session) {
      navigate("/app");
      return;
    }
    if (isInstalled) {
      navigate("/app");
      return;
    }
    if (canInstall) {
      void prompt();
      return;
    }
    if (isIOS) {
      setIosOpen(true);
      return;
    }
    navigate("/login");
  };

  const orgJsonLd = useMemo(
    () => ({
      "@context": "https://schema.org",
      "@type": "Organization",
      name: "GetViews",
      url: SITE_URL,
      description:
        "Dán link video của bạn vào. 1 phút sau biết ngay lỗi ở đâu, nên fix gì, và hook nào đang chạy trong niche của bạn. Không guru. Không screenshot. Data thực từ video thực.",
    }),
    [],
  );

  const faqJsonLd = useMemo(
    () => ({
      "@context": "https://schema.org",
      "@type": "FAQPage",
      mainEntity: faqs.map((f) => ({
        "@type": "Question",
        name: f.q,
        acceptedAnswer: {
          "@type": "Answer",
          text: f.a,
        },
      })),
    }),
    [],
  );

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(orgJsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />

      <Dialog open={iosOpen} onOpenChange={setIosOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Cài GetViews trên iPhone</DialogTitle>
            <DialogDescription className="text-left text-[var(--ink-soft)]">
              Nhấn nút Chia sẻ trong Safari, chọn &quot;Thêm vào Màn hình chính&quot;, rồi mở GetViews từ
              icon trên màn hình.
            </DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>

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
                <span className="text-xs text-white/60 hidden sm:block">Không cần thẻ</span>
                <button
                  type="button"
                  disabled={authLoading}
                  onClick={handlePrimaryCta}
                  className="bg-[var(--purple)] hover:bg-[var(--purple-dark)] text-white text-sm font-medium px-5 py-2 rounded-lg transition-colors duration-[120ms] active:scale-95 disabled:opacity-60"
                >
                  Soi Video Miễn Phí
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <section className="px-4 pt-16 pb-12 md:pt-24 md:pb-16">
        <div className="max-w-2xl mx-auto">
          <div className="mb-8">
            <span className="font-extrabold text-2xl text-[var(--ink)]">
              GetViews<span className="text-[var(--brand-red)]">.vn</span>
            </span>
          </div>

          <h1 className="font-extrabold mb-5 leading-tight" style={{ fontSize: "clamp(1.75rem, 5vw, 2.5rem)" }}>
            <span className="text-[var(--ink)]">Bạn lướt TikTok cả ngày để tìm ý tưởng.</span>
            <br />
            <span className="gradient-text">GetViews làm việc đó thay bạn.</span>
          </h1>

          <p className="text-[var(--ink-soft)] mb-3 max-w-xl" style={{ fontSize: "1rem", lineHeight: "1.6" }}>
            Dán link video của bạn vào. 1 phút sau biết ngay lỗi ở đâu, nên fix gì, và hook nào đang chạy
            trong niche của bạn.
          </p>

          <p className="text-sm text-[var(--muted)] mb-8">
            Không guru. Không screenshot. Data thực từ video thực.
          </p>

          <div className="max-w-xl mb-3">
            <div className="flex gap-2">
              <Input
                placeholder="Dán link TikTok để bắt đầu"
                className="flex-1"
                style={{ fontSize: "16px" }}
                disabled={!online}
                aria-invalid={!online}
              />
              <button
                type="button"
                disabled={authLoading}
                onClick={handlePrimaryCta}
                className="flex-shrink-0 px-6 py-3 gradient-cta font-medium rounded-lg text-sm transition-all duration-[120ms] active:scale-95 whitespace-nowrap disabled:opacity-60"
              >
                Soi Video Miễn Phí
              </button>
            </div>
            {!online ? (
              <p className="text-xs text-[var(--danger)] mt-2" role="alert">
                Không kết nối được — kiểm tra mạng và thử lại.
              </p>
            ) : null}
          </div>

          <p className="text-xs text-[var(--muted)]">
            {isIOS
              ? "Truy cập ngay trong trình duyệt"
              : "10 lần phân tích sâu miễn phí · Lướt xu hướng không giới hạn · Không cần thẻ"}
          </p>
        </div>
      </section>

      <section className="px-4 py-12 bg-[var(--surface)]">
        <div className="max-w-5xl mx-auto">
          <div className="grid md:grid-cols-3 gap-4">
            {painPoints.map((p) => (
              <div key={p.title} className="border border-[var(--border)] rounded-xl p-6 bg-[var(--surface)]">
                <h3 className="font-extrabold text-[var(--ink)] mb-3">{p.title}</h3>
                <p className="text-sm text-[var(--ink-soft)]" style={{ lineHeight: "1.6" }}>
                  {p.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-4 py-12">
        <div className="max-w-5xl mx-auto">
          <div className="grid md:grid-cols-3 gap-4">
            {solutions.map((s) => (
              <div key={s.title} className="border border-[var(--border)] rounded-xl p-6 bg-[var(--surface)]">
                <h3 className="font-extrabold text-[var(--ink)] mb-3">{s.title}</h3>
                <p className="text-sm text-[var(--ink-soft)]" style={{ lineHeight: "1.6" }}>
                  {s.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <LiveDemoSection />

      <section className="px-4 py-12">
        <div className="max-w-3xl mx-auto">
          <div className="border border-[var(--border)] rounded-xl p-8 bg-[var(--surface)]">
            <div className="grid sm:grid-cols-3 gap-6 sm:gap-8 text-center sm:text-left">
              <div className="sm:col-span-1">
                <p className="text-xs text-[var(--muted)] mb-1 uppercase tracking-wide">Trước</p>
                <p className="font-mono font-bold text-[var(--ink)] mb-1" style={{ fontSize: "1.5rem" }}>
                  2.000
                </p>
                <p className="text-sm text-[var(--ink-soft)]">views</p>
              </div>
              <div className="sm:col-span-1 flex flex-col items-center justify-center">
                <div className="text-xs text-[var(--muted)] text-center px-3 py-2 border border-[var(--border)] rounded-lg bg-[var(--surface-alt)]">
                  GetViews phát hiện hook chậm 2.1 giây, không có mặt người
                </div>
              </div>
              <div className="sm:col-span-1 sm:text-right">
                <p className="text-xs text-[var(--muted)] mb-1 uppercase tracking-wide">Sau</p>
                <p className="font-mono font-bold text-[var(--purple)] mb-1" style={{ fontSize: "1.5rem" }}>
                  45.000
                </p>
                <p className="text-sm text-[var(--ink-soft)]">views</p>
              </div>
            </div>
          </div>
          <p
            className="mt-4 text-center text-sm text-[var(--ink-soft)] px-2"
            style={{ lineHeight: 1.6 }}
          >
            Video gốc: 2.000 views. GetViews phát hiện hook chậm 2.1 giây, không có mặt người. Quay lại theo
            gợi ý: 45.000 views.
          </p>
        </div>
      </section>

      <section className="px-4 py-16 bg-[var(--surface)]" id="pricing">
        <div className="max-w-5xl mx-auto">
          <h2 className="font-extrabold text-[var(--ink)] mb-2 text-center" style={{ fontSize: "1.75rem" }}>
            Chọn gói <span className="gradient-text">phù hợp</span>
          </h2>
          <p className="text-sm text-[var(--muted)] text-center mb-8">
            Thanh toán qua MoMo, VNPay, chuyển khoản, hoặc thẻ quốc tế.
          </p>

          <div className="flex justify-center mb-8">
            <div className="inline-flex bg-[var(--background)] border border-[var(--border)] rounded-lg p-1">
              {(["monthly", "biannual", "annual"] as const).map((period) => (
                <button
                  key={period}
                  type="button"
                  onClick={() => setBillingPeriod(period)}
                  className={`px-5 py-2 rounded-md text-sm font-medium transition-all duration-[120ms] relative ${
                    billingPeriod === period
                      ? "bg-[var(--purple)] text-white"
                      : "text-[var(--ink-soft)] hover:text-[var(--ink)]"
                  }`}
                >
                  {period === "monthly" ? "Tháng" : period === "biannual" ? "6 tháng" : "Năm"}
                  {period === "annual" && billingPeriod !== "annual" && (
                    <span className="absolute -top-2 -right-2 bg-[var(--purple)] text-white text-[9px] px-1.5 py-0.5 rounded-full font-medium whitespace-nowrap">
                      Tiết kiệm nhất
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          <div className="grid md:grid-cols-4 gap-4 mb-4">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`border rounded-xl p-5 relative bg-[var(--surface)] ${
                  plan.popular ? "border-[var(--purple)] border-2" : "border-[var(--border)]"
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="bg-[var(--purple)] text-white text-xs px-3 py-1 rounded-full font-medium">
                      Phổ biến nhất
                    </span>
                  </div>
                )}
                <h3 className="font-bold text-[var(--ink)] mb-1">{plan.label}</h3>
                <div className="mb-3">
                  <span className="font-mono font-bold text-[var(--ink)]" style={{ fontSize: "1.25rem" }}>
                    {plan.price}
                  </span>
                  {plan.name !== "Free" && billingPeriod !== "monthly" && (
                    <span className="text-xs text-[var(--muted)]">/tháng</span>
                  )}
                </div>
                <p className="text-xs text-[var(--ink-soft)] mb-5" style={{ lineHeight: "1.5" }}>
                  {plan.credits}
                </p>
                <Link to="/login">
                  <Button fullWidth variant={plan.popular ? "primary" : "outlined"} className="text-sm py-2">
                    {plan.name === "Free" ? "Bắt đầu miễn phí" : `Nâng cấp ${plan.name}`}
                  </Button>
                </Link>
              </div>
            ))}
          </div>

          {pricingSavings[billingPeriod] ? (
            <p className="text-center text-sm text-[var(--purple)] font-medium">
              {pricingSavings[billingPeriod]}
            </p>
          ) : null}
        </div>
      </section>

      <section className="px-4 py-16">
        <div className="max-w-2xl mx-auto">
          <h2 className="font-extrabold text-[var(--ink)] mb-8" style={{ fontSize: "1.75rem" }}>
            Câu hỏi <span className="gradient-text">thường gặp</span>
          </h2>

          <Accordion.Root type="single" collapsible className="space-y-3">
            {faqs.map((faq, idx) => (
              <Accordion.Item
                key={idx}
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
            ))}
          </Accordion.Root>
        </div>
      </section>

      <section className="px-4 py-16 bg-[var(--ink)]">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="font-extrabold text-white mb-4" style={{ fontSize: "clamp(1.5rem, 4vw, 2rem)" }}>
            Thử dán 1 link video vào. Miễn phí. Xem GetViews nói gì.
          </h2>
          <button
            type="button"
            disabled={authLoading}
            onClick={handlePrimaryCta}
            className="bg-white text-[var(--ink)] hover:bg-[var(--surface-alt)] font-medium px-8 py-3 rounded-lg text-sm transition-colors duration-[120ms] active:scale-95 disabled:opacity-60"
          >
            Soi Video Ngay
          </button>
        </div>
      </section>

      {stickyVisible ? <div className="h-14" /> : null}
    </div>
  );
}
