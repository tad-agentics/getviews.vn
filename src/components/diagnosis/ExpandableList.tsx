import { useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

/** Show first N items; "Xem thêm" reveals the rest (Part A6). */
export function ExpandableList<T>({
  items,
  initialCount,
  renderItem,
  itemKey,
  expandLabel = "Xem thêm",
}: {
  items: T[];
  initialCount: number;
  renderItem: (item: T, index: number) => ReactNode;
  itemKey: (item: T, index: number) => string;
  expandLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  if (items.length <= initialCount) {
    return (
      <>
        {items.map((item, i) => (
          <div key={itemKey(item, i)}>{renderItem(item, i)}</div>
        ))}
      </>
    );
  }

  const visible = items.slice(0, initialCount);
  const hidden = items.slice(initialCount);

  return (
    <div className="flex flex-col gap-3">
      {visible.map((item, i) => (
        <div key={itemKey(item, i)}>{renderItem(item, i)}</div>
      ))}
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleContent className="flex flex-col gap-3 data-[state=closed]:hidden">
          {hidden.map((item, i) => (
            <div key={itemKey(item, initialCount + i)}>{renderItem(item, initialCount + i)}</div>
          ))}
        </CollapsibleContent>
        <CollapsibleTrigger className="flex min-h-[44px] w-full items-center gap-2 text-sm font-medium text-[color:var(--gv-accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)]/40">
          <span>{open ? "Thu gọn" : `${expandLabel} (${hidden.length})`}</span>
          <ChevronDown
            className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`}
            aria-hidden
          />
        </CollapsibleTrigger>
      </Collapsible>
    </div>
  );
}
