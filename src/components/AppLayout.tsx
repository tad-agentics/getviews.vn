import { useState, useRef, useEffect, useMemo, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router";
import {
  Plus,
  Home,
  TrendingUp,
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
  Shield,
  Archive,
  Search,
  AlignLeft,
} from 'lucide-react';
import { motion, AnimatePresence, MotionConfig } from "motion/react";
import { BrandMark } from "@/components/BrandMark";
import { useAuth } from "@/lib/auth";
import { useProfile } from "@/hooks/useProfile";
import { useIsAdmin } from "@/hooks/useIsAdmin";
import { useNicheRowsForIds } from "@/hooks/useTopNiches";
import { profileFirstNicheId } from "@/lib/profileNiches";
import { useChatSessions, useDeleteSession, useUpdateSession } from "@/hooks/useChatSessions";
import {
  answerSessionKeys,
  useAnswerSessionsList,
  useDeleteAnswerSession,
  useRenameAnswerSession,
} from "@/hooks/useAnswerSessionQueries";
import { chatKeys } from "@/hooks/useChatSession";
import { env } from "@/lib/env";
import { readChannelHistory } from "@/lib/channelHistory";
import { useQueryClient } from "@tanstack/react-query";
import { UsageArc } from "@/components/UsageArc";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { BottomTabBar, type AppShellActive } from "@/components/BottomTabBar";

/** Sidebar row — legacy chat thread or Phase C answer (research) session. */
type Session = {
  id: string;
  first_message: string | null;
  title?: string | null;
  label?: string;
  source: "chat" | "answer" | "channel";
};

/**
 * Sidebar lockup — canonical Getviews brand mark on a magenta-ink
 * tile per Branding Guideline §05 (lockups: dark / magenta / sky).
 * The 30×30 rounded square matches the design pack's sidebar header
 * band (``shell.jsx`` brand region). The mark itself fills with
 * canvas-white so the lockup reads ink-on-magenta-on-canvas.
 */
function LogoMark() {
  return (
    <div
      className="flex h-[30px] w-[30px] flex-shrink-0 items-center justify-center rounded-[6px] bg-[color:var(--gv-accent)] text-[color:var(--gv-canvas)]"
      aria-hidden
    >
      <BrandMark size={20} />
    </div>
  );
}

/* ── NicheOfYoursBlock ──────────────────────────────────────────────────────
 * "Ngách Của Bạn" — single row from ``profileFirstNicheId`` (creator_niche_id → corpus niche_id).
 * Read-only; đổi trong Cài đặt.
 */
function NicheOfYoursBlock() {
  const { data: profile } = useProfile();

  // Two-axis refactor PR6: profile.primary_niche dropped. Resolve the
  // representative legacy niche_id from creator_niche_id (the canonical
  // UX-facing column) so the existing useNicheRowsForIds lookup
  // (keyed by legacy niche_id) keeps working unchanged.
  const sidebarIds = useMemo(() => {
    const id = profileFirstNicheId(profile);
    return id != null ? [id] : [];
  }, [profile]);

  const { data: niches = [], isPending } = useNicheRowsForIds(sidebarIds.length ? sidebarIds : null);

  if (sidebarIds.length === 0) return null;

  return (
    <div className="px-4 pb-2.5 pt-[14px]">
      <p className="gv-uc mb-2.5 text-[9px] text-[color:var(--gv-ink-4)]">Ngách Của Bạn</p>
      <ul className="flex flex-col gap-1">
        {isPending && niches.length === 0
          ? sidebarIds.map((id) => (
              <li key={id}>
                <div className="flex items-center justify-between gap-2 px-2.5 py-[6px] text-[12px]">
                  <span className="truncate text-[color:var(--gv-ink-4)]">Đang tải…</span>
                </div>
              </li>
            ))
          : niches.map((n) => {
              const isFocus = sidebarIds[0] === n.id;
              return (
                <li key={n.id} aria-current={isFocus ? "true" : undefined}>
                  <div className="flex w-full items-center justify-between gap-2 px-2.5 py-[6px] text-left text-[12px] text-[color:var(--gv-ink-2)]">
                    <span className="truncate">{n.name}</span>
                    <span className="gv-mono shrink-0 text-[10px] text-[color:var(--gv-pos-deep)]">↑{n.hot}</span>
                  </div>
                </li>
              );
            })}
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
      aria-current={active ? "page" : undefined}
      className={[
        "flex w-full items-center gap-2.5 rounded-md px-3 py-[9px] text-left text-[13px] transition-colors duration-150",
        disabled
          ? "cursor-default font-medium text-[color:var(--gv-ink-2)] opacity-60"
          : active
            ? "bg-[color:var(--gv-ink)] font-semibold text-[color:var(--gv-canvas)]"
            : "font-medium text-[color:var(--gv-ink-2)] hover:bg-[rgba(20,17,12,0.05)] hover:text-[color:var(--gv-ink)]",
      ].join(" ")}
    >
      <Icon className="h-[15px] w-[15px] shrink-0" strokeWidth={1.8} />
      <span className="min-w-0 flex-1 whitespace-nowrap">{label}</span>
      {badge ? (
        <span className="shrink-0 text-[9px] font-medium uppercase tracking-wider text-[color:var(--gv-ink-4)]">
          {badge}
        </span>
      ) : null}
    </button>
  );
}

/* ── Delete confirmation dialog ── */
function DeleteConfirmDialog({
  onConfirm,
  onCancel,
  variant,
}: {
  onConfirm: () => void;
  onCancel: () => void;
  variant: "chat" | "answer";
}) {
  const title =
    variant === "answer" ? "Xoá phiên nghiên cứu" : "Xoá cuộc trò chuyện";
  const body =
    variant === "answer" ? (
      <>
        Bạn có chắc muốn xoá phiên này không?
        <br />
        <span className="text-[color:var(--gv-ink)] font-semibold">
          Toàn bộ lượt phân tích và kết quả trong phiên sẽ bị xoá vĩnh viễn — không khôi phục được.
        </span>
      </>
    ) : (
      <>
        Bạn có chắc muốn xoá cuộc trò chuyện này không?
        <br />
        <span className="text-[color:var(--gv-ink)] font-semibold">
          Tất cả phân tích và insights sẽ bị xoá vĩnh viễn.
        </span>
      </>
    );
  const confirmLabel = "Xoá vĩnh viễn";

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
        className="fixed z-[301] left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[320px] bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-[color:var(--gv-neg-soft)] flex items-center justify-center flex-shrink-0">
              <Trash2 className="w-4 h-4 text-[color:var(--gv-neg)]" strokeWidth={1.8} />
            </div>
            <p className="font-extrabold text-sm text-[color:var(--gv-ink)]">{title}</p>
          </div>
          <p className="text-xs text-[color:var(--gv-ink-2)] leading-relaxed mb-5">{body}</p>
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
              {confirmLabel}
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
        className="fixed z-[200] w-[152px] bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-lg overflow-hidden"
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
  isActive = false,
  onNavigate,
  onPin,
  onDelete,
  onRename,
}: {
  session: Session;
  isPinned: boolean;
  /** Current ``/app/answer?session=`` row — matches shell “you are here”. */
  isActive?: boolean;
  onNavigate: () => void;
  onPin?: () => void;
  onDelete?: () => void;
  onRename?: (newLabel: string) => void;
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
    if (trimmed) onRename?.(trimmed);
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

  const displayLabel =
    session.label ??
    session.title ??
    session.first_message ??
    (session.source === "answer" ? "Phiên nghiên cứu" : "Phiên chat");

  return (
    <div className="relative group/row">
      {renaming ? (
        <div className="flex items-center gap-1 px-2 py-1">
          <input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commitRename();
              if (e.key === 'Escape') { setDraft(displayLabel); setRenaming(false); }
            }}
            onBlur={commitRename}
            className="flex-1 min-w-0 text-xs bg-[color:var(--gv-paper)] border border-[color:var(--gv-accent)]/50 rounded px-2 py-1 text-[color:var(--gv-ink)] outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)] focus-visible:ring-offset-1"
          />
          <button
            onMouseDown={(e) => { e.preventDefault(); commitRename(); }}
            type="button"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded text-[color:var(--gv-accent)] hover:bg-[color:var(--gv-rule)]"
            aria-label="Xác nhận đổi tên"
          >
            <Check className="w-3 h-3" strokeWidth={2.5} />
          </button>
        </div>
      ) : (
        <div
          className={
            "flex items-center gap-1.5 rounded-md px-2 py-1 transition-colors duration-100 " +
            (isActive && session.source === "answer"
              ? "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
              : "hover:bg-[rgba(20,17,12,0.04)]")
          }
        >
          <button
            onClick={onNavigate}
            title={displayLabel}
            aria-current={isActive && session.source === "answer" ? "true" : undefined}
            className={
              "flex min-w-0 flex-1 items-center gap-1.5 text-left text-[12px] leading-snug " +
              (isActive && session.source === "answer"
                ? "font-semibold text-[color:var(--gv-canvas)]"
                : "text-[color:var(--gv-ink-2)] hover:text-[color:var(--gv-ink)]")
            }
          >
            {isPinned && (
              <Pin
                className={
                  "h-2.5 w-2.5 flex-shrink-0 rotate-45 " +
                  (isActive && session.source === "answer"
                    ? "text-[color:var(--gv-accent-2)]"
                    : "text-[color:var(--gv-accent)]")
                }
                strokeWidth={2}
              />
            )}
            <span className="min-w-0 truncate">{displayLabel}</span>
          </button>

          {onPin && (
            <button
              ref={moreRef}
              onClick={openMenu}
              aria-label={session.source === "answer" ? "Tuỳ chọn phiên nghiên cứu" : "Tuỳ chọn phiên chat"}
              className={`flex h-11 w-11 shrink-0 items-center justify-center rounded transition-colors duration-100 max-lg:opacity-100 lg:opacity-0 lg:group-hover/row:opacity-100 ${
                isActive && session.source === "answer"
                  ? "text-[color:var(--gv-canvas)] hover:bg-[color:rgba(255,255,255,0.12)]"
                  : `hover:bg-[color:var(--gv-rule)] hover:text-[color:var(--gv-ink-2)] ${
                      menuOpen ? "lg:opacity-100 text-[color:var(--gv-ink-2)]" : "text-[color:var(--gv-ink-4)]"
                    }`
              }`}
            >
              <MoreHorizontal className="h-3.5 w-3.5" strokeWidth={1.8} />
            </button>
          )}
        </div>
      )}

      {/* Context menu rendered at fixed screen position — never clipped by scroll */}
      <AnimatePresence>
        {menuOpen && onPin && onDelete && (
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
  active?: AppShellActive;
  children: ReactNode;
  enableMobileSidebar?: boolean;
}

export function AppLayout({ active, children, enableMobileSidebar = false }: AppLayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, signOut } = useAuth();
  const { data: profile } = useProfile();
  const { isAdmin } = useIsAdmin();
  const chatSessionsQuery = useChatSessions();
  const { data: sessionsData, isPending: chatSessionsPending } = chatSessionsQuery;
  const qc = useQueryClient();
  const deleteSession = useDeleteSession();
  const updateSession = useUpdateSession();
  const deleteAnswerSessionMutation = useDeleteAnswerSession();
  const renameAnswerSession = useRenameAnswerSession();
  const cloudUrl = env.VITE_CLOUD_RUN_API_URL;
  const answerListQuery = useAnswerSessionsList(
    user?.id,
    Boolean(user?.id && cloudUrl),
    "all",
    55,
  );

  const [showProfileModal, setShowProfileModal] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{
    id: string;
    source: "chat" | "answer" | "channel";
  } | null>(null);

  const [pinnedIds, setPinnedIds] = useState<Set<string>>(new Set());
  // Merge legacy ``chat_sessions`` + Phase C ``answer_sessions`` (Cloud Run
  // list) + client-side channel history so the sidebar shows all session types.
  const sessions: Session[] = useMemo(() => {
    const chatRows = sessionsData ?? [];
    const answerRows = answerListQuery.data?.sessions ?? [];
    const channelRows = user?.id ? readChannelHistory(user.id) : [];
    type Row = { session: Session; sortMs: number };
    const merged: Row[] = [];

    for (const s of chatRows as Array<{
      id: string;
      first_message: string | null;
      title?: string | null;
      created_at: string;
    }>) {
      const ts = new Date(s.created_at).getTime();
      merged.push({
        session: {
          id: s.id,
          first_message: s.first_message,
          title: s.title ?? null,
          source: "chat",
        },
        sortMs: Number.isFinite(ts) ? ts : 0,
      });
    }
    for (const s of answerRows) {
      const iso = s.updated_at ?? s.created_at;
      const ts = iso ? new Date(iso).getTime() : 0;
      merged.push({
        session: {
          id: s.id,
          first_message: s.initial_q ?? null,
          title: s.title ?? null,
          source: "answer",
        },
        sortMs: Number.isFinite(ts) ? ts : 0,
      });
    }
    for (const c of channelRows) {
      const ts = new Date(c.visitedAt).getTime();
      merged.push({
        session: {
          id: `channel::${c.handle}`,
          first_message: c.handle,
          title: null,
          source: "channel",
        },
        sortMs: Number.isFinite(ts) ? ts : 0,
      });
    }
    merged.sort((a, b) => b.sortMs - a.sortMs);
    return merged.map((r) => r.session).slice(0, 60);
  }, [sessionsData, answerListQuery.data?.sessions, user?.id]);

  const sidebarSessionsLoading =
    chatSessionsPending || (Boolean(cloudUrl) && answerListQuery.isPending);

  const pinned = sessions.filter((s) => pinnedIds.has(s.id));
  const recent = sessions.filter((s) => !pinnedIds.has(s.id));

  const activeAnswerSessionId = useMemo(() => {
    if (location.pathname !== "/app/answer") return null;
    const q = new URLSearchParams(location.search);
    return q.get("session") ?? q.get("session_id");
  }, [location.pathname, location.search]);

  const handlePin = (id: string) =>
    setPinnedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const handleDelete = (id: string, source: Session["source"]) => {
    setDeleteTarget({ id, source });
  };

  const confirmDelete = () => {
    const t = deleteTarget;
    if (!t) return;
    setDeleteTarget(null);
    if (t.source === "answer") {
      deleteAnswerSessionMutation.mutate(t.id, {
        onSuccess: () => {
          qc.removeQueries({ queryKey: answerSessionKeys.detail(t.id) });
          void qc.invalidateQueries({ queryKey: answerSessionKeys.all });
          setPinnedIds((prev) => {
            const next = new Set(prev);
            next.delete(t.id);
            return next;
          });
          if (
            window.location.pathname === "/app/answer" &&
            new URLSearchParams(window.location.search).get("session") === t.id
          ) {
            navigate("/app/answer");
          }
        },
      });
      return;
    }
    deleteSession.mutate(t.id, {
      onSuccess: () => {
        qc.removeQueries({ queryKey: chatKeys.session(t.id) });
        qc.removeQueries({ queryKey: chatKeys.messages(t.id) });
        setPinnedIds((prev) => {
          const next = new Set(prev);
          next.delete(t.id);
          return next;
        });
        const activeId = new URLSearchParams(window.location.search).get("session");
        if (activeId === t.id) navigate("/app/answer");
      },
    });
  };

  const handleRename = (id: string, label: string, source: Session["source"]) => {
    if (source === "answer") {
      renameAnswerSession.mutate({ sessionId: id, title: label });
      return;
    }
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
        {/* Brand — cùng band với TopBar: min-h + py-3.5 (56 / 64px), viền đáy khớp header trang.
            Adds top safe-area inset so the row clears the iOS notch when the
            mobile drawer is open. h-* swapped for min-h-* so the inset
            doesn't squash the LogoMark on notched iPhones. On desktop the
            inset resolves to 0 — no visual change. */}
        <div className="box-border flex min-h-14 items-center justify-between gap-3 border-b border-[color:var(--gv-rule)] px-4 pt-[env(safe-area-inset-top)] md:min-h-16 md:px-5">
          <div className="flex min-w-0 items-center gap-2.5">
            <LogoMark />
            <div className="min-w-0 leading-none">
              <span
                className="gv-tight block text-[19px] font-bold leading-none text-[color:var(--gv-ink)] md:text-[20px]"
                style={{ letterSpacing: "-0.04em" }}
              >
                Getviews<span className="text-[color:var(--gv-accent-2-deep)]">.</span>
              </span>
              <p className="gv-uc mt-[3px] text-[9px] font-semibold text-[color:var(--gv-ink-4)] md:text-[9.5px]">
                Creator Studio
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <button
              type="button"
              title="Cuộc trò chuyện mới"
              aria-label="Cuộc trò chuyện mới"
              onClick={() => {
                navigate("/app/answer");
                onClose?.();
              }}
              className="flex h-11 w-11 items-center justify-center rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] text-[color:var(--gv-ink-2)] transition-colors hover:bg-[color:var(--gv-canvas-2)]"
            >
              <Plus className="h-3.5 w-3.5 md:h-4 md:w-4" strokeWidth={1.8} />
            </button>
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                aria-label="Đóng menu"
                className="flex h-11 w-11 items-center justify-center rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] text-[color:var(--gv-ink-2)] transition-colors hover:bg-[color:var(--gv-canvas-2)]"
              >
                <X className="h-3.5 w-3.5 md:h-4 md:w-4" strokeWidth={1.8} />
              </button>
            )}
          </div>
        </div>

        {/* Primary nav — Studio → Xu Hướng → Kho Douyin (script lives under Studio /answer); Chat via + only */}
        <nav className="flex flex-col gap-0.5 p-3">
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
            icon={Search}
            label="Khám kênh"
            active={active === "channel"}
            onClick={() => {
              navigate("/app/channel");
              onClose?.();
            }}
          />
          {/* D7 — Kho Douyin (design pack ``shell.jsx``). Badge = CN flag. */}
          <NavItem
            icon={Archive}
            label="Kho Douyin"
            active={active === "douyin"}
            badge="🇨🇳"
            onClick={() => {
              navigate("/app/douyin");
              onClose?.();
            }}
          />
          {isAdmin ? (
            <NavItem
              icon={Shield}
              label="Admin"
              active={active === "admin"}
              onClick={() => {
                navigate("/app/admin");
                onClose?.();
              }}
            />
          ) : null}
        </nav>

        <hr className="m-0 border-0 border-t border-[color:var(--gv-rule)]" />

        {/* Ngách của bạn — mini-block above the recents list. */}
        <NicheOfYoursBlock />

        <hr className="m-0 border-0 border-t border-[color:var(--gv-rule)]" />

        {/* Pinned + Gần đây — shell.jsx “Gần Đây” block: padding 14px 16px 10px, list gap 2 */}
        <div
          className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pb-2.5 pt-[14px]"
          style={{ scrollbarWidth: "none" }}
        >
          <AnimatePresence initial={false}>
            {pinned.length > 0 && (
              <motion.div
                key="pinned-section"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.18, ease: "easeInOut" }}
                className="overflow-hidden"
              >
                <p className="mb-2.5 flex items-center gap-1.5 gv-uc text-[9px] font-semibold text-[color:var(--gv-ink-4)]">
                  <Pin className="h-2.5 w-2.5 rotate-45" strokeWidth={2} />
                  Ghim
                </p>
                <div className="mb-3 flex flex-col gap-0">
                  {pinned.map((session) => (
                    <SessionRow
                      key={`${session.source}-${session.id}`}
                      session={session}
                      isPinned
                      isActive={session.source === "answer" && activeAnswerSessionId === session.id}
                      onNavigate={() => {
                        if (session.source === "answer") {
                          navigate(`/app/answer?session=${encodeURIComponent(session.id)}`);
                        } else {
                          navigate(`/app/history/chat/${session.id}`);
                        }
                        onClose?.();
                      }}
                      onPin={() => handlePin(session.id)}
                      onDelete={() => handleDelete(session.id, session.source)}
                      onRename={(label) => handleRename(session.id, label, session.source)}
                    />
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {recent.length > 0 && (
            <>
              <p className="gv-uc mb-2.5 text-[9px] text-[color:var(--gv-ink-4)]">Gần Đây</p>
              <div className="flex flex-col gap-0">
                {recent.map((session) => (
                  <SessionRow
                    key={`${session.source}-${session.id}`}
                    session={session}
                    isPinned={false}
                    isActive={session.source === "answer" && activeAnswerSessionId === session.id}
                    onNavigate={() => {
                      if (session.source === "channel") {
                        const handle = session.first_message ?? "";
                        navigate(`/app/channel?handle=${encodeURIComponent(handle)}`);
                      } else if (session.source === "answer") {
                        navigate(`/app/answer?session=${encodeURIComponent(session.id)}`);
                      } else {
                        navigate(`/app/history/chat/${session.id}`);
                      }
                      onClose?.();
                    }}
                    onPin={session.source === "channel" ? undefined : () => handlePin(session.id)}
                    onDelete={session.source === "channel" ? undefined : () => handleDelete(session.id, session.source)}
                    onRename={session.source === "channel" ? undefined : (label) => handleRename(session.id, label, session.source)}
                  />
                ))}
              </div>
            </>
          )}

          {sidebarSessionsLoading && sessions.length === 0 ? (
            <p className="py-3 text-[11px] leading-snug text-[color:var(--gv-ink-4)]">Đang tải phiên…</p>
          ) : null}
          {!sidebarSessionsLoading && sessions.length === 0 ? (
            <p className="py-3 text-[11px] leading-snug text-[color:var(--gv-ink-4)]">
              Chưa có hội thoại hay phiên nghiên cứu nào.
            </p>
          ) : null}
        </div>

        {/* Footer — shell.jsx: padding 10px 12px, border-top, gap 8; settings 6px 8px 12px; avatar 28px */}
        <div className="flex flex-col gap-2 border-t border-[color:var(--gv-rule)] px-3 py-2.5">
          <div className="flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={() => {
                navigate("/app/settings");
                onClose?.();
              }}
              className="flex min-w-0 items-center gap-2 rounded-md px-2 py-1.5 text-left text-[12px] font-medium text-[color:var(--gv-ink-3)] transition-colors hover:bg-[rgba(20,17,12,0.05)]"
              title="Cài đặt"
            >
              <Settings className="h-3.5 w-3.5 shrink-0" strokeWidth={1.7} />
              <span className="truncate">Cài đặt</span>
            </button>
            {profile ? (
              <UsageArc
                used={((profile as { credits_total?: number }).credits_total ?? 50) - (profile.credits_remaining ?? 0)}
                limit={(profile as { credits_total?: number }).credits_total ?? 50}
              />
            ) : null}
            <button
              type="button"
              title={displayName}
              aria-label={`Tài khoản: ${displayName}`}
              aria-haspopup="dialog"
              aria-expanded={showProfileModal}
              onClick={() => setShowProfileModal((v) => !v)}
              className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[color:var(--gv-accent)] text-[13px] font-semibold text-white ring-2 ring-transparent transition-all duration-[120ms] hover:ring-[color:var(--gv-rule)]"
            >
              {avatarUrl ? (
                <img src={avatarUrl} alt={displayName} className="h-full w-full object-cover" />
              ) : (
                <span className="flex h-full w-full items-center justify-center">{initials}</span>
              )}
            </button>
          </div>
        </div>
      </>
    );
  }

  return (
    // TooltipProvider lives here (not in src/root.tsx) so the
    // unauthenticated landing page doesn't init Radix tooltip
    // context — only authenticated /app/* screens need it (sidebar
    // ``<UsageArc>`` is the sole consumer).
    //
    // ``<MotionConfig reducedMotion="user">`` propagates the OS
    // ``prefers-reduced-motion`` preference into every nested
    // ``<motion.*>`` and ``<AnimatePresence>`` automatically — no
    // per-component ``useReducedMotion()`` plumbing required.
    // The landing page already strips motion via a local stub
    // (PR #243), so this only affects /app/* surfaces.
    <MotionConfig reducedMotion="user">
    <TooltipProvider delayDuration={200}>
    <div className="flex flex-col h-dvh bg-[color:var(--gv-canvas)]">
      {/* ── Desktop ─────────────────────────── */}
      <div className="hidden lg:flex flex-1 min-h-0 overflow-hidden">
        <div className="flex min-h-0 w-full flex-1">

          {/* ── Sidebar ─── */}
          <aside className="flex h-full min-h-0 w-[240px] flex-shrink-0 flex-col overflow-hidden border-r border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)]">
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
        {enableMobileSidebar ? (
          <>
            <div className="sticky top-0 z-30 flex shrink-0 items-center border-b border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-2 pt-[env(safe-area-inset-top)]">
              <button
                type="button"
                aria-label="Mở lịch sử phiên"
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-[color:var(--gv-ink-2)] transition-colors hover:bg-[color:var(--gv-canvas-2)]"
                onClick={() => setMobileNavOpen(true)}
              >
                <AlignLeft className="h-5 w-5" strokeWidth={1.8} aria-hidden />
              </button>
            </div>
            <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
              <SheetContent
                side="left"
                className="h-full w-full max-w-[min(100vw,320px)] gap-0 border-0 bg-[color:var(--gv-canvas-2)] p-0 [&>button]:hidden sm:max-w-sm"
              >
                <div className="flex h-full max-h-dvh flex-col overflow-hidden">
                  <SidebarContent onClose={() => setMobileNavOpen(false)} />
                </div>
              </SheetContent>
            </Sheet>
          </>
        ) : null}
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
      </div>

      {/* ── Delete confirmation dialog ── */}
      <AnimatePresence>
        {deleteTarget && (
          <DeleteConfirmDialog
            variant={deleteTarget.source === "channel" ? "chat" : deleteTarget.source}
            onConfirm={confirmDelete}
            onCancel={() => setDeleteTarget(null)}
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
              <div className="bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] rounded-xl overflow-hidden">
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
                      type="button"
                      onClick={() => setShowProfileModal(false)}
                      aria-label="Đóng"
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
    </TooltipProvider>
    </MotionConfig>
  );
}