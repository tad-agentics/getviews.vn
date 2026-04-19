import { useState } from "react";
import { Film, Sparkles } from "lucide-react";
import { Btn } from "@/components/v2/Btn";

export type VideoUrlCaptureProps = {
  /** Called with trimmed URL after user submits (parent navigates or sets search params). */
  onSubmitUrl: (tiktokUrl: string) => void;
  defaultValue?: string;
  disabled?: boolean;
  /** `hero` — empty-state primary; `compact` — strip above results for another analysis. */
  variant?: "hero" | "compact";
};

function looksLikeTikTokUrl(raw: string): boolean {
  const s = raw.trim();
  if (!s || s.startsWith("@")) return false;
  const candidate = s.includes("://") ? s : `https://${s}`;
  try {
    return new URL(candidate).hostname.toLowerCase().endsWith("tiktok.com");
  } catch {
    return false;
  }
}

/**
 * B.1.5 — TikTok URL field + analyze CTA (matches `video.jsx` flop input row, gv tokens).
 */
export function VideoUrlCapture({
  onSubmitUrl,
  defaultValue = "",
  disabled = false,
  variant = "hero",
}: VideoUrlCaptureProps) {
  const [value, setValue] = useState(defaultValue);
  const [error, setError] = useState<string | null>(null);

  const submit = () => {
    const t = value.trim();
    if (!t) {
      setError("Dán link TikTok (hoặc URL rút gọn vm.tiktok.com).");
      return;
    }
    if (!looksLikeTikTokUrl(t)) {
      setError("URL cần chứa tiktok.com hoặc domain rút gọn TikTok.");
      return;
    }
    setError(null);
    onSubmitUrl(t);
  };

  const wrap =
    variant === "hero"
      ? "rounded-[var(--gv-radius-md)] border-2 border-[color:var(--gv-ink)] bg-[color:var(--gv-paper)] p-4"
      : "rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-3";

  return (
    <div className={wrap}>
      <div className="flex flex-col gap-3 min-[640px]:flex-row min-[640px]:items-center min-[640px]:gap-3">
        <div className="flex shrink-0 items-center gap-2 text-[color:var(--gv-ink-2)]">
          <Film className="h-4 w-4" strokeWidth={1.75} aria-hidden />
          {variant === "hero" ? (
            <span className="text-sm font-medium text-[color:var(--gv-ink)]">Dán link TikTok</span>
          ) : null}
        </div>
        <input
          type="url"
          name="tiktok_url"
          autoComplete="url"
          inputMode="url"
          placeholder="https://www.tiktok.com/@…/video/… hoặc vm.tiktok.com/…"
          value={value}
          disabled={disabled}
          onChange={(e) => {
            setValue(e.target.value);
            if (error) setError(null);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              submit();
            }
          }}
          className="min-w-0 flex-1 border-0 bg-transparent font-[family-name:var(--gv-font-mono)] text-sm text-[color:var(--gv-ink)] outline-none placeholder:text-[color:var(--gv-ink-4)]"
        />
        <Btn
          type="button"
          variant="accent"
          size="md"
          className="shrink-0"
          disabled={disabled}
          onClick={submit}
        >
          <Sparkles className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden />
          Phân tích
        </Btn>
      </div>
      {error ? (
        <p className="mt-2 text-xs text-[color:var(--gv-neg-deep)]" role="alert">
          {error}
        </p>
      ) : variant === "hero" ? (
        <p className="mt-2 text-xs text-[color:var(--gv-ink-4)]">
          Video phải đã có trong kho corpus Getviews (cùng URL đã ingest).
        </p>
      ) : null}
    </div>
  );
}
