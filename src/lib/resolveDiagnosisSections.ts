import type {
  DiagnosisFinding,
  DiagnosisSectionVi,
  NarrativeVi,
  VideoAnalyzeMode,
  VideoFlopIssue,
} from "@/lib/api-types";

/**
 * Single diagnosis render path: prefer `diagnosis_vi.sections` (v6).
 * Legacy cache rows without sections get a one-shot shim until re-analyze / TRUNCATE.
 */
export function resolveDiagnosisSections(
  narrativeVi: NarrativeVi | undefined,
  flopIssues: VideoFlopIssue[],
  mode: VideoAnalyzeMode,
): DiagnosisSectionVi[] {
  const fromV6 = narrativeVi?.diagnosis_vi?.sections;
  if (Array.isArray(fromV6) && fromV6.length > 0) {
    return fromV6;
  }

  const proseParts: string[] = [];
  const ket = narrativeVi?.ket_luan_nhanh?.trim();
  const vanDe = narrativeVi?.van_de_chinh?.trim();
  if (ket) proseParts.push(ket);
  if (vanDe) proseParts.push(vanDe);
  const prose = proseParts.join("\n\n");

  const findings: DiagnosisFinding[] = flopIssues.slice(0, 3).map((issue) => {
    const narrativeItem = narrativeVi?.loi_chinh_narrative?.find(
      (n) => n.error_id === issue.error_id,
    );
    return {
      title_vi: issue.title,
      body_vi: narrativeItem?.narrative?.trim() || issue.detail?.trim() || "",
      fix_vi: issue.fix?.trim() || undefined,
    };
  }).filter((f) => f.title_vi || f.body_vi || f.fix_vi);

  const sections: DiagnosisSectionVi[] = [];

  if (prose || findings.length > 0) {
    sections.push({
      section_id: "diagnosis",
      title_vi: mode === "flop" ? "Vấn đề cần sửa" : "Chẩn đoán",
      title: mode === "flop" ? "Vấn đề cần sửa" : "Chẩn đoán",
      text_vi: prose,
      text: prose,
      findings,
    });
  }

  const nextSteps = narrativeVi?.dinh_huong_chien_luoc?.trim();
  if (nextSteps) {
    sections.push({
      section_id: "next_video",
      title_vi: "Hướng tiếp theo",
      title: "Hướng tiếp theo",
      text_vi: nextSteps,
      text: nextSteps,
      findings: [],
    });
  }

  return sections;
}
