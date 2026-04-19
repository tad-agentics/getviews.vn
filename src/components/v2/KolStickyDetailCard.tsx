import { Bookmark, Eye, FileText } from "lucide-react";
import type { KolBrowseRow } from "@/lib/api-types";
import { Btn } from "@/components/v2/Btn";

function formatCompactVi(n: number): string {
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}M`;
  }
  if (n >= 1_000) {
    return `${(n / 1_000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}K`;
  }
  return n.toLocaleString("vi-VN");
}

function growthLabel(pct: number): string {
  if (pct === 0) return "—";
  const sign = pct > 0 ? "+" : "";
  return `${sign}${Math.round(pct * 100)}%`;
}

const AVATAR_BG = "bg-[color:var(--gv-accent)] text-[color:var(--gv-canvas)]";

const MATCH_FALLBACK =
  "Cùng audience overlap, khác giọng — bổ sung tốt cho catalog của bạn.";

/**
 * B.2.2 — sticky right column: stats 2×2, match block, CTAs.
 */
export function KolStickyDetailCard({
  row,
  isPinned,
  onTogglePin,
  pinPending,
  onChannel,
  onScript,
  sticky = true,
  className = "",
  channelEnabled = false,
  scriptEnabled = false,
}: {
  row: KolBrowseRow | null;
  isPinned: boolean;
  onTogglePin: () => void;
  pinPending?: boolean;
  onChannel: () => void;
  onScript: () => void;
  /** When false, omit sticky positioning (e.g. mobile duplicate below table). */
  sticky?: boolean;
  className?: string;
  /** B.3 / B.4 routes not shipped yet — buttons stay disabled when false. */
  channelEnabled?: boolean;
  scriptEnabled?: boolean;
}) {
  const stickyCls = sticky ? "min-[1100px]:sticky min-[1100px]:top-[86px]" : "";

  if (!row) {
    return (
      <div className={className}>
        <div
          className={`rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6 text-sm text-[color:var(--gv-ink-3)] ${stickyCls}`.trim()}
        >
          Chọn một kênh trong bảng để xem chi tiết.
        </div>
      </div>
    );
  }

  const letter = (row.name || row.handle || "?").charAt(0).toUpperCase();

  return (
    <div className={className}>
      <div className={`rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-[22px] ${stickyCls}`.trim()}>
        <div className="mb-3.5 flex items-center gap-3.5">
          <div
            className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-full text-[22px] font-medium ${AVATAR_BG}`}
          >
            {letter}
          </div>
          <div className="min-w-0">
            <div className="gv-tight text-[22px] leading-tight text-[color:var(--gv-ink)]">{row.name}</div>
            <div className="gv-mono mt-0.5 text-[11px] text-[color:var(--gv-ink-3)]">@{row.handle}</div>
          </div>
        </div>

        <div className="mb-4 grid grid-cols-2 gap-3.5 rounded-lg bg-[color:var(--gv-canvas-2)] p-3.5">
          <div>
            <div className="gv-mono text-[9px] uppercase tracking-[0.12em] text-[color:var(--gv-ink-4)]">NGÁCH</div>
            <div className="mt-0.5 text-[13px] text-[color:var(--gv-ink)]">{row.niche_label ?? "—"}</div>
          </div>
          <div>
            <div className="gv-mono text-[9px] uppercase tracking-[0.12em] text-[color:var(--gv-ink-4)]">FOLLOW</div>
            <div className="mt-0.5 text-[13px] text-[color:var(--gv-ink)]">{formatCompactVi(row.followers)}</div>
          </div>
          <div>
            <div className="gv-mono text-[9px] uppercase tracking-[0.12em] text-[color:var(--gv-ink-4)]">VIEW TB</div>
            <div className="mt-0.5 text-[13px] text-[color:var(--gv-ink)]">{formatCompactVi(row.avg_views)}</div>
          </div>
          <div>
            <div className="gv-mono text-[9px] uppercase tracking-[0.12em] text-[color:var(--gv-ink-4)]">TĂNG 30D</div>
            <div className="mt-0.5 text-[13px] font-medium text-[color:var(--gv-pos-deep)]">{growthLabel(row.growth_30d_pct)}</div>
          </div>
        </div>

        <div className="mb-3.5">
          <div className="gv-mono mb-1.5 text-[9px] uppercase tracking-[0.12em] text-[color:var(--gv-ink-4)]">
            ĐỘ KHỚP NGÁCH BẠN
          </div>
          <div className="flex flex-wrap items-start gap-2.5">
            <div className="gv-tight text-[36px] leading-none text-[color:var(--gv-accent)]">
              {Math.round(row.match_score)}
              <span className="text-[16px] text-[color:var(--gv-ink-4)]">/100</span>
            </div>
            <p className="max-w-[220px] flex-1 text-[11px] leading-snug text-[color:var(--gv-ink-3)]">
              {(row.match_description && row.match_description.trim()) || MATCH_FALLBACK}
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <Btn
            type="button"
            variant="ink"
            size="md"
            className="w-full"
            disabled={!channelEnabled}
            title={channelEnabled ? undefined : "Sắp có"}
            onClick={onChannel}
          >
            <Eye className="h-3 w-3" strokeWidth={1.75} aria-hidden />
            Phân tích kênh đầy đủ
          </Btn>
          <Btn
            type="button"
            variant="ghost"
            size="md"
            className="w-full"
            onClick={onTogglePin}
            disabled={pinPending}
          >
            <Bookmark className="h-3 w-3" strokeWidth={1.75} aria-hidden />
            {isPinned ? "Bỏ ghim khỏi theo dõi" : "Ghim để theo dõi"}
          </Btn>
          <Btn
            type="button"
            variant="ghost"
            size="md"
            className="w-full"
            disabled={!scriptEnabled}
            title={scriptEnabled ? undefined : "Sắp có"}
            onClick={onScript}
          >
            <FileText className="h-3 w-3" strokeWidth={1.75} aria-hidden />
            Học hook từ kênh này
          </Btn>
        </div>
      </div>
    </div>
  );
}
