/**
 * NextVideoCard — structured “video tiếp theo” hint + optional peer sample link.
 */

import type { ChannelNextVideoConcept } from "@/lib/api-types";
import { VideoThumbnail } from "@/components/VideoThumbnail";

function fmtViews(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return String(Math.round(n));
}

interface NextVideoCardProps {
  concept: ChannelNextVideoConcept;
  streaming?: boolean;
}

export function NextVideoCard({ concept, streaming = false }: NextVideoCardProps) {
  const href = concept.sample_video_url?.startsWith("http") ? concept.sample_video_url : undefined;

  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-[color:var(--gv-accent)]/35 bg-[color-mix(in_srgb,var(--gv-accent)_8%,var(--gv-paper))]">
      <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-stretch">
        {href ? (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="relative block w-full shrink-0 overflow-hidden rounded-[12px] border border-[color:var(--gv-rule)] sm:w-36"
            aria-label={`Mở video mẫu từ @${concept.sample_peer_handle}`}
          >
            <div className="relative pb-[100%]">
              <VideoThumbnail
                thumbnailUrl={concept.sample_thumbnail_url ?? null}
                className="absolute inset-0 w-full h-full"
                alt=""
              />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-black/55 text-white text-xs">
                  ▶
                </div>
              </div>
            </div>
          </a>
        ) : null}
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[color:var(--gv-accent-deep)]">
            Gợi ý video tiếp theo
          </p>
          <p className="mt-1 text-sm font-semibold text-[color:var(--gv-ink)]">
            {concept.format_label} · ~{concept.duration_sec}s · gap{" "}
            <span className="gv-mono">{concept.channel_share_pct}%</span> format trên kênh
          </p>
          <p className="mt-2 text-[12.5px] leading-relaxed text-[color:var(--gv-ink-3)]">
            {concept.rationale_struct} Peer TB{" "}
            <span className="gv-mono">~{fmtViews(concept.peer_avg_views)}</span> view.
          </p>
          {concept.narrative ? (
            <div className="relative mt-2">
              <p className="text-[12.5px] leading-relaxed text-[color:var(--foreground)] whitespace-pre-wrap">
                {concept.narrative}
              </p>
              {streaming ? (
                <span
                  className="inline-block w-0.5 h-4 bg-[color:var(--primary)] animate-pulse ml-0.5 align-text-bottom"
                  aria-hidden
                />
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function NextVideoCardEmpty({ streaming = false }: { streaming?: boolean }) {
  return (
    <div className="mt-3 rounded-[12px] border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-4 py-3">
      <p className="text-xs text-[color:var(--gv-ink-3)]">
        Bạn đã cover đủ format mạnh của peer trong tập 60 video — không có “video tiếp theo” deterministic.
        {streaming ? " Đang chờ phần narrative…" : ""}
      </p>
    </div>
  );
}
