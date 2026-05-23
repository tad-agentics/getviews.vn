import { ExternalLink } from "lucide-react";
import type { FormatCardExample, ReferenceVideoCard } from "@/lib/api-types";
import { formatViews } from "@/lib/formatters";

interface EvidenceVideoEmbedProps {
  aweme_id: string | null;
  reference_videos: ReferenceVideoCard[];
  /** When synthesis citation is missing or not in ``reference_videos``, show corpus row. */
  corpusExample?: FormatCardExample | null;
}

function CorpusEvidenceCard({ ex }: { ex: FormatCardExample }) {
  return (
    <div className="mb-3 mt-2 flex gap-3 rounded-[10px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-3">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-[color:var(--gv-rule)] px-1.5 py-0.5 gv-kicker text-[color:var(--gv-ink-4)]">
            Từ corpus
          </span>
          {ex.creator_handle ? (
            <span className="text-[11px] text-[color:var(--gv-ink-3)]">@{ex.creator_handle}</span>
          ) : null}
        </div>
        {ex.desc ? (
          <p className="truncate text-[12px] text-[color:var(--gv-ink-2)]">
            {ex.desc.slice(0, 60)}
            {ex.desc.length > 60 ? "…" : ""}
          </p>
        ) : null}
        <div className="flex flex-wrap items-center gap-3">
          <span className="gv-kicker text-[color:var(--gv-ink)]">
            {formatViews(ex.play_count)} lượt xem
          </span>
          {ex.tiktok_url ? (
            <a
              href={ex.tiktok_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex min-h-[44px] items-center gap-1 text-[11px] text-[color:var(--gv-accent)] hover:underline"
            >
              Mở TikTok
              <ExternalLink className="h-3 w-3 shrink-0" />
            </a>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function EvidenceVideoEmbed({
  aweme_id,
  reference_videos,
  corpusExample,
}: EvidenceVideoEmbedProps) {
  const video = aweme_id ? reference_videos.find((r) => r.aweme_id === aweme_id) : undefined;
  if (!video && corpusExample?.tiktok_url) {
    return <CorpusEvidenceCard ex={corpusExample} />;
  }
  if (!video) return null;

  return (
    <div className="mb-3 mt-2 flex gap-3 rounded-[10px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-3">
      {video.thumbnail_url ? (
        <img
          src={video.thumbnail_url}
          alt=""
          className="h-16 w-10 shrink-0 rounded-[6px] object-cover"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      ) : null}
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2">
          {video.author_handle ? (
            <span className="text-[11px] text-[color:var(--gv-ink-3)]">@{video.author_handle}</span>
          ) : null}
          {video.source === "live_search" ? (
            <span className="rounded-full border border-[color:var(--gv-rule)] px-1.5 py-0.5 gv-kicker text-[color:var(--gv-ink-4)]">
              Tìm mới
            </span>
          ) : null}
          {video.hook_type ? (
            <span className="rounded-full bg-[color:var(--gv-accent-soft)] px-1.5 py-0.5 gv-kicker text-[color:var(--gv-ink-2)]">
              {video.hook_type}
            </span>
          ) : null}
        </div>
        {video.desc ? (
          <p className="truncate text-[12px] text-[color:var(--gv-ink-2)]">
            {video.desc.slice(0, 60)}
            {video.desc.length > 60 ? "…" : ""}
          </p>
        ) : null}
        <div className="flex flex-wrap items-center gap-3">
          {video.views != null ? (
            <span className="gv-kicker text-[color:var(--gv-ink)]">
              {formatViews(video.views)} lượt xem
            </span>
          ) : null}
          {video.tiktok_url ? (
            <a
              href={video.tiktok_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex min-h-[44px] items-center gap-1 text-[11px] text-[color:var(--gv-accent)] hover:underline"
            >
              Mở TikTok
              <ExternalLink className="h-3 w-3 shrink-0" />
            </a>
          ) : null}
        </div>
      </div>
    </div>
  );
}
