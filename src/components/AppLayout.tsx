import { useState, useRef, useEffect, type ReactNode } from "react";
import { useNavigate } from 'react-router';
import {
  Plus,
  Home,
  MessageCircle,
  TrendingUp,
  Users,
  FileText,
  Settings,
  LogOut,
  X,
  Pin,
  PinOff,
  Pencil,
  Trash2,
  MoreHorizontal,
  Check,
  BookOpen,
  Menu,
} from 'lucide-react';
import { motion, AnimatePresence } from "motion/react";
import { useAuth } from "@/lib/auth";
import { useProfile } from "@/hooks/useProfile";
import { useTopNiches } from "@/hooks/useTopNiches";
import { useChatSessions, useDeleteSession, useUpdateSession } from "@/hooks/useChatSessions";
import { chatKeys } from "@/hooks/useChatSession";
import { useQueryClient } from "@tanstack/react-query";
import { UsageArc } from "@/components/UsageArc";
import { BottomTabBar } from "@/components/BottomTabBar";

type Session = {
  id: string;
  first_message: string | null;
  title?: string | null;
  label?: string;
};

/* ── Logo mark — 30x30 ink square, accent-pink compass spoke icon. ── */
function LogoMark() {
  return (
    <div className="w-[30px] h-[30px] rounded-[6px] bg-[color:var(--gv-ink)] flex items-center justify-center flex-shrink-0">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M8 1v14M1 8h14M3.05 3.05l9.9 9.9M12.95 3.05l-9.9 9.9"
          stroke="var(--gv-accent)"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
}

/* ── NicheOfYoursBlock ──────────────────────────────────────────────────────
 * "Ngách Của Bạn" sidebar block — 3 rows with label + weekly hot count.
 *
 * The user's primary niche floats to the top; the other two slots fill by
 * weekly video count (from niche_intelligence.video_count_7d). No schema
 * for "tracked niches" exists yet, so the 2nd/3rd rows are the hottest
 * niches overall — pragmatic until a Settings-level picker lands.
 */
function NicheOfYoursBlock() {
  const { data: profile } = useProfile();
  const { data: niches = [] } = useTopNiches(profile?.primary_niche ?? null, 3);
  if (niches.length === 0) return null;

  return (
    <div className="px-4 mb-3">
      <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)] mb-2">
        Ngách của bạn
      </p>
      <ul className="flex flex-col gap-0.5">
        {niches.map((n) => (
          <li key={n.id}>
            <div className="flex items-center justify-between gap-2 rounded-md px-2.5 py-1.5 text-xs hover:bg-black/[0.04]">
              <span className="truncate text-[color:var(--gv-ink-2)]">{n.name}</span>
              <span className="gv-mono text-[10px] text-[color:var(--gv-pos-deep)] shrink-0">
                ↑ {n.hot}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ── Nav item ── */
function NavItem({
  icon: Icon,
  label,
  active = false,
  disabled = false,
  badge,
  onClick,
}: {
  icon: React.ElementType;
  label: string;
  active?: boolean;
  disabled?: boolean;
  /** Small right-aligned label, e.g. "Sắp có" on placeholder entries. */
  badge?: string;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      aria-disabled={disabled || undefined}
      className={`w-full text-left px-2.5 py-2 rounded-lg text-sm ${
        active ? 'bg-[var(--border)] text-[var(--ink)]' : 'text-[var(--ink-soft)]'
      } ${disabled ? 'opacity-60 cursor-default' : 'hover:bg-[var(--border)] hover:text-[var(--ink)]'} transition-colors duration-[120ms]`}
    >
      <div className="flex items-center gap-2.5">
        <Icon className="w-4 h-4" strokeWidth={1.8} />
        <span className="font-semibold flex-1">{label}</span>
        {badge ? (
          <span className="text-[9px] uppercase tracking-wider text-[var(--faint)] font-medium">
            {badge}
          </span>
        ) : null}
      </div>
    </button>
  );
}

/* ── Delete confirmation dialog ── */
function DeleteConfirmDialog({
  onConfirm,
  onCancel,
}: {
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
        className="fixed inset-0 z-[300] bg-black/40 backdrop-blur-[2px]"
        onClick={onCancel}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
        className="fixed z-[301] left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[320px] bg-[var(--surface)] border border-[var(--border)] rounded-2xl shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
              <Trash2 className="w-4 h-4 text-[var(--danger)]" strokeWidth={1.8} />
            </div>
            <p className="font-extrabold text-sm text-[var(--ink)]">Xoá cuộc trò chuyện</p>
          </div>
          <p className="text-xs text-[var(--ink-soft)] leading-relaxed mb-5">
            Bạn có chắc muốn xoá cuộc trò chuyện này không?
            <br />
            <span className="text-[var(--ink)] font-semibold">Tất cả phân tích và insights sẽ bị xoá vĩnh viễn.</span>
          </p>
          <div className="flex gap-2">
            <button
              onClick={onCancel}
              className="flex-1 py-2 px-3 rounded-lg text-xs font-semibold text-[var(--ink-soft)] bg-[var(--surface-alt)] hover:bg-[var(--border)] transition-colors duration-[120ms]"
            >
              Huỷ
            </button>
            <button
              onClick={onConfirm}
              className="flex-1 py-2 px-3 rounded-lg text-xs font-semibold text-white bg-[var(--danger)] hover:opacity-90 transition-opacity duration-[120ms]"
            >
              Xoá vĩnh viễn
            </button>
          </div>
        </div>
      </motion.div>
    </>
  );
}

/* ── Context menu ── */
function ContextMenu({
  isPinned,
  top,
  left,
  onPin,
  onRename,
  onDelete,
  onClose,
}: {
  isPinned: boolean;
  top: number;
  left: number;
  onPin: () => void;
  onRename: () => void;
  onDelete: () => void;
  onClose: () => void;
}) {
  return (
    <>
      {/* Backdrop — onClick fires AFTER the menu button's onClick, so Delete
          resolves before the menu closes. onMouseDown/onTouchStart would fire
          before the button click and race with it on mobile. */}
      <div className="fixed inset-0 z-[199]" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: -4 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: -4 }}
        transition={{ duration: 0.1, ease: 'easeOut' }}
        className="fixed z-[200] w-[152px] bg-[var(--surface)] border border-[var(--border)] rounded-lg shadow-xl overflow-hidden"
        style={{ top, left }}
        onClick={(e) => e.stopPropagation()}
      >
      <button
        onClick={() => { onPin(); onClose(); }}
        className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-[var(--ink-soft)] hover:bg-[var(--surface-alt)] hover:text-[var(--ink)] transition-colors duration-[100ms]"
      >
        {isPinned
          ? <PinOff className="w-3.5 h-3.5 flex-shrink-0" strokeWidth={1.8} />
          : <Pin className="w-3.5 h-3.5 flex-shrink-0" strokeWidth={1.8} />
        }
        <span className="font-semibold">{isPinned ? 'Bỏ ghim' : 'Ghim'}</span>
      </button>
      <button
        onClick={() => { onRename(); onClose(); }}
        className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-[var(--ink-soft)] hover:bg-[var(--surface-alt)] hover:text-[var(--ink)] transition-colors duration-[100ms]"
      >
        <Pencil className="w-3.5 h-3.5 flex-shrink-0" strokeWidth={1.8} />
        <span className="font-semibold">Đổi tên</span>
      </button>
      <div className="mx-2 border-t border-[var(--border)]" />
      <button
        onClick={() => { onDelete(); onClose(); }}
        className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-[var(--danger)] hover:bg-red-50/40 transition-colors duration-[100ms]"
      >
        <Trash2 className="w-3.5 h-3.5 flex-shrink-0" strokeWidth={1.8} />
        <span className="font-semibold">Xoá</span>
      </button>
    </motion.div>
    </>
  );
}

/* ── Session row ── */
function SessionRow({
  session,
  isPinned,
  onNavigate,
  onPin,
  onDelete,
  onRename,
}: {
  session: Session;
  isPinned: boolean;
  onNavigate: () => void;
  onPin: () => void;
  onDelete: () => void;
  onRename: (newLabel: string) => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const [renaming, setRenaming] = useState(false);
  const [draft, setDraft] = useState(session.label ?? session.title ?? session.first_message ?? "");
  const inputRef = useRef<HTMLInputElement>(null);
  const moreRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (renaming) inputRef.current?.focus();
  }, [renaming]);

  const commitRename = () => {
    const trimmed = draft.trim();
    if (trimmed) onRename(trimmed);
    else setDraft(session.label ?? session.title ?? session.first_message ?? "");
    setRenaming(false);
  };

  const openMenu = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (moreRef.current) {
      const rect = moreRef.current.getBoundingClientRect();
      const MENU_W = 152;
      const MENU_H = 120; // approximate: 3 buttons + separator
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      // Prefer menu to the left of the button; clamp so it never goes off-screen.
      const rawLeft = rect.left - MENU_W + rect.width;
      const left = Math.max(8, Math.min(rawLeft, vw - MENU_W - 8));
      // Prefer below the button; flip above if not enough room.
      const rawTop = rect.bottom + 4;
      const top = rawTop + MENU_H > vh ? rect.top - MENU_H - 4 : rawTop;
      setMenuPos({ top, left });
    }
    setMenuOpen(true);
  };

  const displayLabel = session.label ?? session.title ?? session.first_message ?? "Phiên chat";

  return (
    <div className="relative group/row">
      {renaming ? (
        <div className="flex items-center gap-1 px-2 py-1.5">
          <input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commitRename();
              if (e.key === 'Escape') { setDraft(displayLabel); setRenaming(false); }
            }}
            onBlur={commitRename}
            className="flex-1 min-w-0 text-xs bg-[var(--surface-alt)] border border-[var(--purple)]/60 rounded px-2 py-1 text-[var(--ink)] outline-none"
          />
          <button
            onMouseDown={(e) => { e.preventDefault(); commitRename(); }}
            className="w-5 h-5 flex items-center justify-center rounded text-[var(--purple)] hover:bg-[var(--border)] flex-shrink-0"
          >
            <Check className="w-3 h-3" strokeWidth={2.5} />
          </button>
        </div>
      ) : (
        <div className="flex items-center rounded-lg hover:bg-[var(--border)] transition-colors duration-[120ms]">
          <button
            onClick={onNavigate}
            title={displayLabel}
            className="flex-1 min-w-0 text-left flex items-center gap-1 pl-2.5 py-2 text-xs text-[var(--ink-soft)] hover:text-[var(--ink)]"
          >
            {isPinned && (
              <Pin className="w-2.5 h-2.5 flex-shrink-0 text-[var(--purple)] rotate-45" strokeWidth={2} />
            )}
            <span className="truncate min-w-0">{displayLabel}</span>
          </button>

          {/* More button — separate element so it never competes with row navigation.
              44×44 touch target on mobile; fades in on desktop hover only. */}
          <button
            ref={moreRef}
            onClick={openMenu}
            aria-label="Tuỳ chọn phiên chat"
            className={`flex-shrink-0 flex items-center justify-center rounded transition-colors duration-[100ms]
              w-9 h-9 lg:w-6 lg:h-6
              hover:text-[var(--ink-soft)] hover:bg-[var(--border)]
              lg:opacity-0 lg:group-hover/row:opacity-100
              ${menuOpen ? 'lg:opacity-100 text-[var(--ink-soft)]' : 'text-[var(--faint)]'}`}
          >
            <MoreHorizontal className="w-3.5 h-3.5" strokeWidth={1.8} />
          </button>
        </div>
      )}

      {/* Context menu rendered at fixed screen position — never clipped by scroll */}
      <AnimatePresence>
        {menuOpen && (
          <ContextMenu
            isPinned={isPinned}
            top={menuPos.top}
            left={menuPos.left}
            onPin={onPin}
            onRename={() => setRenaming(true)}
            onDelete={onDelete}
            onClose={() => setMenuOpen(false)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

/* ════════════════════════════════════════════════
   AppLayout
════════════════════════════════════════════════ */
interface AppLayoutProps {
  active?: "home" | "chat" | "trends" | "settings";
  children: ReactNode;
  enableMobileSidebar?: boolean;
}

export function AppLayout({ active, children, enableMobileSidebar = false }: AppLayoutProps) {
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  const { data: profile } = useProfile();
  const { data: sessionsData } = useChatSessions();
  const qc = useQueryClient();
  const deleteSession = useDeleteSession();
  const updateSession = useUpdateSession();
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const [pinnedIds, setPinnedIds] = useState<Set<string>>(new Set());
  // Derive session list directly from TanStack Query cache — no local copy.
  // The optimistic delete in useDeleteSession mutates the cache immediately,
  // so removing the local useState/useEffect eliminates the race where the
  // useEffect would re-add a deleted session after onSettled invalidation.
  const sessions: Session[] = (sessionsData ?? []).map((s) => ({
    id: s.id,
    first_message: s.first_message,
    title: s.title ?? null,
  }));

  const pinned = sessions.filter((s) => pinnedIds.has(s.id));
  const recent = sessions.filter((s) => !pinnedIds.has(s.id));

  const handlePin = (id: string) =>
    setPinnedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const handleDelete = (id: string) => {
    setDeleteConfirmId(id);
  };

  const confirmDelete = () => {
    const id = deleteConfirmId;
    if (!id) return;
    setDeleteConfirmId(null);
    deleteSession.mutate(id, {
      onSuccess: () => {
        qc.removeQueries({ queryKey: chatKeys.session(id) });
        qc.removeQueries({ queryKey: chatKeys.messages(id) });
        setPinnedIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
        const activeId = new URLSearchParams(window.location.search).get("session");
        if (activeId === id) navigate("/app/chat");
      },
    });
  };

  const handleRename = (id: string, label: string) => {
    updateSession.mutate({ sessionId: id, title: label });
  };

  const displayName =
    (profile?.display_name as string | null | undefined) ||
    user?.user_metadata?.full_name ||
    user?.email?.split("@")[0] ||
    "User";
  const email = user?.email ?? "";
  const initials = displayName
    .split(" ")
    .map((n: string) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const avatarUrl =
    (user?.user_metadata?.avatar_url as string | undefined) ||
    (user?.user_metadata?.picture as string | undefined);


  const handleLogout = async () => {
    setShowProfileModal(false);
    await signOut();
    navigate("/login");
  };

  /* ── Shared sidebar inner content ── */
  function SidebarContent({ onClose }: { onClose?: () => void }) {
    return (
      <>
        {/* Brand mark — 30x30 ink logo + wordmark with cyan dot + mono kicker */}
        <div className="flex items-center justify-between px-3 mb-4">
          <div className="flex items-center gap-2.5 min-w-0">
            <LogoMark />
            <div className="min-w-0">
              <span
                className="block text-[20px] font-bold text-[color:var(--gv-ink)] leading-none"
                style={{ letterSpacing: "-0.04em" }}
              >
                Getviews<span className="text-[color:var(--gv-accent-2-deep)]">.</span>
              </span>
              <p className="mt-1 text-[9px] font-semibold uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
                Studio · Creator
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              title="Chat mới"
              onClick={() => {
                navigate("/app/chat");
                onClose?.();
              }}
              className="w-7 h-7 flex items-center justify-center rounded-lg text-[var(--faint)] hover:text-[var(--ink-soft)] hover:bg-[var(--border)] transition-colors duration-[120ms]"
            >
              <Plus className="w-4 h-4" strokeWidth={1.8} />
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="w-7 h-7 flex items-center justify-center rounded-lg text-[var(--faint)] hover:text-[var(--ink-soft)] hover:bg-[var(--border)] transition-colors duration-[120ms]"
              >
                <X className="w-4 h-4" strokeWidth={1.8} />
              </button>
            )}
          </div>
        </div>

        {/* Primary nav — the 4 design surfaces (2 live, 2 "Sắp có"). */}
        <div className="flex flex-col gap-0.5 px-2 mb-3">
          <NavItem
            icon={Home}
            label="Studio"
            active={active === "home"}
            onClick={() => {
              navigate("/app");
              onClose?.();
            }}
          />
          <NavItem
            icon={TrendingUp}
            label="Xu hướng"
            active={active === "trends"}
            onClick={() => {
              navigate("/app/trends");
              onClose?.();
            }}
          />
          <NavItem
            icon={Users}
            label="Kênh tham chiếu"
            badge="Sắp có"
            disabled
          />
          <NavItem
            icon={FileText}
            label="Kịch bản"
            badge="Sắp có"
            disabled
          />
        </div>

        {/* Chat — secondary, kept accessible while Answer isn't built. */}
        <div className="flex flex-col gap-0.5 px-2 mb-3">
          <NavItem
            icon={MessageCircle}
            label="Chat"
            active={active === "chat"}
            onClick={() => {
              navigate("/app/chat");
              onClose?.();
            }}
          />
        </div>

        {/* Ngách của bạn — mini-block above the recents list. */}
        <NicheOfYoursBlock />

        {/* Divider */}
        <div className="mx-3 mb-3 border-t border-[var(--border)]" />

        {/* Session lists */}
        <div className="flex-1 overflow-y-auto px-2 flex flex-col min-h-0" style={{ scrollbarWidth: 'none' }}>
          <AnimatePresence initial={false}>
            {pinned.length > 0 && (
              <motion.div
                key="pinned-section"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.18, ease: 'easeInOut' }}
                className="overflow-hidden"
              >
                <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--faint)] px-2 mb-1 mt-0.5 flex items-center gap-1.5">
                  <Pin className="w-2.5 h-2.5 rotate-45" strokeWidth={2} />
                  Ghim
                </p>
                <div className="flex flex-col gap-0.5 mb-3">
                  {pinned.map((session) => (
                    <SessionRow
                      key={session.id}
                      session={session}
                      isPinned
                      onNavigate={() => {
                        navigate(`/app/chat?session=${session.id}`);
                        onClose?.();
                      }}
                      onPin={() => handlePin(session.id)}
                      onDelete={() => handleDelete(session.id)}
                      onRename={(label) => handleRename(session.id, label)}
                    />
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {recent.length > 0 && (
            <>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--faint)] px-2 mb-1 flex items-center gap-1.5">
                Gần đây
              </p>
              <div className="flex flex-col gap-0.5">
                {recent.map((session) => (
                  <SessionRow
                    key={session.id}
                    session={session}
                    isPinned={false}
                    onNavigate={() => {
                      navigate(`/app/chat?session=${session.id}`);
                      onClose?.();
                    }}
                    onPin={() => handlePin(session.id)}
                    onDelete={() => handleDelete(session.id)}
                    onRename={(label) => handleRename(session.id, label)}
                  />
                ))}
              </div>
            </>
          )}

          {sessions.length === 0 && (
            <p className="px-2 py-3 text-[11px] text-[var(--faint)]">
              Chưa có hội thoại nào.
            </p>
          )}
        </div>

        {/* Divider */}
        <div className="mx-3 mt-3 mb-2 border-t border-[var(--border)]" />

        {/* Bottom: settings + arc + avatar */}
        <div className="flex items-center justify-between px-3">
          <button
            onClick={() => { navigate('/app/settings'); onClose?.(); }}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-[var(--faint)] hover:text-[var(--ink-soft)] hover:bg-[var(--border)] transition-colors duration-[120ms]"
            title="Cài đặt"
          >
            <Settings className="w-[18px] h-[18px]" strokeWidth={1.7} />
          </button>
          {profile ? (
            <UsageArc
              used={((profile as { deep_credits_total?: number }).deep_credits_total ?? 50) - (profile.deep_credits_remaining ?? 0)}
              limit={(profile as { deep_credits_total?: number }).deep_credits_total ?? 50}
            />
          ) : null}
          <button
            type="button"
            title={displayName}
            onClick={() => setShowProfileModal((v) => !v)}
            className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full ring-2 ring-transparent transition-all duration-[120ms] hover:ring-[var(--border-active)]"
          >
            {avatarUrl ? (
              <img src={avatarUrl} alt={displayName} className="h-full w-full object-cover" />
            ) : (
              <span className="flex h-full w-full items-center justify-center bg-gradient-to-br from-[#a855f7] to-[#7c3aed] text-[10px] font-extrabold text-white">
                {initials}
              </span>
            )}
          </button>
        </div>
      </>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-[var(--background)]">
      {/* ── Desktop ─────────────────────────── */}
      <div className="hidden lg:flex flex-1 overflow-hidden">
        <div className="flex w-full h-full">

          {/* ── Sidebar ─── */}
          <aside className="w-[240px] flex-shrink-0 bg-[color:var(--gv-canvas-2)] flex flex-col py-4 border-r border-[color:var(--gv-rule)]">
            <SidebarContent />
          </aside>

          {/* ── Main content ─────── */}
          <div className="flex-1 bg-[var(--surface-alt)] flex flex-col min-h-0 overflow-hidden">
            {children}
          </div>
        </div>
      </div>

      {/* ── Mobile ─────────────────────────── */}
      <div className="flex flex-col flex-1 lg:hidden overflow-hidden relative">
        <div
          className={`flex min-h-0 flex-1 flex-col overflow-hidden ${
            enableMobileSidebar
              ? "pb-[calc(3.5rem+env(safe-area-inset-bottom))]"
              : ""
          }`}
        >
          {children}
        </div>

        {/* Mobile bottom tab bar — only on /_app/ screens that opt in. */}
        {enableMobileSidebar ? <BottomTabBar active={active} /> : null}

        {/* Mobile sidebar trigger buttons (only when enableMobileSidebar) */}
        {enableMobileSidebar && !mobileSidebarOpen && (
          <>
            {/* Hamburger — top left */}
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="fixed top-3 left-3 z-40 w-9 h-9 flex items-center justify-center rounded-xl bg-[var(--surface)] border border-[var(--border)] text-[var(--ink-soft)] shadow-sm active:scale-95 transition-all duration-[120ms]"
              style={{ boxShadow: '0 1px 4px rgba(0,0,0,0.10)' }}
            >
              <Menu className="w-4 h-4" strokeWidth={1.8} />
            </button>

            {/* New chat — top right */}
            <button
              onClick={() => navigate('/app/chat')}
              className="fixed top-3 right-3 z-40 w-9 h-9 flex items-center justify-center rounded-xl bg-[var(--surface)] border border-[var(--border)] text-[var(--ink-soft)] shadow-sm active:scale-95 transition-all duration-[120ms]"
              style={{ boxShadow: '0 1px 4px rgba(0,0,0,0.10)' }}
            >
              <Plus className="w-4 h-4" strokeWidth={1.8} />
            </button>
          </>
        )}

        {/* Mobile sidebar drawer */}
        {enableMobileSidebar && (
          <AnimatePresence>
            {mobileSidebarOpen && (
              <>
                {/* Backdrop */}
                <motion.div
                  key="mob-backdrop"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="fixed inset-0 z-50"
                  style={{ background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(2px)' }}
                />

                {/* Drawer panel */}
                <motion.aside
                  key="mob-drawer"
                  initial={{ x: '-100%' }}
                  animate={{ x: 0 }}
                  exit={{ x: '-100%' }}
                  transition={{ duration: 0.25, ease: [0.32, 0.72, 0, 1] }}
                  className="fixed top-0 left-0 bottom-0 z-50 flex flex-col py-4 bg-[color:var(--gv-canvas-2)] border-r border-[color:var(--gv-rule)]"
                  style={{ width: 280 }}
                >
                  <SidebarContent onClose={() => setMobileSidebarOpen(false)} />
                </motion.aside>
              </>
            )}
          </AnimatePresence>
        )}

      </div>

      {/* ── Delete confirmation dialog ── */}
      <AnimatePresence>
        {deleteConfirmId && (
          <DeleteConfirmDialog
            onConfirm={confirmDelete}
            onCancel={() => setDeleteConfirmId(null)}
          />
        )}
      </AnimatePresence>

      {/* ── Profile modal ── */}
      <AnimatePresence>
        {showProfileModal && (
          <>
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="fixed inset-0 z-50"
              onClick={() => setShowProfileModal(false)}
            />
            <motion.div
              initial={{ opacity: 0, y: 6, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 6, scale: 0.97 }}
              transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
              className="fixed z-50 w-[260px]"
              style={{ bottom: '16px', left: '12px' }}
            >
              <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl shadow-2xl overflow-hidden">
                <div className="p-4">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#a855f7] to-[#7c3aed] flex items-center justify-center flex-shrink-0">
                      <span className="text-white font-extrabold text-xs">{initials}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="truncate text-sm font-extrabold text-[var(--ink)]">{displayName}</p>
                      <p className="truncate text-xs text-[var(--muted)]">{email}</p>
                    </div>
                    <button
                      onClick={() => setShowProfileModal(false)}
                      className="w-6 h-6 flex items-center justify-center rounded-md text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--surface-alt)] transition-colors duration-[120ms] flex-shrink-0"
                    >
                      <X className="w-3.5 h-3.5" strokeWidth={1.8} />
                    </button>
                  </div>
                  <div className="space-y-0.5">
                    <button
                      onClick={() => { setShowProfileModal(false); navigate('/app/settings'); }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-[var(--ink-soft)] hover:bg-[var(--surface-alt)] hover:text-[var(--ink)] transition-colors duration-[120ms]"
                    >
                      <Settings className="w-3.5 h-3.5" strokeWidth={1.8} />
                      <span className="font-semibold">Cài đặt</span>
                    </button>
                    <button
                      onClick={() => { setShowProfileModal(false); navigate('/app/learn-more'); }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-[var(--ink-soft)] hover:bg-[var(--surface-alt)] hover:text-[var(--ink)] transition-colors duration-[120ms]"
                    >
                      <BookOpen className="w-3.5 h-3.5" strokeWidth={1.8} />
                      <span className="font-semibold">Tìm hiểu thêm</span>
                    </button>
                    <div className="mx-1 my-1 border-t border-[var(--border)]" />
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-[var(--danger)] hover:bg-red-50/60 transition-colors duration-[120ms]"
                    >
                      <LogOut className="w-3.5 h-3.5" strokeWidth={1.8} />
                      <span className="font-semibold">Đăng xuất</span>
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}