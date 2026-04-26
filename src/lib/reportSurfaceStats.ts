import type { ReportV1, SourceRowData } from "@/lib/api-types";

/** Số liệu hiển thị dưới tiêu đề câu hỏi (reference: video mẫu + tổng nguồn). */
export type ReportSurfaceStats = {
  sampleVideos: number;
  /** Tổng count trên các dòng sources (gần với “47 nguồn” trong mock). */
  sourceUnits: number;
  channelRows: number;
};

function sumSourceCounts(rows: SourceRowData[] | undefined): number {
  if (!rows?.length) return 0;
  return rows.reduce((acc, s) => acc + (typeof s.count === "number" ? s.count : 0), 0);
}

function channelCountFromSources(rows: SourceRowData[] | undefined): number {
  if (!rows?.length) return 0;
  return rows.filter((s) => s.kind === "channel").reduce((acc, s) => acc + s.count, 0);
}

/** Lấy stats từ payload turn cuối (mọi kind có `report.sources` + hầu hết có `confidence`). */
export function surfaceStatsFromPayload(payload: ReportV1 | null): ReportSurfaceStats | null {
  if (!payload) return null;
  const r = payload.report as {
    sources?: SourceRowData[];
    confidence?: { sample_size: number };
  };
  const sources = r.sources;
  const sampleVideos = r.confidence?.sample_size ?? 0;
  const sourceUnits = sumSourceCounts(sources);
  const channelRows = channelCountFromSources(sources);
  if (sampleVideos <= 0 && sourceUnits <= 0) return null;
  return {
    sampleVideos: sampleVideos > 0 ? sampleVideos : sourceUnits,
    sourceUnits: sourceUnits > 0 ? sourceUnits : sampleVideos,
    channelRows,
  };
}
