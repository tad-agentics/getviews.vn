/**
 * Shared double-newline → paragraph blocks (channel diagnosis + video v6 sections).
 */

interface SectionProseBlocksProps {
  text: string;
  /** Outer wrapper classes (default matches channel SectionRenderer). */
  wrapperClassName?: string;
  /** Per-paragraph classes. */
  paragraphClassName?: string;
}

export function SectionProseBlocks({
  text,
  wrapperClassName = "space-y-2 mt-2",
  paragraphClassName = "text-sm text-[color:var(--foreground)] leading-relaxed",
}: SectionProseBlocksProps) {
  if (!text.trim()) return null;
  const paragraphs = text.split(/\n{2,}/).map((p) => p.trim()).filter(Boolean);
  return (
    <div className={wrapperClassName}>
      {paragraphs.map((para, i) => (
        <p key={i} className={paragraphClassName}>
          {para}
        </p>
      ))}
    </div>
  );
}
