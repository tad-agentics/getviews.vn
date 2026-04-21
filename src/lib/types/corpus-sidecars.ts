/**
 * Shared shapes for corpus-backed UI tiles (thumbnail analysis, comment radar).
 * Used by VideoAnalyzeResponse, answer structured_output, and tile components.
 */

export type ThumbnailDominantElement = "face" | "product" | "text" | "environment";
export type ThumbnailFacialExpression =
  | "neutral"
  | "surprised"
  | "confused"
  | "smiling"
  | "focused";
export type ThumbnailColourContrast = "high" | "medium" | "low";

export type ThumbnailAnalysisData = {
  stop_power_score: number;
  dominant_element: ThumbnailDominantElement;
  text_on_thumbnail: string | null;
  facial_expression: ThumbnailFacialExpression | null;
  colour_contrast: ThumbnailColourContrast;
  why_it_stops: string;
};

export type CommentRadarData = {
  sampled: number;
  total_available: number;
  sentiment: {
    positive_pct: number;
    negative_pct: number;
    neutral_pct: number;
  };
  purchase_intent: {
    count: number;
    top_phrases: string[];
  };
  questions_asked: number;
  language: "vi" | "mixed" | "non-vi" | "unknown";
};
