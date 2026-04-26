import { memo } from "react";
import { Link } from "react-router";
import { ArrowRight } from "lucide-react";
import { SectionHeader } from "@/components/v2/SectionHeader";
import { TierHeader } from "@/components/v2/TierHeader";
import { BreakoutGrid } from "./BreakoutGrid";
import { HooksTable } from "./HooksTable";
import { StudioHero } from "./StudioHero";

const SEE_ALL_TRENDS = (
  <Link
    to="/app/trends"
    className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1.5 text-xs font-medium text-[color:var(--gv-ink-2)] transition-colors hover:border-[color:var(--gv-ink)] hover:text-[color:var(--gv-ink)]"
  >
    <span>Xem tất cả</span>
    <ArrowRight className="h-3 w-3" aria-hidden />
  </Link>
);

const OPEN_ALL_SCRIPTS = (
  <Link
    to="/app/script"
    className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1.5 text-xs font-medium text-[color:var(--gv-ink-2)] transition-colors hover:border-[color:var(--gv-ink)] hover:text-[color:var(--gv-ink)]"
  >
    <span>Mở tất cả</span>
    <ArrowRight className="h-3 w-3" aria-hidden />
  </Link>
);

/**
 * Khối "GỢI Ý HÔM NAY" — 3 tầng 01 QUAY NGAY · 02 PATTERN · 03 CẢM HỨNG.
 *
 * Tier copy ports verbatim from the design pack's HomeScreen
 * (home.jsx:136-180) — the actionability ladder reads as a single
 * teaching surface (filled-in ideas → templates that produced them →
 * outside case studies).
 */
export const HomeSuggestionsToday = memo(function HomeSuggestionsToday({
  nicheId,
}: {
  nicheId: number | null;
}) {
  return (
    <section className="mb-12">
      <SectionHeader
        kicker="GỢI Ý HÔM NAY"
        kickerSparkles
        title="Từ sẵn-quay đến cảm-hứng"
        caption="Ba tầng theo mức độ hành động: video bạn nên quay hôm nay, công thức hook nền để remix, và case study từ kênh khác."
        className="!mb-10"
      />

      {/* PR-4 — data-tier anchors back the channel diagnostic's bridge
       * pills + the "Xem gợi ý ↓" ribbon at the bottom of the
       * HomeMyChannelSection card (see scrollToTier.ts). */}
      <div className="mb-10 scroll-mt-20" data-tier="01">
        <TierHeader
          num="01"
          tag="HÔM NAY QUAY NGAY"
          tagTone="accent"
          title="Video tiếp theo bạn nên làm"
          caption="Tổng hợp từ pattern thắng 7 ngày qua. Mỗi ý tưởng đã có script viết sẵn — click để mở thẳng."
          right={OPEN_ALL_SCRIPTS}
        />
        <StudioHero nicheId={nicheId} />
      </div>

      <div className="mb-10 scroll-mt-20" data-tier="02">
        <TierHeader
          num="02"
          tag="CÔNG THỨC NỀN"
          tagTone="pos"
          title="6 công thức hook đứng sau gợi ý"
          caption="Đây là các pattern đang ăn nhất tuần qua — các ý tưởng phía trên được sinh ra từ chúng. Lấy công thức trống, điền nội dung khác của bạn vào để mở rộng."
        />
        <HooksTable embedded nicheId={nicheId} />
      </div>

      <div className="scroll-mt-20" data-tier="03">
        <TierHeader
          num="03"
          tag="CẢM HỨNG"
          tagTone="ink"
          title="3 video đột phá ngoài kênh bạn"
          caption="View vượt 10× trung bình kênh đó trong 48h. Để xem cách kênh khác bứt phá."
          right={SEE_ALL_TRENDS}
        />
        <BreakoutGrid embedded nicheId={nicheId} />
      </div>
    </section>
  );
});
