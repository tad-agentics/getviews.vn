import { useState, useRef, useEffect } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  X, VolumeX, Volume2, Heart, MessageCircle, Share2, Eye,
} from "lucide-react";

const PLACEHOLDER_THUMB = "/placeholder.svg";

export type ExploreGridVideo = {
  id: string;
  views: string;
  time: string;
  img: string;
  text: string;
  handle: string;
  caption: string;
  likes: string;
  comments: string;
  shares: string;
  videoUrl: string;
  tiktok_url: string | null;
  breakout?: string | null;
  contentFormat?: string | null;
};

function EngagementSidebar({
  img, likes, comments, shares, views,
}: {
  img: string; likes: string; comments: string; shares: string; views: string;
}) {
  return (
    <div className="hidden md:flex absolute right-3 bottom-24 z-20 flex-col items-center gap-4">
      <div className="w-9 h-9 rounded-full bg-[var(--surface)] border-2 border-white overflow-hidden">
        <img src={img} alt="" className="w-full h-full object-cover" onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = PLACEHOLDER_THUMB; }} />
      </div>
      <div className="flex flex-col items-center gap-0.5">
        <Heart className="w-6 h-6 text-white" strokeWidth={2} />
        <span className="text-white text-[11px] font-semibold">{likes}</span>
      </div>
      <div className="flex flex-col items-center gap-0.5">
        <MessageCircle className="w-6 h-6 text-white" strokeWidth={2} />
        <span className="text-white text-[11px] font-semibold">{comments}</span>
      </div>
      <div className="flex flex-col items-center gap-0.5">
        <Share2 className="w-6 h-6 text-white" strokeWidth={2} />
        <span className="text-white text-[11px] font-semibold">{shares}</span>
      </div>
      <div className="flex flex-col items-center gap-0.5">
        <Eye className="w-6 h-6 text-white" strokeWidth={2} />
        <span className="text-white text-[11px] font-semibold">{views}</span>
      </div>
    </div>
  );
}

export function VideoPlayerModal({
  video,
  allVideos,
  onClose,
}: {
  video: ExploreGridVideo;
  allVideos: ExploreGridVideo[];
  onClose: () => void;
}) {
  const [selected, setSelected] = useState(video);
  const [muted, setMuted] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.load();
      videoRef.current.play().catch(() => {});
    }
  }, [selected]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        transition={{ duration: 0.18 }}
        className="fixed inset-0 z-50 flex items-end md:items-center justify-center md:p-4"
        style={{ background: "rgba(0,0,0,0.65)", backdropFilter: "blur(8px)" }}
        onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      >
        <motion.div
          initial={{ opacity: 0, y: 48 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 48 }}
          transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          className="relative flex flex-col md:flex-row bg-[var(--surface)] w-full md:rounded-2xl overflow-hidden"
          style={{ maxWidth: 960, height: "95dvh", maxHeight: "95dvh", borderRadius: "20px 20px 0 0", boxShadow: "0 32px 80px rgba(0,0,0,0.4)" }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="relative bg-black overflow-hidden order-1 md:order-2 md:flex-1" style={{ minHeight: "55%" }}>
            <video
              ref={videoRef} key={selected.videoUrl} src={selected.videoUrl}
              autoPlay loop playsInline muted={muted}
              className="absolute inset-0 w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/20 pointer-events-none" />
            <button
              onClick={onClose}
              className="absolute top-3 right-3 z-20 w-9 h-9 flex items-center justify-center rounded-full bg-black/40 text-white hover:bg-black/60 transition-colors duration-[120ms] backdrop-blur-sm"
            >
              <X className="w-4 h-4" strokeWidth={2} />
            </button>
            <button
              onClick={() => setMuted((v) => !v)}
              className="absolute top-3 left-3 z-20 w-9 h-9 flex items-center justify-center rounded-full bg-black/40 text-white hover:bg-black/60 transition-colors duration-[120ms] backdrop-blur-sm"
            >
              {muted ? <VolumeX className="w-4 h-4" strokeWidth={2} /> : <Volume2 className="w-4 h-4" strokeWidth={2} />}
            </button>
            <EngagementSidebar img={selected.img} likes={selected.likes} comments={selected.comments} shares={selected.shares} views={selected.views} />
            <div className="absolute bottom-0 inset-x-0 z-20 px-4 pb-4">
              <p className="text-white font-semibold text-sm mb-0.5">{selected.handle} · {selected.time}</p>
              <p className="text-white/85 text-xs leading-snug">{selected.caption}</p>
            </div>
          </div>

          <div
            className="order-2 md:order-1 flex flex-col md:w-[320px] md:flex-shrink-0 border-t md:border-t-0 md:border-r border-[var(--border)] bg-[var(--surface)] overflow-hidden"
            style={{ flex: "0 0 auto", maxHeight: "45%", minHeight: 0 }}
          >
            <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border)] flex-shrink-0">
              <p className="text-[11px] font-bold uppercase tracking-widest text-[var(--faint)]">Khám phá video</p>
              <div className="flex md:hidden items-center gap-3">
                <span className="flex items-center gap-1 text-[11px] text-[var(--muted)]">
                  <Heart className="w-3.5 h-3.5" strokeWidth={2} />{selected.likes}
                </span>
                <span className="flex items-center gap-1 text-[11px] text-[var(--muted)]">
                  <Eye className="w-3.5 h-3.5" strokeWidth={2} />{selected.views}
                </span>
              </div>
            </div>

            {/* Mobile: horizontal scroll */}
            <div className="flex md:hidden flex-1 overflow-x-auto" style={{ scrollbarWidth: "none" }}>
              <div className="flex flex-row gap-2 px-3 py-2.5" style={{ width: "max-content" }}>
                {allVideos.map((v) => {
                  const isSel = v.id === selected.id;
                  return (
                    <button key={v.id} onClick={() => setSelected(v)}
                      className={`flex flex-col items-start gap-1 p-1.5 rounded-xl border transition-colors duration-[120ms] ${isSel ? "border-[var(--purple)] bg-[var(--purple-light)]" : "border-[var(--border)]"}`}
                      style={{ width: 80, flexShrink: 0 }}
                    >
                      <div className="w-full rounded-lg overflow-hidden relative" style={{ height: 100 }}>
                        <img src={v.img} alt="" className="w-full h-full object-cover" onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = PLACEHOLDER_THUMB; }} />
                        {isSel && <div className="absolute inset-0 bg-[var(--purple)]/20 flex items-center justify-center"><div className="w-3 h-3 rounded-full bg-white/90" /></div>}
                      </div>
                      {v.text && <p className={`text-[10px] font-semibold leading-snug line-clamp-2 w-full text-left ${isSel ? "text-[var(--purple)]" : "text-[var(--ink)]"}`}>{v.text}</p>}
                      <p className="text-[10px] font-mono text-[var(--muted)]">{v.views}</p>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Desktop: vertical list */}
            <div className="hidden md:block flex-1 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
              {allVideos.map((v) => {
                const isSel = v.id === selected.id;
                return (
                  <button key={v.id} onClick={() => setSelected(v)}
                    className={`w-full flex items-start gap-2.5 px-3 py-2.5 text-left transition-colors duration-[120ms] border-b border-[var(--border)] last:border-0 ${isSel ? "bg-[var(--purple-light)]" : "hover:bg-[var(--surface-alt)]"}`}
                  >
                    <div className="flex-shrink-0 rounded-md overflow-hidden border border-[var(--border)] relative" style={{ width: 36, height: 50 }}>
                      <img src={v.img} alt="" className="w-full h-full object-cover" onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = PLACEHOLDER_THUMB; }} />
                      {isSel && <div className="absolute inset-0 bg-[var(--purple)]/25 flex items-center justify-center"><div className="w-2.5 h-2.5 rounded-full bg-white/90" /></div>}
                    </div>
                    <div className="flex-1 min-w-0">
                      {v.text && <p className={`text-[11px] font-semibold leading-snug line-clamp-2 mb-0.5 ${isSel ? "text-[var(--purple)]" : "text-[var(--ink)]"}`}>{v.text}</p>}
                      <p className={`text-[11px] ${v.text ? "text-[var(--faint)]" : isSel ? "text-[var(--purple)] font-semibold" : "text-[var(--ink)] font-semibold"} leading-snug line-clamp-1`}>{v.handle}</p>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[11px] font-mono font-semibold text-[var(--ink)]">{v.views}</span>
                        <span className="text-[10px] text-[var(--faint)]">{v.time}</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
