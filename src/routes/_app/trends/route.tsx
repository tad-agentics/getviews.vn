import { AppLayout } from "@/components/AppLayout";

// Phase 2+: Figma Make TSX will be copied here by the Frontend Developer
export default function TrendsScreen() {
  return (
    <AppLayout active="trends" enableMobileSidebar>
      <div className="flex flex-1 flex-col overflow-hidden bg-[var(--surface-alt)]">
        <div className="flex h-14 flex-shrink-0 items-center border-b border-[var(--border)] bg-[var(--surface)] px-6 pl-16 lg:pl-6">
          <span className="font-extrabold text-[var(--ink)]">Xu hướng</span>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          <p className="text-[var(--ink-soft)]">Xu hướng</p>
        </div>
      </div>
    </AppLayout>
  );
}
