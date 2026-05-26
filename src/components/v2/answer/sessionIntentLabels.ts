/**
 * Session-level intent copy — §J payloads share a `format` but `intent_type`
 * reflects the Studio framing (trend vs directions vs subniche vs fatigue, …).
 * Labels stay Vietnamese-first per CLAUDE.md.
 */

export type PatternSectionLabels = {
  tldrKicker: string;
  tldrTitle: string;
  findingsKicker: string;
  findingsTitle: string;
  stalledKicker: string;
  stalledTitle: string;
  evidenceKicker: string;
  evidenceTitleForCount: (count: number) => string;
  patternsKicker: string;
  patternsTitleForSample: (sampleSize: number) => string;
  actionsKicker: string;
  actionsTitle: string;
};

const DEFAULT_PATTERN: PatternSectionLabels = {
  tldrKicker: "Tóm tắt",
  tldrTitle: "Điều bạn nên biết",
  findingsKicker: "Bằng chứng · 3 hook",
  findingsTitle: "Mẫu kịch bản đang thắng, xếp theo tỷ lệ giữ chân",
  stalledKicker: "Đã thử nhưng rơi",
  stalledTitle: "Mẫu kịch bản không còn hiệu quả",
  evidenceKicker: "Video mẫu",
  evidenceTitleForCount: (count) => `${count} video dùng mẫu kịch bản này đang lên`,
  patternsKicker: "Mẫu kịch bản",
  patternsTitleForSample: (n) => `Điểm chung của ${n} video thắng`,
  actionsKicker: "Bước tiếp theo",
  actionsTitle: "Biến ý tưởng thành video",
};

function spikePattern(): PatternSectionLabels {
  return {
    ...DEFAULT_PATTERN,
    tldrTitle: "Điều đang nổi trên feed",
    findingsTitle: "Hook đang kéo lượt xem mạnh nhất tuần này",
    stalledTitle: "Góc đang hạ nhiệt — tránh làm thêm kiểu này",
    evidenceTitleForCount: (count) => `${count} clip minh họa xu hướng đang lên`,
    patternsTitleForSample: (n) => `Điểm chung ${n} clip đang bám xu hướng`,
    actionsTitle: "Biến xu hướng thành video tuần này",
  };
}

function directionsPattern(): PatternSectionLabels {
  return {
    ...DEFAULT_PATTERN,
    tldrTitle: "Hướng quay và góc kể đáng ưu tiên",
    findingsKicker: "Bằng chứng · kiểu mở",
    findingsTitle: "Kiểu mở đang giữ người xem lâu nhất",
    stalledTitle: "Góc đang mất lực — cân nhắc đổi nhịp độ lên bài",
    evidenceTitleForCount: (count) => `${count} ví dụ đi đúng hướng đang chạy`,
    patternsTitleForSample: (n) => `Điểm chung ${n} clip đi đúng hướng nội dung`,
    actionsTitle: "Biến hướng này thành outline tuần tới",
  };
}

function subnichePattern(): PatternSectionLabels {
  return {
    ...DEFAULT_PATTERN,
    tldrTitle: "Ảnh hưởng theo từng mảng nội dung con",
    findingsKicker: "Bằng chứng · theo mảng",
    findingsTitle: "Góc thắng trong từng mảng nội dung con",
    stalledTitle: "Mảng nội dung đang chững — hook hoặc đề tài cần làm mới",
    evidenceTitleForCount: (count) => `${count} clip ví dụ theo từng mảng`,
    evidenceKicker: "Video theo mảng nội dung",
    patternsTitleForSample: (n) => `Đặc điểm chung giữa ${n} clip qua các mảng nội dung`,
    actionsTitle: "Chọn mảng nội dung và thử góc tiếp theo",
  };
}

function fatiguePattern(): PatternSectionLabels {
  return {
    ...DEFAULT_PATTERN,
    tldrTitle: "Vì sao lượt xem đang giảm / bão hòa",
    findingsKicker: "Vẫn còn đất",
    findingsTitle: "Hook hoặc định dạng vẫn giữ được (nếu có trong dữ liệu)",
    stalledKicker: "Đang mệt hook / format",
    stalledTitle: "Góc lặp lại quá nhiều — khán giả không còn tò mò",
    evidenceKicker: "Minh chứng",
    evidenceTitleForCount: (count) => `${count} clip gợi ý dấu hiệu bão hòa / nhàm chán`,
    patternsKicker: "Dấu hiệu",
    patternsTitleForSample: (n) => `Trùng lặp và bão hòa trong ${n} clip gần đây`,
    actionsTitle: "Làm mới hook và dàn cảnh",
  };
}

/** UI labels for `payload.kind === "pattern"` from session `intent_type`. */
export function patternLabelsForSessionIntent(intent: string | undefined): PatternSectionLabels {
  switch (intent) {
    case "trend_spike":
      return spikePattern();
    case "content_directions":
      return directionsPattern();
    case "subniche_breakdown":
      return subnichePattern();
    case "fatigue":
      return fatiguePattern();
    default:
      return DEFAULT_PATTERN;
  }
}

/** `AnswerBlock` kicker when payload is pattern-shaped. */
export function patternAnswerBlockKicker(intent: string | undefined): string {
  switch (intent) {
    case "trend_spike":
      return "Xu hướng nóng";
    case "content_directions":
      return "Hướng nội dung";
    case "subniche_breakdown":
      return "Mảng nội dung con";
    case "fatigue":
      return "Mệt hook";
    default:
      return "Xu hướng";
  }
}

/** Lead + list chrome for ideas / brief_generation. */
export function ideasLeadAndSectionTitles(args: {
  variant: "hook_variants" | "standard";
  sessionIntentType: string | undefined;
}): { leadTitle: string; sectionKicker: string; ideasHeading: string } {
  const { variant, sessionIntentType } = args;
  if (variant === "hook_variants") {
    return {
      leadTitle: "Hook cho mảng nội dung",
      sectionKicker: "Biến thể hook",
      ideasHeading: "5 biến thể hook",
    };
  }
  if (sessionIntentType === "brief_generation") {
    return {
      leadTitle: "Brief ngắn cho lượt quay",
      sectionKicker: "Ý chính trong brief",
      ideasHeading: "Nội dung ưu tiên",
    };
  }
  return {
    leadTitle: "Tóm tắt",
    sectionKicker: "3 video tiếp theo",
    ideasHeading: "Lịch quay tuần này",
  };
}

export function ideasAnswerBlockKicker(sessionIntentType: string | undefined): string {
  return sessionIntentType === "brief_generation" ? "Brief sản xuất" : "Ý tưởng";
}

export function timingHeadlineKickers(sessionIntentType: string | undefined): {
  left: string;
  right: string;
} {
  if (sessionIntentType === "content_calendar") {
    return { left: "Ưu tiên đăng", right: "3 khung tốt nhất" };
  }
  return { left: "Sướng nhất", right: "3 cửa sổ cao nhất" };
}

export function timingAnswerBlockKicker(sessionIntentType: string | undefined): string {
  return sessionIntentType === "content_calendar" ? "Lịch đăng" : "Thời điểm";
}

export function timingActionsSectionTitle(sessionIntentType: string | undefined): string {
  return sessionIntentType === "content_calendar"
    ? "Gắn khung giờ vào lịch đăng"
    : "Biến khung giờ thành lịch quay";
}
