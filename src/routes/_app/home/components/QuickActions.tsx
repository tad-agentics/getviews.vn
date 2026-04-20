import { memo } from "react";
import { useNavigate } from "react-router";
import {
  Film, Eye, TrendingUp, ClipboardList, Users, Sparkles,
} from "lucide-react";
import { SectionHeader } from "@/components/v2/SectionHeader";

/**
 * QuickActions — 6 cards in a 3×2 grid from 901px up (1 col below, matching UIUX
 * `quick-grid` + 900px breakpoint). Matches the
 * design's Home "Thao tác" block: each cell shows a squircle icon + mono
 * numeric badge (01..06), `.tight` title + short description.
 *
 * Six "cửa" (doors) the creator can walk through. Tìm KOL → `/app/kol` (B.2.3).
 * Soi kênh đối thủ → `/app/channel` (B.3.4). Tư vấn still routes into chat until Answer screen ships.
 */

type ActionId = "video" | "channel" | "trends" | "script" | "kol" | "consult";

const ACTIONS: ReadonlyArray<{
  id: ActionId;
  title: string;
  desc: string;
  icon: React.ElementType;
}> = [
  { id: "video",   title: "Soi video",      desc: "Dán link TikTok — mổ hook, pacing, CTA trong phút.", icon: Film },
  { id: "channel", title: "Soi kênh đối thủ", desc: "Trích xuất công thức của một kênh cụ thể.",          icon: Eye },
  { id: "trends",  title: "Xu hướng tuần",   desc: "Video + hook + sound nổi trong ngách.",              icon: TrendingUp },
  { id: "script",  title: "Lên kịch bản",   desc: "Gợi ý shot-list theo hook đang thắng.",              icon: ClipboardList },
  { id: "kol",     title: "Tìm KOL",        desc: "Match theo ngách + audience + giọng.",               icon: Users },
  { id: "consult", title: "Tư vấn content", desc: "Hỏi mình bất kỳ điều gì cần hướng giải.",            icon: Sparkles },
];

const ROUTE: Record<ActionId, string> = {
  video:   "/app/video",
  channel: "/app/channel",
  trends:  "/app/trends",
  script:  "/app/script",
  kol:     "/app/kol",
  consult: "/app/answer",
};

export const QuickActions = memo(function QuickActions() {
  const navigate = useNavigate();
  return (
    <section>
      <SectionHeader
        kicker="THAO TÁC"
        title="Bắt đầu nhanh"
        caption="6 cửa vào — chọn cửa hợp với ý tưởng của bạn."
      />
      <div className="grid grid-cols-1 gap-px overflow-hidden rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-rule)] min-[901px]:grid-cols-2">
        {ACTIONS.map((a, idx) => {
          const Icon = a.icon;
          return (
            <button
              key={a.id}
              type="button"
              onClick={() => navigate(ROUTE[a.id])}
              className="group flex min-h-[150px] flex-col gap-3 bg-[color:var(--gv-paper)] px-5 py-[22px] text-left transition-colors hover:bg-[color:var(--gv-canvas-2)]"
            >
              <div className="flex items-start justify-between">
                <div className="flex h-8 w-8 items-center justify-center rounded-[6px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)]">
                  <Icon className="h-4 w-4 text-[color:var(--gv-ink-2)]" strokeWidth={1.7} />
                </div>
                <span className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">
                  {String(idx + 1).padStart(2, "0")}
                </span>
              </div>
              <div>
                <p className="gv-tight text-[18px] leading-[1.1] text-[color:var(--gv-ink)]">
                  {a.title}
                </p>
                <p className="mt-1 text-xs text-[color:var(--gv-ink-3)]">
                  {a.desc}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
});
