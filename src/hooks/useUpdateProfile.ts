import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { updateProfile, type ProfilePatch } from "@/lib/data/profile";
import { queryKeys } from "@/lib/query-keys";

export function useUpdateProfile() {
  const { session } = useAuth();
  const userId = session?.user.id ?? "";
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (patch: ProfilePatch) => {
      if (!userId) throw new Error("Chưa đăng nhập");
      return updateProfile(userId, patch);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.profile(userId) });
    },
  });
}
