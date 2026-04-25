import { memo, useState, useCallback, useMemo, useEffect } from "react";
import { useNavigate } from "react-router";
import { motion, AnimatePresence } from "motion/react";
import { ChevronRight, Zap, Check, Globe, User, Mail, Activity } from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";
import { AppLayout } from "@/components/AppLayout";
import { Btn } from "@/components/v2/Btn";
import { useAuth } from "@/lib/auth";
import { useProfile, type ProfileRow } from "@/hooks/useProfile";
import { useSubscription } from "@/hooks/useSubscription";
import { useCreditTransactions } from "@/hooks/useCreditTransactions";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import { useUpdateProfile } from "@/hooks/useUpdateProfile";
import { useLogout } from "@/hooks/useLogout";
import type { UseMutationResult } from "@tanstack/react-query";
import { updateProfile, type ProfilePatch } from "@/lib/data/profile";
import { MAX_CREATOR_NICHES, MIN_CREATOR_NICHES, normalizeNicheIds } from "@/lib/profileNiches";

type ProfileUpdateMutation = UseMutationResult<
  Awaited<ReturnType<typeof updateProfile>>,
  Error,
  ProfilePatch
>;

const SETTINGS_SECTIONS = [
  { id: "profile", label: "Hồ Sơ" },
  { id: "niches", label: "Ngách & Đối Thủ" },
  { id: "alerts", label: "Cảnh Báo" },
  { id: "export", label: "Xuất Dữ Liệu" },
  { id: "billing", label: "Gói & Thanh Toán" },
  { id: "team", label: "Nhóm" },
] as const;

type SettingsSectionId = (typeof SETTINGS_SECTIONS)[number]["id"];

const sectionVariants = {
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0 },
};

const SectionLabel = memo(function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-[9px] font-semibold uppercase tracking-wide text-[color:var(--gv-ink-4)] mb-3">
      {children}
    </p>
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
      className={`w-full overflow-hidden rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] ${className}`}
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
        className="h-3.5 w-3.5 text-[color:var(--gv-ink-4)] group-hover:text-[color:var(--gv-ink-2)]"
        strokeWidth={2}
      />
    </motion.span>
  );

  return (
    <Tag
      type={onClick ? "button" : undefined}
      onClick={onClick}
      className={`flex w-full items-center justify-between border-b border-[color:var(--gv-rule)] px-4 py-3.5 text-left last:border-0 transition-colors duration-[120ms] ${
        onClick
          ? danger
            ? "hover:bg-[color:var(--gv-danger)]/5 group"
            : "hover:bg-[color:var(--gv-canvas-2)] group"
          : ""
      }`}
    >
      <div>
        <p className={`text-sm ${danger ? "text-[color:var(--gv-danger)]" : "text-[color:var(--gv-ink-2)]"}`}>
          {label}
        </p>
        {sub ? <p className="mt-0.5 text-[11px] text-[color:var(--gv-ink-4)]">{sub}</p> : null}
      </div>
      {children ? (
        children
      ) : value !== undefined ? (
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[color:var(--gv-ink)]">{value}</span>
          {onClick && chevron}
        </div>
      ) : onClick && !danger ? (
        chevron
      ) : null}
    </Tag>
  );
});

function SettingsField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  // Render as <label> wrapping its child so native HTML association covers
  // <input>/<textarea>/<select> children automatically — no need for id +
  // htmlFor wiring at every call site. Clicking the label focuses the input.
  return (
    <label className="block">
      <span className="mb-1.5 block font-mono text-[9px] font-semibold uppercase tracking-wide text-[color:var(--gv-ink-4)]">
        {label}
      </span>
      {children}
    </label>
  );
}

function SettingsToggle({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      onClick={onToggle}
      className={`relative h-[22px] w-[38px] shrink-0 rounded-full transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)] focus-visible:ring-offset-2 ${
        on ? "bg-[color:var(--gv-accent)]" : "bg-[color:var(--gv-rule)]"
      }`}
    >
      <span
        className="absolute top-0.5 h-[18px] w-[18px] rounded-full bg-white shadow-sm transition-[left] duration-150 ease-out"
        style={{ left: on ? 18 : 2 }}
      />
    </button>
  );
}

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
  admin_grant: "Cộng phân tích",
  expiry_reset: "Gia hạn / reset",
};

function ProfileSettingsSection({
  profile,
  userEmail,
  loading,
  updateProfile: updateMutation,
  goLearnMore,
}: {
  profile: ProfileRow | null | undefined;
  userEmail: string;
  loading: boolean;
  updateProfile: ProfileUpdateMutation;
  goLearnMore: () => void;
}) {
  const displayName = profile?.display_name?.trim() || "";
  const tiktokFromProfile = (profile as { tiktok_handle?: string | null })?.tiktok_handle ?? "";
  const [draftName, setDraftName] = useState(displayName);
  const [draftTiktok, setDraftTiktok] = useState(tiktokFromProfile ?? "");

  useEffect(() => {
    if (!profile) return;
    setDraftName(profile.display_name?.trim() || "");
    setDraftTiktok((profile as { tiktok_handle?: string | null }).tiktok_handle ?? "");
  }, [profile?.id, profile?.display_name, (profile as { tiktok_handle?: string | null })?.tiktok_handle]);

  const hasChanges = useMemo(() => {
    const n = draftName.trim();
    const t = draftTiktok.trim();
    return n !== displayName || t !== (tiktokFromProfile ?? "").trim();
  }, [draftName, draftTiktok, displayName, tiktokFromProfile]);

  const onSave = useCallback(() => {
    const n = draftName.trim();
    if (!n) return;
    updateMutation.mutate({
      display_name: n,
      tiktok_handle: draftTiktok.trim() || null,
    });
  }, [draftName, draftTiktok, updateMutation]);

  const onCancel = useCallback(() => {
    setDraftName(displayName);
    setDraftTiktok(tiktokFromProfile ?? "");
  }, [displayName, tiktokFromProfile]);

  if (loading && !profile) {
    return <div className="h-40 animate-pulse rounded-lg bg-[color:var(--gv-canvas-2)]" />;
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-[18px]">
        <SettingsField label="Tên hiển thị">
          <input
            type="text"
            value={draftName}
            onChange={(e) => setDraftName(e.target.value)}
            maxLength={40}
            className="w-full rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3.5 py-2.5 text-sm text-[color:var(--gv-ink)] outline-none focus:border-[color:var(--gv-ink)]"
          />
        </SettingsField>
        <SettingsField label="Email">
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--gv-ink-4)]" strokeWidth={2} />
            <input
              type="email"
              readOnly
              value={userEmail}
              className="w-full cursor-not-allowed rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] py-2.5 pl-9 pr-3.5 text-sm text-[color:var(--gv-ink-3)]"
            />
          </div>
        </SettingsField>
        <SettingsField label="Handle TikTok">
          <div className="relative">
            <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--gv-ink-4)]" strokeWidth={2} />
            <input
              type="text"
              value={draftTiktok}
              onChange={(e) => setDraftTiktok(e.target.value)}
              placeholder="@username"
              className="w-full rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] py-2.5 pl-9 pr-3.5 text-sm text-[color:var(--gv-ink)] outline-none placeholder:text-[color:var(--gv-ink-4)] focus:border-[color:var(--gv-ink)]"
            />
          </div>
        </SettingsField>
        <SettingsField label="Múi giờ">
          <input
            type="text"
            readOnly
            value="(GMT+7) Việt Nam · Asia/Ho_Chi_Minh"
            className="w-full cursor-default rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-3.5 py-2.5 text-sm text-[color:var(--gv-ink-3)]"
          />
        </SettingsField>
      </div>

      <div className="flex flex-wrap gap-2">
        <Btn variant="ink" size="md" type="button" disabled={!hasChanges || updateMutation.isPending} onClick={onSave}>
          Lưu thay đổi
        </Btn>
        <Btn variant="ghost" size="md" type="button" disabled={!hasChanges || updateMutation.isPending} onClick={onCancel}>
          Huỷ
        </Btn>
      </div>

      <div>
        <SectionLabel>Bảo mật</SectionLabel>
        <Card>
          <Row label="Đổi mật khẩu" onClick={() => {}} />
          <Row label="Xác thực hai yếu tố" sub="Bảo vệ tài khoản của bạn" value="Tắt" onClick={() => {}} />
        </Card>
      </div>

      <div>
        <SectionLabel>Tài liệu</SectionLabel>
        <Card>
          <Row label="Tài liệu & pháp lý" onClick={goLearnMore} />
        </Card>
      </div>
    </div>
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
  const subscriptionCreditsLine = `${remaining} phân tích còn lại`;

  if (loading && !profile) {
    return <div className="h-48 animate-pulse rounded-lg bg-[color:var(--gv-canvas-2)]" />;
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
      <Card className="p-6">
        <p className="font-mono text-[9px] font-semibold uppercase tracking-wide text-[color:var(--gv-ink-4)]">
          Gói hiện tại
        </p>
        <div className="mt-1.5 mb-3.5 flex flex-wrap items-baseline gap-3">
          <h2 className="gv-tight text-[2.625rem] font-bold leading-none tracking-tight text-[color:var(--gv-ink)]">
            {tierName}
          </h2>
          <span className="font-mono text-sm text-[color:var(--gv-ink-3)]">{subscriptionCreditsLine}</span>
        </div>
        <p className="mb-4 text-sm font-medium text-[color:var(--gv-ink-2)]">{subscriptionTierLabel}</p>

        {isFreeTier ? (
          <p className="mb-4 text-xs leading-relaxed text-[color:var(--gv-ink-3)]">
            10 lần phân tích sâu miễn phí (lifetime)
          </p>
        ) : showExpiredCopy ? (
          <p className="mb-4 text-xs font-medium text-[color:var(--gv-danger)]">
            Gói đã hết hạn — gia hạn để tiếp tục phân tích sâu.
          </p>
        ) : creditsResetAt ? (
          <p className="mb-4 font-mono text-[11px] text-[color:var(--gv-ink-4)]">
            Credits hết hạn: {formatVnDate(creditsResetAt)}
          </p>
        ) : null}

        <div className="mb-5 grid grid-cols-1 gap-3.5 sm:grid-cols-3">
          <div>
            <p className="font-mono text-[9px] font-semibold uppercase tracking-wide text-[color:var(--gv-ink-4)]">
              Phân tích
            </p>
            <p className="gv-tight text-[1.375rem] font-bold text-[color:var(--gv-ink)]">
              {remaining}/{cap}
            </p>
          </div>
          <div>
            <p className="font-mono text-[9px] font-semibold uppercase tracking-wide text-[color:var(--gv-ink-4)]">
              Đăng ký
            </p>
            <p className="gv-tight text-[1.375rem] font-bold text-[color:var(--gv-ink)]">{tierName}</p>
          </div>
          <div>
            <p className="font-mono text-[9px] font-semibold uppercase tracking-wide text-[color:var(--gv-ink-4)]">
              Trạng thái
            </p>
            <p className="gv-tight text-[1.375rem] font-bold text-[color:var(--gv-ink)]">
              {showExpiredCopy ? "Hết hạn" : isFreeTier ? "Free" : "Hoạt động"}
            </p>
          </div>
        </div>

        <div className="mb-5 h-2 overflow-hidden rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)]">
          <motion.div
            initial={{ width: 0 }}
            whileInView={{ width: `${creditPct}%` }}
            viewport={{ once: true }}
            transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
            className="h-full rounded-full bg-[color:var(--gv-accent)]"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          <Btn variant="ink" size="md" type="button" onClick={goToPricing}>
            <Zap className="h-3.5 w-3.5" strokeWidth={2.5} />
            {isFreeTier || remaining <= 0 ? "Nâng cấp" : "Mở thêm phân tích"}
          </Btn>
        </div>
      </Card>

      <div>
        <SectionLabel>Chi tiết gói</SectionLabel>
        <Card>
          <Row label="Gói hiện tại" value={subscriptionTierLabel} onClick={goToPricing} />
          <Row label="Lịch sử thanh toán" onClick={goToPricing} />
        </Card>
      </div>

      <div className="rounded-xl border border-[color:var(--gv-accent)]/25 bg-[color:var(--gv-accent)]/8 p-4">
        <div className="flex flex-wrap items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[color:var(--gv-accent)]/15">
            <Zap className="h-4 w-4 text-[color:var(--gv-accent-deep)]" strokeWidth={2.2} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="mb-0.5 text-sm font-bold text-[color:var(--gv-ink)]">Mở thêm phân tích</p>
            <p className="text-xs text-[color:var(--gv-ink-3)]">Chọn gói phù hợp trên trang thanh toán.</p>
          </div>
          <Btn variant="accent" size="sm" type="button" onClick={goToPricing} className="shrink-0">
            Xem gói
          </Btn>
        </div>
      </div>
    </motion.div>
  );
}

const NicheToggleChip = memo(function NicheToggleChip({
  name,
  id,
  selected,
  isFocus,
  disabled,
  onToggle,
}: {
  name: string;
  id: number;
  selected: boolean;
  isFocus: boolean;
  disabled?: boolean;
  onToggle: (id: number) => void;
}) {
  const handleClick = useCallback(() => onToggle(id), [id, onToggle]);
  return (
    <motion.button
      type="button"
      disabled={disabled}
      onClick={handleClick}
      whileTap={{ scale: 0.98 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
      className={`flex items-center justify-between gap-2 rounded-lg border px-4 py-3.5 text-left text-sm transition-colors duration-[120ms] ${
        selected
          ? "border-[color:var(--gv-ink)] bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
          : "border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] text-[color:var(--gv-ink)] hover:border-[color:var(--gv-ink-3)]"
      } disabled:opacity-50`}
    >
      <span className="font-medium">
        {name}
        {isFocus && selected ? (
          <span className="ml-1.5 font-mono text-[9px] font-semibold uppercase tracking-wider opacity-70">
            · trọng tâm
          </span>
        ) : null}
      </span>
      <AnimatePresence initial={false}>
        {selected ? (
          <motion.span
            key="check"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            className="inline-flex"
          >
            <Check className="h-4 w-4" strokeWidth={2.5} />
          </motion.span>
        ) : null}
      </AnimatePresence>
    </motion.button>
  );
});

function NichePanel({
  profile,
  niches,
  nicheLoading,
  updateProfile: updateMutation,
}: {
  profile: ProfileRow | null | undefined;
  niches: { id: number; name: string }[] | undefined;
  nicheLoading: boolean;
  updateProfile: ProfileUpdateMutation;
}) {
  const serverSelected = useMemo(() => {
    const ids = profile?.niche_ids;
    if (Array.isArray(ids) && ids.length > 0) return normalizeNicheIds(ids);
    if (profile?.primary_niche != null) return [profile.primary_niche];
    return [];
  }, [profile?.niche_ids, profile?.primary_niche]);

  const serverKey = useMemo(() => serverSelected.join(","), [serverSelected]);

  const [draft, setDraft] = useState<number[] | null>(null);

  useEffect(() => {
    setDraft(null);
  }, [serverKey]);

  const selected = draft ?? serverSelected;

  const handleToggle = useCallback(
    (id: number) => {
      const base = draft ?? serverSelected;
      const set = new Set(base);
      if (set.has(id)) {
        set.delete(id);
      } else {
        if (base.length >= MAX_CREATOR_NICHES) return;
        set.add(id);
      }
      const next = normalizeNicheIds(Array.from(set));
      if (next.length >= MIN_CREATOR_NICHES) {
        updateMutation.mutate({ niche_ids: next, primary_niche: next[0] });
        setDraft(null);
      } else {
        setDraft(next);
      }
    },
    [draft, serverSelected, updateMutation],
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
      <p className="text-sm text-[color:var(--gv-ink-3)]">
        Chọn ít nhất {MIN_CREATOR_NICHES} ngách (tối đa {MAX_CREATOR_NICHES}). Ngách chọn đầu tiên là trọng tâm — bỏ chọn
        rồi chọn lại để đổi thứ tự.
      </p>
      <p className="text-[12px] text-[color:var(--gv-ink-4)]">
        Đã chọn <span className="font-medium text-[color:var(--gv-ink)]">{selected.length}</span> /{" "}
        {MIN_CREATOR_NICHES} tối thiểu
        {draft != null && selected.length < MIN_CREATOR_NICHES ? (
          <span className="ml-1 text-[color:var(--gv-accent-deep)]"> — chưa lưu cho đến khi đủ 3 ngách</span>
        ) : null}
      </p>
      {nicheLoading ? (
        <div className="h-24 animate-pulse rounded-lg bg-[color:var(--gv-canvas-2)]" />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {(niches ?? []).map((n) => {
            const isSel = selected.includes(n.id);
            return (
              <NicheToggleChip
                key={n.id}
                id={n.id}
                name={n.name}
                selected={isSel}
                isFocus={selected[0] === n.id}
                onToggle={handleToggle}
                disabled={updateMutation.isPending}
              />
            );
          })}
        </div>
      )}
    </motion.div>
  );
}

const ALERT_DEFAULTS: { title: string; description: string; initial: boolean }[] = [
  {
    title: "Hook mới bứt phá trong ngách",
    description: "Khi 1 mẫu hook tăng >100% sử dụng tuần",
    initial: true,
  },
  {
    title: "Đối thủ post video viral",
    description: "Khi kênh trong shortlist post bài >2× view trung bình",
    initial: true,
  },
  {
    title: "Báo cáo tuần",
    description: "Email tổng hợp gửi mỗi sáng thứ Hai",
    initial: false,
  },
  {
    title: "Sound đang lên",
    description: "Khi 1 sound được dùng >500 video trong ngách",
    initial: false,
  },
];

function AlertsPanel() {
  const [flags, setFlags] = useState(() => ALERT_DEFAULTS.map((a) => a.initial));
  const toggle = useCallback((i: number) => {
    setFlags((prev) => {
      const next = [...prev];
      next[i] = !next[i];
      return next;
    });
  }, []);

  return (
    <div className="flex flex-col gap-2">
      {ALERT_DEFAULTS.map((row, i) => (
        <Card key={row.title} className="flex items-center justify-between gap-4 p-4">
          <div className="min-w-0">
            <p className="text-sm font-medium text-[color:var(--gv-ink)]">{row.title}</p>
            <p className="text-xs text-[color:var(--gv-ink-3)]">{row.description}</p>
          </div>
          <SettingsToggle on={flags[i] ?? false} onToggle={() => toggle(i)} />
        </Card>
      ))}

      <div className="mt-6">
        <SectionLabel>Ngôn ngữ & khu vực</SectionLabel>
        <Card>
          <Row label="Ngôn ngữ" onClick={() => {}}>
            <div className="flex items-center gap-2">
              <Globe className="h-3.5 w-3.5 text-[color:var(--gv-ink-4)]" />
              <span className="text-sm font-medium text-[color:var(--gv-ink)]">Tiếng Việt</span>
              <ChevronRight className="h-3.5 w-3.5 text-[color:var(--gv-ink-4)]" strokeWidth={2} />
            </div>
          </Row>
        </Card>
      </div>
    </div>
  );
}

function PlaceholderSection({ message }: { message: string }) {
  return (
    <Card className="p-10 text-center">
      <p className="text-sm text-[color:var(--gv-ink-4)]">{message}</p>
    </Card>
  );
}

function HistoryPanelSkeleton() {
  return (
    <div className="space-y-0 border-b border-[color:var(--gv-rule)] last:border-0">
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className="flex animate-pulse items-center justify-between border-b border-[color:var(--gv-rule)] px-4 py-3.5 last:border-0"
        >
          <div className="flex flex-1 items-center gap-3.5">
            <div className="h-7 w-7 rounded bg-[color:var(--gv-canvas-2)]" />
            <div className="flex-1 space-y-2">
              <div className="h-3 w-32 rounded bg-[color:var(--gv-canvas-2)]" />
              <div className="h-2 w-48 rounded bg-[color:var(--gv-canvas-2)]" />
            </div>
          </div>
          <div className="h-3 w-16 rounded bg-[color:var(--gv-canvas-2)]" />
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
            <div className="px-4 py-8 text-center text-sm text-[color:var(--gv-ink-3)]">Chưa có lịch sử phân tích.</div>
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
                    ? `−${Math.abs(tx.delta)} phân tích`
                    : `+${tx.delta} phân tích`;
              const isFree = tx.delta === 0;
              return (
                <motion.div
                  key={tx.id}
                  className="flex items-center justify-between border-b border-[color:var(--gv-rule)] px-4 py-3.5 last:border-0"
                  initial={{ opacity: 0, x: -12 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.3, delay: idx * 0.06, ease: [0.16, 1, 0.3, 1] }}
                >
                  <div className="flex min-w-0 items-center gap-3.5">
                    <Activity className="h-5 w-5 shrink-0 text-[color:var(--gv-ink-4)]" strokeWidth={2} />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-[color:var(--gv-ink)]">{label}</p>
                      <p className="font-mono text-[11px] text-[color:var(--gv-ink-4)]">
                        {dateLabel} · {timeLabel}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`ml-2 shrink-0 font-mono text-xs font-semibold ${
                      isFree ? "text-[color:var(--gv-pos)]" : "text-[color:var(--gv-ink-3)]"
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
    <div className="mt-12 w-full">
      <SectionLabel>Tài khoản</SectionLabel>
      <Card>
        <Dialog.Root open={open} onOpenChange={setOpen}>
          <Dialog.Trigger asChild>
            <button
              type="button"
              className="flex w-full items-center justify-between px-4 py-3.5 text-left text-sm font-medium text-[color:var(--gv-danger)] transition-colors duration-[120ms] hover:bg-[color:var(--gv-danger)]/5"
            >
              Đăng xuất
              <ChevronRight className="h-3.5 w-3.5 text-[color:var(--gv-ink-4)]" strokeWidth={2} />
            </button>
          </Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" />
            <Dialog.Content
              className="fixed left-1/2 top-1/2 z-50 w-[calc(100vw-2rem)] max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5 shadow-2xl outline-none"
              aria-describedby={undefined}
            >
              <Dialog.Title className="mb-4 font-bold text-[color:var(--gv-ink)]">Đăng xuất khỏi GetViews?</Dialog.Title>
              <div className="flex gap-2.5">
                <Dialog.Close asChild>
                  <button
                    type="button"
                    className="flex-1 rounded-xl border border-[color:var(--gv-rule)] py-2.5 text-sm text-[color:var(--gv-ink-2)] transition-colors duration-[120ms] hover:bg-[color:var(--gv-canvas-2)]"
                  >
                    Huỷ
                  </button>
                </Dialog.Close>
                <button
                  type="button"
                  onClick={onConfirm}
                  disabled={logout.isPending}
                  className="flex-1 rounded-xl bg-[color:var(--gv-danger)] py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
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
  const updateProfileMutation = useUpdateProfile();
  const logout = useLogout();

  const userEmail = user?.email ?? "";
  const [activeSection, setActiveSection] = useState<SettingsSectionId>("profile");

  const goLearnMore = useCallback(() => navigate("/app/learn-more"), [navigate]);

  const sectionTitle = useMemo(
    () => SETTINGS_SECTIONS.find((s) => s.id === activeSection)?.label ?? "",
    [activeSection],
  );

  if (profileError) {
    return (
      <AppLayout active="settings" enableMobileSidebar>
        <div className="flex flex-1 items-center justify-center overflow-y-auto p-6">
          <div className="max-w-md space-y-3 text-center">
            <p className="text-sm text-[color:var(--gv-ink-2)]">Không tải được thông tin tài khoản — thử lại.</p>
            <button
              type="button"
              onClick={() => void refetch()}
              className="rounded-lg bg-[color:var(--gv-ink)] px-4 py-2 text-sm font-semibold text-[color:var(--gv-canvas)]"
            >
              Thử lại
            </button>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout active="settings" enableMobileSidebar>
      <div className="flex-1 overflow-y-auto bg-[color:var(--gv-canvas)]" style={{ scrollbarWidth: "thin" }}>
        <div className="mx-auto max-w-[1100px] px-7 pb-20 pt-8 lg:pt-10">
          <div className="grid grid-cols-1 gap-9 lg:grid-cols-[220px_minmax(0,1fr)] lg:items-start">
            <aside className="lg:sticky lg:top-8">
              <p className="mb-3 font-mono text-[9px] font-semibold uppercase tracking-wide text-[color:var(--gv-ink-4)]">
                Cài đặt
              </p>
              <nav className="flex flex-col gap-0.5" aria-label="Mục cài đặt">
                {SETTINGS_SECTIONS.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => setActiveSection(s.id)}
                    className={`rounded-md px-3 py-2.5 text-left text-[13px] font-medium transition-colors duration-[120ms] ${
                      activeSection === s.id
                        ? "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
                        : "text-[color:var(--gv-ink-2)] hover:bg-[color:var(--gv-canvas-2)]"
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </nav>
            </aside>

            <div className="min-w-0">
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
              >
                <h1 className="gv-tight mb-1.5 text-4xl font-bold tracking-tight text-[color:var(--gv-ink)]">{sectionTitle}</h1>
              </motion.div>
              <hr className="mb-6 mt-[18px] border-0 border-t border-[color:var(--gv-rule)]" />

              {activeSection === "profile" ? (
                <ProfileSettingsSection
                  profile={profile}
                  userEmail={userEmail}
                  loading={profileLoading}
                  updateProfile={updateProfileMutation}
                  goLearnMore={goLearnMore}
                />
              ) : null}

              {activeSection === "niches" ? (
                <NichePanel
                  profile={profile}
                  niches={niches}
                  nicheLoading={nicheLoading}
                  updateProfile={updateProfileMutation}
                />
              ) : null}

              {activeSection === "alerts" ? <AlertsPanel /> : null}

              {activeSection === "export" ? (
                <PlaceholderSection message="Đang phát triển — xuất dữ liệu sẽ có trong bản cập nhật tới." />
              ) : null}

              {activeSection === "billing" ? (
                <div className="space-y-8">
                  <PlanPanel
                    navigate={navigate}
                    profile={profile}
                    subscription={subscription ?? undefined}
                    loading={profileLoading}
                  />
                  <HistoryPanel transactions={transactions} loading={txLoading} />
                </div>
              ) : null}

              {activeSection === "team" ? (
                <PlaceholderSection message="Đang phát triển — quản lý nhóm sẽ có trong bản cập nhật tới." />
              ) : null}
            </div>
          </div>

          <LogoutSection logout={logout} navigate={navigate} />

          <p className="mt-10 text-center font-mono text-[11px] text-[color:var(--gv-ink-4)]">Getviews.vn · v1.0.0</p>
        </div>
      </div>
    </AppLayout>
  );
}
