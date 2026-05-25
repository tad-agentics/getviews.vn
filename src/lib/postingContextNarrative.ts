import type { DiagnosisPostingContextPayload } from "@/lib/api-types";

/**
 * Vietnamese prose for diagnosis posting embed (FE fallback when v6 `distribution`
 * section did not emit). Use double newlines so `SectionProseBlocks` splits paragraphs.
 */
export function buildDiagnosisPostingNarrative(
  payload: DiagnosisPostingContextPayload,
): string {
  const paragraphs: string[] = [];
  const n = payload.sample_size;
  const days = payload.window_days;
  const label = payload.niche_label?.trim();
  const kind = String(payload.variance_note?.kind ?? "sparse");
  const detail = String(payload.variance_note?.detail ?? "").trim();

  const opener = label
    ? `Dựa trên ${n} video trong ngách ${label} (~${days} ngày gần nhất)`
    : `Dựa trên ${n} video (~${days} ngày gần nhất)`;

  if (kind === "strong") {
    paragraphs.push(
      `${opener}, khung giờ đăng trong ngách có tín hiệu ổn định — có thể ưu tiên khi lên lịch bài tiếp theo.`,
    );
  } else if (kind === "weak") {
    paragraphs.push(
      `${opener}, khung giờ có xu hướng nhưng chưa đủ chắc để chốt một slot cố định; nên thử nhiều khung trước khi kết luận.`,
    );
  } else {
    paragraphs.push(
      `${opener}, khung giờ chưa đủ ổn định để chốt một slot — heatmap mang tính tham khảo, nên thử nhiều khung.`,
    );
  }

  if (detail) {
    paragraphs.push(detail);
  }

  const userLine = payload.user_post_window_vi?.trim();
  const tops = payload.top_3_windows?.slice(0, 3) ?? [];

  if (userLine || tops.length > 0) {
    const compareParts: string[] = [];
    if (userLine) {
      compareParts.push(
        userLine.startsWith("Bài") ? userLine : `Bài đang phân tích: ${userLine}`,
      );
    }
    if (tops.length > 0) {
      const formatted = tops.map((w) => {
        const day = String(w.day ?? "").trim();
        const hours = String(w.hours ?? "").trim();
        const liftRaw = w.lift_multiplier;
        const lift = typeof liftRaw === "number" ? liftRaw : Number(liftRaw);
        const samp = w.sample;
        let chunk = `${day} ${hours}`.trim();
        if (Number.isFinite(lift)) {
          chunk += ` (~${lift % 1 === 0 ? lift.toFixed(0) : lift.toFixed(1)}× trung vị ngách`;
          if (typeof samp === "number") {
            chunk += `, ${samp} clip`;
          }
          chunk += ")";
        } else if (typeof samp === "number") {
          chunk += ` (${samp} clip trong ô)`;
        }
        return chunk;
      });
      compareParts.push(
        `Ba cửa sổ corpus mạnh nhất: ${formatted.join("; ")}. So khung bạn đăng với các ô này — lệch khung mạnh thì thử dịch ±1 khung giờ hoặc đổi ngày trong tuần.`,
      );
    }
    paragraphs.push(compareParts.join(" "));
  }

  return paragraphs.join("\n\n");
}
