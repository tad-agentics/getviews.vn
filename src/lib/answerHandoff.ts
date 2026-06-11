import { scriptPrefillFromQueryParams } from "./scriptPrefill";

/** §3.1 — shared `/app/answer` entry query contract (incremental v1 Wave 1). */

export type AnswerHandoffMode = "win" | "flop";

export type AnswerHandoffParams = {
  q: string;
  mode?: AnswerHandoffMode;
  from?: string;
};

export type ParsedAnswerHandoff = {
  mode: AnswerHandoffMode | null;
  from: string | null;
};

export function buildAnswerHandoffPath({ q, mode, from }: AnswerHandoffParams): string {
  const params = new URLSearchParams();
  params.set("q", q);
  if (mode) params.set("mode", mode);
  if (from) params.set("from", from);
  return `/app/answer?${params.toString()}`;
}

export function parseAnswerHandoffParams(
  searchParams: URLSearchParams,
): ParsedAnswerHandoff {
  const modeRaw = searchParams.get("mode");
  const mode: AnswerHandoffMode | null =
    modeRaw === "win" || modeRaw === "flop" ? modeRaw : null;
  const from = searchParams.get("from")?.trim() || null;
  return { mode, from };
}

/** Resolve TikTok URL/`q` when `?q=` is absent (session-only URLs). */
export function resolveVideoHandoffQuery(options: {
  seedQ?: string | null;
  sessionInitialQ?: string | null;
  videoId?: string | null;
  creatorHandle?: string | null;
}): string | null {
  const fromSeed = options.seedQ?.trim();
  if (fromSeed) return fromSeed;
  const fromSession = options.sessionInitialQ?.trim();
  if (fromSession) return fromSession;
  const vid = String(options.videoId ?? "").trim();
  if (!vid) return null;
  const raw = String(options.creatorHandle ?? "").trim();
  if (raw) {
    const handle = raw.startsWith("@") ? raw.slice(1) : raw;
    if (handle) return `https://www.tiktok.com/@${handle}/video/${vid}`;
  }
  return `https://www.tiktok.com/video/${vid}`;
}

/** Trends / kho video — corpus-hit win path entry. */
export function trendsVideoHandoffPath(q: string): string {
  return buildAnswerHandoffPath({ q, mode: "win", from: "trends" });
}

/** Inherit mode from current Answer URL when drilling from evidence tiles. */
export function inheritHandoffFromSearch(
  searchParams: URLSearchParams,
  q: string,
  from?: string,
): string {
  const { mode } = parseAnswerHandoffParams(searchParams);
  return buildAnswerHandoffPath({
    q,
    mode: mode ?? "win",
    from: from ?? searchParams.get("from") ?? undefined,
  });
}

/** Redirect target for deprecated ``/app/script`` — always Answer composer prefill. */
export function scriptRouteRedirectPath(searchParams: URLSearchParams): string {
  return scriptPrefillFromQueryParams(searchParams) ?? "/app/answer";
}

/** Redirect legacy shoot route → Answer in-session shoot panel. */
export function scriptShootRedirectPath(
  draftId: string,
  searchParams: URLSearchParams,
): string {
  const params = new URLSearchParams();
  const session = searchParams.get("session") ?? searchParams.get("session_id");
  if (session) params.set("session", session);
  params.set("shoot", draftId);
  return `/app/answer?${params.toString()}`;
}
