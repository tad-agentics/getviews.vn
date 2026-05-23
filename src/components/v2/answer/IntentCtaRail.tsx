import { useMemo, useState } from "react";
import { Sparkles } from "lucide-react";

import {
  getIntentCtaSuggestions,
  intentCtaQueryForSuggestion,
  type IntentCtaContext,
  type IntentCtaSuggestion,
} from "@/lib/intentCtaSuggestions";

const CTA_PILL =
  "inline-flex min-h-[44px] max-w-full items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2 text-left text-[11px] font-medium leading-snug text-[color:var(--gv-ink-2)] transition-colors hover:border-[color:var(--gv-ink)] hover:bg-[color:var(--gv-canvas-2)] disabled:pointer-events-none disabled:pointer-events-none disabled:cursor-not-allowed disabled:border-[color:var(--gv-rule)] disabled:bg-[color:var(--gv-faint)] disabled:text-[color:var(--gv-ink-4)] disabled:opacity-100";

export function IntentCtaRail({
  context,
  disabled,
  onCta,
}: {
  context: IntentCtaContext;
  disabled?: boolean;
  onCta: (suggestion: IntentCtaSuggestion, query: string) => void;
}) {
  const suggestions = useMemo(() => getIntentCtaSuggestions(context), [context]);
  const [compareUrl, setCompareUrl] = useState("");
  const [compareOpen, setCompareOpen] = useState(false);

  if (suggestions.length === 0) return null;

  const handleTap = (s: IntentCtaSuggestion) => {
    if (s.disabledReason || disabled) return;
    if (s.action === "compare_navigate") {
      setCompareOpen(true);
      return;
    }
    onCta(s, intentCtaQueryForSuggestion(s, context));
  };

  const submitCompare = () => {
    const b = compareUrl.trim();
    if (!b || disabled) return;
    const compareSuggestion = suggestions.find((s) => s.action === "compare_navigate");
    if (!compareSuggestion) return;
    onCta(compareSuggestion, b);
    setCompareUrl("");
    setCompareOpen(false);
  };

  return (
    <div className="mt-10" aria-label="Gợi ý bước tiếp theo">
      <p className="mb-3 gv-kicker text-[color:var(--gv-ink-3)]">
        Tiếp tục nghiên cứu
      </p>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((s) => (
          <button
            key={s.id}
            type="button"
            disabled={disabled || Boolean(s.disabledReason)}
            title={s.disabledReason}
            className={CTA_PILL}
            onClick={() => handleTap(s)}
          >
            <Sparkles className="h-3 w-3 shrink-0 text-[color:var(--gv-accent)]" aria-hidden />
            <span className="min-w-0">{s.label}</span>
          </button>
        ))}
      </div>
      {compareOpen ? (
        <div className="mt-3 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-3">
          <p className="m-0 text-[12px] text-[color:var(--gv-ink-3)]">
            Dán URL video thứ hai để so sánh
          </p>
          <div className="mt-2 flex flex-col gap-2 min-[480px]:flex-row">
            <input
              type="url"
              inputMode="url"
              className="min-h-[44px] flex-1 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-3 text-[17px] text-[color:var(--gv-ink)]"
              placeholder="https://www.tiktok.com/…"
              value={compareUrl}
              onChange={(e) => setCompareUrl(e.target.value)}
              disabled={disabled}
            />
            <button
              type="button"
              className={CTA_PILL}
              disabled={disabled || !compareUrl.trim()}
              onClick={submitCompare}
            >
              So sánh
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
