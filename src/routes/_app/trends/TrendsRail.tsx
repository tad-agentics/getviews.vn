import { memo, useCallback, useMemo, useState } from "react";
import { useNavigate } from "react-router";

import {
  CorpusVideoPreviewDialog,
  type CorpusVideoPreviewItem,
} from "@/components/explore/CorpusVideoPreviewDialog";
import { VideoThumbnail } from "@/components/VideoThumbnail";
import { contentFormatLabelVi } from "@/lib/contentFormatLabels";
import { trendsVideoHandoffPath } from "@/lib/answerHandoff";
import { formatRelativeSinceVi, formatViews } from "@/lib/formatters";

import {
  useTrendsRailVideos,
  type TrendsRailVideo,
} from "@/hooks/useTrendsRailVideos";

function railThumbPlaceholderStyle(videoId: string): {
  wrapClass: string;
  placeholderClassName: string;
} {
  let h = 0;
  for (let i = 0; i < videoId.length; i++) h = (h * 33 + videoId.charCodeAt(i)) >>> 0;
  const cyan = (h & 1) === 1;
  if (cyan) {
    return {
      wrapClass: "bg-[color:var(--gv-accent-2-soft)]",
      placeholderClassName:
        "bg-[color:var(--gv-accent-2-soft)] ring-1 ring-inset ring-[color:color-mix(in_srgb,var(--gv-accent-2)_22%,transparent)]",
    };
  }
  return {
    wrapClass: "bg-[color:var(--gv-accent-soft)]",
    placeholderClassName:
      "bg-[color:var(--gv-accent-soft)] ring-1 ring-inset ring-[color:color-mix(in_srgb,var(--gv-accent)_22%,transparent)]",
  };
}

function tiktokUrlForVideo(video: TrendsRailVideo): string {
  if (video.tiktok_url?.trim()) return video.tiktok_url.trim();
  const handle = video.creator_handle?.replace(/^@/, "") ?? "";
  if (handle) {
    return `https://www.tiktok.com/@${handle}/video/${video.video_id}`;
  }
  return video.video_id;
}

function rowTitle(video: TrendsRailVideo): string {
  const hook = video.hook_phrase?.trim();
  if (hook) return hook;
  if (video.hook_type?.trim()) return video.hook_type.trim();
  return "Video";
}

const MIN_DISPLAY_BREAKOUT = 1.0;

function formatMultiplier(bm: number | null): string | null {
  if (bm == null || !Number.isFinite(bm) || bm < MIN_DISPLAY_BREAKOUT) return null;
  return `${bm.toFixed(1)}×`;
}

function previewItemForVideo(video: TrendsRailVideo): CorpusVideoPreviewItem {
  const handle = video.creator_handle
    ? video.creator_handle.startsWith("@")
      ? video.creator_handle
      : `@${video.creator_handle}`
    : "—";
  const bmLabel = formatMultiplier(video.breakout_multiplier);
  const subtitle = [
    handle,
    video.views > 0 ? `↑${formatViews(video.views)}` : null,
    bmLabel ? `${bmLabel} so với kênh` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return {
    video_id: video.video_id,
    title: rowTitle(video),
    subtitle,
    thumbnail_url: video.thumbnail_url,
    tiktok_url: tiktokUrlForVideo(video),
  };
}

/**
 * Trends breakout rail — recent organic-shaped breakouts in the user's format
 * junction. Desktop: right sidebar. Mobile: inline block in Explore main column.
 */
export const TrendsRail = memo(function TrendsRail({
  contentClassIds,
  legacyNicheId = null,
  nicheScopeLabel,
  layout = "sidebar",
}: {
  contentClassIds: number[];
  legacyNicheId?: number | null;
  nicheScopeLabel?: string | null;
  /** sidebar = compact rows; inline = same content, used in mobile main flow */
  layout?: "sidebar" | "inline";
}) {
  const navigate = useNavigate();
  const { data, isPending } = useTrendsRailVideos({ contentClassIds, legacyNicheId });
  const [previewVideo, setPreviewVideo] = useState<TrendsRailVideo | null>(null);

  const previewItem = useMemo(
    () => (previewVideo ? previewItemForVideo(previewVideo) : null),
    [previewVideo],
  );

  const openPreview = useCallback((video: TrendsRailVideo) => {
    window.setTimeout(() => setPreviewVideo(video), 0);
  }, []);

  const handleAnalyze = useCallback(
    (item: CorpusVideoPreviewItem) => {
      setPreviewVideo(null);
      navigate(trendsVideoHandoffPath(item.tiktok_url ?? item.video_id));
    },
    [navigate],
  );

  const hasScope = contentClassIds.length > 0 || legacyNicheId != null;
  if (!hasScope) return null;

  const videos = data?.videos ?? [];
  const meta = data?.meta;
  const scopeHint = nicheScopeLabel?.trim()
    ? `format trong ${nicheScopeLabel.trim()}`
    : "format bạn đang duyệt";

  return (
    <>
      <section
        aria-labelledby="trends-rail-breakouts"
        className={layout === "inline" ? "mb-8" : undefined}
        data-testid="trends-rail"
      >
        <p className="gv-mono mb-1 text-[11px] font-semibold gv-kicker tracking-[0.08em] text-[color:var(--gv-ink-3)]">
          BREAKOUT GẦN ĐÂY
        </p>
        <h3
          id="trends-rail-breakouts"
          className="gv-tight m-0 mb-1 border-b border-[color:var(--gv-ink)] pb-2 text-[22px] font-semibold leading-none tracking-[-0.02em] text-[color:var(--gv-ink)]"
        >
          Video organic đáng xem
        </h3>
        <p className="gv-mono mb-3 text-[11px] leading-relaxed text-[color:var(--gv-ink-3)]">
          Top 5 breakout đăng trong 14 ngày ({scopeHint}) — xếp theo hệ số so với trung bình kênh,
          ưu tiên mẫu organic. Luôn xem trước, phân tích khi cần.
        </p>

        {meta?.usedFallback && meta.eligibleCount < 5 ? (
          <p
            className="mb-3 rounded-md border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2 text-[11px] leading-snug text-[color:var(--gv-ink-3)]"
            data-testid="trends-rail-fallback-note"
          >
            Mẫu organic còn mỏng — một số video bổ sung chưa qua lọc boost. So format và hook, đừng
            chỉ nhìn view tuyệt đối.
          </p>
        ) : null}

        {isPending ? (
          <div className="flex flex-col gap-2.5">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="h-16 animate-pulse rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)]"
              />
            ))}
          </div>
        ) : videos.length === 0 ? (
          <p className="m-0 rounded-md border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-3 text-[12px] text-[color:var(--gv-ink-3)]">
            Chưa đủ breakout đăng trong 14 ngày — thử lại sau khi cron cập nhật kho.
          </p>
        ) : (
          <ul className="flex flex-col gap-2.5">
            {videos.map((v) => (
              <RailRow key={v.video_id} video={v} onPreview={() => openPreview(v)} />
            ))}
          </ul>
        )}
      </section>

      <CorpusVideoPreviewDialog
        video={previewItem}
        open={previewVideo != null}
        onOpenChange={(next) => {
          if (!next) setPreviewVideo(null);
        }}
        onAnalyze={handleAnalyze}
      />
    </>
  );
});

function RailRow({ video, onPreview }: { video: TrendsRailVideo; onPreview: () => void }) {
  const title = rowTitle(video);
  const handle = video.creator_handle
    ? video.creator_handle.startsWith("@")
      ? video.creator_handle
      : `@${video.creator_handle}`
    : null;
  const ageLabel = video.posted_at
    ? `đăng ${formatRelativeSinceVi(new Date(), new Date(video.posted_at))}`
    : null;
  const bmLabel = formatMultiplier(video.breakout_multiplier);
  const formatLabel = contentFormatLabelVi(video.content_format);
  const thumbPh = railThumbPlaceholderStyle(video.video_id);

  return (
    <li>
      <button
        type="button"
        onClick={onPreview}
        className="grid w-full grid-cols-[44px_1fr] items-center gap-2.5 rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2.5 py-2 text-left transition-colors hover:border-[color:var(--gv-ink)]"
      >
        <span
          className={`relative overflow-hidden rounded ${thumbPh.wrapClass}`}
          style={{ aspectRatio: "9 / 16", height: 56 }}
          aria-hidden
        >
          <VideoThumbnail
            thumbnailUrl={video.thumbnail_url}
            videoId={video.video_id}
            className="absolute inset-0 h-full w-full"
            loading="lazy"
            placeholderClassName={thumbPh.placeholderClassName}
          />
          {bmLabel ? (
            <span className="gv-mono absolute bottom-0.5 left-0.5 rounded bg-[color:var(--gv-ink)]/85 px-1 py-px text-[9px] font-semibold text-[color:var(--gv-paper)]">
              {bmLabel}
            </span>
          ) : null}
        </span>
        <span className="min-w-0">
          <span className="flex flex-wrap items-center gap-1.5">
            <span className="m-0 line-clamp-2 min-w-0 flex-1 text-[12px] leading-[1.3] text-[color:var(--gv-ink)]">
              {title}
            </span>
            {formatLabel ? (
              <span className="gv-mono shrink-0 rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-1.5 py-px text-[9px] font-semibold tracking-[0.04em] text-[color:var(--gv-ink-3)]">
                {formatLabel}
              </span>
            ) : null}
          </span>
          <span className="gv-mono mt-1 block text-[11px] text-[color:var(--gv-ink-4)]">
            {[handle, video.views > 0 ? `↑${formatViews(video.views)}` : null, ageLabel]
              .filter(Boolean)
              .join(" · ")}
          </span>
        </span>
      </button>
    </li>
  );
}
