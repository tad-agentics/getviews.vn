/**
 * Phase C.6 — /history restyle.
 * Phase D.2.4 — IntersectionObserver pagination + cross-type search.
 *
 * Unified browsing surface for both `/answer` research sessions and legacy
 * `chat_sessions`. Uses the server-side `history_union` Postgres RPC
 * (migration 20260430000003) with keyset `p_cursor` pagination + an
 * IntersectionObserver on the last row that triggers `fetchNextPage`.
 *
 * Search uses `search_history_union` (D.2.4 migration 20260501000001) so
 * a single query box now covers answer_sessions.title / initial_q +
 * chat_sessions.title / first_message + chat_messages.content. Filter
 * ribbon stays disabled while searching.
 *
 * Legacy rename / delete actions only surface on chat rows; answer
 * sessions archive via their own PATCH endpoint (not wired here).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { Pencil, Search, Trash2 } from "lucide-react";

import { AppLayout } from "@/components/AppLayout";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
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
import { useDeleteSession, useUpdateSession } from "@/hooks/useChatSessions";
import {
  type HistoryUnionRow,
  useHistoryUnion,
  useSearchHistoryUnion,
} from "@/hooks/useHistoryUnion";
import { logUsage } from "@/lib/logUsage";

import { HistoryFilterRibbon, type HistoryFilter } from "./HistoryFilterRibbon";
import { HistoryRow, relativeTime } from "./HistoryRow";

function parseFilter(raw: string | null): HistoryFilter {
  if (raw === "answer" || raw === "chat" || raw === "all") return raw;
  return "all";
}

function groupByDate(rows: HistoryUnionRow[]): Record<string, HistoryUnionRow[]> {
  return rows.reduce<Record<string, HistoryUnionRow[]>>((acc, r) => {
    const key = relativeTime(r.updated_at) || "—";
    if (!acc[key]) acc[key] = [];
    acc[key].push(r);
    return acc;
  }, {});
}

function HistoryListSkeleton() {
  return (
    <div className="divide-y divide-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="px-4 py-4 animate-pulse">
          <div className="mb-2 flex items-center gap-2">
            <div className="h-4 w-16 rounded bg-[color:var(--gv-canvas-2)]" />
            <div className="h-4 w-20 rounded bg-[color:var(--gv-canvas-2)]" />
          </div>
          <div className="h-4 w-4/5 rounded bg-[color:var(--gv-canvas-2)]" />
        </div>
      ))}
    </div>
  );
}

export default function HistoryScreen() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const filter = parseFilter(searchParams.get("filter"));
  const setFilter = (next: HistoryFilter) => {
    const params = new URLSearchParams(searchParams);
    if (next === "all") params.delete("filter");
    else params.set("filter", next);
    setSearchParams(params, { replace: true });
  };

  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(query), 300);
    return () => clearTimeout(t);
  }, [query]);
  const trimmed = debounced.trim();
  const isSearch = trimmed.length > 0;

  const unionQuery = useHistoryUnion(filter, Boolean(session) && !isSearch);
  const searchQuery = useSearchHistoryUnion(trimmed);

  const deleteSession = useDeleteSession();
  const updateSession = useUpdateSession();

  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");

  const pagedRows: HistoryUnionRow[] = useMemo(
    () => unionQuery.data?.pages.flatMap((p) => p) ?? [],
    [unionQuery.data],
  );

  const rows: HistoryUnionRow[] = useMemo(() => {
    if (isSearch) return searchQuery.data ?? [];
    return pagedRows;
  }, [isSearch, searchQuery.data, pagedRows]);

  // Client-side counts for the filter ribbon (cheap; driven by the
  // currently-loaded union pages). When search is active the ribbon is
  // disabled so counts are meaningless — we hide them.
  const counts = useMemo(() => {
    if (isSearch) return undefined;
    if (filter !== "all") return undefined;
    let answer = 0;
    let chat = 0;
    for (const r of pagedRows) {
      if (r.type === "answer") answer += 1;
      else if (r.type === "chat") chat += 1;
    }
    return { all: pagedRows.length, answer, chat };
  }, [filter, isSearch, pagedRows]);

  const loading = isSearch
    ? searchQuery.isLoading
    : unionQuery.isLoading || unionQuery.isFetching && pagedRows.length === 0;
  const errored = isSearch ? searchQuery.isError : unionQuery.isError;
  const refetch = () => (isSearch ? searchQuery.refetch() : unionQuery.refetch());
  const grouped = useMemo(() => groupByDate(rows), [rows]);

  // D.2.4 — IntersectionObserver pagination. `sentinelRef` is attached
  // to a zero-height div rendered after the last row; when it enters
  // viewport and the query still has more pages, fetch the next one.
  // Skips when a search is active (search has no pagination yet).
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const observeSentinel = useCallback(
    (node: HTMLDivElement | null) => {
      sentinelRef.current = node;
      if (!node) return;
      const target = node;
      const obs = new IntersectionObserver(
        (entries) => {
          for (const e of entries) {
            if (
              e.isIntersecting &&
              !isSearch &&
              unionQuery.hasNextPage &&
              !unionQuery.isFetchingNextPage
            ) {
              void unionQuery.fetchNextPage();
            }
          }
        },
        { rootMargin: "200px 0px" },
      );
      obs.observe(target);
      return () => obs.disconnect();
    },
    [isSearch, unionQuery],
  );

  const handleRowClick = (row: HistoryUnionRow) => {
    logUsage("history_session_open", { type: row.type, session_id: row.id });
    if (row.type === "answer") {
      navigate(`/app/answer?session=${encodeURIComponent(row.id)}`);
    } else {
      navigate(`/app/history/chat/${row.id}`);
    }
  };

  const commitRename = (id: string) => {
    const t = draftTitle.trim();
    if (t) void updateSession.mutateAsync({ sessionId: id, title: t });
    setEditingId(null);
    setDraftTitle("");
  };

  if (!session) return null;

  return (
    <AppLayout enableMobileSidebar>
      <AlertDialog
        open={deleteTargetId !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTargetId(null);
        }}
      >
        <AlertDialogContent className="bg-[color:var(--gv-paper)] border-[color:var(--gv-rule)]">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-[color:var(--gv-ink)]">
              Xoá phiên này?
            </AlertDialogTitle>
            <AlertDialogDescription className="text-[color:var(--gv-ink-3)]">
              Bạn sẽ mất toàn bộ lịch sử hội thoại.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-[color:var(--gv-rule)]">
              Huỷ
            </AlertDialogCancel>
            <Button
              type="button"
              variant="danger"
              onClick={async () => {
                const idToDelete = deleteTargetId;
                setDeleteTargetId(null);
                if (idToDelete) {
                  try {
                    await deleteSession.mutateAsync(idToDelete);
                  } catch {
                    /* optimistic rollback handled in hook */
                  }
                }
              }}
            >
              Xoá
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Header */}
      <div className="flex-shrink-0 border-b border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-6 pt-4 pb-4 lg:px-6">
        <p className="gv-mono text-[10px] uppercase tracking-[0.18em] text-[color:var(--gv-ink-4)]">
          Lịch sử nghiên cứu
        </p>
        <h1 className="gv-serif mt-1 text-[28px] font-medium leading-tight text-[color:var(--gv-ink)]">
          Tất cả các phiên
        </h1>
        <div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[color:var(--gv-ink-4)]" />
            <Input
              placeholder="Tìm trong hội thoại cũ..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <HistoryFilterRibbon
            value={filter}
            onChange={setFilter}
            disabled={isSearch}
            counts={counts}
          />
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl">
          {errored ? (
            <div className="flex flex-col items-center gap-3 px-4 py-12 text-center">
              <p className="text-sm text-[color:var(--gv-ink-3)]">
                Không tải được lịch sử — thử lại.
              </p>
              <button
                type="button"
                onClick={() => void refetch()}
                className="text-sm text-[color:var(--gv-accent)] underline"
              >
                Thử lại
              </button>
            </div>
          ) : loading ? (
            <HistoryListSkeleton />
          ) : rows.length === 0 ? (
            <div className="px-4 py-12 text-center">
              {isSearch ? (
                <p className="text-[color:var(--gv-ink-3)]">
                  Không tìm thấy phiên nào với từ khoá này.
                </p>
              ) : filter === "answer" ? (
                <>
                  <p className="mb-4 text-[color:var(--gv-ink-3)]">
                    Chưa có phiên nghiên cứu nào. Mở Studio hoặc bắt đầu từ Phiên nghiên cứu
                    mới.
                  </p>
                  <Button type="button" variant="primary" onClick={() => navigate("/app/answer")}>
                    Phiên nghiên cứu mới →
                  </Button>
                </>
              ) : filter === "chat" ? (
                <p className="text-[color:var(--gv-ink-3)]">
                  Chưa có hội thoại cũ nào để hiển thị.
                </p>
              ) : (
                <>
                  <p className="mb-4 text-[color:var(--gv-ink-3)]">
                    Chưa có phiên nào. Bắt đầu phân tích để tạo phiên đầu tiên.
                  </p>
                  <Button type="button" variant="primary" onClick={() => navigate("/app/answer")}>
                    Bắt đầu phân tích →
                  </Button>
                </>
              )}
            </div>
          ) : (
            <>
            {Object.entries(grouped).map(([dateGroup, groupRows]) => (
              <div key={dateGroup}>
                <div className="px-4 py-2 bg-[color:var(--gv-canvas-2)]">
                  <p className="gv-mono text-[10px] font-medium uppercase tracking-wide text-[color:var(--gv-ink-4)]">
                    {dateGroup}
                  </p>
                </div>
                <div className="divide-y divide-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]">
                  {groupRows.map((row) => {
                    const editing = editingId === row.id;
                    return (
                      <div key={row.id} className="relative">
                        {editing ? (
                          <div className="px-4 py-3">
                            <Input
                              value={draftTitle}
                              onChange={(e) => setDraftTitle(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") commitRename(row.id);
                                if (e.key === "Escape") {
                                  setEditingId(null);
                                  setDraftTitle("");
                                }
                              }}
                              onBlur={() => commitRename(row.id)}
                              autoFocus
                              className="text-sm"
                            />
                          </div>
                        ) : (
                          <HistoryRow
                            row={row}
                            onClick={() => handleRowClick(row)}
                            actions={
                              row.type === "chat" ? (
                                <>
                                  <button
                                    type="button"
                                    title="Đổi tên"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setEditingId(row.id);
                                      setDraftTitle(row.title ?? "");
                                    }}
                                    className="flex h-[44px] min-w-[44px] items-center justify-center rounded-lg text-[color:var(--gv-ink-3)] hover:bg-[color:var(--gv-canvas-2)] hover:text-[color:var(--gv-ink)]"
                                  >
                                    <Pencil className="h-4 w-4" strokeWidth={1.8} />
                                  </button>
                                  <button
                                    type="button"
                                    title="Xoá"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setDeleteTargetId(row.id);
                                    }}
                                    className="flex h-[44px] min-w-[44px] items-center justify-center rounded-lg text-[color:var(--gv-danger)] hover:bg-[color:var(--gv-canvas-2)]"
                                  >
                                    <Trash2 className="h-4 w-4" strokeWidth={1.8} />
                                  </button>
                                </>
                              ) : null
                            }
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
            {/* D.2.4 — sentinel + loading stub for infinite scroll.
                Rendered only in paginated mode (search is a single-shot). */}
            {!isSearch && unionQuery.hasNextPage ? (
              <div
                ref={observeSentinel}
                aria-hidden
                className="h-12 flex items-center justify-center"
              >
                {unionQuery.isFetchingNextPage ? (
                  <p
                    role="status"
                    aria-label="Đang tải thêm"
                    className="gv-mono text-[11px] text-[color:var(--gv-ink-4)]"
                  >
                    Đang tải thêm…
                  </p>
                ) : null}
              </div>
            ) : null}
            </>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
