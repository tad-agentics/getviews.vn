import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";

import { Btn } from "@/components/v2/Btn";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { VideoThumbnail } from "@/components/VideoThumbnail";
import { tiktokAwemeIdForEmbed } from "@/lib/tiktokEmbed";

export type CorpusVideoPreviewItem = {
  video_id: string;
  title: string;
  /** Mono caption under title — handle, views, multiplier, etc. */
  subtitle: string;
  thumbnail_url: string | null;
  tiktok_url: string | null;
  /** Public R2 clip — preferred over TikTok iframe (reliable in Radix dialog). */
  video_url?: string | null;
};

type CorpusVideoPreviewDialogProps = {
  video: CorpusVideoPreviewItem | null;
  open: boolean;
  onOpenChange: (next: boolean) => void;
  onAnalyze: (video: CorpusVideoPreviewItem) => void;
  analyzeLabel?: string;
  description?: string;
  /** When false, TikTok link only shows in thumbnail fallback (Explore grid legacy). */
  showTikTokLinkButton?: boolean;
};

function PreviewMedia({
  video,
  open,
  showTikTokLinkButton,
}: {
  video: CorpusVideoPreviewItem;
  open: boolean;
  showTikTokLinkButton: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [autoplayBlocked, setAutoplayBlocked] = useState(false);
  const clipSrc = video.video_url?.trim() ?? "";
  const tiktokUrl = video.tiktok_url?.trim() || null;
  const embedId = tiktokAwemeIdForEmbed(video.video_id, video.tiktok_url);

  useEffect(() => {
    if (!open || !clipSrc) return;
    setAutoplayBlocked(false);
    const el = videoRef.current;
    if (!el) return;
    el.load();
    try {
      const playPromise = el.play();
      if (playPromise && typeof playPromise.catch === "function") {
        void playPromise.catch(() => setAutoplayBlocked(true));
      }
    } catch {
      setAutoplayBlocked(true);
    }
  }, [open, clipSrc, video.video_id]);

  const shellClass =
    "relative mx-auto max-w-[280px] overflow-hidden rounded-[10px] bg-[color:var(--gv-canvas-2)]";
  const shellStyle = { aspectRatio: "9 / 16" as const };

  if (clipSrc) {
    const videoEl = (
      <video
        ref={videoRef}
        key={clipSrc}
        src={clipSrc}
        muted
        loop
        playsInline
        controls={!tiktokUrl}
        className="absolute inset-0 h-full w-full object-cover"
      />
    );

    const inner = (
      <>
        {videoEl}
        {autoplayBlocked ? (
          <button
            type="button"
            aria-label="Phát video"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setAutoplayBlocked(false);
              try {
                const playPromise = videoRef.current?.play();
                if (playPromise && typeof playPromise.catch === "function") {
                  void playPromise.catch(() => setAutoplayBlocked(true));
                }
              } catch {
                setAutoplayBlocked(true);
              }
            }}
            className="absolute inset-0 z-10 flex items-center justify-center bg-black/35 text-white"
          >
            <span className="rounded-full bg-black/50 px-4 py-2 text-[12px] font-semibold backdrop-blur-sm">
              Nhấn để phát
            </span>
          </button>
        ) : null}
      </>
    );

    if (tiktokUrl?.startsWith("http")) {
      return (
        <a
          href={tiktokUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={`${shellClass} block transition-opacity hover:opacity-95`}
          style={shellStyle}
          aria-label="Mở video trên TikTok"
        >
          {inner}
        </a>
      );
    }

    return (
      <div className={shellClass} style={shellStyle}>
        {inner}
      </div>
    );
  }

  if (embedId) {
    return (
      <div className={shellClass} style={shellStyle}>
        <iframe
          key={embedId}
          title={`TikTok video ${embedId}`}
          src={`https://www.tiktok.com/embed/v2/${embedId}`}
          className="absolute inset-0 h-full w-full border-0"
          allow="encrypted-media; fullscreen; autoplay; picture-in-picture"
          allowFullScreen
        />
      </div>
    );
  }

  return (
    <div className={shellClass} style={shellStyle}>
      <VideoThumbnail
        thumbnailUrl={video.thumbnail_url}
        videoId={video.video_id}
        className="absolute inset-0 h-full w-full"
        placeholderClassName=""
      />
      {tiktokUrl && !showTikTokLinkButton ? (
        <a
          href={tiktokUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="gv-mono absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1.5 text-[11px] font-semibold gv-kicker tracking-[0.06em] text-[color:var(--gv-ink)] shadow-sm hover:border-[color:var(--gv-ink)]"
        >
          Mở trên TikTok
        </a>
      ) : null}
    </div>
  );
}

export function CorpusVideoPreviewDialog({
  video,
  open,
  onOpenChange,
  onAnalyze,
  analyzeLabel = "Phân tích video này (1 credit)",
  description = "Xem trước video trước khi phân tích hoặc mở TikTok",
  showTikTokLinkButton = true,
}: CorpusVideoPreviewDialogProps) {
  const tiktokUrl = video?.tiktok_url?.trim() || null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton={false}
        className="!max-w-[min(420px,calc(100%-2rem))] gap-0 overflow-hidden border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] p-0"
      >
        {video ? (
          <>
            <header className="flex items-start justify-between gap-3 border-b border-[color:var(--gv-rule)] px-4 py-3 min-[420px]:px-5">
              <div className="min-w-0 flex-1">
                <DialogTitle className="gv-tight m-0 text-left text-[17px] font-semibold leading-snug text-[color:var(--gv-ink)]">
                  {video.title}
                </DialogTitle>
                <p className="gv-mono mt-1 mb-0 text-[11px] text-[color:var(--gv-ink-3)]">
                  {video.subtitle}
                </p>
              </div>
              <DialogClose asChild>
                <button
                  type="button"
                  aria-label="Đóng"
                  className="-mr-1 -mt-0.5 shrink-0 rounded-md p-2 text-[color:var(--gv-ink-3)] transition-colors hover:bg-[color:var(--gv-canvas-2)] hover:text-[color:var(--gv-ink)]"
                >
                  <X className="h-4 w-4" strokeWidth={2} aria-hidden />
                </button>
              </DialogClose>
            </header>
            <DialogDescription className="sr-only">{description}</DialogDescription>
            <div className="px-4 pb-4 pt-4 min-[420px]:px-5">
              <PreviewMedia
                video={video}
                open={open}
                showTikTokLinkButton={showTikTokLinkButton}
              />
            </div>
            <div className="flex flex-col gap-2 border-t border-[color:var(--gv-rule)] px-4 py-4 min-[420px]:px-5">
              {showTikTokLinkButton && tiktokUrl?.startsWith("http") ? (
                <a
                  href={tiktokUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="gv-mono flex min-h-[44px] items-center justify-center rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 text-[12px] font-semibold tracking-[0.04em] text-[color:var(--gv-ink)] hover:border-[color:var(--gv-ink)]"
                >
                  Xem trên TikTok
                </a>
              ) : null}
              <Btn
                variant="accent"
                size="md"
                type="button"
                className="w-full justify-center"
                onClick={() => onAnalyze(video)}
              >
                {analyzeLabel}
              </Btn>
            </div>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
