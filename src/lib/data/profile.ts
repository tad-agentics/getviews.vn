import { supabase } from "@/lib/supabase";

export interface ProfilePatch {
  /** Single niche per user (PR1 of single-niche refactor — niche_ids array dropped). */
  primary_niche?: number | null;
  // profiles.niche_id was dropped in migration 0017 — do NOT add it back.
  tiktok_handle?: string | null;
  display_name?: string;
  /** 0–3 TikTok handles the creator tracks as "kênh tham chiếu". */
  reference_channel_handles?: string[];
}

export async function updateProfile(userId: string, patch: ProfilePatch) {
  const { data, error } = await supabase
    .from("profiles")
    .update({ ...patch, updated_at: new Date().toISOString() })
    .eq("id", userId)
    .select()
    .single();
  if (error) throw error;
  return data;
}
