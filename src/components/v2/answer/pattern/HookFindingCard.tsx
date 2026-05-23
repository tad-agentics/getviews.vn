import type { EvidenceCardPayloadData, HookFindingData } from "@/lib/api-types";
import { formatViews } from "@/lib/formatters";
import { momentumVi, tiktokVideoHref } from "./patternFormat";

function TonePill({ tone }: { tone: "up" | "down" | "neutral" }) {
  const cls =
    tone === "up"
      ? "text-[color:var(--gv-pos)]"
      : tone === "down"
        ? "text-[color:var(--gv-neg)]"
        : "text-[color:var(--gv-ink-3)]";
  const glyph = tone === "up" ? "↑" : tone === "down" ? "↓" : "—";
  return (
    <span className={`font-mono text-[10px] ${cls}`} aria-hidden="true">
      {glyph}
    </span>
  );
}

function InlineThumbnail({ video }: { video: EvidenceCardPayloadData }) {
  const href = tiktokVideoHref(video);
  const recency =
    video.days_ago === 0
      ? "Hôm nay"
      : video.days_ago === 1
        ? "Hôm qua"
        : video.days_ago != null
          ? `${video.days_ago} ngày trước`
          : null;

  return (
    <a
      href={href ?? undefined}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-2.5 rounded-lg border border-[color:var(--gv-rule-2)] bg-[color:var(--gv-canvas-2)] p-2 transition-opacity hover:opacity-80"
    >
      <div
        className="h-12 w-9 shrink-0 overflow-hidden rounded"
        style={{ background: video.bg_color || "var(--gv-canvas-2)" }}
      >
        {video.thumbnail_url ? (
          <img
            src={video.thumbnail_url}
            alt=""
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : null}
      </div>
      <div className="min-w-0 flex-1">
        <p className="gv-mono truncate text-[11px] font-medium text-[color:var(--gv-ink)]">
          @{String(video.creator_handle).replace(/^@/, "")}
        </p>
        <p className="gv-mono text-[10px] text-[color:var(--gv-ink-3)]">
          {formatViews(video.views)} view
          {recency ? ` · ${recency}` : ""}
        </p>
      </div>
    </a>
  );
}

export function HookFindingCard({
  row,
  evidenceVideos = [],
}: {
  row: HookFindingData;
  evidenceVideos?: EvidenceCardPayloadData[];
}) {
  const mom = momentumVi(row.lifecycle.momentum);

  const inlineVideo =
    row.evidence_video_ids.length > 0
      ? (evidenceVideos.find((v) => v.video_id === row.evidence_video_ids[0]) ?? null)
      : null;

  const bodyText = row.narrative?.trim() || row.insight;

  return (
    <div className="grid grid-cols-[40px_minmax(0,1fr)_auto] gap-x-3 gap-y-2 border-b border-[color:var(--gv-rule-2)] pb-6 last:border-b-0 last:pb-0">
      {/* Rank */}
      <div className="gv-serif text-[28px] leading-none text-[color:var(--gv-ink-3)]">#{row.rank}</div>

      {/* Main content */}
      <div className="min-w-0 space-y-3">
        <p className="gv-serif text-[17px] leading-snug text-[color:var(--gv-ink)]">{row.pattern}</p>

        {/* Primary narrative — journalist prose when available, insight fallback */}
        <p className="text-[13.5px] leading-relaxed text-[color:var(--gv-ink-2)]">{bodyText}</p>

        {/* Inline evidence thumbnail */}
        {inlineVideo ? <InlineThumbnail video={inlineVideo} /> : null}

        {/* Lifecycle + contrast */}
        <p className="gv-mono mt-[10px] flex flex-wrap gap-x-[14px] gap-y-1 text-[11px] text-[color:var(--gv-ink-3)]">
          <span>Xuất hiện {row.lifecycle.first_seen}</span>
          <span>·</span>
          <span>Đỉnh {row.lifecycle.peak}</span>
          <span>·</span>
          <span style={{ color: mom.colorVar }}>{mom.label}</span>
        </p>
        <p className="text-[12px] leading-[1.5] text-[color:var(--gv-ink-2)]">
          Thắng vì: {row.contrast_against.why_this_won} · So với: &ldquo;
          {row.contrast_against.pattern}&rdquo;
        </p>

        {/* Vì sao hiệu quả */}
        {row.why_it_works?.trim() ? (
          <div className="mt-3 space-y-1">
            <p className="gv-mono text-[10px] font-semibold uppercase tracking-wider text-[color:var(--gv-ink-4)]">
              Vì sao hiệu quả
            </p>
            <p className="text-[12.5px] leading-relaxed text-[color:var(--gv-ink-2)]">
              {row.why_it_works}
            </p>
          </div>
        ) : null}

        {/* Biến thể đang nổi */}
        {row.micro_pattern?.trim() ? (
          <div className="mt-2 rounded-md border border-[color:var(--gv-accent)] bg-[color:var(--gv-canvas-2)] px-3 py-2 opacity-90">
            <p className="text-[12px] leading-relaxed text-[color:var(--gv-ink-2)]">
              <span className="gv-mono text-[10px] font-semibold text-[color:var(--gv-accent)]">
                ↑ BIẾN THỂ ĐANG NỔI{" "}
              </span>
              {row.micro_pattern}
            </p>
          </div>
        ) : null}

        {/* VN cultural framing */}
        {row.cultural_framing?.trim() ? (
          <div className="mt-2 flex items-start gap-2 rounded-md bg-[color:var(--gv-accent-soft)] px-3 py-2">
            <span
              className="gv-mono mt-0.5 shrink-0 text-[9px] font-semibold uppercase tracking-wider text-[color:var(--gv-accent)]"
              aria-label="Văn hóa Việt Nam"
            >
              VN
            </span>
            <p className="text-[12px] leading-relaxed text-[color:var(--gv-ink-3)]">{row.cultural_framing}</p>
          </div>
        ) : null}

        {/* Prerequisites chips */}
        {row.prerequisites.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {row.prerequisites.map((p) => (
              <span
                key={p}
                className="gv-mono rounded bg-[color:var(--gv-canvas-2)] px-2 py-0.5 text-[10px] text-[color:var(--gv-ink-3)]"
              >
                {p}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      {/* Metrics column */}
      <div className="flex flex-col items-end gap-1 text-right">
        <div className="flex items-center gap-1">
          <span
            className="gv-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]"
            aria-label="Tỉ lệ giữ chân người xem"
          >
            Giữ
          </span>
          <TonePill tone="up" />
          <span className="gv-mono text-sm font-medium text-[color:var(--gv-ink)]">{row.retention.value}</span>
        </div>
        <div className="flex items-center gap-1">
          <span
            className="gv-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]"
            aria-label="Thay đổi so với tuần trước"
          >
            Đổi
          </span>
          <TonePill tone={row.delta.numeric >= 0 ? "up" : "down"} />
          <span
            className={`gv-mono text-sm font-medium ${
              row.delta.numeric >= 0 ? "text-[color:var(--gv-pos)]" : "text-[color:var(--gv-neg)]"
            }`}
          >
            {row.delta.value}
          </span>
        </div>
        <p className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">
          {row.uses} lượt
          {row.creator_count != null && row.creator_count > 0 ? ` · ${row.creator_count} creator` : ""}
        </p>
      </div>
    </div>
  );
}
