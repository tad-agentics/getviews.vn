import type { ReactNode } from "react";

const TAG_STYLES = {
  accent: "bg-[color:var(--gv-accent)]",
  pos: "bg-[color:var(--gv-pos)]",
  ink: "bg-[color:var(--gv-ink)]",
} as const;

export type TierTagTone = keyof typeof TAG_STYLES;

/**
 * Tier label under “GỢI Ý HÔM NAY” — large index, colored tag, title + caption (ref home.jsx).
 */
export function TierHeader({
  num,
  tag,
  tagTone,
  title,
  caption,
  right,
  className,
}: {
  num: string;
  tag: string;
  tagTone: TierTagTone;
  title: ReactNode;
  caption?: ReactNode;
  right?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={[
        "mb-3.5 flex flex-wrap items-end justify-between gap-4 border-t border-[color:var(--gv-rule)] pt-[18px]",
        className ?? "",
      ]
        .join(" ")
        .trim()}
    >
      <div className="flex min-w-0 flex-1 items-start gap-4">
        <div
          className="gv-mono gv-tight shrink-0 pt-1 text-[36px] font-semibold leading-[0.85] tracking-[-0.04em] text-[color:var(--gv-ink-4)]"
          aria-hidden
        >
          {num}
        </div>
        <div className="min-w-0">
          <div
            className={[
              "gv-uc mb-2 inline-block rounded px-2 py-0.5 text-[10px] font-bold tracking-[0.08em] text-white",
              TAG_STYLES[tagTone],
            ].join(" ")}
          >
            {tag}
          </div>
          <h3 className="gv-tight m-0 text-[22px] font-semibold leading-tight tracking-[-0.025em] text-[color:var(--gv-ink)]">
            {title}
          </h3>
          {caption ? (
            <p className="mt-1 max-w-[640px] text-[12.5px] leading-normal text-[color:var(--gv-ink-3)]">
              {caption}
            </p>
          ) : null}
        </div>
      </div>
      {right ? <div className="shrink-0">{right}</div> : null}
    </div>
  );
}
