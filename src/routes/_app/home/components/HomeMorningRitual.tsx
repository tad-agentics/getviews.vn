import { memo } from "react";
import { SectionHeader } from "@/components/v2/SectionHeader";
import { useDailyRitual, type RitualScript } from "@/hooks/useDailyRitual";

/**
 * MorningRitual on the Home screen — the design's hero block.
 *
 * 3 script cards; the first is ink-filled (primary), the other two are
 * paper. Each card: hook-type chip, serif-italic quoted title, why-works
 * caption, retention estimate in pos-blue, shot count + length in mono.
 *
 * Click hands a pre-formed prompt up to the caller — which routes into
 * the existing chat stream until /answer exists in A3.3+.
 */

function promptFromScript(script: RitualScript, nicheLabel: string) {
  return (
    `Lên kịch bản cho video TikTok trong ngách ${nicheLabel} theo hướng sau:\n` +
    `Hook: ${script.title_vi}\n` +
    `Loại hook: ${script.hook_type_vi}\n` +
    `Độ dài dự kiến: ${script.length_sec} giây, ${script.shot_count} shot.\n` +
    `Lý do hook chạy: ${script.why_works}\n\n` +
    `Viết kịch bản chi tiết cho mình.`
  );
}

export const HomeMorningRitual = memo(function HomeMorningRitual({
  nicheLabel,
  onSelectPrompt,
}: {
  nicheLabel: string;
  onSelectPrompt: (prompt: string) => void;
}) {
  const { data: ritual, isPending } = useDailyRitual();

  if (isPending) {
    return (
      <section>
        <SectionHeader
          kicker="SÁNG NAY · 06:00"
          title="3 kịch bản sẵn sàng cho bạn"
          caption="Được tạo qua đêm từ dữ liệu ngách tuần này."
        />
        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-52 animate-pulse rounded-[12px] bg-[color:var(--gv-canvas-2)]" />
          ))}
        </div>
      </section>
    );
  }

  if (!ritual || ritual.scripts.length === 0) {
    return (
      <section>
        <SectionHeader
          kicker="SÁNG NAY · 06:00"
          title="Đang tạo kịch bản cho ngày đầu"
          caption="Cron sáng sẽ xếp sẵn 3 kịch bản mới vào 7h. Ghé lại sáng mai nhé."
        />
      </section>
    );
  }

  const isThin = ritual.adequacy === "none" || ritual.adequacy === "reference_pool";

  return (
    <section>
      <SectionHeader
        kicker="SÁNG NAY · 06:00"
        title="3 kịch bản sẵn sàng cho bạn"
        caption={
          isThin
            ? "Dữ liệu ngách đang thưa — các retention estimate dưới đây là định hướng, không chính xác tuyệt đối."
            : "Tổng hợp từ pattern thắng trong ngách của bạn qua đêm qua."
        }
      />

      <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
        {ritual.scripts.map((s, idx) => {
          const isHero = idx === 0;
          return (
            <button
              key={`${s.hook_type_en}-${idx}`}
              type="button"
              onClick={() => onSelectPrompt(promptFromScript(s, nicheLabel))}
              className={
                "group flex h-full flex-col gap-3 rounded-[12px] p-5 text-left transition-all hover:-translate-y-0.5 " +
                (isHero
                  ? "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)] hover:shadow-[4px_4px_0_var(--gv-ink)]"
                  : "border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] text-[color:var(--gv-ink)] hover:border-[color:var(--gv-ink)] hover:shadow-[4px_4px_0_var(--gv-ink)]")
              }
            >
              <div className="flex items-center justify-between">
                <span
                  className={
                    "inline-flex items-center rounded-[3px] px-2 py-0.5 gv-mono text-[10px] font-semibold uppercase tracking-[0.08em] " +
                    (isHero
                      ? "bg-[color:var(--gv-accent)] text-white"
                      : "bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent-deep)]")
                  }
                >
                  HOOK #{idx + 1}
                </span>
                <span
                  className={
                    "gv-mono text-[10px] " +
                    (isHero ? "text-white/60" : "text-[color:var(--gv-ink-4)]")
                  }
                >
                  {s.shot_count} shot · {s.length_sec}s
                </span>
              </div>

              <p
                className={
                  "gv-serif-italic text-[20px] leading-tight " +
                  (isHero ? "text-[color:var(--gv-canvas)]" : "text-[color:var(--gv-ink)]")
                }
              >
                "{s.title_vi}"
              </p>

              <p
                className={
                  "flex-1 text-xs leading-snug " +
                  (isHero ? "text-white/70" : "text-[color:var(--gv-ink-3)]")
                }
              >
                {s.why_works}
              </p>

              {/* Footer: ▲ est on the left, "Mở kịch bản →" action on the right */}
              <div
                className={
                  "flex items-center justify-between pt-2.5 border-t " +
                  (isHero ? "border-white/15" : "border-[color:var(--gv-rule-2)]")
                }
              >
                <span
                  className="gv-mono text-[11px]"
                  style={{ color: "var(--gv-pos)" }}
                >
                  ▲ ~{s.retention_est_pct}% giữ chân
                </span>
                <span
                  className={
                    "gv-mono text-[11px] " +
                    (isHero ? "text-white" : "text-[color:var(--gv-ink)]")
                  }
                >
                  Mở kịch bản →
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
});
