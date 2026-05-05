import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { Btn } from "@/components/v2/Btn";
import { useProfile } from "@/hooks/useProfile";
import { useCreatorNiches, type CreatorNiche } from "@/hooks/useCreatorNiches";
import { useUpdateProfile } from "@/hooks/useUpdateProfile";
import { legacyNicheIdForCreatorNiche, profileHasNiche } from "@/lib/profileNiches";

/**
 * Onboarding — single-step single-niche pick (BƯỚC 01 / 01).
 *
 * Two-axis refactor PR4 (2026-05-10): picker now reads ``creator_niches``
 * (14 UX-facing buckets) instead of the legacy ``niche_taxonomy``. Save
 * dual-writes ``creator_niche_id`` (new canonical) AND ``primary_niche``
 * (legacy, via ``legacyNicheIdForCreatorNiche``) so Cloud Run /home/*
 * endpoints (still on primary_niche pre-PR5) keep working through the
 * transition.
 */

export default function OnboardingScreen() {
  const navigate = useNavigate();
  const { data: profile, isPending: profilePending } = useProfile();
  const save = useUpdateProfile();
  const {
    data: niches,
    isPending: nichesPending,
    isError: nichesError,
    refetch: refetchNiches,
  } = useCreatorNiches();

  const [pendingNiche, setPendingNiche] = useState<number | null>(null);
  const didInitFromProfile = useRef(false);

  useEffect(() => {
    if (profilePending) return;
    if (didInitFromProfile.current) return;
    didInitFromProfile.current = true;
    if (profileHasNiche(profile)) {
      // User already onboarded — bounce them back into the studio.
      navigate("/app", { replace: true });
      return;
    }
  }, [profilePending, profile, navigate]);

  const canAdvance = pendingNiche != null;

  const finish = async () => {
    if (!canAdvance) return;
    // Dual-write during the two-axis transition: new column is the
    // canonical UX identity; legacy column keeps Cloud Run /home/*
    // working until PR5 pivots its reads to creator_niche_id.
    await save.mutateAsync({
      creator_niche_id: pendingNiche,
      primary_niche: legacyNicheIdForCreatorNiche(pendingNiche),
    });
    navigate("/app", { replace: true });
  };

  const skip = () => navigate("/", { replace: true });

  if (profilePending) {
    return (
      <div
        className="flex min-h-dvh items-center justify-center bg-[color:var(--gv-canvas)]"
        role="status"
        aria-label="Đang tải"
      >
        <p className="text-sm text-[color:var(--gv-ink-4)]">Đang tải hồ sơ…</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh bg-[color:var(--gv-canvas)]">
      {/* Left column — editorial — hidden on mobile */}
      <aside className="hidden md:flex flex-1 flex-col justify-between border-r border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-[60px] py-[60px]">
        <p className="gv-mono text-[10px] uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
          GETVIEWS · CREATOR STUDIO · SỐ 01
        </p>

        <div>
          <p className="gv-mono text-[10px] uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)] mb-4">
            BƯỚC 01 / 01
          </p>
          <h1
            className="gv-tight text-[64px] leading-[0.95] text-[color:var(--gv-ink)]"
            style={{ fontFamily: "var(--gv-font-display)", letterSpacing: "-0.04em" }}
          >
            Bạn đang làm việc với{" "}
            <em className="gv-serif-italic text-[color:var(--gv-accent)]">ngách</em> nào?
          </h1>
          <p className="mt-[18px] max-w-[420px] text-base leading-snug text-[color:var(--gv-ink-3)]">
            Chọn ngách của bạn. Studio tải dữ liệu 14 ngày gần nhất —
            xu hướng, hook, sound đang nổi trong ngách bạn chọn.
          </p>
        </div>

        <p className="gv-mono inline-flex items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-[color:var(--gv-accent)]" />
          CREATOR STUDIO · MẤT ~30 GIÂY
        </p>
      </aside>

      {/* Right column — form */}
      <section className="flex flex-1 flex-col justify-center px-6 py-12 md:px-[60px] md:py-[60px]">
        <div className="w-full max-w-[640px] mx-auto">
          {nichesError ? (
            <div className="rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5 text-center">
              <p className="mb-4 text-sm text-[color:var(--gv-ink-3)]">
                Không tải được danh sách ngách.
              </p>
              <Btn type="button" variant="ink" size="sm" onClick={() => void refetchNiches()}>
                Thử lại
              </Btn>
            </div>
          ) : nichesPending ? (
            <p className="text-sm text-[color:var(--gv-ink-4)]">Đang tải danh sách ngách…</p>
          ) : !niches || niches.length === 0 ? (
            <p className="text-sm text-[color:var(--gv-ink-3)]">
              Chưa có ngách trong hệ thống. Liên hệ hỗ trợ.
            </p>
          ) : (
            <>
              <NicheGrid
                niches={niches}
                selectedId={pendingNiche}
                disabled={save.isPending}
                onSelect={setPendingNiche}
              />

              <div className="mt-9 flex items-center justify-between">
                <button
                  type="button"
                  onClick={skip}
                  className="inline-flex items-center gap-1.5 text-[13px] text-[color:var(--gv-ink-3)] hover:text-[color:var(--gv-ink)] transition-colors"
                >
                  <ArrowLeft className="h-3 w-3" strokeWidth={1.7} />
                  Bỏ qua
                </button>
                <Btn
                  type="button"
                  variant="ink"
                  size="sm"
                  disabled={!canAdvance || save.isPending}
                  onClick={() => void finish()}
                >
                  Vào Creator Studio
                  <ArrowRight className="h-3 w-3" strokeWidth={1.7} />
                </Btn>
              </div>
            </>
          )}
        </div>
      </section>
    </div>
  );
}

function NicheGrid({
  niches,
  selectedId,
  disabled,
  onSelect,
}: {
  niches: ReadonlyArray<CreatorNiche>;
  selectedId: number | null;
  disabled: boolean;
  onSelect: (id: number) => void;
}) {
  return (
    <div role="radiogroup" aria-label="Chọn ngách">
      <div className="mb-3.5 flex items-center justify-between">
        <p className="gv-mono text-[9px] uppercase tracking-[0.18em] text-[color:var(--gv-ink-4)]">
          NGÁCH CỦA BẠN
        </p>
        <p
          className={
            "gv-mono text-[10px] " +
            (selectedId != null
              ? "text-[color:var(--gv-accent-deep)]"
              : "text-[color:var(--gv-ink-4)]")
          }
        >
          {selectedId != null ? "đã chọn" : "chưa chọn"}
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {niches.map((n) => {
          const selected = selectedId === n.id;
          return (
            <button
              key={n.id}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={disabled}
              onClick={() => onSelect(n.id)}
              className={
                "flex items-start justify-between gap-3 rounded-[8px] px-4 py-3.5 text-left text-sm transition-colors " +
                (selected
                  ? "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)] border border-[color:var(--gv-ink)]"
                  : "bg-[color:var(--gv-paper)] text-[color:var(--gv-ink)] border border-[color:var(--gv-rule)] hover:border-[color:var(--gv-ink-4)]")
              }
            >
              <span className="flex items-start gap-2.5 min-w-0">
                <span
                  aria-hidden="true"
                  className={
                    "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border " +
                    (selected
                      ? "border-[color:var(--gv-canvas)] bg-[color:var(--gv-canvas)] text-[color:var(--gv-ink)]"
                      : "border-[color:var(--gv-ink-3)] bg-transparent text-transparent")
                  }
                >
                  {selected ? <Check className="h-2.5 w-2.5" strokeWidth={3} /> : null}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{n.name}</span>
                  {n.description ? (
                    <span
                      className={
                        "mt-0.5 block text-[11px] leading-snug " +
                        (selected ? "opacity-70" : "text-[color:var(--gv-ink-4)]")
                      }
                    >
                      {n.description}
                    </span>
                  ) : null}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
