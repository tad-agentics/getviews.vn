import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { updateProfile, type ProfilePatch } from "@/lib/data/profile";
import { queryKeys } from "@/lib/query-keys";
import type { ProfileRow } from "@/hooks/useProfile";

export function useUpdateProfile() {
  const { session } = useAuth();
  const userId = session?.user.id ?? "";
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (patch: ProfilePatch) => {
      if (!userId) throw new Error("Chưa đăng nhập");
      return updateProfile(userId, patch);
    },
    onMutate: async (patch) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.profile(userId) });
      const previous = queryClient.getQueryData<ProfileRow | null>(queryKeys.profile(userId));
      if (previous) {
        queryClient.setQueryData<ProfileRow | null>(queryKeys.profile(userId), {
          ...previous,
          ...patch,
        });
      }
      return { previous };
    },
    onError: (_err, _patch, context) => {
      if (context?.previous !== undefined) {
        queryClient.setQueryData(queryKeys.profile(userId), context.previous);
      }
    },
    onSuccess: (_data, patch) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.profile(userId) });
      if (patch.primary_niche !== undefined) {
        void queryClient.invalidateQueries({ queryKey: ["daily_ritual"] });
      }
    },
  });
}
