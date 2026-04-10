import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/Button";

type EmptyStateProps = {
  icon: LucideIcon;
  heading: string;
  subtext: string;
  ctaLabel?: string;
  onCta?: () => void;
};

export function EmptyState({ icon: Icon, heading, subtext, ctaLabel, onCta }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[var(--surface-alt)] text-[var(--muted)]">
        <Icon className="h-7 w-7" strokeWidth={1.5} aria-hidden />
      </div>
      <h2 className="text-lg font-bold text-[var(--ink)]">{heading}</h2>
      <p className="max-w-sm text-sm text-[var(--ink-soft)]" style={{ lineHeight: 1.6 }}>
        {subtext}
      </p>
      {ctaLabel && onCta ? (
        <Button type="button" variant="primary" className="mt-2" onClick={onCta}>
          {ctaLabel}
        </Button>
      ) : null}
    </div>
  );
}
