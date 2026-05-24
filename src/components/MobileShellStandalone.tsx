import { MobileShellDrawerButton } from "@/components/mobileShell";

/** Mobile header row for screens without a ``TopBar`` (Settings, History, checkout…). */
export function MobileShellStandalone() {
  return (
    <div className="sticky top-0 z-20 border-b border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] pt-[env(safe-area-inset-top)] lg:hidden">
      <div className="flex min-h-11 items-center px-2 py-1">
        <MobileShellDrawerButton />
      </div>
    </div>
  );
}
