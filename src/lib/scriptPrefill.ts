import type { RitualScript } from "@/hooks/useDailyRitual";
import type { TopPattern } from "@/hooks/useTopPatterns";

function answerComposerPath(message: string): string {
  const q = message.trim();
  return `/app/answer?q=${encodeURIComponent(q)}`;
}

function appendHookAndDurationLines(
  parts: string[],
  hook: string | null | undefined,
  durationSec: number | null | undefined,
) {
  const h = hook?.trim();
  if (h) parts.push(`Góc hook: ${h}.`);
  if (durationSec != null && Number.isFinite(durationSec) && durationSec > 0) {
    parts.push(`Độ dài: ${Math.round(durationSec)} giây.`);
  }
}

/** Path + query for Studio → answer composer (``shot_list`` → script report). */
export function scriptPrefillFromRitual(script: RitualScript, _nicheId: number): string {
  const parts: string[] = [`Viết kịch bản TikTok cho chủ đề: ${script.title_vi.trim()}.`];
  const hookLabel = script.hook_type_vi?.trim() || script.hook_type_en?.trim();
  appendHookAndDurationLines(parts, hookLabel || null, script.length_sec ?? null);
  if (script.sound_name?.trim()) {
    parts.push(`Nhạc nền gợi ý: ${script.sound_name.trim()}.`);
  }
  return answerComposerPath(parts.join(" "));
}

/** Path + query from channel analysis (formula CTA). */
export function scriptPrefillFromChannel(data: {
  niche_id: number;
  name: string;
  handle: string;
  top_hook: string | null;
}): string {
  const name = data.name?.trim() || `@${data.handle.trim() || "kênh"}`;
  const parts = [`Viết kịch bản TikTok theo công thức · ${name}.`];
  appendHookAndDurationLines(parts, data.top_hook, null);
  return answerComposerPath(parts.join(" "));
}

/**
 * Path + query for Studio script from a Trends pattern formula.
 */
export function scriptPrefillFromPattern(pattern: TopPattern, _nicheId: number): string {
  const hookLine = pattern.structure?.[0]
    ?.trim()
    ?.replace(/^(?:Mở|Hook)\s*[:：]\s*/i, "")
    .trim();
  const topic =
    hookLine || pattern.display_name?.trim() || "Công thức từ video viral";
  const hook = pattern.sample_hook?.trim() || pattern.display_name?.trim() || null;
  const parts = [`Viết kịch bản TikTok dựa trên công thức: ${topic.slice(0, 500)}.`];
  appendHookAndDurationLines(parts, hook, null);
  return answerComposerPath(parts.join(" "));
}

/** Path + query from a winning video analysis screen. */
export function scriptPrefillFromVideo(opts: {
  niche_id?: number | null;
  topic: string;
  hook?: string | null;
  duration_sec?: number | null;
}): string {
  const topic = opts.topic.trim().slice(0, 500) || "Kịch bản từ video";
  const parts = [`Viết kịch bản TikTok cho: ${topic}.`];
  appendHookAndDurationLines(parts, opts.hook, opts.duration_sec ?? null);
  return answerComposerPath(parts.join(" "));
}

/** Deeplink params from legacy ``/app/script?topic=&hook=&duration=`` or channel formula. */
export function scriptPrefillFromDeeplink(opts: {
  topic?: string | null;
  hook?: string | null;
  duration_sec?: number | null;
  prefill_handle?: string | null;
  prefill_format?: string | null;
}): string | null {
  const handle = opts.prefill_handle?.trim().replace(/^@/, "");
  const fmt = opts.prefill_format?.trim();
  if (handle || fmt) {
    const name = handle ? `@${handle}` : "kênh";
    const formatLabel = fmt || "format chính";
    return answerComposerPath(
      `Viết kịch bản TikTok theo format ${formatLabel} cho ${name}.`,
    );
  }
  const topic = opts.topic?.trim();
  const hook = opts.hook?.trim();
  const dur = opts.duration_sec;
  if (!topic && !hook && (dur == null || !Number.isFinite(dur))) {
    return null;
  }
  const parts = topic
    ? [`Viết kịch bản TikTok cho: ${topic.slice(0, 500)}.`]
    : ["Viết kịch bản TikTok."];
  appendHookAndDurationLines(parts, hook || null, dur ?? null);
  return answerComposerPath(parts.join(" "));
}

/** Map legacy ``/app/script`` query params → Answer composer ``?q=`` prefill. */
export function scriptPrefillFromQueryParams(params: URLSearchParams): string | null {
  const durationRaw = params.get("duration");
  const durationParsed =
    durationRaw != null && durationRaw.trim()
      ? Number.parseInt(durationRaw, 10)
      : null;
  return scriptPrefillFromDeeplink({
    topic: params.get("topic"),
    hook: params.get("hook"),
    duration_sec:
      durationParsed != null && Number.isFinite(durationParsed) ? durationParsed : null,
    prefill_handle: params.get("prefill_handle"),
    prefill_format: params.get("prefill_format"),
  });
}
