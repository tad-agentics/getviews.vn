import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { ArrowLeft } from "lucide-react";
import { Btn } from "@/components/v2/Btn";
import { useProfile } from "@/hooks/useProfile";
import { useTopNiches } from "@/hooks/useTopNiches";
import { useUpdateProfile } from "@/hooks/useUpdateProfile";
import { ReferenceChannelsStep } from "@/routes/_app/components/ReferenceChannelsStep";

/**
 * Full-bleed onboarding (Phase A · A3.5) — matches the design bundle:
 * split-screen with editorial left column + form right column. Two steps:
 *   0 — pick ngách (primary_niche)
 *   1 — pick 1–3 kênh tham chiếu (reference_channel_handles)
 *
 * Rendered at /app/onboarding, OUTSIDE the AppLayout shell. The index
 * route sends new creators here when primary_niche is unset.
 */
export default function OnboardingScreen() {
  const navigate = useNavigate();
  const { data: profile } = useProfile();
  const save = useUpdateProfile();
  const { data: niches = [] } = useTopNiches(profile?.primary_niche ?? null, 24);

  const [step, setStep] = useState<0 | 1>(profile?.primary_niche ? 1 : 0);
  const [pendingNiche, setPendingNiche] = useState<number | null>(
    profile?.primary_niche ?? null,
  );

  const onNichePicked = async (id: number) => {
    setPendingNiche(id);
    await save.mutateAsync({ primary_niche: id });
    setStep(1);
  };

  const goHome = () => navigate("/app");

  const leftCopy = useMemo(() => {
    if (step === 0) {
      return {
        h1: (
          <>
            Bạn đang làm việc với{" "}
            <em className="gv-serif-italic text-[color:var(--gv-accent)]">ngách</em>{" "}
            nào?
          </>
        ),
        caption:
          "Chúng tôi sẽ tải về dữ liệu 14 ngày gần nhất của ngách đó — xu hướng, hook, sound, và creator đang nổi.",
      };
    }
    return {
      h1: (
        <>
          Ai là{" "}
          <em className="gv-serif-italic text-[color:var(--gv-accent)]">
            đối thủ tham chiếu
          </em>{" "}
          của bạn?
        </>
      ),
      caption:
        "Chọn 1–3 kênh. Studio sẽ tự cập nhật khi họ post bài mới và so sánh hiệu suất với kênh của bạn.",
    };
  }, [step]);

  return (
    <div className="flex min-h-screen bg-[color:var(--gv-canvas)]">
      {/* Left column — editorial — hidden on mobile */}
      <aside className="hidden md:flex flex-1 flex-col justify-between border-r border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-[60px] py-[60px]">
        <p className="gv-mono text-[10px] uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
          GETVIEWS · CREATOR STUDIO · SỐ 01
        </p>

        <div>
          <p className="gv-mono text-[10px] uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)] mb-4">
            BƯỚC 0{step + 1} / 02
          </p>
          <h1
            className="gv-tight text-[64px] leading-[0.95] text-[color:var(--gv-ink)]"
            style={{ fontFamily: "var(--gv-font-display)", letterSpacing: "-0.04em" }}
          >
            {leftCopy.h1}
          </h1>
          <p className="mt-[18px] max-w-[420px] text-base leading-snug text-[color:var(--gv-ink-3)]">
            {leftCopy.caption}
          </p>
        </div>

        <p className="gv-mono inline-flex items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-[color:var(--gv-accent)]" />
          CREATOR STUDIO · MẤT ~45 GIÂY
        </p>
      </aside>

      {/* Right column — form */}
      <section className="flex flex-1 flex-col justify-center px-6 py-12 md:px-[60px] md:py-[60px]">
        <div className="w-full max-w-[640px] mx-auto">
          {step === 0 ? (
            <NicheGrid
              niches={niches}
              selectedId={pendingNiche}
              disabled={save.isPending}
              onPick={onNichePicked}
            />
          ) : (
            <ReferenceChannelsStep
              onDone={goHome}
              onBack={() => setStep(0)}
            />
          )}

          {/* Footer: back / progress pills / CTA (step 0 only; step 1 owns its own footer) */}
          {step === 0 ? (
            <div className="mt-9 flex items-center justify-between">
              <Btn
                type="button"
                variant="ghost"
                size="sm"
                onClick={goHome}
              >
                <ArrowLeft className="h-3.5 w-3.5" strokeWidth={1.7} />
                Quay lại
              </Btn>
              <ProgressPills step={step} />
              <div className="gv-mono text-[10px] uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
                01 / 02
              </div>
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}

function ProgressPills({ step }: { step: 0 | 1 }) {
  return (
    <div className="flex items-center gap-1.5">
      {[0, 1].map((i) => (
        <span
          key={i}
          aria-hidden="true"
          className={
            "block h-1 w-9 rounded-full " +
            (i <= step ? "bg-[color:var(--gv-accent)]" : "bg-[color:var(--gv-rule)]")
          }
        />
      ))}
    </div>
  );
}

function NicheGrid({
  niches,
  selectedId,
  disabled,
  onPick,
}: {
  niches: ReadonlyArray<{ id: number; name: string; hot: number }>;
  selectedId: number | null;
  disabled: boolean;
  onPick: (id: number) => void;
}) {
  return (
    <div>
      <p className="gv-mono text-[9px] uppercase tracking-[0.18em] text-[color:var(--gv-ink-4)] mb-3.5">
        NGÁCH CHÍNH
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {niches.map((n) => {
          const selected = n.id === selectedId;
          return (
            <button
              key={n.id}
              type="button"
              disabled={disabled}
              onClick={() => onPick(n.id)}
              className={
                "flex items-center justify-between gap-3 rounded-[8px] px-4 py-3.5 text-left text-sm transition-colors " +
                (selected
                  ? "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)] border border-[color:var(--gv-ink)]"
                  : "bg-[color:var(--gv-paper)] text-[color:var(--gv-ink)] border border-[color:var(--gv-rule)] hover:border-[color:var(--gv-ink-4)]")
              }
            >
              <span className="truncate">{n.name}</span>
              <span
                className={
                  "gv-mono text-[10px] " +
                  (selected ? "opacity-60" : "text-[color:var(--gv-ink-4)]")
                }
              >
                {n.hot} video
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
