/**
 * Shared TypeScript interfaces for GetViews.vn
 * Extended during /foundation and /feature phases
 */

export type IntentType =
  | "video_diagnosis"
  | "content_directions"
  | "competitor_profile"
  | "soi_kenh"
  | "brief_generation"
  | "trend_spike"
  | "find_creators"
  | "follow_up";

export type CreditTier = "free" | "starter" | "pro" | "agency";

export interface UserProfile {
  id: string;
  email: string;
  display_name: string | null;
  primary_niche: string | null;
  inferred_niche: string | null;
  tier: CreditTier;
  deep_credits_remaining: number;
  deep_credits_total: number;
  daily_free_queries: number;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  intent_type: IntentType | null;
  credits_used: number;
  created_at: string;
}

export interface CorpusVideo {
  id: string;
  video_id: string;
  niche_id: number;
  hook_type: string | null;
  face_appears_at: number | null;
  text_overlays: string[] | null;
  pacing_score: number | null;
  engagement_rate: number | null;
  view_count: number;
  creator_handle: string | null;
  tiktok_url: string;
  frame_url: string | null;
  indexed_at: string;
}
