import { memo, useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router";
import { motion, AnimatePresence } from "motion/react";
import {
  ChevronRight,
  Zap,
  Check,
  Globe,
  X,
  User,
  Mail,
  Activity,
} from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";
import { AppLayout } from "@/components/AppLayout";
import { useAuth } from "@/lib/auth";
import { useProfile, type ProfileRow } from "@/hooks/useProfile";
import { useSubscription } from "@/hooks/useSubscription";
import { useCreditTransactions } from "@/hooks/useCreditTransactions";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import { useUpdateProfile } from "@/hooks/useUpdateProfile";
import { useLogout } from "@/hooks/useLogout";
import type { UseMutationResult } from "@tanstack/react-query";
import { updateProfile, type ProfilePatch } from "@/lib/data/profile";

type ProfileUpdateMutation = UseMutationResult<
  Awaited<ReturnType<typeof updateProfile>>,
  Error,
  ProfilePatch
>;

const fadeSlideUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: 12, scale: 0.98 },
};

const sectionVariants = {
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0 },
};

const SectionLabel = memo(function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-semibold uppercase tracking-widest text-[var(--faint)] mb-3">{children}</p>
  );
});

const Card = memo(function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`w-full bg-[var(--surface)] border border-[var(--border)] rounded-xl overflow-hidden ${className}`}
    >
      {children}
    </div>
  );
});

const Row = memo(function Row({
  label,
  sub,
  value,
  onClick,
  danger = false,
  children,
}: {
  label: string;
  sub?: string;
  value?: string;
  onClick?: () => void;
  danger?: boolean;
  children?: React.ReactNode;
}) {
  const Tag = onClick ? "button" : "div";
  const chevron = (
    <motion.span
      className="inline-flex"
      whileHover={{ x: 2 }}
      transition={{ type: "spring", stiffness: 500, damping: 30 }}
    >
      <ChevronRight
        className="w-3.5 h-3.5 text-[var(--faint)] group-hover:text-[var(--ink-soft)]"
        strokeWidth={2}
      />
    </motion.span>
  );

  return (
    <Tag
      type={onClick ? "button" : undefined}
      onClick={onClick}
      className={`w-full flex items-center justify-between px-4 py-3.5 border-b border-[var(--border)] last:border-0 transition-colors duration-[120ms] ${
        onClick
          ? danger
            ? "hover:bg-[var(--danger)]/5 group"
            : "hover:bg-[var(--surface-alt)] group"
          : ""
      }`}
    >
      <div>
        <p className={`text-sm ${danger ? "text-[var(--danger)]" : "text-[var(--ink-soft)]"}`}>{label}</p>
        {sub && <p className="text-[11px] text-[var(--faint)] mt-0.5">{sub}</p>}
      </div>
      {children ? (
        children
      ) : value !== undefined ? (
        <div className="flex items-center gap-2">
          <span className="text-sm text-[var(--ink)] font-medium">{value}</span>
          {onClick && chevron}
        </div>
      ) : onClick && !danger ? (
        chevron
      ) : null}
    </Tag>
  );
});

const TierBadge = memo(function TierBadge({ tier }: { tier: string }) {
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: "spring", stiffness: 400, damping: 25, delay: 0.1 }}
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[var(--purple)]/10 border border-[var(--purple)]/20 text-[var(--purple)] text-[11px] font-semibold uppercase tracking-wide"
    >
      <Zap className="w-2.5 h-2.5" strokeWidth={2.5} />
      {tier}
    </motion.span>
  );
});

function formatVnDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function tierLabelFromProfile(profile: ProfileRow | null | undefined): string {
  const t = profile?.subscription_tier ?? "free";
  if (t === "free") return "Free";
  if (t === "starter") return "Starter";
  return t.charAt(0).toUpperCase() + t.slice(1);
}

const REASON_LABELS: Record<string, string> = {
  purchase: "Mua gói",
  query: "Phân tích sâu",
  refund: "Hoàn tiền",
  admin_grant: "Cộng credit",
  expiry_reset: "Gia hạn / reset",
};

function ProfilePanelSkeleton() {
  return (
    <div className="w-full space-y-5 animate-pulse">
      <div>
        <div className="h-3 w-28 bg-[var(--surface-alt)] rounded mb-3" />
        <div className="h-40 bg-[var(--surface-alt)] border border-[var(--border)] rounded-xl" />
      </div>
    </div>
  );
}

function ProfilePanel({
  profile,
  userEmail,
  loading,
  updateProfile,
}: {
  profile: ProfileRow | null | undefined;
  userEmail: string;
  loading: boolean;
  updateProfile: ProfileUpdateMutation;
}) {
  const [open, setOpen] = useState(false);
  const displayName = profile?.display_name?.trim() || "Bạn";
  const [draft, setDraft] = useState(displayName);
  const [saved, setSaved] = useState(false);

  const initials = useMemo(
    () =>
      displayName
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2),
    [displayName],
  );

  const draftInitials = useMemo(
    () =>
      draft
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2),
    [draft],
  );

  const hasChanges = useMemo(() => Boolean(draft.trim()) && draft.trim() !== displayName, [draft, displayName]);

  const openEditor = useCallback(() => {
    setDraft(displayName);
    setSaved(false);
    setOpen(true);
  }, [displayName]);

  const handleSave = useCallback(() => {
    const next = draft.trim();
    if (!next || next === displayName) return;
    updateProfile.mutate(
      { display_name: next },
      {
        onSuccess: () => {
          setSaved(true);
          setTimeout(() => {
            setSaved(false);
            setOpen(false);
          }, 700);
        },
      },
    );
  }, [draft, displayName, updateProfile]);

  const tierBadge = tierLabelFromProfile(profile ?? null);

  if (loading && !profile) {
    return <ProfilePanelSkeleton />;
  }

  return (
    <motion.div
      className="w-full space-y-5"
      variants={sectionVariants}
      initial="initial"
      whileInView="animate"
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      <div>
        <SectionLabel>Hồ sơ cá nhân</SectionLabel>
        <Card>
          <div className="p-5 flex items-start gap-5 border-b border-[var(--border)]">
            <AnimatePresence mode="wait">
              <motion.div
                key={initials}
                initial={{ scale: 0.7, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.7, opacity: 0 }}
                transition={{ type: "spring", stiffness: 500, damping: 28 }}
                className="w-16 h-16 rounded-full bg-[var(--purple)] flex items-center justify-center flex-shrink-0 ring-4 ring-[var(--purple)]/10"
              >
                <span className="text-white font-extrabold text-lg tracking-tight">{initials}</span>
              </motion.div>
            </AnimatePresence>

            <div className="flex-1 min-w-0">
              <AnimatePresence mode="wait">
                <motion.p
                  key={displayName}
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 6 }}
                  transition={{ duration: 0.2 }}
                  className="font-extrabold text-[var(--ink)]"
                >
                  {displayName}
                </motion.p>
              </AnimatePresence>
              <div className="mt-2">
                <TierBadge tier={tierBadge} />
              </div>
            </div>

            <Dialog.Root open={open} onOpenChange={setOpen}>
              <Dialog.Trigger asChild>
                <motion.button
                  type="button"
                  whileTap={{ scale: 0.94 }}
                  onClick={openEditor}
                  className="flex-shrink-0 mt-0.5 px-3.5 py-1.5 rounded-lg border border-[var(--border)] text-xs text-[var(--ink-soft)] hover:bg-[var(--surface-alt)] hover:border-[var(--border-active)] transition-all duration-[120ms]"
                >
                  Chỉnh sửa
                </motion.button>
              </Dialog.Trigger>

              <AnimatePresence>
                {open && (
                  <Dialog.Portal forceMount>
                    <Dialog.Overlay asChild forceMount>
                      <motion.div
                        className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                      />
                    </Dialog.Overlay>

                    <Dialog.Content asChild forceMount aria-describedby={undefined}>
                      <motion.div
                        className="fixed z-50 left-1/2 top-1/2 w-[calc(100vw-2rem)] max-w-sm bg-[var(--surface)] border border-[var(--border)] rounded-2xl shadow-2xl outline-none"
                        style={{ x: "-50%", y: "-50%" }}
                        variants={fadeSlideUp}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                        transition={{ type: "spring", stiffness: 380, damping: 28 }}
                      >
                        <div className="flex items-center justify-between px-5 pt-5 pb-4 border-b border-[var(--border)]">
                          <Dialog.Title className="font-extrabold text-[var(--ink)]">Chỉnh sửa hồ sơ</Dialog.Title>
                          <Dialog.Close asChild>
                            <motion.button
                              type="button"
                              whileTap={{ scale: 0.88, rotate: 90 }}
                              transition={{ duration: 0.15 }}
                              className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--muted)] hover:bg-[var(--surface-alt)] hover:text-[var(--ink)] transition-colors duration-[120ms]"
                            >
                              <X className="w-4 h-4" strokeWidth={2} />
                            </motion.button>
                          </Dialog.Close>
                        </div>

                        <div className="p-5 space-y-4">
                          <div className="flex justify-center">
                            <AnimatePresence mode="wait">
                              <motion.div
                                key={draftInitials}
                                initial={{ scale: 0.8, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                exit={{ scale: 0.8, opacity: 0 }}
                                transition={{ type: "spring", stiffness: 500, damping: 30 }}
                                className="w-20 h-20 rounded-full bg-[var(--purple)] flex items-center justify-center ring-4 ring-[var(--purple)]/10"
                              >
                                <span className="text-white font-extrabold text-xl tracking-tight">{draftInitials}</span>
                              </motion.div>
                            </AnimatePresence>
                          </div>

                          <div>
                            <label className="block text-[11px] font-semibold uppercase tracking-widest text-[var(--faint)] mb-2">
                              Tên hiển thị
                            </label>
                            <div className="relative">
                              <User
                                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--faint)]"
                                strokeWidth={2}
                              />
                              <input
                                type="text"
                                value={draft}
                                onChange={(e) => setDraft(e.target.value)}
                                maxLength={40}
                                placeholder="Nhập tên hiển thị..."
                                className="w-full pl-9 pr-4 py-2.5 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-sm text-[var(--ink)] placeholder:text-[var(--faint)] outline-none focus:border-[var(--purple)] focus:ring-2 focus:ring-[var(--purple)]/20 transition-all duration-[120ms]"
                              />
                            </div>
                            <p className="text-[11px] text-[var(--faint)] mt-1.5 text-right font-mono">{draft.length}/40</p>
                          </div>

                          <div>
                            <label className="block text-[11px] font-semibold uppercase tracking-widest text-[var(--faint)] mb-2">
                              Email
                            </label>
                            <div className="relative">
                              <Mail
                                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--faint)]"
                                strokeWidth={2}
                              />
                              <input
                                type="email"
                                readOnly
                                value={userEmail}
                                className="w-full pl-9 pr-4 py-2.5 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-sm text-[var(--muted)] outline-none cursor-not-allowed"
                              />
                            </div>
                          </div>
                        </div>

                        <div className="px-5 pb-5 flex gap-2.5">
                          <Dialog.Close asChild>
                            <button
                              type="button"
                              className="flex-1 py-2.5 rounded-xl border border-[var(--border)] text-sm text-[var(--ink-soft)] hover:bg-[var(--surface-alt)] transition-colors duration-[120ms]"
                            >
                              Huỷ
                            </button>
                          </Dialog.Close>
                          <motion.button
                            type="button"
                            onClick={handleSave}
                            disabled={!hasChanges || updateProfile.isPending}
                            whileTap={hasChanges ? { scale: 0.96 } : {}}
                            className="flex-1 py-2.5 rounded-xl bg-[var(--purple)] hover:bg-[var(--purple-dark)] text-white text-sm font-semibold transition-colors duration-[120ms] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-1.5 overflow-hidden"
                          >
                            <AnimatePresence mode="wait" initial={false}>
                              {saved ? (
                                <motion.span
                                  key="saved"
                                  className="flex items-center gap-1.5"
                                  initial={{ opacity: 0, y: 10 }}
                                  animate={{ opacity: 1, y: 0 }}
                                  exit={{ opacity: 0, y: -10 }}
                                  transition={{ duration: 0.18 }}
                                >
                                  <Check className="w-4 h-4" strokeWidth={2.5} />
                                  Đã lưu
                                </motion.span>
                              ) : (
                                <motion.span
                                  key="save"
                                  initial={{ opacity: 0, y: 10 }}
                                  animate={{ opacity: 1, y: 0 }}
                                  exit={{ opacity: 0, y: -10 }}
                                  transition={{ duration: 0.18 }}
                                >
                                  Lưu thay đổi
                                </motion.span>
                              )}
                            </AnimatePresence>
                          </motion.button>
                        </div>
                      </motion.div>
                    </Dialog.Content>
                  </Dialog.Portal>
                )}
              </AnimatePresence>
            </Dialog.Root>
          </div>
          <Row label="Tên hiển thị" value={displayName} onClick={openEditor} />
          <Row label="Email" value={userEmail || "—"} />
        </Card>
      </div>

      <div>
        <SectionLabel>Bảo mật</SectionLabel>
        <Card>
          <Row label="Đổi mật khẩu" onClick={() => {}} />
          <Row
            label="Xác thực hai yếu tố"
            sub="Bảo vệ tài khoản của bạn"
            value="Tắt"
            onClick={() => {}}
          />
        </Card>
      </div>
    </motion.div>
  );
}

function PlanPanel({
  navigate,
  profile,
  subscription,
  loading,
}: {
  navigate: (path: string) => void;
  profile: ProfileRow | null | undefined;
  subscription: { tier: string; expires_at: string; deep_credits_granted: number } | null | undefined;
  loading: boolean;
}) {
  const cap = (profile as { deep_credits_total?: number } | null)?.deep_credits_total ?? 50;
  const remaining = profile?.deep_credits_remaining ?? 0;
  const creditPct = useMemo(
    () => (cap > 0 ? Math.min(100, Math.round((remaining / cap) * 100)) : 0),
    [remaining, cap],
  );

  const goToPricing = useCallback(() => navigate("/app/pricing"), [navigate]);

  const tierRaw = profile?.subscription_tier ?? "free";
  const isFreeTier = tierRaw === "free" && !subscription;
  const creditsResetAt = profile?.credits_reset_at;
  const expiryPassed =
    creditsResetAt != null && creditsResetAt !== "" && new Date(creditsResetAt).getTime() < Date.now();
  const showExpiredCopy = !isFreeTier && expiryPassed;

  const tierName = subscription
    ? subscription.tier === "starter"
      ? "Starter"
      : subscription.tier.charAt(0).toUpperCase() + subscription.tier.slice(1)
    : tierLabelFromProfile(profile ?? null);
  const subscriptionTierLabel = `Gói ${tierName}`;
  const subscriptionCreditsLine = `${remaining} deep credits còn lại`;

  if (loading && !profile) {
    return (
      <div className="w-full space-y-5 animate-pulse">
        <div className="h-48 bg-[var(--surface-alt)] border border-[var(--border)] rounded-xl" />
      </div>
    );
  }

  return (
    <motion.div
      className="w-full space-y-5"
      variants={sectionVariants}
      initial="initial"
      whileInView="animate"
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1], delay: 0.05 }}
    >
      <Card>
        <div className="p-5">
          <div className="flex items-start justify-between mb-4 gap-2">
            <div className="min-w-0">
              <p className="text-[11px] uppercase tracking-widest text-[var(--faint)] mb-1">{subscriptionTierLabel}</p>
              <p className="text-sm text-[var(--ink-soft)] mb-2 font-medium">{subscriptionCreditsLine}</p>
              {isFreeTier ? (
                <p className="text-xs text-[var(--muted)] leading-relaxed">
                  10 lần phân tích sâu miễn phí (lifetime)
                </p>
              ) : showExpiredCopy ? (
                <p className="text-xs text-[var(--danger)] font-medium">
                  Gói đã hết hạn — gia hạn để tiếp tục phân tích sâu.
                </p>
              ) : creditsResetAt ? (
                <p className="text-[11px] text-[var(--faint)] font-mono">
                  Credits hết hạn: {formatVnDate(creditsResetAt)}
                </p>
              ) : null}
              <div className="flex items-baseline gap-2 mt-3">
                <span className="font-extrabold font-mono text-[var(--ink)] text-[2.5rem] leading-none">{remaining}</span>
                <span className="text-sm text-[var(--muted)] font-mono">/ {cap}</span>
              </div>
            </div>
            <motion.button
              type="button"
              whileTap={{ scale: 0.94 }}
              onClick={goToPricing}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--purple)] hover:bg-[var(--purple-dark)] text-white text-sm font-semibold transition-colors duration-[120ms] flex-shrink-0"
            >
              <Zap className="w-3.5 h-3.5" strokeWidth={2.5} />
              {isFreeTier || remaining <= 0 ? "Nâng cấp" : "Mua thêm credits"}
            </motion.button>
          </div>

          <div className="h-2 bg-[var(--surface-alt)] border border-[var(--border)] rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              whileInView={{ width: `${creditPct}%` }}
              viewport={{ once: true }}
              transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
              className="h-full rounded-full gradient-cta"
            />
          </div>
        </div>
      </Card>

      <div>
        <SectionLabel>Chi tiết gói</SectionLabel>
        <Card>
          <Row label="Gói hiện tại" value={subscriptionTierLabel} onClick={goToPricing} />
          <Row label="Lịch sử thanh toán" onClick={goToPricing} />
        </Card>
      </div>

      <div className="p-4 rounded-xl border border-[var(--purple)]/20 bg-[var(--purple)]/5">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-[var(--purple)]/15 flex items-center justify-center flex-shrink-0 mt-0.5">
            <Zap className="w-4 h-4 text-[var(--purple)]" strokeWidth={2.2} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-extrabold text-[var(--ink)] mb-0.5">Mua thêm deep credits</p>
            <p className="text-xs text-[var(--muted)]">Chọn gói phù hợp trên trang thanh toán.</p>
          </div>
          <motion.button
            type="button"
            whileTap={{ scale: 0.94 }}
            onClick={goToPricing}
            className="px-3.5 py-1.5 rounded-lg bg-[var(--purple)] hover:bg-[var(--purple-dark)] text-white text-xs font-semibold transition-colors duration-[120ms] flex-shrink-0"
          >
            Xem gói
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
}

const NicheChip = memo(function NicheChip({
  name,
  id,
  selectedId,
  onSelect,
  disabled,
}: {
  name: string;
  id: number;
  selectedId: number | null;
  onSelect: (id: number) => void;
  disabled?: boolean;
}) {
  const isActive = selectedId === id;
  const handleClick = useCallback(() => onSelect(id), [id, onSelect]);
  return (
    <motion.button
      type="button"
      disabled={disabled}
      onClick={handleClick}
      whileTap={{ scale: 0.92 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs border transition-all duration-[120ms] ${
        isActive
          ? "bg-[var(--purple)] border-[var(--purple)] text-white"
          : "bg-[var(--surface-alt)] border-[var(--border)] text-[var(--ink-soft)] hover:border-[var(--border-active)] hover:text-[var(--ink)]"
      } disabled:opacity-50`}
    >
      <AnimatePresence initial={false}>
        {isActive && (
          <motion.span
            key="check"
            initial={{ scale: 0, opacity: 0, width: 0 }}
            animate={{ scale: 1, opacity: 1, width: "auto" }}
            exit={{ scale: 0, opacity: 0, width: 0 }}
            transition={{ type: "spring", stiffness: 500, damping: 28 }}
            className="inline-flex overflow-hidden"
          >
            <Check className="w-3 h-3" strokeWidth={2.5} />
          </motion.span>
        )}
      </AnimatePresence>
      {name}
    </motion.button>
  );
});

function NichePanel({
  profile,
  niches,
  nicheLoading,
  updateProfile,
}: {
  profile: ProfileRow | null | undefined;
  niches: { id: number; name: string }[] | undefined;
  nicheLoading: boolean;
  updateProfile: ProfileUpdateMutation;
}) {
  const primary = profile?.primary_niche;
  const selectedId = typeof primary === "number" ? primary : primary != null ? Number(primary) : null;
  const selectedName = niches?.find((n) => n.id === selectedId)?.name ?? "Chưa chọn";

  const handleSelect = useCallback(
    (id: number) => {
      updateProfile.mutate({ primary_niche: id });
    },
    [updateProfile],
  );

  return (
    <motion.div
      className="w-full space-y-5"
      variants={sectionVariants}
      initial="initial"
      whileInView="animate"
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1], delay: 0.08 }}
    >
      <div>
        <SectionLabel>Niche chính của bạn</SectionLabel>
        <Card>
          <div className="p-5">
            <p className="text-sm text-[var(--ink-soft)] mb-4">
              Chọn niche để Getviews cá nhân hóa phân tích xu hướng và hook cho bạn.
            </p>
            {nicheLoading ? (
              <div className="h-24 animate-pulse rounded-lg bg-[var(--surface-alt)]" />
            ) : (
              <div className="flex flex-wrap gap-2">
                {(niches ?? []).map((n) => (
                  <NicheChip
                    key={n.id}
                    id={n.id}
                    name={n.name}
                    selectedId={Number.isFinite(selectedId as number) ? (selectedId as number) : null}
                    onSelect={handleSelect}
                    disabled={updateProfile.isPending}
                  />
                ))}
              </div>
            )}
          </div>
        </Card>
      </div>

      <div>
        <SectionLabel>Niche đang chọn</SectionLabel>
        <Card>
          <div className="px-4 py-3.5 flex items-center justify-between">
            <AnimatePresence mode="wait">
              <motion.div
                key={selectedName}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 8 }}
                transition={{ duration: 0.2 }}
              >
                <p className="text-sm text-[var(--ink)] font-medium">{selectedName}</p>
                <p className="text-[11px] text-[var(--faint)] mt-0.5">Được dùng để cá nhân hóa kết quả phân tích</p>
              </motion.div>
            </AnimatePresence>
            <motion.span
              className="w-2 h-2 rounded-full bg-[var(--success)] flex-shrink-0"
              animate={{ scale: [1, 1.4, 1] }}
              transition={{ duration: 0.4, ease: "easeInOut" }}
              key={selectedName}
            />
          </div>
        </Card>
      </div>
    </motion.div>
  );
}

function PreferencesPanel() {
  const [emailNotif, setEmailNotif] = useState(true);

  const toggleNotif = useCallback(() => setEmailNotif((v) => !v), []);

  return (
    <motion.div
      className="w-full space-y-5"
      variants={sectionVariants}
      initial="initial"
      whileInView="animate"
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
    >
      <div>
        <SectionLabel>Ngôn ngữ & khu vực</SectionLabel>
        <Card>
          <Row label="Ngôn ngữ" onClick={() => {}}>
            <div className="flex items-center gap-2">
              <Globe className="w-3.5 h-3.5 text-[var(--faint)]" />
              <span className="text-sm text-[var(--ink)] font-medium">Tiếng Việt</span>
              <motion.span
                className="inline-flex"
                whileHover={{ x: 2 }}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
              >
                <ChevronRight className="w-3.5 h-3.5 text-[var(--faint)]" strokeWidth={2} />
              </motion.span>
            </div>
          </Row>
          <Row label="Múi giờ" value="Asia/Ho_Chi_Minh" onClick={() => {}} />
        </Card>
      </div>

      <div>
        <SectionLabel>Thông báo</SectionLabel>
        <Card>
          <div className="flex items-center justify-between px-4 py-3.5 border-b border-[var(--border)]">
            <div>
              <p className="text-sm text-[var(--ink-soft)]">Thông báo qua email</p>
              <p className="text-[11px] text-[var(--faint)] mt-0.5">Nhận cập nhật xu hướng hàng tuần</p>
            </div>
            <motion.button
              type="button"
              onClick={toggleNotif}
              whileTap={{ scale: 0.9 }}
              transition={{ type: "spring", stiffness: 400, damping: 25 }}
              className={`relative w-10 h-[22px] rounded-full transition-colors duration-200 flex-shrink-0 ${
                emailNotif ? "bg-[var(--purple)]" : "bg-[var(--border-active)]"
              }`}
            >
              <motion.span
                layout
                className="absolute top-0.5 w-[18px] h-[18px] bg-white rounded-full shadow-sm"
                animate={{ left: emailNotif ? "19px" : "2px" }}
                transition={{ type: "spring", stiffness: 500, damping: 35 }}
              />
            </motion.button>
          </div>
          <Row
            label="Thông báo khi credits sắp hết"
            sub="Cảnh báo khi còn dưới 5 credits"
            value="Bật"
            onClick={() => {}}
          />
        </Card>
      </div>

      <div>
        <SectionLabel>Quyền riêng tư</SectionLabel>
        <Card>
          <Row label="Xuất dữ liệu của tôi" onClick={() => {}} />
          <Row label="Xoá tài khoản" danger onClick={() => {}} />
        </Card>
      </div>
    </motion.div>
  );
}

function HistoryPanelSkeleton() {
  return (
    <div className="space-y-0 border-b border-[var(--border)] last:border-0">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="flex items-center justify-between px-4 py-3.5 border-b border-[var(--border)] last:border-0 animate-pulse">
          <div className="flex items-center gap-3.5 flex-1">
            <div className="w-7 h-7 rounded bg-[var(--surface-alt)]" />
            <div className="flex-1 space-y-2">
              <div className="h-3 w-32 bg-[var(--surface-alt)] rounded" />
              <div className="h-2 w-48 bg-[var(--surface-alt)] rounded" />
            </div>
          </div>
          <div className="h-3 w-16 bg-[var(--surface-alt)] rounded" />
        </div>
      ))}
    </div>
  );
}

const HistoryPanel = memo(function HistoryPanel({
  transactions,
  loading,
}: {
  transactions:
    | {
        id: string;
        created_at: string;
        delta: number;
        balance_after: number;
        reason: string;
      }[]
    | undefined;
  loading: boolean;
}) {
  return (
    <motion.div
      className="w-full space-y-5"
      variants={sectionVariants}
      initial="initial"
      whileInView="animate"
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1], delay: 0.12 }}
    >
      <div>
        <SectionLabel>Hoạt động gần đây</SectionLabel>
        <Card>
          {loading ? (
            <HistoryPanelSkeleton />
          ) : !transactions?.length ? (
            <div className="px-4 py-8 text-center text-sm text-[var(--muted)]">Chưa có lịch sử credit.</div>
          ) : (
            transactions.map((tx, idx) => {
              const label = REASON_LABELS[tx.reason] ?? tx.reason;
              const d = new Date(tx.created_at);
              const dateLabel = d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
              const timeLabel = d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
              const creditLabel =
                tx.delta === 0
                  ? "Miễn phí"
                  : tx.delta < 0
                    ? `−${Math.abs(tx.delta)} credit`
                    : `+${tx.delta} credit`;
              const isFree = tx.delta === 0;
              return (
                <motion.div
                  key={tx.id}
                  className="flex items-center justify-between px-4 py-3.5 border-b border-[var(--border)] last:border-0"
                  initial={{ opacity: 0, x: -12 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.3, delay: idx * 0.06, ease: [0.16, 1, 0.3, 1] }}
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    <Activity className="w-5 h-5 text-[var(--faint)] flex-shrink-0" strokeWidth={2} />
                    <div className="min-w-0">
                      <p className="text-sm text-[var(--ink)] font-medium truncate">{label}</p>
                      <p className="text-[11px] font-mono text-[var(--faint)]">
                        {dateLabel} · {timeLabel}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`text-xs font-mono font-semibold flex-shrink-0 ml-2 ${
                      isFree ? "text-[var(--success)]" : "text-[var(--muted)]"
                    }`}
                  >
                    {creditLabel}
                  </span>
                </motion.div>
              );
            })
          )}
        </Card>
      </div>
    </motion.div>
  );
});

function LogoutSection({
  logout,
  navigate,
}: {
  logout: ReturnType<typeof useLogout>;
  navigate: ReturnType<typeof useNavigate>;
}) {
  const [open, setOpen] = useState(false);

  const onConfirm = useCallback(() => {
    logout.mutate(undefined, {
      onSuccess: () => {
        navigate("/login", { replace: true });
      },
    });
  }, [logout, navigate]);

  return (
    <div className="w-full">
      <SectionLabel>Tài khoản</SectionLabel>
      <Card>
        <Dialog.Root open={open} onOpenChange={setOpen}>
          <Dialog.Trigger asChild>
            <button
              type="button"
              className="w-full flex items-center justify-between px-4 py-3.5 text-left text-sm font-medium text-[var(--danger)] hover:bg-[var(--danger)]/5 transition-colors duration-[120ms]"
            >
              Đăng xuất
              <ChevronRight className="w-3.5 h-3.5 text-[var(--faint)]" strokeWidth={2} />
            </button>
          </Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" />
            <Dialog.Content
              className="fixed z-50 left-1/2 top-1/2 w-[calc(100vw-2rem)] max-w-sm -translate-x-1/2 -translate-y-1/2 bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-5 shadow-2xl outline-none"
              aria-describedby={undefined}
            >
              <Dialog.Title className="font-extrabold text-[var(--ink)] mb-4">Đăng xuất khỏi GetViews?</Dialog.Title>
              <div className="flex gap-2.5">
                <Dialog.Close asChild>
                  <button
                    type="button"
                    className="flex-1 py-2.5 rounded-xl border border-[var(--border)] text-sm text-[var(--ink-soft)] hover:bg-[var(--surface-alt)] transition-colors duration-[120ms]"
                  >
                    Huỷ
                  </button>
                </Dialog.Close>
                <button
                  type="button"
                  onClick={onConfirm}
                  disabled={logout.isPending}
                  className="flex-1 py-2.5 rounded-xl bg-[var(--danger)] text-white text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  Đăng xuất
                </button>
              </div>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      </Card>
    </div>
  );
}

export default function SettingsScreen() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data: profile, isPending: profileLoading, isError: profileError, refetch } = useProfile();
  const { data: subscription } = useSubscription();
  const { data: transactions, isPending: txLoading } = useCreditTransactions(20);
  const { data: niches, isPending: nicheLoading } = useNicheTaxonomy();
  const updateProfile = useUpdateProfile();
  const logout = useLogout();

  const userEmail = user?.email ?? "";

  const goLearnMore = useCallback(() => navigate("/app/learn-more"), [navigate]);

  if (profileError) {
    return (
      <AppLayout enableMobileSidebar>
        <div className="flex-1 overflow-y-auto flex items-center justify-center p-6">
          <div className="max-w-md text-center space-y-3">
            <p className="text-sm text-[var(--ink-soft)]">Không tải được thông tin tài khoản — thử lại.</p>
            <button
              type="button"
              onClick={() => void refetch()}
              className="px-4 py-2 rounded-lg bg-[var(--purple)] text-white text-sm font-semibold"
            >
              Thử lại
            </button>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout enableMobileSidebar>
      <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
        <div className="max-w-2xl mx-auto px-4 lg:px-8 pt-16 lg:pt-8 pb-8 space-y-8">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          >
            <h1 className="font-extrabold text-[var(--ink)] mb-1 text-[1.75rem]">Cài đặt</h1>
            <p className="text-sm text-[var(--muted)]">Quản lý tài khoản và tùy chọn của bạn</p>
          </motion.div>

          <ProfilePanel
            profile={profile}
            userEmail={userEmail}
            loading={profileLoading}
            updateProfile={updateProfile}
          />

          <motion.div
            className="w-full"
            variants={sectionVariants}
            initial="initial"
            whileInView="animate"
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1], delay: 0.03 }}
          >
            <SectionLabel>Tìm hiểu thêm</SectionLabel>
            <Card>
              <Row label="Tài liệu & pháp lý" onClick={goLearnMore} />
            </Card>
          </motion.div>

          <PlanPanel
            navigate={navigate}
            profile={profile}
            subscription={subscription ?? undefined}
            loading={profileLoading}
          />

          <NichePanel
            profile={profile}
            niches={niches}
            nicheLoading={nicheLoading}
            updateProfile={updateProfile}
          />

          <PreferencesPanel />

          <HistoryPanel transactions={transactions} loading={txLoading} />

          <LogoutSection logout={logout} navigate={navigate} />

          <p className="text-center text-[11px] font-mono text-[var(--faint)] mt-8">Getviews.vn · v1.0.0</p>
        </div>
      </div>
    </AppLayout>
  );
}
