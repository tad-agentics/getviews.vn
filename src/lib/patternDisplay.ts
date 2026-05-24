import type { TopPattern } from "@/hooks/useTopPatterns";

const INVALID_HOOK_PHRASES = new Set([
  "none",
  "null",
  "n/a",
  "na",
  "unknown",
  "-",
  "—",
]);

/** Corpus / Gemini sometimes stores literal "none" — hide from UI. */
export function normalizeHookPhrase(raw: string | null | undefined): string | null {
  const t = raw?.trim();
  if (!t || t.length < 2) return null;
  if (INVALID_HOOK_PHRASES.has(t.toLowerCase())) return null;
  return t;
}

function cleanDeckHookLine(raw: string | null | undefined): string | null {
  const t = raw?.trim();
  if (!t) return null;
  return t.replace(/^(?:Mở|Hook)\s*[:：]\s*/i, "");
}

/** Recipe hook line (structure[0]) — Trends PatternCard headline. */
export function pickPatternHeadline(pattern: TopPattern): string {
  const first = cleanDeckHookLine(pattern.structure?.[0]);
  if (first) return first;
  return pattern.display_name?.trim() || "Pattern";
}

/**
 * Studio HooksTable MẪU HOOK — taxonomy formula label, enriched when the
 * bucket name alone is too vague (e.g. lone "Cận").
 */
export function pickPatternFormula(pattern: TopPattern): string {
  const name = pattern.display_name?.trim() || "Pattern";
  const hookLine = cleanDeckHookLine(pattern.structure?.[0]);
  if (!hookLine) return name;
  const nameLooksVague = name.length < 14 && !name.includes("+");
  if (nameLooksVague && hookLine.length > name.length) {
    return hookLine;
  }
  if (nameLooksVague && hookLine !== name) {
    return `${name} · ${hookLine}`;
  }
  return name;
}

export function formatCreatorHandle(handle: string | null | undefined): string | null {
  const t = handle?.trim();
  if (!t) return null;
  return t.startsWith("@") ? t : `@${t}`;
}

/** Ví dụ column — real hook line, else top creator, else deck ``why`` teaser. */
export function pickPatternExample(pattern: TopPattern): string | null {
  const hook = normalizeHookPhrase(pattern.sample_hook);
  if (hook) return hook;
  const handle = formatCreatorHandle(
    pattern.sample_creator_handle ?? pattern.videos[0]?.creator_handle,
  );
  if (handle) return `Video ${handle}`;
  const why = pattern.why?.trim();
  if (why) return why.length > 120 ? `${why.slice(0, 117)}…` : why;
  const deckHook = cleanDeckHookLine(pattern.structure?.[0]);
  if (deckHook && deckHook.length >= 8) return deckHook;
  return null;
}
