// Renders a subtle circular arc showing analysis usage.
// Invisible below 70% — appears amber at or above 90%.
// Never shows a number in the sidebar; tooltip only on hover.
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";

interface UsageArcProps {
  used: number;   // analyses used (deep_credits_remaining subtracted from cap)
  limit: number;  // monthly cap (deep_credits_total)
}

export function UsageArc({ used, limit }: UsageArcProps) {
  const pct = limit > 0 ? used / limit : 0;

  if (pct < 0.7) return null;

  const isAmber = pct >= 0.9;

  const r = 10;
  const cx = 12;
  const cy = 12;
  const circumference = 2 * Math.PI * r;
  const strokeDashoffset = circumference * (1 - pct);

  const gradientId = isAmber ? "arc-amber" : "arc-purple";

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className="flex items-center justify-center cursor-default"
            style={{ width: 24, height: 24 }}
            aria-label={`Đã dùng ${used} trong ${limit} phân tích tháng này`}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <defs>
                <linearGradient id="arc-purple" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#a855f7" />
                  <stop offset="100%" stopColor="#7c3aed" />
                </linearGradient>
                <linearGradient id="arc-amber" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#fbbf24" />
                  <stop offset="100%" stopColor="#d97706" />
                </linearGradient>
              </defs>
              {/* Track */}
              <circle
                cx={cx}
                cy={cy}
                r={r}
                stroke="var(--border)"
                strokeWidth={2.5}
                fill="none"
              />
              {/* Arc */}
              <circle
                cx={cx}
                cy={cy}
                r={r}
                stroke={`url(#${gradientId})`}
                strokeWidth={2.5}
                fill="none"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                transform="rotate(-90 12 12)"
                style={{ transition: "stroke-dashoffset 0.4s ease, stroke 0.3s ease" }}
              />
            </svg>
          </div>
        </TooltipTrigger>
        <TooltipContent side="right" className="text-sm">
          <p>
            Đã dùng <strong>{used}</strong> / {limit} phân tích tháng này
          </p>
          {isAmber && (
            <p className="mt-0.5 text-xs text-muted-foreground">
              Sắp hết — nâng cấp để tiếp tục không bị gián đoạn
            </p>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
