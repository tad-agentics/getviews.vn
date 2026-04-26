import { memo } from "react";
import { Link } from "react-router";
import { ArrowRight } from "lucide-react";
import { SectionHeader } from "@/components/v2/SectionHeader";
import { TierHeader } from "@/components/v2/TierHeader";
import { BreakoutGrid } from "./BreakoutGrid";
import { HomeMorningRitual } from "./HomeMorningRitual";
import { HooksTable } from "./HooksTable";
import { NextVideosCard } from "./NextVideosCard";

const SEE_ALL_TRENDS = (
  <Link
    to="/app/trends"
    className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1.5 text-xs font-medium text-[color:var(--gv-ink-2)] transition-colors hover:border-[color:var(--gv-ink)] hover:text-[color:var(--gv-ink)]"
  >
    <span>Xem tất cả</span>
    <ArrowRight className="h-3 w-3" aria-hidden />
  </Link>
);

/**
 * Khối “GỢI Ý HÔM NAY” — 3 tầng 01 QUAY NGAY · 02 PATTERN · 03 CẢM HỨNG (ref UIUX).
 */
export const HomeSuggestionsToday = memo(function HomeSuggestionsToday({
  nicheLabel,
  nicheId,
  onSelectPrompt,
}: {
  nicheLabel: string;
  nicheId: number | null;
  onSelectPrompt: (prompt: string) => void;
}) {
  return (
    <section className="mb-12">
      <SectionHeader
        kicker="GỢI Ý HÔM NAY"
        kickerSparkles
        title="Từ sẵn-quay đến cảm-hứng"
        caption="Ba tầng gợi ý: kịch bản & lịch 5 video quay ngay, pattern để remix, và case study từ kênh khác."
        className="!mb-10"
      />

      {/* PR-4 — data-tier anchors back the channel diagnostic's bridge
       * pills + the "Xem gợi ý ↓" ribbon at the bottom of the
       * HomeMyChannelSection card (see scrollToTier.ts). */}
      <div className="mb-10 scroll-mt-20" data-tier="01">
        <TierHeader
          num="01"
          tag="QUAY NGAY"
          tagTone="accent"
          title="3 kịch bản sẵn sàng & 5 video tiếp theo"
          caption="Kịch bản từ pattern thắng qua đêm (hook, structure, CTA). Tiếp theo là báo cáo 5 video với hook, câu mở và góc nội dung — dựa trên 7 ngày gần nhất trong ngách bạn."
        />
        <HomeMorningRitual
          embedded
          nicheLabel={nicheLabel}
          nicheId={nicheId}
          onSelectPrompt={onSelectPrompt}
        />
        <div className="mt-10">
          <NextVideosCard embedded nicheLabel={nicheLabel} />
        </div>
      </div>

      <div className="mb-10 scroll-mt-20" data-tier="02">
        <TierHeader
          num="02"
          tag="PATTERN DỄ REMIX"
          tagTone="pos"
          title="Hook đang chạy trong ngách"
          caption="Top 6 mẫu hook 3 giây tăng trưởng nhanh nhất tuần qua. Lấy công thức, đổi nội dung của bạn vào."
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
