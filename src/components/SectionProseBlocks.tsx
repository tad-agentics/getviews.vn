/**
 * Shared prose renderer for channel diagnosis + video v6 sections.
 *
 * Handles mixed content: prose paragraphs (double-newline separated) interspersed
 * with bullet-point blocks (lines starting with •, -, *, or 1./2. etc.).
 * Bullet blocks render as <ul>/<li>; prose blocks render as <p>.
 */

const BULLET_RE = /^[•\-*]\s+|^\d+[.)]\s+/;

type Block =
  | { type: "paragraph"; text: string }
  | { type: "list"; items: string[] };

function stripBulletPrefix(line: string): string {
  return line.replace(BULLET_RE, "").trim();
}

function parseBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  const lines = text.split("\n");

  let buf: string[] = [];
  let inList = false;

  const flush = () => {
    if (!buf.length) return;
    if (inList) {
      const items = buf.map(stripBulletPrefix).filter(Boolean);
      if (items.length) blocks.push({ type: "list", items });
    } else {
      const para = buf.join(" ").trim();
      if (para) blocks.push({ type: "paragraph", text: para });
    }
    buf = [];
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed === "") {
      flush();
      inList = false;
    } else if (BULLET_RE.test(trimmed)) {
      if (!inList) {
        flush();
        inList = true;
      }
      buf.push(trimmed);
    } else {
      if (inList) {
        flush();
        inList = false;
      }
      buf.push(trimmed);
    }
  }
  flush();
  return blocks;
}

interface SectionProseBlocksProps {
  text: string;
  /** Outer wrapper classes. */
  wrapperClassName?: string;
  /** Per-paragraph classes. */
  paragraphClassName?: string;
  /** Per-list-item classes. */
  listItemClassName?: string;
}

export function SectionProseBlocks({
  text,
  wrapperClassName = "space-y-2 mt-2",
  paragraphClassName = "text-sm text-[color:var(--foreground)] leading-relaxed",
  listItemClassName,
}: SectionProseBlocksProps) {
  if (!text.trim()) return null;
  const blocks = parseBlocks(text);
  const liClass =
    listItemClassName ??
    "flex items-start gap-2 text-sm leading-relaxed text-[color:var(--foreground)]";

  return (
    <div className={wrapperClassName}>
      {blocks.map((block, i) => {
        if (block.type === "list") {
          return (
            <ul key={i} className="m-0 flex list-none flex-col gap-1.5 p-0">
              {block.items.map((item, j) => (
                <li key={j} className={liClass}>
                  <span
                    className="mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full bg-[color:var(--gv-accent)]"
                    aria-hidden
                  />
                  {item}
                </li>
              ))}
            </ul>
          );
        }
        return (
          <p key={i} className={paragraphClassName}>
            {block.text}
          </p>
        );
      })}
    </div>
  );
}
