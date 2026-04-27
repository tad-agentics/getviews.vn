import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { ArrowRight, Sparkles } from "lucide-react";
import { useDailyRitual, type RitualScript } from "@/hooks/useDailyRitual";
import { useScriptDrafts } from "@/hooks/useScriptSave";
import { useProfile } from "@/hooks/useProfile";
import { formatRelativeSinceVi } from "@/lib/formatters";
import { scriptPrefillFromRitual } from "@/lib/scriptPrefill";
import type { ScriptDraftRow } from "@/lib/api-types";

/**
 * IdeaWorkspace — Script step 1 (per design pack
 * ``screens/script.jsx`` lines 51-179). Renders when the user lands on
 * /app/script with no ``?topic=``/``?hook=``/``?duration=`` deeplink.
 *
 * Three paths:
 *   A · 5 ý tưởng AI gợi ý hôm nay  → reuses ``useDailyRitual`` (the same
 *     nightly-generated scripts Studio Home shows). Today's source produces
 *     up to 3 cards; the design's "5" is mock — we render whatever the
 *     ritual emits and let the cron grow.
 *   B · Tôi có ý tưởng riêng        → textarea + duration → navigates to
 *     ``/app/script?topic=…&duration=…`` so the existing detail screen
 *     prefills via its current URL-param flow.
 *   C · Nháp của bạn                → ``useScriptDrafts``; clicking a row
 *     opens the read-only shoot view (``/app/script/shoot/:id``) which is
 *     where saved drafts already live. Resume-editing back into the editor
 *     is a follow-up PR.
 *
 * Path D (Shopee/Products) intentionally omitted — out-of-scope per
 * CLAUDE.md.
 */

const DURATION_OPTIONS_SEC = [18, 24, 32, 45, 60, 90] as const;

export function IdeaWorkspace() {
  const navigate = useNavigate();
  const { data: profile } = useProfile();
  const primaryNicheId = profile?.primary_niche ?? null;

  const ritual = useDailyRitual(true, primaryNicheId);
  const ideas: RitualScript[] = ritual.data?.scripts ?? [];
  const ritualNicheId = ritual.data?.niche_id ?? primaryNicheId ?? null;

  const drafts = useScriptDrafts(true);
  const draftsList: ScriptDraftRow[] = drafts.data?.drafts ?? [];

  const [showAllDrafts, setShowAllDrafts] = useState(false);
  const visibleDrafts = showAllDrafts ? draftsList : draftsList.slice(0, 6);

  const pickIdea = (idea: RitualScript) => {
    if (ritualNicheId == null) return;
    navigate(scriptPrefillFromRitual(idea, ritualNicheId));
  };

  return (
    <div className="bg-[color:var(--gv-canvas)] min-h-full">
      <div className="mx-auto max-w-[1080px] px-7 pt-6 pb-14">
        {/* Header */}
        <div className="mb-5">
          <p className="gv-mono text-[10px] uppercase tracking-[0.18em] text-[color:var(--gv-accent)] font-semibold mb-2">
            XƯỞNG VIẾT · CHỌN XUẤT PHÁT ĐIỂM
          </p>
          <h1
            className="gv-tight text-[clamp(30px,3.6vw,42px)] font-medium leading-[1.1] text-[color:var(--gv-ink)]"
            style={{ fontFamily: "var(--gv-font-display)", letterSpacing: "-0.025em" }}
          >
            Bạn muốn viết gì hôm nay?
          </h1>
          <p className="mt-2 max-w-[640px] text-sm leading-relaxed text-[color:var(--gv-ink-3)]">
            Chọn từ ý tưởng AI gợi ý dựa trên ngách của bạn, tự nhập chủ đề, hoặc
            mở nháp đang viết dở.
          </p>
        </div>

        {/* Path A — AI ideas */}
        <section className="mb-10">
          <PathHeader
            letter="A"
            title="Ý tưởng hôm nay"
            caption={
              ritual.isPending
                ? "AI đang chuẩn bị…"
                : ideas.length > 0
                  ? `${ideas.length} ý tưởng dựa trên pattern thắng tuần qua trong ngách của bạn`
                  : "Chưa có ý tưởng cho hôm nay — quay lại sáng mai"
            }
          />
          {ritual.isPending ? (
            <div className="rounded-[6px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5 text-sm text-[color:var(--gv-ink-4)]">
              Đang tải ý tưởng…
            </div>
          ) : ideas.length === 0 ? (
            <div className="rounded-[6px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5 text-sm text-[color:var(--gv-ink-3)]">
              {ritual.emptyReason === "ritual_niche_stale"
                ? "Bạn vừa đổi ngách — bộ ý tưởng mới sẽ xuất hiện sau khi cron chạy lại."
                : "Hôm nay AI chưa gợi ý — quay lại sáng mai. Trong lúc đó, bạn có thể tự nhập ý tưởng ở Mục B."}
            </div>
          ) : (
            <IdeaList ideas={ideas} onPick={pickIdea} />
          )}
        </section>

        {/* Path B — custom */}
        <section className="mb-10">
          <PathHeader
            letter="B"
            title="Tôi có ý tưởng riêng"
            caption="Nhập tự do — AI ráp script + reference"
          />
          <CustomIdeaCard
            onSubmit={(topic, duration) => {
              const qs = new URLSearchParams();
              qs.set("topic", topic.slice(0, 500));
              qs.set("duration", String(duration));
              if (primaryNicheId != null) qs.set("niche_id", String(primaryNicheId));
              navigate(`/app/script?${qs.toString()}`);
            }}
          />
        </section>

        {/* Path C — drafts */}
        <section>
          <PathHeader
            letter="C"
            title="Nháp của bạn"
            caption={
              drafts.isPending
                ? "Đang tải…"
                : draftsList.length === 0
                  ? "Chưa có nháp nào"
                  : `${draftsList.length} nháp · 6 gần nhất`
            }
          />
          {drafts.isPending ? (
            <div className="rounded-[6px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5 text-sm text-[color:var(--gv-ink-4)]">
              Đang tải nháp…
            </div>
          ) : draftsList.length === 0 ? (
            <div className="rounded-[6px] border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5 text-sm text-[color:var(--gv-ink-3)]">
              Chưa có nháp nào — bắt đầu từ Mục A hoặc B ở trên.
            </div>
          ) : (
            <>
              <DraftsList drafts={visibleDrafts} />
              {draftsList.length > 6 ? (
                <div className="mt-3 text-center">
                  <button
                    type="button"
                    onClick={() => setShowAllDrafts((v) => !v)}
                    className="text-[12px] text-[color:var(--gv-ink-3)] hover:text-[color:var(--gv-ink)] transition-colors"
                  >
                    {showAllDrafts ? "← Thu gọn" : `Xem tất cả ${draftsList.length} nháp →`}
                  </button>
                </div>
              ) : null}
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function PathHeader({
  letter,
  title,
  caption,
}: {
  letter: string;
  title: string;
  caption: string;
}) {
  return (
    <div className="mb-3 flex items-baseline gap-3 flex-wrap">
      <span className="gv-mono text-[11px] font-bold uppercase tracking-wider bg-[color:var(--gv-ink)] text-white px-1.5 py-0.5 rounded-[3px]">
        {letter}
      </span>
      <h2
        className="gv-tight text-[22px] font-medium leading-tight text-[color:var(--gv-ink)] m-0"
        style={{ fontFamily: "var(--gv-font-display)", letterSpacing: "-0.015em" }}
      >
        {title}
      </h2>
      <span className="text-[12.5px] text-[color:var(--gv-ink-3)]">{caption}</span>
    </div>
  );
}

function IdeaList({
  ideas,
  onPick,
}: {
  ideas: ReadonlyArray<RitualScript>;
  onPick: (idea: RitualScript) => void;
}) {
  return (
    <ol className="flex flex-col rounded-[6px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] overflow-hidden">
      {ideas.map((idea, i) => (
        <li key={`${idea.title_vi}-${i}`}>
          <button
            type="button"
            onClick={() => onPick(idea)}
            className={
              "w-full text-left grid items-center gap-4 px-4 py-3.5 hover:bg-[color:var(--gv-canvas-2)] transition-colors " +
              (i > 0 ? "border-t border-[color:var(--gv-rule)]" : "")
            }
            style={{ gridTemplateColumns: "32px 1fr auto auto" }}
          >
            <span className="gv-mono text-[11px] font-bold text-[color:var(--gv-ink-4)]">
              {String(i + 1).padStart(2, "0")}
            </span>
            <div className="min-w-0">
              <div className="mb-1 flex items-center gap-2 flex-wrap">
                <span className="gv-mono text-[9px] font-bold uppercase tracking-wider bg-[color:var(--gv-ink)] text-white px-1.5 py-0.5 rounded-[3px]">
                  CƠ HỘI #{i + 1}
                </span>
                <span className="gv-mono text-[10px] text-[color:var(--gv-ink-4)] font-medium">
                  {idea.hook_type_vi || idea.hook_type_en}
                </span>
              </div>
              <div
                className="font-medium text-[17px] leading-snug text-[color:var(--gv-ink)] mb-0.5"
                style={{
                  fontFamily: "var(--gv-font-display)",
                  letterSpacing: "-0.015em",
                }}
              >
                {idea.title_vi}
              </div>
              {idea.why_works ? (
                <div className="text-[12px] text-[color:var(--gv-ink-3)] leading-snug">
                  {idea.why_works}
                </div>
              ) : null}
            </div>
            <div className="flex flex-col items-end gap-0.5">
              <span className="gv-mono text-[13px] font-bold text-[color:var(--gv-ink)]">
                ~{Math.round(idea.retention_est_pct)}%
              </span>
              <span className="gv-mono text-[9px] uppercase tracking-wider text-[color:var(--gv-ink-4)]">
                GIỮ CHÂN
              </span>
            </div>
            <ArrowRight
              className="h-3.5 w-3.5 text-[color:var(--gv-ink-3)]"
              aria-hidden="true"
            />
          </button>
        </li>
      ))}
    </ol>
  );
}

function CustomIdeaCard({
  onSubmit,
}: {
  onSubmit: (topic: string, durationSec: number) => void;
}) {
  const [text, setText] = useState("");
  const [durationSec, setDurationSec] = useState<number>(32);

  const submit = () => {
    const trimmed = text.trim();
    if (trimmed.length === 0) return;
    onSubmit(trimmed, durationSec);
  };

  return (
    <div className="relative overflow-hidden rounded-[6px] border border-[color:var(--gv-ink)] bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)] p-5 flex flex-col gap-3.5 min-h-[240px] shadow-[6px_6px_0_var(--gv-rule)]">
      <div
        className="absolute top-0 right-0 h-[140px] w-[140px] pointer-events-none"
        style={{
          background:
            "radial-gradient(circle at top right, color-mix(in srgb, var(--gv-accent) 35%, transparent), transparent 70%)",
        }}
        aria-hidden="true"
      />
      <p className="gv-mono text-[10px] font-bold uppercase tracking-[0.18em] text-[color:var(--gv-accent)] relative z-[1]">
        ✦ NHẬP TỰ DO
      </p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
        }}
        placeholder='Mô tả ý tưởng video của bạn — vd "So sánh 3 chiếc bàn phím cơ dưới 1 triệu", "Phản ứng khi bạn lần đầu thử AirPods Pro 3"…'
        className="relative z-[1] w-full min-h-[140px] p-3.5 rounded text-[16px] leading-relaxed text-[color:var(--gv-canvas)] resize-y outline-none"
        style={{
          fontFamily: "var(--gv-font-display)",
          background: "color-mix(in srgb, var(--gv-canvas) 8%, var(--gv-ink))",
          border: "1px solid color-mix(in srgb, var(--gv-canvas) 18%, transparent)",
        }}
      />
      <div className="relative z-[1] flex items-center gap-2 flex-wrap">
        <span
          className="gv-mono text-[9px] font-semibold uppercase tracking-[0.12em]"
          style={{ color: "color-mix(in srgb, var(--gv-canvas) 50%, transparent)" }}
        >
          ĐỘ DÀI
        </span>
        <select
          value={durationSec}
          onChange={(e) => setDurationSec(Number(e.target.value))}
          className="text-[11.5px] font-medium px-2 py-0.5 rounded-[3px] text-[color:var(--gv-canvas)] outline-none"
          style={{
            background: "color-mix(in srgb, var(--gv-canvas) 12%, var(--gv-ink))",
            border: "1px solid color-mix(in srgb, var(--gv-canvas) 18%, transparent)",
          }}
        >
          {DURATION_OPTIONS_SEC.map((d) => (
            <option key={d} value={d}>
              {d}s
            </option>
          ))}
        </select>
        <span className="flex-1" />
        <button
          type="button"
          onClick={submit}
          disabled={text.trim().length === 0}
          className="inline-flex items-center gap-1.5 rounded bg-[color:var(--gv-accent)] px-3 py-1.5 text-[12px] font-semibold text-white transition-opacity disabled:opacity-40"
        >
          <Sparkles className="h-3 w-3" /> Tạo script
        </button>
      </div>
    </div>
  );
}

function DraftsList({ drafts }: { drafts: ReadonlyArray<ScriptDraftRow> }) {
  const now = useMemo(() => new Date(), []);

  return (
    <div className="grid gap-2.5" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}>
      {drafts.map((d) => {
        const updated = d.updated_at ? new Date(d.updated_at) : null;
        const ago = updated ? formatRelativeSinceVi(now, updated) : "—";
        const shotCount = Array.isArray(d.shots) ? d.shots.length : 0;
        return (
          <a
            key={d.id}
            href={`/app/script/shoot/${encodeURIComponent(d.id)}`}
            className="text-left flex flex-col gap-2 px-3.5 py-3 rounded-[6px] bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)] hover:border-[color:var(--gv-ink)] transition-colors"
          >
            <div
              className="font-medium text-[15px] leading-snug text-[color:var(--gv-ink)]"
              style={{
                fontFamily: "var(--gv-font-display)",
                letterSpacing: "-0.01em",
              }}
            >
              {d.topic || "Nháp không tiêu đề"}
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="gv-mono text-[9px] font-semibold uppercase tracking-wider text-[color:var(--gv-ink-4)]">
                {ago} · {shotCount} shot · {d.duration_sec}s
              </span>
            </div>
          </a>
        );
      })}
    </div>
  );
}
