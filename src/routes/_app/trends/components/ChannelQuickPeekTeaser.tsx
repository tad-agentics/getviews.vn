import { useChannelQuickPeek } from "@/hooks/useChannelQuickPeek";

/** F5 — P0 channel finding teaser on Trends pattern card. */
export function ChannelQuickPeekTeaser({ handle }: { handle: string | null }) {
  const { data } = useChannelQuickPeek(handle);
  const teaser = data?.teaser?.trim();
  if (!teaser) return null;
  return (
    <p className="mt-1 text-[11px] leading-snug text-[color:var(--gv-ink-3)] line-clamp-2">
      <span className="gv-kicker text-[color:var(--gv-accent)]">
        Soi kênh ·{" "}
      </span>
      {teaser}
    </p>
  );
}
