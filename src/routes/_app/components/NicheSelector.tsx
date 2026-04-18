import { useState } from "react";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import { useUpdateProfile } from "@/hooks/useUpdateProfile";
import { useProfile } from "@/hooks/useProfile";
import { Kicker } from "@/components/v2/Kicker";
import { ReferenceChannelsStep } from "./ReferenceChannelsStep";

/**
 * Onboarding entry point — 2-step flow:
 *   step "niche"      → pick primary_niche (existing behaviour)
 *   step "references" → pick 0–3 reference channels (new in A3.1)
 *
 * Mounted from ChatScreen when profile.primary_niche is null. Once the user
 * has a niche, the "references" step runs *only* if they haven't set any
 * handles yet — subsequent sessions skip the wizard entirely.
 */

type Step = "niche" | "references" | "done";

export function NicheSelector({ userId: _userId }: { userId: string }) {
  const { data: profile } = useProfile();
  const { data: niches, isPending, error } = useNicheTaxonomy();
  const save = useUpdateProfile();

  // Start at the earliest step the user hasn't completed. Reference step is
  // skipped if the user already has handles stored.
  const [step, setStep] = useState<Step>(() => {
    if (!profile?.primary_niche) return "niche";
    const handles = (profile as { reference_channel_handles?: string[] })
      .reference_channel_handles;
    if (!handles || handles.length === 0) return "references";
    return "done";
  });

  if (step === "done") return null;

  if (step === "references") {
    return (
      <ReferenceChannelsStep
        onDone={() => setStep("done")}
        onBack={() => setStep("niche")}
      />
    );
  }

  // step === "niche"
  if (isPending) {
    return (
      <p className="text-sm text-[color:var(--gv-ink-4)]">Đang tải danh sách ngách…</p>
    );
  }
  if (error) {
    return (
      <p className="text-sm text-[color:var(--gv-neg-deep)]">
        Không tải được danh sách ngách.
      </p>
    );
  }

  return (
    <div className="rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
      <Kicker>BƯỚC 1 / 2</Kicker>
      <h2
        className="gv-tight mt-2 text-[22px] leading-tight text-[color:var(--gv-ink)]"
        style={{ fontFamily: "var(--gv-font-display)" }}
      >
        Bạn đang làm việc với{" "}
        <em className="gv-serif-italic text-[color:var(--gv-accent)]">ngách</em>{" "}
        nào?
      </h2>
      <p className="mt-2 text-sm leading-snug text-[color:var(--gv-ink-3)]">
        Mọi gợi ý sẽ được neo theo ngách này. Bạn có thể đổi bất cứ lúc nào trong Cài đặt.
      </p>
      <div className="mt-4 flex max-h-[260px] flex-wrap gap-2 overflow-y-auto">
        {(niches ?? []).map((n) => (
          <button
            key={n.id}
            type="button"
            disabled={save.isPending}
            onClick={async () => {
              await save.mutateAsync({ primary_niche: n.id });
              setStep("references");
            }}
            className="rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-3 py-2 text-xs font-semibold text-[color:var(--gv-ink)] transition-colors duration-[120ms] hover:border-[color:var(--gv-ink)] disabled:opacity-50"
          >
            {n.name}
          </button>
        ))}
      </div>
    </div>
  );
}
