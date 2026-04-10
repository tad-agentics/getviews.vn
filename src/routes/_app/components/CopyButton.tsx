import { useState } from "react";
import { Check, Copy } from "lucide-react";

export function CopyButton({ textToCopy }: { textToCopy: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={() => {
        void navigator.clipboard.writeText(textToCopy);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className={`flex h-12 w-full items-center justify-center gap-2 rounded-lg border text-sm font-medium transition-all duration-[120ms] ${
        copied
          ? "border-[var(--purple)] bg-[var(--purple-light)] text-[var(--purple)]"
          : "border-[var(--border)] bg-[var(--surface)] text-[var(--ink)] hover:border-[var(--border-active)] hover:bg-[var(--surface-alt)]"
      }`}
    >
      {copied ? (
        <>
          <Check className="h-4 w-4" />
          Đã copy ✓
        </>
      ) : (
        <>
          <Copy className="h-4 w-4" />
          Copy kết quả
        </>
      )}
    </button>
  );
}
