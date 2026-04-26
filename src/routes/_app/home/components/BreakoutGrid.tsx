import { memo } from "react";
import { Link } from "react-router";
import { ArrowRight } from "lucide-react";
import { SectionHeader } from "@/components/v2/SectionHeader";
import { useTopBreakouts, type BreakoutVideo } from "@/hooks/useTopBreakouts";

/**
 * BreakoutGrid — UIUX `home.jsx`: 4/5 tiles, gap 18px, BREAKOUT + duration,
 * 22px quoted title on panel, mono row + ↑ views in accent-deep below.
 */

function formatViews(n: number): string {
  if (n >= 1_000_000) {
    const m = n / 1_000_000;
    return m >= 10 ? `${Math.round(m)}M` : `${m.toFixed(1).replace(/\.0$/, "")}M`;
  }
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return n.toLocaleString("vi-VN");
}

function formatDuration(sec: number | string | null | undefined): string | null {
  const n = sec == null ? NaN : Number(sec);
  if (!Number.isFinite(n) || n <= 0) return null;
  const m = Math.floor(n / 60);
  const s = Math.floor(n % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const FALLBACK_PANEL = ["bg-[#2d2640]", "bg-[#5c1f2a]", "bg-[#1f3d2d]"] as const;

export const BreakoutGrid = memo(function BreakoutGrid({
  nicheId,
  embedded = false,
}: {
  nicheId: number | null;
  embedded?: boolean;
}) {
  const { data: videos, isPending } = useTopBreakouts(nicheId, 3);

  const headerRight = (
    <Link
      to="/app/trends"
      className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1.5 text-xs font-medium text-[color:var(--gv-ink-2)] transition-colors hover:border-[color:var(--gv-ink)] hover:text-[color:var(--gv-ink)]"
    >
      Xem tất cả
      <ArrowRight className="h-3 w-3" aria-hidden />
    </Link>
  );

  if (isPending) {
    return (
      <section>
        {!embedded ? (
          <SectionHeader
            kicker="BIÊN TẬP CHỌN"
            title="3 video bứt phá"
            caption="View vượt 10× so với trung bình kênh trong 48 giờ qua."
            right={headerRight}
          />
        ) : null}
        <div className="grid [grid-template-columns:repeat(auto-fit,minmax(280px,1fr))] gap-[18px]">
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex flex-col gap-3">
              <div className="aspect-[4/5] animate-pulse rounded-[10px] bg-[color:var(--gv-canvas-2)]" />
              <div className="h-10 animate-pulse rounded-md bg-[color:var(--gv-canvas-2)]" />
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (!videos || videos.length === 0) {
    return (
      <section>
        {!embedded ? (
          <SectionHeader
            kicker="BIÊN TẬP CHỌN"
            title="3 video bứt phá"
            caption="View vượt 10× so với trung bình kênh trong 48 giờ qua."
            right={headerRight}
          />
        ) : null}
        <p className="mt-0 max-w-prose text-[14px] leading-relaxed text-[color:var(--gv-ink-3)]">
          Chưa có video trong kho dữ liệu để hiển thị. Khi pipeline cập nhật breakout và lượt xem, ba
          video nổi bật sẽ xuất hiện tại đây. Bạn có thể xem xu hướng rộng hơn ở mục{" "}
          <Link to="/app/trends" className="font-semibold text-[color:var(--gv-ink)] underline-offset-2 hover:underline">
            Xu hướng
          </Link>
          .
        </p>
      </section>
    );
  }

  return (
    <section>
      {!embedded ? (
        <SectionHeader
          kicker="BIÊN TẬP CHỌN"
          title="3 video bứt phá"
          caption="View vượt 10× so với trung bình kênh trong 48 giờ qua."
          right={headerRight}
        />
      ) : null}
      <div className="grid [grid-template-columns:repeat(auto-fit,minmax(280px,1fr))] gap-[18px]">
        {videos.map((v: BreakoutVideo, idx: number) => {
          const dur = formatDuration(v.video_duration ?? undefined);
          const isBreakout = v.breakout_multiplier != null;
          const panelClass = v.thumbnail_url
            ? ""
            : (FALLBACK_PANEL[idx % FALLBACK_PANEL.length] ?? "bg-[color:var(--gv-ink-2)]");
          const hookShort =
            v.hook_phrase && v.hook_phrase.length > 48 ? `${v.hook_phrase.slice(0, 48)}…` : v.hook_phrase;

          return (
            <a
              key={v.video_id}
              href={v.tiktok_url}
              target="_blank"
              rel="noreferrer"
              className="group block text-left"
            >
              <div
                className={`relative aspect-[4/5] w-full overflow-hidden rounded-[10px] border border-[color:var(--gv-rule)] ${!v.thumbnail_url ? panelClass : "bg-[color:var(--gv-ink)]"}`}
              >
                {v.thumbnail_url ? (
                  <img
                    src={v.thumbnail_url}
                    alt=""
                    loading="lazy"
                    className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
                  />
                ) : null}
                {v.thumbnail_url ? (
                  <div
                    className="pointer-events-none absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/75 via-black/20 to-transparent"
                    aria-hidden
                  />
                ) : null}
                <div className="pointer-events-none absolute inset-0 flex flex-col justify-between p-3.5 text-white">
                  <div className="flex items-start justify-between gap-2">
                    <span className="rounded px-2 py-0.5 gv-mono text-[10px] font-bold uppercase tracking-[0.05em] text-white bg-[color:var(--gv-accent)]">
                      {isBreakout ? "BREAKOUT" : "ĐANG NỔI"}
                    </span>
                    {dur ? <span className="gv-mono text-[11px] opacity-95">{dur}</span> : null}
                  </div>
                  <div className="min-h-0 flex-1 flex flex-col justify-end pt-8">
                    {v.hook_phrase ? (
                      <p
                        className="gv-tight line-clamp-4 text-[22px] leading-[1.1] text-white"
                        style={{ textShadow: "0 2px 12px rgba(0,0,0,0.5)" }}
                      >
                        &ldquo;{v.hook_phrase}&rdquo;
                      </p>
                    ) : (
                      <p className="gv-tight text-[22px] leading-[1.1] text-white/90" style={{ textShadow: "0 2px 12px rgba(0,0,0,0.5)" }}>
                        @{v.creator_handle}
                      </p>
                    )}
                  </div>
                </div>
              </div>
              <div className="mt-3 space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="gv-mono text-[11px] font-semibold text-[color:var(--gv-ink-3)]">
                    @{v.creator_handle}
                  </span>
                  <span className="gv-mono text-[11px] font-bold text-[color:var(--gv-accent-deep)]">
                    ↑ {formatViews(v.views)}
                  </span>
                </div>
                {v.hook_phrase ? (
                  <p className="text-[12px] text-[color:var(--gv-ink-3)]">
                    Hook ·{" "}
                    <span className="font-semibold text-[color:var(--gv-ink-2)]">
                      &ldquo;{hookShort}&rdquo;
                    </span>
                  </p>
                ) : v.hook_type ? (
                  <p className="text-[12px] text-[color:var(--gv-ink-3)]">
                    Hook · <span className="font-semibold text-[color:var(--gv-ink-2)]">{v.hook_type}</span>
                  </p>
                ) : null}
              </div>
            </a>
          );
        })}
      </div>
    </section>
  );
});
