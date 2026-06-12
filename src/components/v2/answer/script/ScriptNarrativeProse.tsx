import { humanizeStatsProse } from "@/lib/humanizeStatsProse";

const HANDLE_IN_PROSE = /(@[\w.]+)/g;

function handleHref(handleToken: string): string {
  const handle = handleToken.replace(/^@/, "").trim();
  return `https://www.tiktok.com/@${handle}`;
}

export function ScriptNarrativeProse({
  text,
  className,
}: {
  text: string;
  className?: string;
}) {
  const normalized = humanizeStatsProse(text.trim());
  if (!normalized) return null;

  const paragraphs = normalized.split(/\n\n+/).map((p) => p.trim()).filter(Boolean);

  return (
    <div className={className ?? "mt-2 space-y-2"}>
      {paragraphs.map((para, pi) => {
        const parts = para.split(HANDLE_IN_PROSE);
        return (
          <p
            key={pi}
            className="m-0 text-[15px] leading-relaxed text-[color:var(--gv-ink-2)]"
          >
            {parts.map((part, i) => {
              if (part.startsWith("@") && part.length > 1) {
                return (
                  <a
                    key={`${pi}-${i}`}
                    href={handleHref(part)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-[color:var(--gv-accent-deep)] underline-offset-2 hover:underline"
                  >
                    {part}
                  </a>
                );
              }
              return part;
            })}
          </p>
        );
      })}
    </div>
  );
}
