import type { RitualScript } from "@/hooks/useDailyRitual";
import type { TopPattern } from "@/hooks/useTopPatterns";

function appendHookAndDuration(
  qs: URLSearchParams,
  hook: string | null | undefined,
  durationSec: number | null | undefined,
) {
  const h = hook?.trim();
  if (h) qs.set("hook", h);
  if (durationSec != null && Number.isFinite(durationSec) && durationSec > 0) {
    qs.set("duration", String(Math.round(durationSec)));
  }
}

/** Path + query for Studio script from a daily ritual card + profile niche.
 * L2.2 Sprint 3 — when the ritual idea carries a Sound Radar
 * recommendation (``sound_id`` + ``sound_name``), pass both forward as
 * query params so the script studio can weave them into the brief.
 * Pre-Sprint-3 ritual rows have neither field; the URL just omits them. */
export function scriptPrefillFromRitual(script: RitualScript, nicheId: number): string {
  const qs = new URLSearchParams();
  qs.set("niche_id", String(nicheId));
  qs.set("topic", script.title_vi);
  const hookLabel = script.hook_type_vi?.trim() || script.hook_type_en?.trim();
  appendHookAndDuration(qs, hookLabel || null, script.length_sec);
  if (script.sound_id) qs.set("sound_id", script.sound_id);
  if (script.sound_name) qs.set("sound_name", script.sound_name);
  return `/app/script?${qs.toString()}`;
}

/** Path + query from channel analysis (formula CTA). */
export function scriptPrefillFromChannel(data: {
  niche_id: number;
  name: string;
  handle: string;
  top_hook: string | null;
}): string {
  const qs = new URLSearchParams();
  qs.set("niche_id", String(data.niche_id));
  const name = data.name?.trim() || `@${data.handle.trim() || "kênh"}`;
  qs.set("topic", `Kịch bản theo công thức · ${name}`);
  appendHookAndDuration(qs, data.top_hook, null);
  return `/app/script?${qs.toString()}`;
}

/**
 * Path + query for Studio script from a Trends pattern formula.
 *
 * L2.2 Sprint 6b — closes the discovery → action gap. Creator opens the
 * PatternModal, reads the deck, then taps "Áp dụng công thức này" — we
 * route them to ``/app/script`` with the formula identity (Hook line
 * from ``structure[0]``) as the topic and the most-viewed
 * ``sample_hook`` as the hook reference. The script studio then has
 * enough to draft a brief grounded in the pattern.
 *
 * Why ``structure[0]`` not ``display_name``:
 * ``display_name`` is the 7-attribute taxonomy bucket label
 * ("Hướng dẫn + mặt người"); not actionable as a topic. ``structure[0]``
 * is the deck-synthesized Hook line ("Mở: câu hỏi cá nhân (0-2s)") —
 * concrete recipe-shaped topic the script studio can build a brief
 * around.
 */
export function scriptPrefillFromPattern(
  pattern: TopPattern,
  nicheId: number,
): string {
  const qs = new URLSearchParams();
  qs.set("niche_id", String(nicheId));

  // Topic = the recipe headline (Hook line). Strip the leading "Mở:" /
  // "Hook:" tag the deck synth sometimes produces — same rule the card
  // headline applies — so the topic field reads as a clean sentence.
  const hookLine = pattern.structure?.[0]?.trim()
    ?.replace(/^(?:Mở|Hook)\s*[:：]\s*/i, "")
    .trim();
  const topic = hookLine || pattern.display_name?.trim() || "Công thức từ video viral";
  qs.set("topic", topic.slice(0, 500));

  // Hook reference = the most-viewed sample_hook in this pattern (a real
  // line a real creator used). Fallback to the bucket display_name —
  // less useful but still a hook signal for Gemini.
  const hook = pattern.sample_hook?.trim() || pattern.display_name?.trim() || null;
  appendHookAndDuration(qs, hook, null);

  return `/app/script?${qs.toString()}`;
}

/** Path + query from a winning video analysis screen. */
export function scriptPrefillFromVideo(opts: {
  /** When omitted (default for video → script), URL has no ``niche_id`` — ``ScriptScreen`` falls back to profile niche (``creator_niche_id`` → legacy row). */
  niche_id?: number | null;
  topic: string;
  hook?: string | null;
  duration_sec?: number | null;
}): string {
  const qs = new URLSearchParams();
  const nid = opts.niche_id;
  if (nid != null && Number.isFinite(nid) && nid > 0) {
    qs.set("niche_id", String(Math.trunc(nid)));
  }
  const topic = opts.topic.trim().slice(0, 500) || "Kịch bản từ video";
  qs.set("topic", topic);
  appendHookAndDuration(qs, opts.hook, opts.duration_sec ?? null);
  return `/app/script?${qs.toString()}`;
}
