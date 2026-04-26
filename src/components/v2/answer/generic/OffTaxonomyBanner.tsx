/**
 * Phase C.5.2 — OffTaxonomyBanner (plan §2.4 section 2).
 *
 * Soft suggestion chip strip. Copy:
 *   "Câu hỏi này ngoài taxonomy — gợi ý: dùng Soi Kênh / Xưởng Viết
 *    thay vì đào sâu ở đây."
 *
 * Chip buttons route to `/app/channel`, `/app/script`, etc. — driven by
 * the server's `off_taxonomy.suggestions` payload.
 *
 * Creator-only pivot (claude/remove-kol-creator-only): /app/kol no
 * longer exists; suggestions pointing there are filtered out at render.
 * Dashed ink-4 border signals "soft suggestion" rather than "error".
 */

import { Eye, Film } from "lucide-react";
import { useNavigate } from "react-router";

import type { GenericReportPayload } from "@/lib/api-types";

type Suggestion = { label?: string; route?: string; icon?: string } & Record<string, unknown>;

function iconFor(symbol: string | undefined): React.ElementType {
  switch (symbol) {
    case "eye":
      return Eye;
    case "film":
      return Film;
    default:
      return Eye;
  }
}

export function OffTaxonomyBanner({
  data,
}: {
  data: GenericReportPayload["off_taxonomy"];
}) {
  const navigate = useNavigate();
  const rawSuggestions = (data?.suggestions as Suggestion[] | undefined) ?? [];
  // Drop server suggestions pointing to retired routes (currently /app/kol).
  const suggestions = rawSuggestions.filter((s) => {
    const route = (s.route as string | undefined) ?? "";
    return !route.startsWith("/app/kol");
  });
  if (suggestions.length === 0) return null;
  return (
    <section
      className="flex flex-col gap-3 rounded border border-dashed border-[color:var(--gv-ink-4)] bg-[color:var(--gv-canvas-2)] px-[18px] py-[14px]"
      aria-label="Gợi ý công cụ ngoài taxonomy"
    >
      <p className="text-[14px] leading-[1.55] text-[color:var(--gv-ink-2)]">
        Câu hỏi này ngoài taxonomy — gợi ý: dùng{" "}
        <strong className="text-[color:var(--gv-ink)]">Soi Kênh / Xưởng Viết</strong>{" "}
        thay vì đào sâu ở đây.
      </p>
      <ul className="flex flex-wrap gap-2">
        {suggestions.map((s) => {
          const label = (s.label as string | undefined) ?? "Mở";
          const route = (s.route as string | undefined) ?? "/app";
          const Icon = iconFor(s.icon as string | undefined);
          return (
            <li key={`${label}-${route}`}>
              <button
                type="button"
                onClick={() => navigate(route)}
                className="gv-mono inline-flex items-center gap-1.5 rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2.5 py-1 text-[11px] text-[color:var(--gv-ink-2)] hover:border-[color:var(--gv-ink)]"
              >
                <Icon className="size-3" aria-hidden />
                {label}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
