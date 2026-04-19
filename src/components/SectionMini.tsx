/**
 * Section kicker + title with ink rule (Phase B · `/app/video` + shared screens).
 */

export type SectionMiniProps = {
  kicker: string;
  title: string;
  className?: string;
};

export function SectionMini({ kicker, title, className = "" }: SectionMiniProps) {
  return (
    <div
      className={`mb-3.5 border-b border-[color:var(--gv-ink)] pb-2 ${className}`.trim()}
    >
      <div className="gv-uc mb-1 text-[9px] text-[color:var(--gv-ink-4)]">{kicker}</div>
      <h3 className="gv-tight m-0 text-[22px] leading-tight text-[color:var(--gv-ink)]">{title}</h3>
    </div>
  );
}
