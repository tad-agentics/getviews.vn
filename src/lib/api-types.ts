// Shared TypeScript interfaces — single source of truth for all entity types.
// Re-export or extend from database.types.ts as needed.

export interface UserProfile {
  id: string;
  email: string;
  display_name: string | null;
  primary_niche: string | null;
  inferred_niche: string | null;
  created_at: string;
}

export interface Credits {
  user_id: string;
  deep_remaining: number;
  plan_tier: "free" | "starter" | "pro" | "agency";
  expires_at: string | null;
  unlimited_browse: boolean;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  user_id: string;
  role: "user" | "assistant";
  content: string;
  intent: IntentType | null;
  is_deep_query: boolean;
  created_at: string;
}

export type IntentType =
  | "video_diagnosis"
  | "content_directions"
  | "competitor_profile"
  | "soi_kenh"
  | "brief_generation"
  | "trend_spike"
  | "find_creators"
  | "followup";
