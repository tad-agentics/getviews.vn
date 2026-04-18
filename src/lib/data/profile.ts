import { supabase } from "@/lib/supabase";

export interface ProfilePatch {
  primary_niche?: number | null;
  // profiles.niche_id was dropped in migration 0017 — do NOT add it back.
  // The supported niche column is primary_niche.
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
