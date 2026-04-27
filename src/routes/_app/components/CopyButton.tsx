import { useState } from "react";
import { Check, Copy } from "lucide-react";

export function CopyButton({ textToCopy }: { textToCopy: string }) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);

  // Only flip ``copied`` after the Clipboard API actually resolves.
  // Previously the button said "Đã copy ✓" the moment it was tapped,
  // even when ``writeText`` rejected (Safari without focus, missing
  // ``clipboard-write`` permission, insecure context). Surface a
  // recoverable failure state so the user knows nothing landed and
  // can copy manually.
  const handleClick = () => {
    setFailed(false);
    navigator.clipboard.writeText(textToCopy).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
      (err) => {
        console.warn("[CopyButton] clipboard.writeText failed:", err);
        setFailed(true);
        setTimeout(() => setFailed(false), 3000);
      },
    );
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`flex h-12 w-full items-center justify-center gap-2 rounded-lg border text-sm font-medium transition-all duration-[120ms] ${
        copied
          ? "border-[var(--gv-accent)] bg-[var(--gv-accent-soft)] text-[var(--gv-accent)]"
          : failed
            ? "border-[var(--gv-danger)] bg-[var(--surface)] text-[var(--gv-danger)]"
            : "border-[var(--border)] bg-[var(--surface)] text-[var(--ink)] hover:border-[var(--gv-ink)] hover:bg-[var(--surface-alt)]"
      }`}
    >
      {copied ? (
        <>
          <Check className="h-4 w-4" />
          Đã copy ✓
        </>
      ) : failed ? (
        <>
          <Copy className="h-4 w-4" />
          Không copy được — chọn và nhấn ⌘C
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
