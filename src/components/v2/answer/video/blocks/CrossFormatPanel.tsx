import { SectionMini } from "@/components/SectionMini";
import type { VideoReportPayload } from "@/lib/api-types";
import { formatViews } from "@/lib/formatters";

export function CrossFormatPanel({
  signal,
}: {
  signal: NonNullable<VideoReportPayload["cross_format_signal"]>;
}) {
  return (
    <section className="rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
      <SectionMini
        kicker="Tín hiệu liên ngách"
        title={`Format ${signal.format_label_vi} đang lan toả ${signal.niches_with_format} ngách`}
      />
      <p className="mt-1 text-sm text-[color:var(--gv-ink-3)]">
        Trong 30 ngày qua, {signal.total_sample_size} video cùng format này
        đang chạy ở {signal.niches_with_format} ngách khác nhau — tín hiệu
        format hot ngoài ngách của bạn.
      </p>
      {signal.top_hooks.length > 0 ? (
        <ul className="mt-3 grid list-none grid-cols-1 gap-2 p-0 sm:grid-cols-2">
          {signal.top_hooks.map((h) => (
            <li
              key={h.hook_type}
              className="flex items-center justify-between gap-3 rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-3 py-2 text-[12px]"
            >
              <span className="font-medium text-[color:var(--gv-ink)]">
                {h.hook_type_vi || h.hook_type}
              </span>
              <span className="gv-kicker text-[color:var(--gv-ink-3)]">
                {formatViews(Math.round(h.avg_views))} view ·{" "}
                {h.niche_spread} ngách
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
