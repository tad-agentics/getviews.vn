import { useState } from "react";

import type { EvidenceCardPayloadData } from "@/lib/api-types";
import { evidenceTiktokHref, formatDurationSec, formatViews } from "./patternFormat";

function RecencyBadge({ daysAgo }: { daysAgo: number | null | undefined }) {
  if (daysAgo == null) return null;
  const label =
    daysAgo === 0
      ? "Hôm nay"
      : daysAgo === 1
        ? "Hôm qua"
        : daysAgo <= 7
          ? `${daysAgo} ngày trước`
          : daysAgo <= 14
            ? `${Math.round(daysAgo / 7)} tuần trước`
            : null;
  if (!label) return null;
  return (
    <span className="gv-mono rounded-full bg-[color:var(--gv-accent-soft)] px-1.5 py-0.5 text-[11px] font-semibold text-[color:var(--gv-accent)]">
      {label}
    </span>
  );
}

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
      {items.map((v, i) => {
        const href = evidenceTiktokHref(v);
        const body = (
          <>
            <EvidenceThumb item={v} />
            <div className="space-y-1 p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="gv-kicker text-[color:var(--gv-ink-3)]">{v.creator_handle}</p>
                <RecencyBadge daysAgo={v.days_ago} />
              </div>
              <p className="line-clamp-2 text-sm font-medium text-[color:var(--gv-ink)]">{v.title}</p>
              <div className="flex flex-wrap gap-x-3 gap-y-1 gv-kicker text-[color:var(--gv-ink-3)]">
                <span>{formatViews(v.views)} view</span>
                {v.engagement_rate != null && v.engagement_rate > 0 && (
                  <span className="font-semibold text-[color:var(--gv-accent)]">
                    {(v.engagement_rate * 100).toFixed(1)}% ER
                  </span>
                )}
                <span>{Math.round(v.retention * 100)}% tương tác</span>
                <span>{formatDurationSec(v.duration_sec)}</span>
                <span className="text-[color:var(--gv-accent)]">{v.hook_family}</span>
              </div>
            </div>
          </>
        );
        return (
          <li
            key={`${v.video_id}-${i}`}
            className="overflow-hidden rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]"
          >
            {href ? (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="block no-underline"
                aria-label={`Xem video của ${v.creator_handle} trên TikTok`}
              >
                {body}
              </a>
            ) : (
              <div className="block" aria-label={`Video ${v.creator_handle} — không có liên kết TikTok`}>
                {body}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
