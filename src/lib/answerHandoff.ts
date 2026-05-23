import { scriptPrefillFromQueryParams } from "./scriptPrefill";

/** §3.1 — shared `/app/answer` entry query contract (incremental v1 Wave 1). */

export type AnswerHandoffDepth = "basic" | "deep";
export type AnswerHandoffMode = "win" | "flop";

export type AnswerHandoffParams = {
  q: string;
  depth?: AnswerHandoffDepth;
  mode?: AnswerHandoffMode;
  from?: string;
};

export type ParsedAnswerHandoff = {
  depth: AnswerHandoffDepth;
  mode: AnswerHandoffMode | null;
  from: string | null;
};

export function buildAnswerHandoffPath({
  q,
  depth = "basic",
  mode,
  from,
}: AnswerHandoffParams): string {
  const params = new URLSearchParams();
  params.set("q", q);
  params.set("depth", depth);
  if (mode) params.set("mode", mode);
  if (from) params.set("from", from);
  return `/app/answer?${params.toString()}`;
}

export function parseAnswerHandoffParams(
  searchParams: URLSearchParams,
): ParsedAnswerHandoff {
  const depthRaw = searchParams.get("depth");
  const depth: AnswerHandoffDepth = depthRaw === "deep" ? "deep" : "basic";
  const modeRaw = searchParams.get("mode");
  const mode: AnswerHandoffMode | null =
    modeRaw === "win" || modeRaw === "flop" ? modeRaw : null;
  const from = searchParams.get("from")?.trim() || null;
  return { depth, mode, from };
}

/** Resolve TikTok URL/`q` for depth upsell when `?q=` is absent (session-only URLs). */
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
  return buildAnswerHandoffPath({ q, depth: "basic", mode: "win", from: "trends" });
}

/** Inherit depth/mode from current Answer URL when drilling from evidence tiles. */
export function inheritHandoffFromSearch(
  searchParams: URLSearchParams,
  q: string,
  from?: string,
): string {
  const { depth, mode } = parseAnswerHandoffParams(searchParams);
  return buildAnswerHandoffPath({
    q,
    depth,
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
