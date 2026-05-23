/** W5-2 — unified headline from narrative_vi or legacy report fields. */
import type {
  GenericReportPayload,
  IdeasReportPayload,
  LifecycleReportPayload,
  PatternReportPayload,
  TimingReportPayload,
} from "@/lib/api-types";

export type ReportHeadlineSource =
  | { kind: "pattern"; report: PatternReportPayload }
  | { kind: "ideas"; report: IdeasReportPayload }
  | { kind: "timing"; report: TimingReportPayload }
  | { kind: "lifecycle"; report: LifecycleReportPayload }
  | { kind: "generic"; report: GenericReportPayload };

export function reportHeadlineVi(source: ReportHeadlineSource): string | null {
  const fromNv = (report: { narrative_vi?: { headline_vi?: string } | null }) =>
    report.narrative_vi?.headline_vi?.trim() || null;

  switch (source.kind) {
    case "pattern":
      return fromNv(source.report) || source.report.tldr.thesis?.trim() || null;
    case "ideas":
      return fromNv(source.report) || source.report.lead?.trim() || null;
    case "timing": {
      const nv = fromNv(source.report);
      if (nv) return nv;
      const tw = source.report.top_window as { insight?: string; day?: string; hours?: string };
      return tw.insight?.trim() || (tw.day && tw.hours ? `${tw.day}, ${tw.hours}` : null);
    }
    case "lifecycle":
      return fromNv(source.report) || source.report.subject_line?.trim() || null;
    case "generic": {
      const nv = fromNv(source.report);
      if (nv) return nv;
      const paras = (source.report.narrative as { paragraphs?: string[] })?.paragraphs;
      return paras?.[0]?.trim() || null;
    }
    default:
      return null;
  }
}
