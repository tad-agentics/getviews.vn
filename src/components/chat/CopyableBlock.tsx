/**
 * CopyableBlock — highlighted block for hook formula templates (P0-3).
 *
 * Rendered when MarkdownRenderer detects a line starting with "Hook:" or "**Hook:**".
 * Visual spec: purple-light bg, 2px purple left-border, copy button right-aligned.
 */
import { useState } from "react";
import { Copy, Check } from "lucide-react";

/** Strip leading/trailing asterisks and whitespace from hook text. */
function cleanHookText(text: string): string {
  return text.replace(/^\*+|\*+$/g, "").trim();
}

/** Render **bold** markers as <strong> within hook text. */
function renderHookInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**") ? <strong key={i}>{p.slice(2, -2)}</strong> : p
  );
}

interface Props {
  text: string;
}

export function CopyableBlock({ text }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(cleanHookText(text));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable — silent fail */
    }
  };

  return (
    <div
      className="my-2 flex items-start justify-between gap-3 rounded-lg px-3 py-2.5"
      style={{
        background: "var(--purple-light)",
        borderLeft: "2px solid var(--purple)",
      }}
    >
      <p className="flex-1 text-sm font-semibold leading-snug text-[var(--ink)]">
        {renderHookInline(cleanHookText(text))}
      </p>
      <button
        type="button"
        onClick={() => void handleCopy()}
        className="flex-shrink-0 rounded p-1 transition-colors duration-[120ms] hover:bg-[var(--purple-light)]"
        aria-label="Copy hook formula"
        title={copied ? "Đã copy ✓" : "Copy"}
      >
        {copied ? (
          <Check className="h-3.5 w-3.5 text-[var(--purple)]" strokeWidth={2.5} />
        ) : (
          <Copy className="h-3.5 w-3.5 text-[var(--muted)]" strokeWidth={2} />
        )}
      </button>
    </div>
  );
}
