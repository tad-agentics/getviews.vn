import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { FileText } from "lucide-react";

import { Btn } from "@/components/v2/Btn";
import type { useChannelDiagnose } from "@/hooks/useChannelDiagnose";
import { logUsage } from "@/lib/logUsage";
import { scriptPrefillFromDeeplink } from "@/lib/scriptPrefill";
import { ChannelFindingsStrip } from "./ChannelFindingsStrip";
import { ProvenanceLine } from "./ProvenanceLine";
import { ScoreCard, ScoreCardSkeleton } from "./ScoreCard";
import { SectionRenderer } from "./SectionRenderer";
import { StepProgress, TRAJECTORY_LABELS } from "./StepProgress";

type DiagnoseHook = ReturnType<typeof useChannelDiagnose>;

function channelInitial(name: string, handle: string): string {
  const s = (name?.trim() || handle).trim();
  if (!s) return "?";
  return s[0]?.toUpperCase() ?? "?";
}

export function ChannelDiagnosisBody({
  handle,
  nicheId,
  videoUrlInput,
  setVideoUrlInput,
  showVideoUrlInput,
  setShowVideoUrlInput,
  diagnose,
  onRestart,
  onChangeHandle,
}: {
  handle: string;
  nicheId: number;
  videoUrlInput: string;
  setVideoUrlInput: (v: string) => void;
  showVideoUrlInput: boolean;
  setShowVideoUrlInput: (v: boolean) => void;
  diagnose: DiagnoseHook;
  onRestart: () => void;
  onChangeHandle: (h: string) => void;
}) {
  const navigate = useNavigate();
  const [another, setAnother] = useState("");

  const at = handle.startsWith("@") ? handle : `@${handle}`;

  const errorMessages: Record<string, string> = {
    insufficient_credits: "Không đủ credit để phân tích kênh này.",
    channel_not_found: "Không tìm thấy kênh — hãy kiểm tra lại @handle.",
    stream_failed: "Phân tích thất bại — vui lòng thử lại.",
    no_cloud_run: "Chưa cấu hình Cloud Run API.",
    no_session: "Phiên đăng nhập hết hạn — vui lòng đăng nhập lại.",
    already_in_flight: "Đang có phân tích cùng kênh đang chạy — vui lòng chờ.",
    stream_timeout: "Phân tích quá thời gian — vui lòng thử lại.",
  };

  const errorMessage = diagnose.error
    ? (errorMessages[diagnose.error] ?? `Lỗi: ${diagnose.error}`)
    : null;

  const scriptHref = useMemo(() => {
    const fp = diagnose.finalPayload;
    if (!fp) return null;
    const fmt = fp.channel_persona?.dominant_format ?? fp.dominant_format ?? "";
    if (!fmt || !handle) return null;
    return scriptPrefillFromDeeplink({
      prefill_handle: handle,
      prefill_format: fmt,
    });
  }, [diagnose.finalPayload, handle]);

  const isDone = diagnose.status === "done";
  const isStreaming = diagnose.status === "streaming";
  const isError = diagnose.status === "error";
  const channelFindings = diagnose.channelFindings ?? [];
  const hasEarlyDeepContent =
    diagnose.scoreCard != null || channelFindings.length > 0;
  const hasReportBody = hasEarlyDeepContent || diagnose.sections.length > 0;

  return (
    <div className="flex flex-col gap-6">
      <form
        className="flex flex-col gap-2 border-b border-[color:var(--gv-rule)] pb-4 sm:flex-row sm:items-end sm:gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          onChangeHandle(another);
        }}
      >
        <label className="flex min-w-0 flex-1 flex-col gap-1.5">
          <span className="gv-kicker text-[color:var(--gv-ink-4)]">Kênh khác</span>
          <input
            value={another}
            onChange={(e) => setAnother(e.target.value)}
            placeholder={at}
            className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2 text-base text-[color:var(--gv-ink)] outline-none focus-visible:border-[color:var(--gv-accent)] focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)] focus-visible:ring-offset-1"
            autoComplete="off"
          />
        </label>
        <Btn type="submit" variant="ghost" size="sm" disabled={!another.trim()}>
          Tải
        </Btn>
      </form>

      <div>
        <button
          type="button"
          className="text-xs text-[color:var(--gv-accent)] underline-offset-2 hover:underline"
          onClick={() => setShowVideoUrlInput(!showVideoUrlInput)}
        >
          {showVideoUrlInput ? "Ẩn video so sánh" : "+ So sánh với video cụ thể"}
        </button>
        {showVideoUrlInput && (
          <div className="mt-2 flex gap-2">
            <input
              type="url"
              value={videoUrlInput}
              onChange={(e) => setVideoUrlInput(e.target.value)}
              placeholder="https://tiktok.com/@handle/video/..."
              className="min-w-0 flex-1 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2 text-base text-[color:var(--gv-ink)] outline-none focus-visible:border-[color:var(--gv-accent)] focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)] focus-visible:ring-offset-1"
              autoComplete="off"
            />
            <Btn type="button" variant="ghost" size="sm" onClick={onRestart} disabled={isStreaming}>
              Phân tích lại
            </Btn>
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[color:var(--gv-canvas-2)] text-xl font-semibold text-[color:var(--gv-ink)]">
          {channelInitial("", handle)}
        </div>
        <div>
          <h2 className="gv-tight m-0 text-[22px] font-semibold leading-tight">{at}</h2>
          {diagnose.trajectoryShape && (
            <p className="mt-0.5 text-xs text-[color:var(--gv-ink-3)]">
              {TRAJECTORY_LABELS[diagnose.trajectoryShape] ?? diagnose.trajectoryShape.replace(/_/g, " ")}
            </p>
          )}
        </div>
      </div>

      {isStreaming && !hasReportBody && (
        <div className="rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]">
          <StepProgress
            activeStepIndex={diagnose.activeStepIndex}
            activeStepLabel={diagnose.activeStepLabel}
            heartbeatCount={diagnose.heartbeatCount}
            trajectoryShape={diagnose.trajectoryShape}
          />
        </div>
      )}

      {hasReportBody && (
        <div className="rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-6 sm:px-7">
          {isStreaming &&
          !diagnose.scoreCard &&
          channelFindings.length === 0 &&
          diagnose.sections.length === 0 ? (
            <ScoreCardSkeleton />
          ) : null}
          {diagnose.scoreCard ? <ScoreCard card={diagnose.scoreCard} /> : null}
          {channelFindings.length > 0 ? (
            <ChannelFindingsStrip findings={channelFindings} />
          ) : null}
          {diagnose.sections.map((section) => (
            <SectionRenderer
              key={section.section_id}
              section={section}
              recommendations={
                section.section_id === "recommendations" ? diagnose.recommendations : []
              }
              streaming={isStreaming && diagnose.activeSectionId === section.section_id}
            />
          ))}

          {isDone && diagnose.finalPayload && (
            <ProvenanceLine
              provenance={diagnose.finalPayload.provenance}
              cacheHit={diagnose.finalPayload.cache_hit}
            />
          )}

          {isDone && (diagnose.peerSource === "thin" || diagnose.finalPayload?.niche_thin) && (
            <p className="mt-2 text-xs italic text-[color:var(--gv-ink-3)]">
              Kết quả benchmark mang tính tham khảo.
            </p>
          )}
        </div>
      )}

      {isError && errorMessage && (
        <div className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
          <p className="text-sm text-[color:var(--gv-neg-deep)]">{errorMessage}</p>
          <Btn className="mt-3" type="button" variant="ghost" size="sm" onClick={onRestart}>
            Thử lại
          </Btn>
        </div>
      )}

      {isDone && scriptHref && (
        <div className="flex justify-end pb-2">
          <Btn
            type="button"
            onClick={() => {
              logUsage("channel_diagnose_to_script", { handle });
              navigate(scriptHref);
            }}
          >
            <FileText className="mr-1.5 size-[13px] shrink-0" strokeWidth={1.7} aria-hidden />
            Tạo kịch bản theo phân tích này
          </Btn>
        </div>
      )}
    </div>
  );
}
