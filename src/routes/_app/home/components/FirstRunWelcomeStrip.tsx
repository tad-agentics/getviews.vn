import { memo } from "react";
import { Settings as SettingsIcon, X as XIcon } from "lucide-react";

/**
 * Studio Home — Day-1 welcome strip (PR-6).
 *
 * Mirrors the design pack's FirstRunWelcomeStrip (lines 7-49 of
 * ``screens/home.jsx``): ink-bg full-width strip with a coral
 * "● NGÀY ĐẦU TIÊN" tag, a one-sentence orientation message, an "Đổi
 * ngách / đối thủ" shortcut, and an X dismiss button.
 *
 * Trigger logic lives in ``useIsFirstRun.ts`` — the strip only renders
 * when the profile was created within 24h and the user hasn't dismissed
 * it. Dismissal persists in localStorage scoped to the user id.
 */

export const FirstRunWelcomeStrip = memo(function FirstRunWelcomeStrip({
  firstName,
  nicheLabel,
  onEditNiches,
  onDismiss,
}: {
  firstName: string;
  nicheLabel: string;
  onEditNiches: () => void;
  onDismiss: () => void;
}) {
  return (
    <section
      aria-label="Chào mừng ngày đầu"
      className="flex flex-wrap items-center justify-between gap-4 border-b border-[color:var(--gv-rule)] bg-[color:var(--gv-ink)] px-5 py-3.5 text-[color:var(--gv-canvas)] sm:px-7"
    >
      <div className="flex min-w-0 flex-wrap items-center gap-3.5">
        <span className="gv-mono inline-flex items-center gap-1.5 whitespace-nowrap rounded-[4px] bg-[color:var(--gv-accent)] px-2 py-[3px] text-[10px] font-bold uppercase tracking-[0.1em] text-white">
          <span aria-hidden>●</span>
          NGÀY ĐẦU TIÊN
        </span>
        <p
          className="m-0 text-[13px] leading-[1.5] text-[color:var(--gv-canvas)]"
          style={{ textWrap: "pretty" }}
        >
          Chào {firstName} — đây là toàn cảnh ngách{" "}
          <strong className="font-semibold">{nicheLabel}</strong> 14 ngày qua. Hồ sơ kênh của bạn đang được dựng, sẽ có thêm{" "}
          <em className="gv-serif-italic">so sánh riêng</em> trong 24h.
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <button
          type="button"
          onClick={onEditNiches}
          className="inline-flex items-center gap-1.5 rounded-md border border-white/30 px-3 py-1.5 text-[12px] font-medium text-[color:var(--gv-canvas)] transition-colors hover:bg-white/10"
        >
          <SettingsIcon className="h-3 w-3" strokeWidth={2} aria-hidden />
          Đổi ngách / đối thủ
        </button>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Đóng chào mừng"
          className="flex h-7 w-7 items-center justify-center rounded-md text-[color:var(--gv-canvas)]/70 transition-colors hover:bg-white/10 hover:text-[color:var(--gv-canvas)]"
        >
          <XIcon className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
        </button>
      </div>
    </section>
  );
});
