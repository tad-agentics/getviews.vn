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
        kickerTone="accent"
        title="Ý tưởng sẵn quay & Cảm hứng sáng tạo"
        caption="Gợi ý chi tiết video bạn có thể quay ngay hôm nay, các công thức hook hiệu quả nhất để bạn biến tấu theo phong cách riêng, cùng những ý tưởng bứt phá thực tế từ đối thủ để tham khảo."
        className="!mb-10"
      />

      {/* PR-4 — data-tier anchors back the channel diagnostic's bridge
       * pills + the "Xem gợi ý ↓" ribbon at the bottom of the
       * Scroll tier deep-link from channel diagnostics (see scrollToTier.ts). */}
      <div className="mb-10 scroll-mt-20" data-tier="01">
        <TierHeader
          num="I"
          tag="Ý TƯỞNG ĂN LIỀN"
          tagTone="accent"
          title="3 video tiếp theo bạn nên quay"
          caption="Tổng hợp từ các định dạng (format) thành công nhất 7 ngày qua. Cả 3 ý tưởng đều có sẵn kịch bản chi tiết — bấm vào dòng bất kỳ để xem."
        />
        <StudioHero nicheId={patternScope?.legacyNicheId ?? null} />
      </div>

      <div className="mb-10 scroll-mt-20" data-tier="02">
        <TierHeader
          num="II"
          tag="CÔNG THỨC HOOK"
          tagTone="pos"
          title={tier02Title}
          caption="Khung tiêu đề (hook) thu hút người xem nhất 7 ngày qua — ba ý tưởng gợi ý ở trên đều được phát triển dựa theo các công thức này. Hãy giữ nguyên cấu trúc và thay đổi chủ đề theo phong cách của bạn."
        />
        <HooksTable embedded patternScope={patternScope} />
      </div>

      <div className="scroll-mt-20" data-tier="03">
        <TierHeader
          num="III"
          tag="CẢM HỨNG BỨT PHÁ"
          tagTone="ink"
          title="3 video bứt phá nổi bật trong ngách"
          caption="Tuyển chọn video đạt lượng xem vượt trội so với trung bình kênh của đối thủ — học hỏi cách làm khác biệt để tạo nội dung độc đáo cho riêng bạn."
          right={SEE_ALL_TRENDS}
        />
        <BreakoutGrid embedded creatorNicheId={creatorNicheId} />
      </div>
    </section>
  );
});
