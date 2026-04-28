/**
 * Phase C.5.2 — Generic evidence tiles (3 only, per plan §2.4).
 *
 * Same EvidenceCardPayload shape as Pattern, but scoped to exactly 3
 * tiles. Thumbnails use the server-seeded `bg_color`; clicking a tile
 * launches a new video diagnosis session on `/app/answer` (PR-3 of
 * the video-as-template migration; previously this routed to the
 * deleted `/app/video?video_id=…` deep-link).
 */

import { useNavigate } from "react-router";

import { VideoThumbnail } from "@/components/VideoThumbnail";
import type { EvidenceCardPayloadData } from "@/lib/api-types";

function tiktokUrlFor(handle: string, videoId: string): string {
  const h = handle.replace(/^@/, "");
  return `https://www.tiktok.com/@${h}/video/${videoId}`;
}

function formatViews(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return String(n);
}

function formatDuration(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function GenericEvidenceGrid({
  items,
}: {
  items: EvidenceCardPayloadData[];
}) {
  const navigate = useNavigate();
  if (items.length === 0) return null;
  return (
    <ul
      className="grid grid-cols-1 gap-[14px] min-[700px]:grid-cols-3"
      aria-label="Video mẫu"
    >
      {items.slice(0, 3).map((v, i) => (
        <li
          key={v.video_id}
          className="overflow-hidden rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]"
        >
          <button
            type="button"
            onClick={() =>
              navigate("/app/answer", {
                state: { prefillUrl: tiktokUrlFor(v.creator_handle, v.video_id) },
              })
            }
            aria-label={`Mở video tham khảo ${v.video_id}`}
            className="relative block aspect-[9/12] w-full text-left"
            style={{ backgroundColor: v.bg_color || "var(--gv-canvas-2)" }}
          >
            <VideoThumbnail
              thumbnailUrl={v.thumbnail_url}
              className="h-full w-full"
              placeholderClassName=""
            />
            <span className="gv-mono absolute left-1 top-1 rounded bg-[color:var(--gv-paper)] px-1 text-[10px] text-[color:var(--gv-ink-3)]">
              #{i + 1}
            </span>
          </button>
          <div className="flex flex-col gap-1 border-t border-[color:var(--gv-rule)] px-3 py-2 text-[12px]">
            <p className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">
              {v.creator_handle}
            </p>
            <p className="line-clamp-2 text-[color:var(--gv-ink-2)]">{v.title}</p>
            <p className="gv-mono flex items-center justify-between text-[10px] text-[color:var(--gv-ink-3)]">
              <span>{formatViews(v.views)} views</span>
              <span>{formatDuration(v.duration_sec)}</span>
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}
