import { buildAnswerHandoffPath } from "@/lib/answerHandoff";
import { buildLoginPath } from "@/lib/postLoginRedirect";
import { nonTikTokUrlValidationMessage } from "@/lib/tiktokUrl";

export type LandingHeroSubmitResult =
  | { ok: true; loginPath: string }
  | { ok: false; error: string };

/** Shared path for hero form submit and sticky CTA (keeps pasted URL in ?next=). */
export function resolveLandingHeroSubmit(pasted: string): LandingHeroSubmitResult {
  const raw = pasted.trim();
  if (raw) {
    const invalid = nonTikTokUrlValidationMessage(raw);
    if (invalid) return { ok: false, error: invalid };
  }
  const next = raw ? buildAnswerHandoffPath({ q: raw, from: "landing" }) : undefined;
  return { ok: true, loginPath: buildLoginPath(next) };
}
