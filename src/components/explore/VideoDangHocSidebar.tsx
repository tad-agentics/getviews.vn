import { useState } from "react";
import { useNavigate } from "react-router";
import { formatViews } from "@/lib/formatters";
import { useVideoDangHoc, type VideoRow } from "@/hooks/useVideoDangHoc";

const PLACEHOLDER_THUMB = "/placeholder.svg";

function formatVelocityViewsPerHour(velocity: number): string {
  if (velocity >= 1000) {
    return `${(velocity / 1000).toFixed(1).replace(".", ",")}k views/h`;
  }
  if (velocity >= 100) {
    return `${velocity.toFixed(0).replace(/\B/g, ".")} views/h`;
  }
  return `${velocity.toFixed(1).replace(".", ",")} views/h`;
}

function VideoDangHocSkeleton() {
  return (
    <div className="space-y-2" aria-hidden>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex gap-2.5 animate-pulse">
          <div className="w-10 h-[72px] flex-shrink-0 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)]" />
          <div className="flex-1 space-y-2 pt-0.5">
            <div className="h-3 w-[75%] rounded bg-[var(--surface-alt)]" />
            <div className="h-3 w-1/2 rounded bg-[var(--surface-alt)]" />
          </div>
        </div>
      ))}
    </div>
  );
}

function VideoDangHocRow({
  row,
  showVelocity,
  onClick,
}: {
  row: VideoRow;
  showVelocity: boolean;
  onClick?: () => void;
}) {
  const [imgFailed, setImgFailed] = useState(false);
  const mult = row.breakout_multiplier;
  const showBreakoutBadge = mult != null && mult > 2;

  return (
    <div
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={onClick ? (e) => { if (e.key === "Enter" || e.key === " ") onClick(); } : undefined}
      className={`flex gap-2.5 py-2 border-b border-[var(--border)] last:border-0 group ${onClick ? "cursor-pointer" : ""}`}
    >
      <div className="w-10 h-[72px] flex-shrink-0 rounded-lg overflow-hidden bg-[var(--surface-alt)] border border-[var(--border)]">
        {!imgFailed ? (
          <img
            src={row.thumbnail_url || PLACEHOLDER_THUMB}
            alt=""
            className="w-full h-full object-cover"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div className="w-full h-full bg-[var(--surface-alt)]" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-xs truncate transition-colors duration-[120ms] ${onClick ? "group-hover:text-[var(--purple)]" : "text-[var(--purple)]"} text-[var(--purple)]`}>
          {row.creator_handle ? `@${row.creator_handle}` : "@—"}
        </p>
        <p className="text-xs text-[var(--ink)]">{formatViews(row.views)}</p>
        {showVelocity && row.velocity != null ? (
          <p className="text-[10px] font-mono text-[var(--ink-soft)] mt-0.5">
            {formatVelocityViewsPerHour(row.velocity)}
          </p>
        ) : null}
        {showBreakoutBadge && mult != null ? (
          <p className="text-[10px] font-mono text-[var(--purple)] mt-0.5">
            {mult.toFixed(1).replace(".", ",")}×
          </p>
        ) : null}
      </div>
    </div>
  );
}

export function VideoDangHocSidebar() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<"bung_no" | "dang_hot">("bung_no");
  const { bungNo, dangHot, isLoading, error } = useVideoDangHoc();

  const list = tab === "bung_no" ? bungNo : dangHot;
  const showVelocity = tab === "dang_hot";

  return (
    <section className="mt-4 pt-4 border-t border-[var(--border)] -mx-5 lg:-mx-7 px-5 lg:px-7">
      <h2 className="text-sm font-bold text-[var(--ink)] mb-3">Video Đáng Học</h2>

      <div className="flex gap-2 mb-3" role="tablist" aria-label="Danh sách Video Đáng Học">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "bung_no"}
          className={`min-h-[44px] px-3 py-2 rounded-full text-xs font-semibold transition-colors duration-[120ms] ${
            tab === "bung_no"
              ? "bg-[var(--purple-light)] text-[var(--purple)]"
              : "bg-[var(--surface-alt)] text-[var(--ink-soft)] border border-[var(--border)]"
          }`}
          onClick={() => setTab("bung_no")}
        >
          🔴 Bùng Nổ
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "dang_hot"}
          className={`min-h-[44px] px-3 py-2 rounded-full text-xs font-semibold transition-colors duration-[120ms] ${
            tab === "dang_hot"
              ? "bg-[var(--purple-light)] text-[var(--purple)]"
              : "bg-[var(--surface-alt)] text-[var(--ink-soft)] border border-[var(--border)]"
          }`}
          onClick={() => setTab("dang_hot")}
        >
          🟡 Đang Hot
        </button>
      </div>

      {error ? (
        <p className="text-xs text-[var(--ink-soft)]">Không tải được bảng xếp hạng — thử lại sau.</p>
      ) : null}

      {isLoading ? <VideoDangHocSkeleton /> : null}

      {!isLoading && !error && list.length === 0 ? (
        <p className="text-xs text-[var(--faint)]">Chưa có dữ liệu — cập nhật hàng ngày</p>
      ) : null}

      {!isLoading && !error && list.length > 0 ? (
        <div className="flex flex-col">
          {list.map((row) => (
            <VideoDangHocRow
              key={`${row.list_type}-${row.video_id}`}
              row={row}
              showVelocity={showVelocity}
              onClick={
                row.tiktok_url
                  ? () =>
                      navigate(`/app/answer?q=${encodeURIComponent(row.tiktok_url!)}`)
                  : undefined
              }
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}
