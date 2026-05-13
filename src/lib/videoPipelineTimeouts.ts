/**
 * Mirrors defaults in ``cloud-run/getviews_pipeline/config.py``.
 *
 * - ``VIDEO_PIPELINE_ANALYSIS_HARD_TIMEOUT_MS`` — hard stall hint (e.g. LivePipelineStrip
 *   ``clientTimedOut``). Matches ``GEMINI_VIDEO_ANALYSIS_HARD_TIMEOUT_SEC`` (120s) so
 *   the UI does not surface “hết thời gian” *after* the server’s forensic cap when
 *   SSE/error delivery lags (previously 150s vs 120s).
 * - ``VIDEO_PIPELINE_SEQUENTIAL_HARD_CAP_MS`` — sum of download + extract + diagnosis
 *   caps (330s); reference if a future UI needs a longer ceiling for the full chain.
 */
export const VIDEO_PIPELINE_DOWNLOAD_TIMEOUT_SEC = 90;
export const VIDEO_PIPELINE_ANALYSIS_HARD_TIMEOUT_SEC = 120;
export const VIDEO_PIPELINE_DIAGNOSIS_HARD_TIMEOUT_SEC = 120;

/** Matches ``GEMINI_VIDEO_ANALYSIS_HARD_TIMEOUT_SEC`` default (single forensic extract cap). */
export const VIDEO_PIPELINE_ANALYSIS_HARD_TIMEOUT_MS =
  VIDEO_PIPELINE_ANALYSIS_HARD_TIMEOUT_SEC * 1000;

/** Sum of the three sequential caps — full ``analyze_aweme`` chain worst case (330s). */
export const VIDEO_PIPELINE_SEQUENTIAL_HARD_CAP_MS =
  (VIDEO_PIPELINE_DOWNLOAD_TIMEOUT_SEC +
    VIDEO_PIPELINE_ANALYSIS_HARD_TIMEOUT_SEC +
    VIDEO_PIPELINE_DIAGNOSIS_HARD_TIMEOUT_SEC) *
  1000;

/** First nudge when the stream is still loading (audit PERF-1). */
export const VIDEO_PIPELINE_SLOW_HINT_MS = 30_000;
