import { useState } from "react";
import { Check, Users } from "lucide-react";
import { Kicker } from "@/components/v2/Kicker";
import { Btn } from "@/components/v2/Btn";
import { useStarterCreators, type StarterCreator } from "@/hooks/useStarterCreators";
import { useUpdateProfile } from "@/hooks/useUpdateProfile";

/**
 * Onboarding step 2 — creator picks 1–3 reference channels to anchor every
 * home signal on. Skippable; writes an empty array if the creator opts out.
 *
 * Data source: GET /home/starter-creators (top 10 by follower count per
 * niche, seeded from video_corpus). Display_name falls back to @handle
 * when the corpus didn't carry a pretty name.
 */

const MAX_SELECTED = 3;

function formatCount(n: number): string {
  if (n >= 1_000_000) {
    const m = n / 1_000_000;
    return m >= 10 ? `${Math.round(m)}M` : `${m.toFixed(1).replace(/\.0$/, "")}M`;
  }
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return n.toString();
}

export function ReferenceChannelsStep({
  onDone,
  onBack,
}: {
  onDone: () => void;
  onBack?: () => void;
}) {
  const { data: creators, isPending, error } = useStarterCreators();
  const save = useUpdateProfile();
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggle = (handle: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(handle)) {
        next.delete(handle);
      } else if (next.size < MAX_SELECTED) {
        next.add(handle);
      }
      return next;
    });
  };

  const commit = async (handles: string[]) => {
    try {
      await save.mutateAsync({ reference_channel_handles: handles });
    } finally {
      onDone();
    }
  };

  // Treat network failure / empty cloudrun config as "skip silently" —
  // reference channels are optional; we'd rather let the user proceed than
  // block onboarding on an auxiliary step.
  if (error || (creators && creators.length === 0 && !isPending)) {
    return (
      <div className="rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5 text-center">
        <Users className="mx-auto mb-3 h-5 w-5 text-[color:var(--gv-ink-4)]" strokeWidth={1.5} />
        <p className="mb-4 text-sm text-[color:var(--gv-ink-3)]">
          Chưa có danh sách gợi ý cho ngách này. Bạn có thể thêm kênh tham chiếu sau trong Cài đặt.
        </p>
        <div className="flex items-center justify-center gap-2">
          {onBack ? (
            <Btn type="button" variant="ghost" size="sm" onClick={onBack}>
              Quay lại
            </Btn>
          ) : null}
          <Btn type="button" variant="ink" size="sm" onClick={() => commit([])}>
            Tiếp tục
          </Btn>
        </div>
      </div>
    );
  }

  if (isPending) {
    return (
      <div className="rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
        <p className="text-sm text-[color:var(--gv-ink-4)]">Đang tải danh sách kênh…</p>
      </div>
    );
  }

  const list = creators ?? [];

  return (
    <div className="rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
      <Kicker>CHỌN 1–3 KÊNH</Kicker>
      <h3
        className="gv-tight mt-2 text-[22px] leading-tight text-[color:var(--gv-ink)]"
        style={{ fontFamily: "var(--gv-font-display)" }}
      >
        Những kênh bạn theo dõi sát trong ngách này?
      </h3>
      <p className="mt-2 text-sm leading-snug text-[color:var(--gv-ink-3)]">
        Mọi gợi ý hook + kịch bản hằng ngày sẽ được neo theo giọng + phong cách của các kênh bạn chọn.
      </p>

      <ul className="mt-4 flex max-h-[320px] flex-col gap-2 overflow-y-auto">
        {list.map((c: StarterCreator) => {
          const isSelected = selected.has(c.handle);
          const disabled = !isSelected && selected.size >= MAX_SELECTED;
          const display = c.display_name?.trim() || `@${c.handle}`;
          return (
            <li key={c.handle}>
              <button
                type="button"
                disabled={disabled}
                aria-pressed={isSelected}
                onClick={() => toggle(c.handle)}
                className={
                  "flex w-full items-center justify-between gap-3 rounded-[12px] border px-3 py-2.5 text-left transition-colors " +
                  (isSelected
                    ? "border-[color:var(--gv-ink)] bg-[color:var(--gv-accent-soft)]"
                    : "border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] hover:border-[color:var(--gv-ink-4)] disabled:opacity-40")
                }
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-[color:var(--gv-ink)]">
                    {display}
                  </p>
                  <p className="truncate text-[11px] text-[color:var(--gv-ink-4)]">
                    @{c.handle} · {formatCount(c.followers)} follow · TB {formatCount(c.avg_views)} view
                  </p>
                </div>
                <span
                  aria-hidden="true"
                  className={
                    "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border " +
                    (isSelected
                      ? "border-[color:var(--gv-ink)] bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
                      : "border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]")
                  }
                >
                  {isSelected ? <Check className="h-3 w-3" strokeWidth={3} /> : null}
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      <div className="mt-4 flex items-center gap-2">
        <p className="text-[11px] uppercase tracking-wider text-[color:var(--gv-ink-4)]">
          {selected.size}/{MAX_SELECTED} kênh
        </p>
        <div className="ml-auto flex items-center gap-2">
          {onBack ? (
            <Btn
              type="button"
              variant="ghost"
              size="sm"
              onClick={onBack}
              disabled={save.isPending}
            >
              Quay lại
            </Btn>
          ) : null}
          <Btn
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => commit([])}
            disabled={save.isPending}
          >
            Bỏ qua
          </Btn>
          <Btn
            type="button"
            variant="ink"
            size="sm"
            onClick={() => commit(Array.from(selected))}
            disabled={save.isPending || selected.size === 0}
          >
            Tiếp tục
          </Btn>
        </div>
      </div>
    </div>
  );
}
