import { memo } from "react";
import { useNavigate } from "react-router";
import { ArrowRight } from "lucide-react";

import { Btn } from "@/components/v2/Btn";
import { useDailyRitual, type RitualScript } from "@/hooks/useDailyRitual";
import { formatRelativeSinceVi } from "@/lib/formatters";
import { scriptPrefillFromRitual } from "@/lib/scriptPrefill";

/**
 * Studio Home — Tier 01 hero ("HÔM NAY QUAY NGAY") ranked list.
 *
 * Replaces the earlier HomeMorningRitual (3 cards) + NextVideosCard
 * (link to /app/answer) split — the design pack's
 * StudioHero (home.jsx:1154-1248) renders a single full-width ranked
 * list of idea rows, not a grid. Each row carries:
 *   • pad-zero rank ``01..NN``
 *   • mono uppercase HOOK badge
 *   • cyan ``● SCRIPT SẴN · X shot · Ys`` pill (every ritual script
 *     ships with a draft, so we always show the pill)
 *   • mono angle subtitle (hook_type_vi)
 *   • serif italicised quoted title (the actual hook text)
 *   • right column with ``▲ ~X%`` retention estimate + ``MỞ SCRIPT →``
 *
 * Click routes to ``/app/script`` with the idea preselected via
 * ``scriptPrefillFromRitual``.
 *
 * Today the BE generates 3 ritual scripts per niche per night; the
 * design pack mocks 5. The component renders whatever the BE returns,
 * so once the cron is extended the row count flexes up automatically.
 */

export const StudioHero = memo(function StudioHero({
  nicheId,
}: {
  nicheId: number | null;
}) {
  const { data: ritual, emptyReason, isPending, refetch } = useDailyRitual(true, nicheId);
  const navigate = useNavigate();

  if (isPending) {
    return (
      <div className="overflow-hidden rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-[18px]">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className={
              "h-[100px] animate-pulse " +
              (i === 0 ? "" : "border-t border-[color:var(--gv-rule)]")
            }
          />
        ))}
      </div>
    );
  }

  if (!ritual || ritual.scripts.length === 0) {
    const isNicheStale = emptyReason === "ritual_niche_stale";
    return (
      <div className="rounded-md border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-6 text-[13px] leading-relaxed text-[color:var(--gv-ink-3)]">
        <p className="m-0 text-[14px] font-medium text-[color:var(--gv-ink)]">
          {isNicheStale ? "Kịch bản mới đang chuẩn bị cho ngách này" : "Đang tạo kịch bản cho ngày đầu"}
        </p>
        <p className="mt-1.5">
          {isNicheStale
            ? "Lần tạo kế tiếp sẽ có 3 kịch bản theo ngách bạn vừa chọn."
            : "Cron sáng sẽ xếp sẵn 3 kịch bản mới vào 7h. Ghé lại sáng mai nhé."}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Btn variant="ghost" size="sm" type="button" onClick={() => void refetch()}>
            Thử tải lại
          </Btn>
          <Btn variant="ghost" size="sm" type="button" onClick={() => navigate("/app/trends")}>
            Khám phá ngách
          </Btn>
        </div>
      </div>
    );
  }

  const isThin = ritual.adequacy === "none" || ritual.adequacy === "reference_pool";
  const updatedRel = formatRelativeSinceVi(new Date(), new Date(ritual.generated_at));

  return (
    <div>
      <p className="gv-mono mb-3 text-[11px] text-[color:var(--gv-ink-4)]">
        Cập nhật · {updatedRel}
        {isThin ? (
          <span className="text-[color:var(--gv-ink-3)]">
            {" "}· Dữ liệu ngách đang thưa, các retention estimate là định hướng.
          </span>
        ) : null}
      </p>
      <div className="overflow-hidden rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-[18px]">
        {ritual.scripts.map((s, i) => (
          <StudioHeroRow
            key={`${s.hook_type_en}-${i}`}
            script={s}
            rank={i + 1}
            isFirst={i === 0}
            onClick={() => {
              if (nicheId == null) return;
              navigate(scriptPrefillFromRitual(s, nicheId));
            }}
          />
        ))}
      </div>
    </div>
  );
});

const StudioHeroRow = memo(function StudioHeroRow({
  script,
  rank,
  isFirst,
  onClick,
}: {
  script: RitualScript;
  rank: number;
  isFirst: boolean;
  onClick: () => void;
}) {
  const rankLabel = String(rank).padStart(2, "0");
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        "group grid w-full grid-cols-[40px_1fr_auto] items-center gap-x-4 gap-y-2 py-[18px] text-left transition-colors hover:bg-[color:var(--gv-canvas-2)] " +
        (isFirst ? "" : "border-t border-[color:var(--gv-rule)]")
      }
    >
      <span
        className="gv-mono self-start pt-1 text-[26px] font-semibold leading-none tracking-[-0.02em] text-[color:var(--gv-ink-4)]"
        aria-hidden
      >
        {rankLabel}
      </span>
      <div className="min-w-0">
        <div className="mb-1.5 flex flex-wrap items-center gap-2">
          <span className="gv-mono inline-flex items-center whitespace-nowrap rounded-[2px] bg-[color:var(--gv-ink)] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-[0.1em] text-white">
            HOOK #{rank}
          </span>
          <span
            className="gv-mono inline-flex items-center gap-1 whitespace-nowrap rounded-[2px] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-[0.1em]"
            style={{
              background: "color-mix(in srgb, var(--gv-pos) 12%, transparent)",
              color: "var(--gv-pos-deep)",
            }}
          >
            <span aria-hidden>●</span>
            SCRIPT SẴN · {script.shot_count} shot · {script.length_sec}s
          </span>
          {script.hook_type_vi ? (
            <span className="gv-mono text-[10px] font-medium text-[color:var(--gv-ink-4)]">
              {script.hook_type_vi}
            </span>
          ) : null}
        </div>
        <p
          className="gv-serif-italic m-0 text-[19px] font-medium leading-[1.3] tracking-[-0.01em] text-[color:var(--gv-ink)]"
          style={{ textWrap: "pretty" }}
        >
          &ldquo;{script.title_vi}&rdquo;
        </p>
        {script.why_works ? (
          <p className="mt-1.5 text-[12.5px] leading-[1.5] text-[color:var(--gv-ink-3)]">
            {script.why_works}
          </p>
        ) : null}
      </div>
      <div className="flex flex-col items-end gap-1 whitespace-nowrap">
        <span className="gv-mono text-[14px] font-bold" style={{ color: "var(--gv-pos)" }}>
          ▲ ~{script.retention_est_pct}%
        </span>
        <span className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">giữ chân</span>
        <span className="gv-mono mt-1 inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-[0.1em] text-[color:var(--gv-accent)] group-hover:translate-x-0.5 transition-transform">
          MỞ SCRIPT
          <ArrowRight className="h-3 w-3" strokeWidth={2.4} aria-hidden />
        </span>
      </div>
    </button>
  );
});
