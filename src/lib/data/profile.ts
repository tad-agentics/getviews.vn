import { supabase } from "@/lib/supabase";

export interface ProfilePatch {
  primary_niche?: string | null;
  niche_id?: number | null;
  tiktok_handle?: string | null;
  display_name?: string;
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
