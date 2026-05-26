import type { ChannelDiagnosisFinding } from "@/lib/api-types";
import { ChannelAuditRingsPanel } from "./ChannelAuditRingsPanel";

/** @deprecated Prefer ``ChannelAuditRingsPanel`` — kept for import stability. */
export function ChannelFindingsStrip({ findings }: { findings: ChannelDiagnosisFinding[] }) {
  return <ChannelAuditRingsPanel findings={findings} />;
}
