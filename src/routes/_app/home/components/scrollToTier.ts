/**
 * Studio Home — scroll to a tier anchor on HomeSuggestionsToday (PR-4).
 *
 * The design pack's MyChannelCard exposes two ways to jump from the
 * channel diagnostic into the GỢI Ý HÔM NAY stack:
 *   • per-item bridge pill ("→ 01" / "→ 02") on each strength/weakness
 *   • the bottom "Xem gợi ý ↓" ribbon
 *
 * Both call this helper. We rely on plain ``document.querySelector`` so
 * the channel section doesn't need a ref to the suggestions section
 * (different parent in HomeScreen) — DOM lookup keeps the components
 * loosely coupled.
 */

export type SuggestionsTier = "01" | "02" | "03";

export function scrollToSuggestionsTier(
  tier: SuggestionsTier,
  options: ScrollIntoViewOptions = { behavior: "smooth", block: "start" },
): boolean {
  if (typeof document === "undefined") return false;
  const target = document.querySelector(`[data-tier="${tier}"]`);
  if (!target) return false;
  target.scrollIntoView(options);
  return true;
}
