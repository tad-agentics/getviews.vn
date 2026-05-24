import { MobileShellBar } from "@/components/mobileShell";

/** Mobile nav row for screens without a ``TopBar`` (Settings, History, checkout…). */
export function MobileShellStandalone() {
  return <MobileShellBar placement="standalone" />;
}
