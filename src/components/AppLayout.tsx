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
    <div className="mb-3 px-4 pb-2.5 pt-3.5">
      <p className="gv-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)] mb-2.5">
        Ngách Của Bạn
      </p>
      <ul className="flex flex-col gap-1">
        {niches.map((n) => (
          <li key={n.id}>
            <div className="flex items-center justify-between gap-2 rounded-md px-2.5 py-[7px] text-xs hover:bg-[rgba(20,17,12,0.04)]">
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
      className={[
        "w-full rounded-md text-left text-[13px] transition-colors duration-150",
        "flex items-center gap-2.5 px-3 py-[9px]",
        disabled
          ? "cursor-default opacity-60 font-medium text-[color:var(--gv-ink-2)]"
          : active
            ? "bg-[color:var(--gv-ink)] font-semibold text-[color:var(--gv-canvas)]"
            : "font-medium text-[color:var(--gv-ink-2)] hover:bg-[rgba(20,17,12,0.05)] hover:text-[color:var(--gv-ink)]",
      ].join(" ")}
    >
      <div className="flex min-w-0 flex-1 items-center gap-2.5">
        <Icon className="h-[15px] w-[15px] shrink-0" strokeWidth={1.8} />
        <span className="min-w-0 flex-1 whitespace-nowrap">{label}</span>
        {badge ? (
          <span className="text-[9px] uppercase tracking-wider text-[color:var(--gv-ink-4)] font-medium">
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
        className="fixed z-[301] left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[320px] bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-2xl shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-[color:var(--gv-neg-soft)] flex items-center justify-center flex-shrink-0">
              <Trash2 className="w-4 h-4 text-[color:var(--gv-neg)]" strokeWidth={1.8} />
            </div>
            <p className="font-extrabold text-sm text-[color:var(--gv-ink)]">Xoá cuộc trò chuyện</p>
          </div>
          <p className="text-xs text-[color:var(--gv-ink-2)] leading-relaxed mb-5">
            Bạn có chắc muốn xoá cuộc trò chuyện này không?
            <br />
            <span className="text-[color:var(--gv-ink)] font-semibold">Tất cả phân tích và insights sẽ bị xoá vĩnh viễn.</span>
          </p>
          <div className="flex gap-2">
            <button
              onClick={onCancel}
              className="flex-1 py-2 px-3 rounded-lg text-xs font-semibold text-[color:var(--gv-ink-2)] bg-[color:var(--gv-canvas-2)] hover:bg-[color:var(--gv-rule)] transition-colors duration-[120ms]"
            >
              Huỷ
            </button>
            <button
              onClick={onConfirm}
              className="flex-1 py-2 px-3 rounded-lg text-xs font-semibold text-white bg-[color:var(--gv-neg)] hover:opacity-90 transition-opacity duration-[120ms]"
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
        className="fixed z-[200] w-[152px] bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-lg shadow-xl overflow-hidden"
        style={{ top, left }}
        onClick={(e) => e.stopPropagation()}
      >
      <button
        onClick={() => { onPin(); onClose(); }}
        className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-[color:var(--gv-ink-2)] hover:bg-[color:var(--gv-canvas-2)] hover:text-[color:var(--gv-ink)] transition-colors duration-[100ms]"
      >
        {isPinned
          ? <PinOff className="w-3.5 h-3.5 flex-shrink-0" strokeWidth={1.8} />
          : <Pin className="w-3.5 h-3.5 flex-shrink-0" strokeWidth={1.8} />
        }
        <span className="font-semibold">{isPinned ? 'Bỏ ghim' : 'Ghim'}</span>
      </button>
      <button
        onClick={() => { onRename(); onClose(); }}
        className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-[color:var(--gv-ink-2)] hover:bg-[color:var(--gv-canvas-2)] hover:text-[color:var(--gv-ink)] transition-colors duration-[100ms]"
      >
        <Pencil className="w-3.5 h-3.5 flex-shrink-0" strokeWidth={1.8} />
        <span className="font-semibold">Đổi tên</span>
      </button>
      <div className="mx-2 border-t border-[color:var(--gv-rule)]" />
      <button
        onClick={() => { onDelete(); onClose(); }}
        className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-[color:var(--gv-neg)] hover:bg-[color:var(--gv-neg-soft)]/60 transition-colors duration-[100ms]"
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
            className="flex-1 min-w-0 text-xs bg-[color:var(--gv-paper)] border border-[color:var(--gv-accent)]/50 rounded px-2 py-1 text-[color:var(--gv-ink)] outline-none"
          />
          <button
            onMouseDown={(e) => { e.preventDefault(); commitRename(); }}
            className="w-5 h-5 flex items-center justify-center rounded text-[color:var(--gv-accent)] hover:bg-[color:var(--gv-rule)] flex-shrink-0"
          >
            <Check className="w-3 h-3" strokeWidth={2.5} />
          </button>
        </div>
      ) : (
        <div className="flex items-center rounded-md transition-colors duration-[120ms] hover:bg-[rgba(20,17,12,0.04)]">
          <button
            onClick={onNavigate}
            title={displayLabel}
            className="flex flex-1 items-center gap-1 py-[7px] pl-2.5 pr-1 text-left text-xs text-[color:var(--gv-ink-2)] hover:text-[color:var(--gv-ink)]"
          >
            {isPinned && (
              <Pin className="w-2.5 h-2.5 flex-shrink-0 text-[color:var(--gv-accent)] rotate-45" strokeWidth={2} />
            )}
            <span className="truncate min-w-0">{displayLabel}</span>
          </button>

          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            aria-label="Xóa phiên chat"
            title="Xóa"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded text-[color:var(--gv-ink-4)] transition-colors hover:bg-[color:var(--gv-rule)] hover:text-[color:var(--gv-ink-2)]"
          >
            <X className="h-3.5 w-3.5" strokeWidth={2} />
          </button>

          {/* More button — separate element so it never competes with row navigation.
              44×44 touch target on mobile; fades in on desktop hover only. */}
          <button
            ref={moreRef}
            onClick={openMenu}
            aria-label="Tuỳ chọn phiên chat"
            className={`flex-shrink-0 flex items-center justify-center rounded transition-colors duration-[100ms]
              w-9 h-9 lg:w-6 lg:h-6
              hover:text-[color:var(--gv-ink-2)] hover:bg-[color:var(--gv-rule)]
              lg:opacity-0 lg:group-hover/row:opacity-100
              ${menuOpen ? 'lg:opacity-100 text-[color:var(--gv-ink-2)]' : 'text-[color:var(--gv-ink-4)]'}`}
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
        {/* Brand mark — UIUX shell.jsx: 20px/18px padding, then full-width rule */}
        <div className="flex items-center justify-between px-5 pb-3 pt-2">
          <div className="flex min-w-0 items-center gap-2.5">
            <LogoMark />
            <div className="min-w-0">
              <span
                className="block text-[20px] font-bold leading-none text-[color:var(--gv-ink)]"
                style={{ letterSpacing: "-0.04em" }}
              >
                Getviews<span className="text-[color:var(--gv-accent-2-deep)]">.</span>
              </span>
              <p className="mt-0.5 text-[9px] font-semibold uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
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
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] text-[color:var(--gv-ink-2)] transition-colors hover:bg-[color:var(--gv-canvas-2)]"
            >
              <Plus className="h-3.5 w-3.5" strokeWidth={1.8} />
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] text-[color:var(--gv-ink-2)] transition-colors hover:bg-[color:var(--gv-canvas-2)]"
              >
                <X className="h-3.5 w-3.5" strokeWidth={1.8} />
              </button>
            )}
          </div>
        </div>

        <hr className="m-0 border-0 border-t border-[color:var(--gv-rule)]" />

        {/* Primary nav — the 4 design surfaces (2 live, 2 "Sắp có"). */}
        <div className="mb-3 flex flex-col gap-0.5 px-3 py-3">
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
            label="Xu Hướng"
            active={active === "trends"}
            onClick={() => {
              navigate("/app/trends");
              onClose?.();
            }}
          />
          <NavItem
            icon={Users}
            label="Kênh Tham Chiếu"
            badge="Sắp có"
            disabled
          />
          <NavItem
            icon={FileText}
            label="Kịch Bản"
            badge="Sắp có"
            disabled
          />
        </div>

        <hr className="m-0 border-0 border-t border-[color:var(--gv-rule)]" />

        {/* Chat — secondary, kept accessible while Answer isn't built. */}
        <div className="mb-3 flex flex-col gap-0.5 px-3">
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

        <hr className="m-0 border-0 border-t border-[color:var(--gv-rule)]" />

        {/* Ngách của bạn — mini-block above the recents list. */}
        <NicheOfYoursBlock />

        <hr className="m-0 border-0 border-t border-[color:var(--gv-rule)]" />

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
                <p className="mb-2.5 mt-0.5 flex items-center gap-1.5 px-2 gv-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
                  <Pin className="h-2.5 w-2.5 rotate-45" strokeWidth={2} />
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
              <p className="gv-mono mb-2.5 px-2 text-[9px] font-semibold uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
                Gần Đây
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
            <p className="px-2 py-3 text-[11px] text-[color:var(--gv-ink-4)]">
              Chưa có hội thoại nào.
            </p>
          )}
        </div>

        {/* Footer — UIUX: border-top rule, settings label + avatar */}
        <div className="mt-2 border-t border-[color:var(--gv-rule)] px-3 pb-1 pt-2.5">
        <div className="flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={() => { navigate('/app/settings'); onClose?.(); }}
            className="flex min-w-0 items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs font-medium text-[color:var(--gv-ink-3)] transition-colors hover:bg-[rgba(20,17,12,0.05)]"
            title="Cài đặt"
          >
            <Settings className="h-3.5 w-3.5 shrink-0" strokeWidth={1.7} />
            <span className="truncate">Cài đặt</span>
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
            className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full ring-2 ring-transparent transition-all duration-[120ms] hover:ring-[color:var(--gv-rule)]"
          >
            {avatarUrl ? (
              <img src={avatarUrl} alt={displayName} className="h-full w-full object-cover" />
            ) : (
              <span className="flex h-full w-full items-center justify-center bg-gradient-to-br from-[color:var(--gv-accent)] to-[color:var(--gv-accent-deep)] text-[10px] font-extrabold text-white">
                {initials}
              </span>
            )}
          </button>
        </div>
        </div>
      </>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-[color:var(--gv-canvas)]">
      {/* ── Desktop ─────────────────────────── */}
      <div className="hidden lg:flex flex-1 min-h-0 overflow-hidden">
        <div className="flex min-h-0 w-full flex-1">

          {/* ── Sidebar ─── */}
          <aside className="flex h-full min-h-0 w-[240px] flex-shrink-0 flex-col overflow-hidden border-r border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] pt-2 pb-4">
            <SidebarContent />
          </aside>

          {/* ── Main content — scrolls; overflow-hidden here was clipping Home past the viewport. ── */}
          <div className="flex min-h-0 flex-1 flex-col overflow-y-auto overflow-x-hidden bg-[color:var(--gv-canvas)]">
            {children}
          </div>
        </div>
      </div>

      {/* ── Mobile ─────────────────────────── */}
      <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden lg:hidden">
        <div
          className={`flex min-h-0 flex-1 flex-col overflow-y-auto overflow-x-hidden ${
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
              className="fixed top-3 left-3 z-40 w-9 h-9 flex items-center justify-center rounded-xl bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] text-[color:var(--gv-ink-2)] shadow-sm active:scale-95 transition-all duration-[120ms]"
              style={{ boxShadow: '0 1px 4px rgba(0,0,0,0.10)' }}
            >
              <Menu className="w-4 h-4" strokeWidth={1.8} />
            </button>

            {/* New chat — top right */}
            <button
              onClick={() => navigate('/app/chat')}
              className="fixed top-3 right-3 z-40 w-9 h-9 flex items-center justify-center rounded-xl bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] text-[color:var(--gv-ink-2)] shadow-sm active:scale-95 transition-all duration-[120ms]"
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
              <div className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl shadow-2xl overflow-hidden">
                <div className="p-4">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[color:var(--gv-accent)] to-[color:var(--gv-accent-deep)] flex items-center justify-center flex-shrink-0">
                      <span className="text-white font-extrabold text-xs">{initials}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="truncate text-sm font-extrabold text-[color:var(--gv-ink)]">{displayName}</p>
                      <p className="truncate text-xs text-[color:var(--gv-ink-3)]">{email}</p>
                    </div>
                    <button
                      onClick={() => setShowProfileModal(false)}
                      className="w-6 h-6 flex items-center justify-center rounded-md text-[color:var(--gv-ink-3)] hover:text-[color:var(--gv-ink)] hover:bg-[color:var(--gv-canvas-2)] transition-colors duration-[120ms] flex-shrink-0"
                    >
                      <X className="w-3.5 h-3.5" strokeWidth={1.8} />
                    </button>
                  </div>
                  <div className="space-y-0.5">
                    <button
                      onClick={() => { setShowProfileModal(false); navigate('/app/settings'); }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-[color:var(--gv-ink-2)] hover:bg-[color:var(--gv-canvas-2)] hover:text-[color:var(--gv-ink)] transition-colors duration-[120ms]"
                    >
                      <Settings className="w-3.5 h-3.5" strokeWidth={1.8} />
                      <span className="font-semibold">Cài đặt</span>
                    </button>
                    <button
                      onClick={() => { setShowProfileModal(false); navigate('/app/learn-more'); }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-[color:var(--gv-ink-2)] hover:bg-[color:var(--gv-canvas-2)] hover:text-[color:var(--gv-ink)] transition-colors duration-[120ms]"
                    >
                      <BookOpen className="w-3.5 h-3.5" strokeWidth={1.8} />
                      <span className="font-semibold">Tìm hiểu thêm</span>
                    </button>
                    <div className="mx-1 my-1 border-t border-[color:var(--gv-rule)]" />
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-[color:var(--gv-neg)] hover:bg-[color:var(--gv-neg-soft)]/70 transition-colors duration-[120ms]"
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