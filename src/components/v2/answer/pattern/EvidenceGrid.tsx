import { useState } from "react";

import type { EvidenceCardPayloadData } from "@/lib/api-types";
import { formatDurationSec, formatViews } from "./patternFormat";

function EvidenceThumb({ item }: { item: EvidenceCardPayloadData }) {
  const [failed, setFailed] = useState(false);
  const url = item.thumbnail_url?.trim();
  if (url && !failed) {
    return (
      <img
        src={url}
        alt=""
        className="aspect-video w-full rounded border border-[color:var(--gv-rule)] object-cover"
        loading="lazy"
        onError={() => setFailed(true)}
      />
    );
  }
  return (
    <div className="aspect-video w-full bg-[color:var(--gv-canvas-2)]" style={{ backgroundColor: item.bg_color }} />
  );
}

export function EvidenceGrid({ items }: { items: EvidenceCardPayloadData[] }) {
  if (items.length === 0) return null;
  return (
    <ul className="grid grid-cols-1 gap-3 min-[700px]:grid-cols-2 min-[1100px]:grid-cols-3">
      {items.map((v, i) => (
        <li
          key={`${v.video_id}-${i}`}
          className="overflow-hidden rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]"
        >
          <EvidenceThumb item={v} />
          <div className="space-y-1 p-3">
            <p className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">{v.creator_handle}</p>
            <p className="line-clamp-2 text-sm font-medium text-[color:var(--gv-ink)]">{v.title}</p>
            <div className="flex flex-wrap gap-x-3 gap-y-1 gv-mono text-[10px] text-[color:var(--gv-ink-3)]">
              <span>{formatViews(v.views)} view</span>
              <span>{Math.round(v.retention * 100)}% giữ</span>
              <span>{formatDurationSec(v.duration_sec)}</span>
              <span className="text-[color:var(--gv-accent)]">{v.hook_family}</span>
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
