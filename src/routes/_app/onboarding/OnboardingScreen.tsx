import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { ArrowLeft } from "lucide-react";
import { Btn } from "@/components/v2/Btn";
import { useProfile } from "@/hooks/useProfile";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import { useTopNiches } from "@/hooks/useTopNiches";
import { useUpdateProfile } from "@/hooks/useUpdateProfile";
import { ReferenceChannelsStep } from "@/routes/_app/components/ReferenceChannelsStep";
import {
  MAX_CREATOR_NICHES,
  MIN_CREATOR_NICHES,
  normalizeNicheIds,
  profileHasMinimumNiches,
} from "@/lib/profileNiches";

/**
 * Full-bleed onboarding (Phase A · A3.5) — matches the design bundle:
 * split-screen with editorial left column + form right column. Two steps:
 *   0 — pick ít nhất 3 ngách (niche_ids + primary_niche = first)
 *   1 — pick 1–3 kênh tham chiếu (reference_channel_handles)
 *
 * Rendered at /app/onboarding, OUTSIDE the AppLayout shell. The index
 * route sends new creators here until profileHasMinimumNiches is satisfied.
 */
export default function OnboardingScreen() {
  const navigate = useNavigate();
  const { data: profile, isPending: profilePending } = useProfile();
  const save = useUpdateProfile();
  const {
    data: taxonomy,
    isPending: taxonomyPending,
    isError: taxonomyError,
    refetch: refetchTaxonomy,
  } = useNicheTaxonomy();

  const [step, setStep] = useState<0 | 1>(0);
  const [pendingNiches, setPendingNiches] = useState<number[]>([]);
  const didInitFromProfile = useRef(false);

  const primaryForOrdering =
    pendingNiches[0] ??
    (typeof profile?.primary_niche === "number" ? profile.primary_niche : null);
  const { data: topNiches } = useTopNiches(primaryForOrdering, "all");

  const niches = useMemo(() => {
    const hotBy = new Map<number, number>();
    for (const n of topNiches ?? []) hotBy.set(n.id, n.hot);
    return (taxonomy ?? []).map((t) => ({ id: t.id, name: t.name, hot: hotBy.get(t.id) ?? 0 }));
  }, [taxonomy, topNiches]);

  useEffect(() => {
    if (profilePending) return;
    if (didInitFromProfile.current) return;
    didInitFromProfile.current = true;
    if (profileHasMinimumNiches(profile)) {
      const ids = profile?.niche_ids;
      if (Array.isArray(ids) && ids.length >= MIN_CREATOR_NICHES) {
        setPendingNiches(normalizeNicheIds(ids));
      } else if (profile?.primary_niche != null) {
        setPendingNiches([profile.primary_niche]);
      }
      setStep(1);
      return;
    }
    const ids = profile?.niche_ids;
    if (Array.isArray(ids) && ids.length > 0) {
      setPendingNiches(normalizeNicheIds(ids));
    } else if (profile?.primary_niche != null) {
      setPendingNiches([profile.primary_niche]);
    }
  }, [profilePending, profile]);

  const togglePendingNiche = (id: number) => {
    setPendingNiches((prev) => {
      const set = new Set(prev);
      if (set.has(id)) {
        set.delete(id);
        return Array.from(set);
      }
      if (prev.length >= MAX_CREATOR_NICHES) return prev;
      set.add(id);
      return Array.from(set);
    });
  };

  const onNicheStepContinue = async () => {
    const ids = normalizeNicheIds(pendingNiches);
    if (ids.length < MIN_CREATOR_NICHES) return;
    await save.mutateAsync({ niche_ids: ids, primary_niche: ids[0] });
    setStep(1);
  };

  const goHome = () => navigate("/app");

  if (profilePending) {
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-[color:var(--gv-canvas)]"
        role="status"
        aria-label="Đang tải"
      >
        <p className="text-sm text-[color:var(--gv-ink-4)]">Đang tải hồ sơ…</p>
      </div>
    );
  }

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
          "Chọn ít nhất 3 ngách bạn quan tâm — studio sẽ cá nhân hóa xu hướng, hook và sound theo từng ngách.",
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
          {step === 0 && taxonomyError ? (
            <div className="rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5 text-center">
              <p className="mb-4 text-sm text-[color:var(--gv-ink-3)]">Không tải được danh sách ngách.</p>
              <Btn type="button" variant="ink" size="sm" onClick={() => void refetchTaxonomy()}>
                Thử lại
              </Btn>
            </div>
          ) : null}
          {step === 0 && !taxonomyError && taxonomyPending ? (
            <p className="text-sm text-[color:var(--gv-ink-4)]">Đang tải danh sách ngách…</p>
          ) : null}
          {step === 0 && !taxonomyError && !taxonomyPending && niches.length === 0 ? (
            <p className="text-sm text-[color:var(--gv-ink-3)]">Chưa có ngách trong hệ thống. Liên hệ hỗ trợ.</p>
          ) : null}
          {step === 0 && !taxonomyError && !taxonomyPending && niches.length > 0 ? (
            <>
              <NicheGrid
                niches={niches}
                selectedIds={pendingNiches}
                disabled={save.isPending}
                onToggle={togglePendingNiche}
              />
              <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-[12px] text-[color:var(--gv-ink-4)]">
                  Đã chọn{" "}
                  <span className="font-medium text-[color:var(--gv-ink)]">{pendingNiches.length}</span> /{" "}
                  {MIN_CREATOR_NICHES} tối thiểu
                  {pendingNiches.length >= MAX_CREATOR_NICHES ? (
                    <span className="ml-1">(tối đa {MAX_CREATOR_NICHES})</span>
                  ) : null}
                </p>
                <Btn
                  type="button"
                  variant="ink"
                  size="sm"
                  disabled={pendingNiches.length < MIN_CREATOR_NICHES || save.isPending}
                  onClick={() => void onNicheStepContinue()}
                >
                  Tiếp tục
                </Btn>
              </div>
            </>
          ) : null}
          {step === 1 ? (
            <ReferenceChannelsStep
              onDone={goHome}
              onBack={() => setStep(0)}
            />
          ) : null}

          {/* Footer: back / progress pills / CTA (step 0 only; step 1 owns its own footer) */}
          {step === 0 && !taxonomyError && !taxonomyPending && niches.length > 0 ? (
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
  selectedIds,
  disabled,
  onToggle,
}: {
  niches: ReadonlyArray<{ id: number; name: string; hot: number }>;
  selectedIds: readonly number[];
  disabled: boolean;
  onToggle: (id: number) => void;
}) {
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);
  return (
    <div>
      <p className="gv-mono text-[9px] uppercase tracking-[0.18em] text-[color:var(--gv-ink-4)] mb-3.5">
        NGÁCH CỦA BẠN (CHỌN {MIN_CREATOR_NICHES}–{MAX_CREATOR_NICHES})
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {niches.map((n) => {
          const selected = selectedSet.has(n.id);
          const isFocus = selectedIds[0] === n.id;
          return (
            <button
              key={n.id}
              type="button"
              disabled={disabled}
              onClick={() => onToggle(n.id)}
              className={
                "flex items-center justify-between gap-3 rounded-[8px] px-4 py-3.5 text-left text-sm transition-colors " +
                (selected
                  ? "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)] border border-[color:var(--gv-ink)]"
                  : "bg-[color:var(--gv-paper)] text-[color:var(--gv-ink)] border border-[color:var(--gv-rule)] hover:border-[color:var(--gv-ink-4)]")
              }
            >
              <span className="truncate">
                {n.name}
                {isFocus && selectedIds.length >= MIN_CREATOR_NICHES ? (
                  <span className="ml-1.5 gv-mono text-[9px] uppercase tracking-wider opacity-70">
                    · trọng tâm
                  </span>
                ) : null}
              </span>
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
      <p className="mt-3 text-[11px] text-[color:var(--gv-ink-4)]">
        Nhấn lần đầu để chọn. Ngách chọn đầu tiên là ngách trọng tâm — đổi thứ tự bằng cách bỏ chọn rồi chọn lại theo thứ tự mong muốn.
      </p>
    </div>
  );
}
