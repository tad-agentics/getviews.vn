import { useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { queryKeys } from "@/lib/query-keys";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";

export function NicheSelector({ userId }: { userId: string }) {
  const qc = useQueryClient();
  const { data: niches, isPending, error } = useNicheTaxonomy();

  const save = useMutation({
    mutationFn: async (nicheId: number) => {
      const { error: e } = await supabase
        .from("profiles")
        .update({ primary_niche: String(nicheId) })
        .eq("id", userId);
      if (e) throw e;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.profile(userId) });
    },
  });

  if (isPending) {
    return <p className="text-sm text-[var(--muted)]">Đang tải niche...</p>;
  }
  if (error) {
    return <p className="text-sm text-[var(--danger)]">Không tải được danh sách niche.</p>;
  }

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <h2 className="mb-3 text-base font-extrabold text-[var(--ink)]">Bạn sáng tác content về chủ đề gì?</h2>
      <div className="flex max-h-[220px] flex-wrap gap-2 overflow-y-auto">
        {(niches ?? []).map((n) => (
          <button
            key={n.id}
            type="button"
            disabled={save.isPending}
            onClick={() => save.mutate(n.id)}
            className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2 text-xs font-semibold text-[var(--ink)] transition-colors duration-[120ms] hover:border-[var(--purple)] disabled:opacity-50"
          >
            {n.name}
          </button>
        ))}
      </div>
    </div>
  );
}
