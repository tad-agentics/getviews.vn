import { memo } from "react";
import { Link } from "react-router";
import { ArrowRight } from "lucide-react";
import { SectionHeader } from "@/components/v2/SectionHeader";
import { TierHeader } from "@/components/v2/TierHeader";
import { useTopPatterns, type TopPatternsScope } from "@/hooks/useTopPatterns";
import { BreakoutGrid } from "./BreakoutGrid";
import { HooksTable } from "./HooksTable";
import { StudioHero } from "./StudioHero";

function hookTierTitle(nicheId: number | null, isPending: boolean, count: number): string {
  if (nicheId == null) return "Công thức hook đứng sau gợi ý";
  if (isPending) return "Công thức hook đứng sau gợi ý";
  if (count === 0) return "Chưa có công thức hook sau gợi ý";
  return `${count} công thức hook đứng sau gợi ý`;
}

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
 * Khối "GỢI Ý HÔM NAY" — 3 tầng I QUAY NGAY · II PATTERN · III CẢM HỨNG.
 *
 * Tier copy ports verbatim from the design pack's HomeScreen
 * (home.jsx:136-180) — the actionability ladder reads as a single
 * teaching surface (filled-in ideas → templates that produced them →
 * outside case studies).
 */
export const HomeSuggestionsToday = memo(function HomeSuggestionsToday({
  patternScope,
  creatorNicheId,
}: {
  patternScope: TopPatternsScope | null;
  creatorNicheId: number | null;
}) {
  const { data: hookPatterns, isPending: hooksPending } = useTopPatterns(patternScope);
  const hookCount = hookPatterns?.length ?? 0;
  const tier02Title = hookTierTitle(patternScope?.legacyNicheId ?? null, hooksPending, hookCount);

  return (
    <section className="mb-12">
      <SectionHeader
        kicker="GỢI Ý HÔM NAY"
        kickerSparkles
        title="Từ sẵn-quay đến cảm-hứng"
        caption={
          <>
            <span className="sm:hidden">
              3 tầng: quay ngay → công thức hook để remix → case study kênh khác.
            </span>
            <span className="hidden sm:inline">
              Gợi ý video cụ thể để quay ngay hôm nay, công thức hook để bạn biến tấu theo phong cách của mình, và bài học
              thực tế từ kênh khác để đối chiếu.
            </span>
          </>
        }
        className="!mb-10"
      />

      {/* PR-4 — data-tier anchors back the channel diagnostic's bridge
       * pills + the "Xem gợi ý ↓" ribbon at the bottom of the
       * Scroll tier deep-link from channel diagnostics (see scrollToTier.ts). */}
      <div className="mb-10 scroll-mt-20" data-tier="01">
        <TierHeader
          num="I"
          tag="HÔM NAY QUAY NGAY"
          tagTone="accent"
          title="3 video tiếp theo bạn nên làm"
          caption="Tổng hợp từ pattern thắng 7 ngày qua. Cả 3 ý tưởng đều có kịch bản sẵn — bấm dòng để mở trong Phân tích."
        />
        <StudioHero nicheId={patternScope?.legacyNicheId ?? null} />
      </div>

      <div className="mb-10 scroll-mt-20" data-tier="02">
        <TierHeader
          num="II"
          tag="CÔNG THỨC NỀN"
          tagTone="pos"
          title={tier02Title}
          caption="Đây là các pattern đang ăn nhất tuần qua — các ý tưởng phía trên được sinh ra từ chúng. Lấy công thức trống, điền nội dung khác của bạn vào để mở rộng."
        />
        <HooksTable embedded patternScope={patternScope} />
      </div>

      <div className="scroll-mt-20" data-tier="03">
        <TierHeader
          num="III"
          tag="CẢM HỨNG"
          tagTone="ink"
          title="3 video breakout trong ngách của bạn"
          caption="Breakout trong ngách bạn (Tier III) — khác rail 7 ngày và format khác ngách ở tab Xu hướng."
          right={SEE_ALL_TRENDS}
        />
        <BreakoutGrid embedded creatorNicheId={creatorNicheId} />
      </div>
    </section>
  );
});
