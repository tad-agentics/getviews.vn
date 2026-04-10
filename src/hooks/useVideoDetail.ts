import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { corpusKeys } from "./useVideoCorpus";

export function useVideoDetail(videoId: string | null) {
  return useQuery({
    queryKey: corpusKeys.detail(videoId ?? ""),
    queryFn: async () => {
      const { data, error } = await supabase.from("video_corpus").select("*").eq("id", videoId!).single();
      if (error) throw error;
      return data;
    },
    enabled: !!videoId,
    staleTime: 10 * 60_000,
  });
}
