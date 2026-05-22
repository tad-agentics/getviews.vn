import { memo, useCallback, useState } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowRight, TrendingDown, TrendingUp, Sparkles } from "lucide-react";
import { dismissClassSignal, type ClassMorningSignal } from "@/lib/classMorningSignals";
import {
  readMorningEnergyMode,
  writeMorningEnergyMode,
  type MorningEnergyMode,
} from "@/lib/productionFriction";
import { scriptPrefillFromMorningSignal } from "@/lib/scriptPrefill";
import { useClassMorningSignals } from "@/hooks/useClassMorningSignals";

function formatViews(n: number | null): string {
  if (n == null || !Number.isFinite(n)) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return n.toLocaleString("vi-VN");
}

function signalHeadline(signal: ClassMorningSignal): string {
  switch (signal.signal_type) {
    case "new_class":
      return "Mới xuất hiện trong ngách";
    case "emerging":
      return "Format đang tăng tốc";
    case "growing":
      return "Format đang lên";
    case "declining":
      return "Format đang chững";
    default:
      return "Tín hiệu format";
  }
}

function signalBody(signal: ClassMorningSignal): string {
  const views = formatViews(signal.avg_views);
  if (signal.signal_type === "new_class") {
    return `${signal.label_vn} — ${signal.corpus_citation}, chưa có baseline tuần trước. View TB hiện tại ${views}.`;
  }
  if (signal.signal_type === "declining" && signal.delta_pct != null) {
    return `${signal.label_vn} — lượng video mới giảm ${Math.abs(signal.delta_pct)}% tuần này (${signal.corpus_citation}).`;
  }
  if (signal.delta_pct != null && signal.delta_pct > 0) {
    return `${signal.label_vn} — view TB ↑${signal.delta_pct}% so với tuần trước (${signal.corpus_citation}).`;
  }
  return `${signal.label_vn} — ${signal.corpus_citation}. View TB ${views}.`;
}

const SignalCard = memo(function SignalCard({
  signal,
  onDismiss,
}: {
  signal: ClassMorningSignal;
  onDismiss: (id: number) => void;
}) {
  const navigate = useNavigate();
  const isDefensive = signal.signal_type === "declining";
  const Icon = isDefensive ? TrendingDown : signal.signal_type === "new_class" ? Sparkles : TrendingUp;

  return (
    <article
      className={`rounded-[10px] border px-4 py-3 ${
        isDefensive
          ? "border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]"
          : "border-[color:var(--gv-accent)]/30 bg-[color:var(--gv-paper)]"
      }`}
    >
      <div className="mb-1 flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon
            className={`h-4 w-4 shrink-0 ${isDefensive ? "text-[color:var(--gv-ink-3)]" : "text-[color:var(--gv-accent)]"}`}
            aria-hidden
          />
          <span className="gv-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[color:var(--gv-ink-3)]">
            {signalHeadline(signal)}
          </span>
        </div>
        <button
          type="button"
          className="min-h-[44px] min-w-[44px] shrink-0 text-xs text-[color:var(--gv-ink-4)] hover:text-[color:var(--gv-ink-2)]"
          onClick={() => onDismiss(signal.content_class_id)}
          aria-label="Ẩn tín hiệu 48 giờ"
        >
          ✕
        </button>
      </div>
      <p className="mb-3 text-sm leading-snug text-[color:var(--gv-ink-2)]">{signalBody(signal)}</p>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="inline-flex min-h-[44px] items-center rounded-full bg-[color:var(--gv-ink)] px-4 py-2 text-xs font-medium text-[color:var(--gv-paper)]"
          onClick={() => navigate(scriptPrefillFromMorningSignal(signal))}
        >
          Tạo kịch bản
        </button>
        <Link
          to="/app/trends"
          className="inline-flex min-h-[44px] items-center gap-1 text-xs font-medium text-[color:var(--gv-ink-3)] hover:text-[color:var(--gv-ink)]"
        >
          Xem phân tích chuyên sâu
          <ArrowRight className="h-3 w-3" aria-hidden />
        </Link>
      </div>
    </article>
  );
});

export const MorningSignalStrip = memo(function MorningSignalStrip({
  creatorNicheId,
}: {
  creatorNicheId: number | null;
}) {
  const [energyMode, setEnergyMode] = useState<MorningEnergyMode>(() => readMorningEnergyMode());
  const { data: signals = [], refetch } = useClassMorningSignals(creatorNicheId, energyMode);

  const handleDismiss = useCallback(
    (id: number) => {
      dismissClassSignal(id);
      void refetch();
    },
    [refetch],
  );

  const setMode = useCallback((mode: MorningEnergyMode) => {
    writeMorningEnergyMode(mode);
    setEnergyMode(mode);
  }, []);

  if (creatorNicheId == null) return null;
  if (signals.length === 0 && energyMode === "high") return null;

  return (
    <div className="mb-6" data-testid="morning-signal-strip">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-xs text-[color:var(--gv-ink-3)]">Năng lượng hôm nay:</span>
        <button
          type="button"
          className={`min-h-[44px] rounded-full px-3 py-2 text-xs font-medium ${
            energyMode === "low"
              ? "bg-[color:var(--gv-ink)] text-[color:var(--gv-paper)]"
              : "border border-[color:var(--gv-rule)] text-[color:var(--gv-ink-2)]"
          }`}
          onClick={() => setMode("low")}
        >
          Quay nhẹ hôm nay
        </button>
        <button
          type="button"
          className={`min-h-[44px] rounded-full px-3 py-2 text-xs font-medium ${
            energyMode === "high"
              ? "bg-[color:var(--gv-ink)] text-[color:var(--gv-paper)]"
              : "border border-[color:var(--gv-rule)] text-[color:var(--gv-ink-2)]"
          }`}
          onClick={() => setMode("high")}
        >
          Tràn năng lượng
        </button>
      </div>
      {signals.length === 0 ? (
        <p className="text-sm text-[color:var(--gv-ink-3)]">
          {energyMode === "low"
            ? "Chưa có format dễ quay đang nổi trong ngách — thử chế độ tràn năng lượng."
            : null}
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {signals.map((s) => (
            <SignalCard key={s.content_class_id} signal={s} onDismiss={handleDismiss} />
          ))}
        </div>
      )}
    </div>
  );
});
