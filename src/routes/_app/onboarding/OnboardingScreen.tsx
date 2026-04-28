import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { Btn } from "@/components/v2/Btn";
import { useProfile } from "@/hooks/useProfile";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import { useTopNiches } from "@/hooks/useTopNiches";
import { useUpdateProfile } from "@/hooks/useUpdateProfile";
import {
  MAX_CREATOR_NICHES,
  MIN_CREATOR_NICHES,
  normalizeNicheIds,
  profileHasMinimumNiches,
} from "@/lib/profileNiches";

/**
 * Onboarding — single-step niche pick (BƯỚC 01 / 01) per the creator-only
 * design pack (screens/onboarding-settings.jsx). Reference-channels step was
 * removed: the design treats onboarding as a 30-second niche pick and pushes
 * reference-channel curation downstream (Settings → Ngách + the in-app
 * "track this channel" CTA on /app/video). Selection is fixed to
 * MIN_CREATOR_NICHES–MAX_CREATOR_NICHES (3) for studio personalisation.
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
      // User already onboarded — bounce them back into the studio.
      navigate("/app", { replace: true });
      return;
    }
    const ids = profile?.niche_ids;
    if (Array.isArray(ids) && ids.length > 0) {
      setPendingNiches(normalizeNicheIds(ids).slice(0, MAX_CREATOR_NICHES));
    } else if (profile?.primary_niche != null) {
      setPendingNiches([profile.primary_niche]);
    }
  }, [profilePending, profile, navigate]);

  const togglePendingNiche = (id: number) => {
    setPendingNiches((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= MAX_CREATOR_NICHES) return prev;
      return [...prev, id];
    });
  };

  const canAdvance = pendingNiches.length >= MIN_CREATOR_NICHES;

  const finish = async () => {
    if (!canAdvance) return;
    const ids = normalizeNicheIds(pendingNiches);
    await save.mutateAsync({ niche_ids: ids, primary_niche: ids[0] });
    navigate("/app", { replace: true });
  };

  // ``Bỏ qua`` lets users back out to the marketing landing without
  // committing. The index route still redirects unniche'd users back here
  // on next /app visit — this is just a visible escape hatch that matches
  // the design's footer pattern.
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
            Chọn đúng {MAX_CREATOR_NICHES} ngách. Studio tải dữ liệu 14 ngày
            gần nhất — xu hướng, hook, sound đang nổi trong các ngách bạn quan tâm.
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
          {taxonomyError ? (
            <div className="rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5 text-center">
              <p className="mb-4 text-sm text-[color:var(--gv-ink-3)]">
                Không tải được danh sách ngách.
              </p>
              <Btn type="button" variant="ink" size="sm" onClick={() => void refetchTaxonomy()}>
                Thử lại
              </Btn>
            </div>
          ) : taxonomyPending ? (
            <p className="text-sm text-[color:var(--gv-ink-4)]">Đang tải danh sách ngách…</p>
          ) : niches.length === 0 ? (
            <p className="text-sm text-[color:var(--gv-ink-3)]">
              Chưa có ngách trong hệ thống. Liên hệ hỗ trợ.
            </p>
          ) : (
            <>
              <NicheGrid
                niches={niches}
                selectedIds={pendingNiches}
                disabled={save.isPending}
                onToggle={togglePendingNiche}
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
  const atCap = selectedIds.length >= MAX_CREATOR_NICHES;
  return (
    <div>
      <div className="mb-3.5 flex items-center justify-between">
        <p className="gv-mono text-[9px] uppercase tracking-[0.18em] text-[color:var(--gv-ink-4)]">
          NGÁCH CHÍNH · {MAX_CREATOR_NICHES} NGÁCH
        </p>
        <p
          className={
            "gv-mono text-[10px] " +
            (atCap
              ? "text-[color:var(--gv-accent-deep)]"
              : "text-[color:var(--gv-ink-4)]")
          }
        >
          {selectedIds.length}/{MAX_CREATOR_NICHES} đã chọn
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {niches.map((n) => {
          const selected = selectedSet.has(n.id);
          const lockAdd = !selected && atCap;
          return (
            <button
              key={n.id}
              type="button"
              disabled={disabled || lockAdd}
              onClick={() => onToggle(n.id)}
              className={
                "flex items-center justify-between gap-3 rounded-[8px] px-4 py-3.5 text-left text-sm transition-colors " +
                (selected
                  ? "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)] border border-[color:var(--gv-ink)]"
                  : "bg-[color:var(--gv-paper)] text-[color:var(--gv-ink)] border border-[color:var(--gv-rule)] hover:border-[color:var(--gv-ink-4)]") +
                (lockAdd ? " opacity-40 cursor-not-allowed" : "")
              }
            >
              <span className="flex items-center gap-2.5 min-w-0">
                <span
                  aria-hidden="true"
                  className={
                    "flex h-4 w-4 shrink-0 items-center justify-center rounded-[3px] border " +
                    (selected
                      ? "border-[color:var(--gv-canvas)] bg-[color:var(--gv-canvas)] text-[color:var(--gv-ink)]"
                      : "border-[color:var(--gv-ink-3)] bg-transparent text-transparent")
                  }
                >
                  {selected ? <Check className="h-2.5 w-2.5" strokeWidth={3} /> : null}
                </span>
                <span className="truncate">{n.name}</span>
              </span>
              <span
                className={
                  "gv-mono text-[10px] shrink-0 " +
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
