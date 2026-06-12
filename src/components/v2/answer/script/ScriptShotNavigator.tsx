import { ChevronLeft, ChevronRight } from "lucide-react";
import { Btn } from "@/components/v2/Btn";

export function ScriptShotNavigator({
  index,
  total,
  onPrev,
  onNext,
}: {
  index: number;
  total: number;
  onPrev: () => void;
  onNext: () => void;
}) {
  if (total <= 0) return null;

  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <Btn
        variant="ghost"
        size="sm"
        type="button"
        className="min-h-[44px] gap-1"
        disabled={index <= 0}
        onClick={onPrev}
      >
        <ChevronLeft className="h-4 w-4" strokeWidth={2} aria-hidden />
        Cảnh trước
      </Btn>
      <Btn
        variant="ghost"
        size="sm"
        type="button"
        className="min-h-[44px] gap-1"
        disabled={index >= total - 1}
        onClick={onNext}
      >
        Cảnh tiếp
        <ChevronRight className="h-4 w-4" strokeWidth={2} aria-hidden />
      </Btn>
    </div>
  );
}
