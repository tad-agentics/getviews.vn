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
