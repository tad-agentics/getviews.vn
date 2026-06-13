import type { StreamStatus } from "@/hooks/useSessionStream";

/**
 * Inputs that drive whether the start/follow-up composer is shown, and the two
 * derived loading flags AnswerScreen reuses elsewhere (resume guard, reset).
 *
 * The SSE stream produces a report before the turn is persisted to the DB, so
 * naively keying the composer off `turnCount === 0` would flash the empty-state
 * composer over an in-flight (or just-finished-but-unsaved) stream. `done` with
 * zero turns is still "in flight" from the user's perspective until the detail
 * query refetches the persisted turn.
 */
export interface ComposerVisibilityInput {
  streamStatus: StreamStatus;
  turnCount: number;
  bootstrapLoading: boolean;
  hasSessionId: boolean;
  detailLoading: boolean;
  hasDetailData: boolean;
}

export interface ComposerVisibility {
  streamInFlight: boolean;
  loading: boolean;
  showStartComposer: boolean;
}

export function computeComposerVisibility({
  streamStatus,
  turnCount,
  bootstrapLoading,
  hasSessionId,
  detailLoading,
  hasDetailData,
}: ComposerVisibilityInput): ComposerVisibility {
  const streamInFlight =
    streamStatus === "streaming" || (streamStatus === "done" && turnCount === 0);

  const loading =
    bootstrapLoading ||
    streamInFlight ||
    (hasSessionId && detailLoading && !hasDetailData);

  const showStartComposer = turnCount === 0 && !loading;

  return { streamInFlight, loading, showStartComposer };
}
