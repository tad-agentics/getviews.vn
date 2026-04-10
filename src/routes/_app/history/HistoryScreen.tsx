import { useState } from "react";
import { useNavigate } from "react-router";
import { Search, Pencil, Trash2 } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useAuth } from "@/hooks/useAuth";
import {
  useChatSessions,
  useDeleteSession,
  useUpdateSession,
  useSearchSessions,
} from "@/hooks/useChatSessions";

/** Copy slots + intent mapping (screen spec). */
const INTENT_BADGES: Record<string, string> = {
  video_diagnosis: "Soi Video",
  competitor_profile: "Đối thủ",
  own_channel: "Soi Kênh",
  soi_kenh: "Soi Kênh",
  brief_generation: "Brief",
  trend_spike: "Xu hướng",
  find_creators: "Tìm KOL",
  format_lifecycle: "Brief",
  follow_up: "",
  content_directions: "",
};

type SessionRow = {
  id: string;
  title: string | null;
  first_message: string | null;
  created_at: string;
  intent_type: string | null;
  credits_used: number;
};

function formatDate(dateString: string) {
  const date = new Date(dateString);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const sessionDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());

  if (sessionDate.getTime() === today.getTime()) return "Hôm nay";
  if (sessionDate.getTime() === yesterday.getTime()) return "Hôm qua";
  return date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
}

function formatTime(dateString: string) {
  return new Date(dateString).toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function sessionPreview(s: SessionRow) {
  const t = s.title?.trim();
  if (t) return t;
  return s.first_message?.trim() || "Phiên chat";
}

function HistoryListSkeleton() {
  return (
    <div className="divide-y divide-[var(--border)] bg-[var(--surface)]">
      {[0, 1, 2].map((i) => (
        <div key={i} className="px-4 py-4 animate-pulse">
          <div className="flex items-start gap-3 mb-2">
            <div className="h-5 w-16 rounded bg-[var(--border)] flex-shrink-0" />
            <div className="flex-1 space-y-2 min-w-0">
              <div className="h-3 w-full rounded bg-[var(--border)]" />
              <div className="h-3 w-4/5 rounded bg-[var(--border)]" />
            </div>
          </div>
          <div className="flex justify-between">
            <div className="h-3 w-12 rounded bg-[var(--border)]" />
            <div className="h-3 w-20 rounded bg-[var(--border)]" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function HistoryScreen() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const trimmedQuery = query.trim();
  const isSearch = trimmedQuery.length > 0;

  const {
    data: listSessions,
    isLoading: listLoading,
    isError: listError,
    refetch: refetchList,
  } = useChatSessions();
  const {
    data: searchResults,
    isLoading: searchLoading,
    isError: searchError,
    refetch: refetchSearch,
  } = useSearchSessions(trimmedQuery);

  const deleteSession = useDeleteSession();
  const updateSession = useUpdateSession();

  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");

  const sessions: SessionRow[] = (isSearch ? searchResults : listSessions) as SessionRow[];
  const isLoading = isSearch ? searchLoading : listLoading;
  const isError = isSearch ? searchError : listError;

  const refetchHistory = () => {
    if (isSearch) void refetchSearch();
    else void refetchList();
  };

  const filteredSessions = sessions ?? [];

  const groupedSessions = filteredSessions.reduce(
    (groups, sess) => {
      const dateGroup = formatDate(sess.created_at);
      if (!groups[dateGroup]) groups[dateGroup] = [];
      groups[dateGroup].push(sess);
      return groups;
    },
    {} as Record<string, SessionRow[]>,
  );

  const openRename = (s: SessionRow) => {
    setEditingId(s.id);
    setDraftTitle(sessionPreview(s));
  };

  const commitRename = (sessionId: string) => {
    const t = draftTitle.trim();
    if (t) {
      void updateSession.mutateAsync({ sessionId, title: t });
    }
    setEditingId(null);
    setDraftTitle("");
  };

  if (!session) {
    return null;
  }

  return (
    <AppLayout enableMobileSidebar>
      <AlertDialog
        open={deleteTargetId !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTargetId(null);
        }}
      >
        <AlertDialogContent className="bg-[var(--surface)] border-[var(--border)]">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-[var(--ink)]">Xoá phiên này?</AlertDialogTitle>
            <AlertDialogDescription className="text-[var(--muted)]">
              Bạn sẽ mất toàn bộ lịch sử chat.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-[var(--border)]">Huỷ</AlertDialogCancel>
            <Button
              type="button"
              variant="danger"
              onClick={() => {
                if (deleteTargetId) {
                  void deleteSession.mutateAsync(deleteTargetId);
                }
                setDeleteTargetId(null);
              }}
            >
              Xoá
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Header */}
      <div className="flex-shrink-0 h-14 bg-[var(--surface)] border-b border-[var(--border)] flex items-center px-6 pt-0 lg:px-6">
        <span className="font-extrabold text-[var(--ink)] pl-10 lg:pl-0">Lịch sử</span>
      </div>

      {/* Search Bar */}
      <div className="flex-shrink-0 p-4 bg-[var(--surface)] border-b border-[var(--border)]">
        <div className="max-w-2xl mx-auto relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--muted)]" />
          <Input
            placeholder="Tìm trong lịch sử..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto">
          {isError ? (
            <div className="flex flex-col items-center gap-3 px-4 py-12 text-center">
              <p className="text-sm text-[var(--muted)]">Không tải được lịch sử — thử lại.</p>
              <button
                type="button"
                onClick={() => refetchHistory()}
                className="text-sm text-[var(--purple)] underline"
              >
                Thử lại
              </button>
            </div>
          ) : isLoading ? (
            <HistoryListSkeleton />
          ) : filteredSessions.length === 0 ? (
            <div className="px-4 py-12 text-center">
              {isSearch ? (
                <p className="text-[var(--ink-soft)]">Không tìm thấy phiên nào với từ khoá này.</p>
              ) : (
                <>
                  <p className="text-[var(--ink-soft)] mb-4">
                    Chưa có phiên nào. Dán link TikTok hoặc hỏi câu đầu tiên để bắt đầu.
                  </p>
                  <Button type="button" onClick={() => navigate("/app")} variant="primary">
                    Bắt đầu phân tích →
                  </Button>
                </>
              )}
            </div>
          ) : (
            Object.entries(groupedSessions).map(([dateGroup, groupSessions]) => (
              <div key={dateGroup}>
                <div className="px-4 py-2 bg-[var(--background)]">
                  <p className="text-xs font-medium text-[var(--faint)] uppercase tracking-wide">
                    {dateGroup}
                  </p>
                </div>
                <div className="divide-y divide-[var(--border)] bg-[var(--surface)]">
                  {groupSessions.map((session) => {
                    const badgeText = session.intent_type
                      ? (INTENT_BADGES[session.intent_type] ?? "")
                      : "";
                    const editing = editingId === session.id;

                    return (
                      <div
                        key={session.id}
                        className="flex w-full items-stretch gap-1 px-2 py-2 hover:bg-[var(--surface-alt)] transition-colors duration-[120ms]"
                      >
                        <button
                          type="button"
                          onClick={() => navigate(`/app?session=${session.id}`)}
                          className="min-h-[44px] flex-1 px-2 py-2 text-left rounded-lg"
                        >
                          {editing ? (
                            <div className="mb-2" onClick={(e) => e.stopPropagation()}>
                              <Input
                                value={draftTitle}
                                onChange={(e) => setDraftTitle(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") commitRename(session.id);
                                  if (e.key === "Escape") {
                                    setEditingId(null);
                                    setDraftTitle("");
                                  }
                                }}
                                onBlur={() => commitRename(session.id)}
                                className="text-sm"
                                autoFocus
                              />
                            </div>
                          ) : (
                            <div className="flex items-start gap-3 mb-2">
                              {badgeText ? (
                                <Badge variant="purple" className="text-xs flex-shrink-0">
                                  {badgeText}
                                </Badge>
                              ) : (
                                <span className="w-0 flex-shrink-0" aria-hidden />
                              )}
                              <p className="flex-1 text-sm text-[var(--ink)] line-clamp-2 min-w-0">
                                {sessionPreview(session)}
                              </p>
                            </div>
                          )}
                          {!editing ? (
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-mono text-[var(--faint)]">
                                {formatTime(session.created_at)}
                              </span>
                              <span className="font-mono text-[var(--muted)]">
                                {session.credits_used === 0
                                  ? "miễn phí"
                                  : `−${session.credits_used} credit`}
                              </span>
                            </div>
                          ) : null}
                        </button>
                        {!editing ? (
                          <div className="flex flex-col justify-center gap-1 pr-1 flex-shrink-0">
                            <button
                              type="button"
                              title="Đổi tên"
                              onClick={(e) => {
                                e.stopPropagation();
                                openRename(session);
                              }}
                              className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--border)] transition-colors duration-[120ms]"
                            >
                              <Pencil className="w-4 h-4" strokeWidth={1.8} />
                            </button>
                            <button
                              type="button"
                              title="Xoá"
                              onClick={(e) => {
                                e.stopPropagation();
                                setDeleteTargetId(session.id);
                              }}
                              className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg text-[var(--danger)] hover:bg-red-50/40 transition-colors duration-[120ms]"
                            >
                              <Trash2 className="w-4 h-4" strokeWidth={1.8} />
                            </button>
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </AppLayout>
  );
}
