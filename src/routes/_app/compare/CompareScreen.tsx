/**
 * Wave 4 PR #3 — Compare screen.
 *
 * Reads ``?url_a=`` + ``?url_b=`` from the URL, generates a fresh
 * client-side session UUID (compare doesn't need chat history;
 * server's session_store falls back to a fresh context), and calls
 * ``useSessionStream`` with intent ``compare_videos``. The Cloud Run
 * /stream endpoint orchestrates parallel diagnoses + delta and
 * returns a ``ComparePayload`` as the SSE final payload.
 *
 * Render states:
 *   - missing one or both URLs → empty-state CTA back to /app
 *   - streaming → skeleton + loading status
 *   - error → AnalysisError messaging + retry
 *   - done → ``CompareBody``
 *
 * Single-side fallback (one diagnosis fails inside the orchestrator):
 * server returns the surviving side's ``run_video_diagnosis`` shape
 * (intent === "video_diagnosis", no ``delta``). We detect that and
 * redirect to ``/app/video?url=…`` for the surviving URL — better
 * than rendering a half-broken compare layout.
 */

import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { Loader2 } from "lucide-react";

import { AppLayout } from "@/components/AppLayout";
import { Btn } from "@/components/v2/Btn";
import { TopBar } from "@/components/v2/TopBar";
import { CompareBody } from "@/components/v2/answer/compare/CompareBody";
import { useSessionStream } from "@/hooks/useSessionStream";
import { env } from "@/lib/env";
import type { ComparePayload } from "@/lib/api-types";
import { logUsage } from "@/lib/logUsage";

function _isCompare(payload: unknown): payload is ComparePayload {
  return (
    typeof payload === "object"
    && payload !== null
    && (payload as { intent?: string }).intent === "compare_videos"
  );
}

export default function CompareScreen() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const urlA = searchParams.get("url_a") ?? "";
  const urlB = searchParams.get("url_b") ?? "";

  const cloudConfigured = Boolean(env.VITE_CLOUD_RUN_API_URL);

  // Fresh session UUID per compare invocation. We don't need chat
  // history for a one-shot URL pair — the server's session_store
  // falls back to a fresh context when no chat_messages back the id.
  const sessionId = useMemo(() => crypto.randomUUID(), []);

  const { stream } = useSessionStream<ComparePayload>();
  const [status, setStatus] = useState<"idle" | "streaming" | "done" | "error">("idle");
  const [payload, setPayload] = useState<ComparePayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!cloudConfigured) return;
    if (!urlA || !urlB) return;
    let cancelled = false;
    setStatus("streaming");
    setError(null);
    void logUsage("compare_videos_started");
    void (async () => {
      const result = await stream({
        sessionId,
        query: `${urlA} ${urlB}`,
        intentType: "compare_videos",
      });
      if (cancelled) return;
      if (!result.ok) {
        setStatus("error");
        setError(result.error);
        return;
      }
      const final = result.finalPayload;
      // Single-side fallback: server returns a video_diagnosis dict
      // when one side fails inside the orchestrator. Redirect to the
      // dedicated single-video screen with the surviving URL.
      if (
        final
        && typeof final === "object"
        && (final as { intent?: string }).intent === "video_diagnosis"
      ) {
        const surviving =
          (final as { metadata?: { tiktok_url?: string } }).metadata?.tiktok_url
          ?? urlA;
        navigate(`/app/video?url=${encodeURIComponent(surviving)}`, { replace: true });
        return;
      }
      if (_isCompare(final)) {
        setPayload(final);
        setStatus("done");
        return;
      }
      setStatus("error");
      setError("compare_payload_invalid");
    })();
    return () => {
      cancelled = true;
    };
  }, [cloudConfigured, urlA, urlB, sessionId, stream, navigate]);

  // ── Empty / config states ────────────────────────────────────────

  if (!cloudConfigured) {
    return (
      <AppLayout enableMobileSidebar>
      <TopBar kicker="BÁO CÁO" title="So Sánh Hai Video" />
        <main className="container-app pb-12">
          <div className="rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6">
            <p className="gv-mono gv-uc text-[10px] tracking-[0.16em] text-[color:var(--gv-ink-4)]">
              So sánh hai video
            </p>
            <p className="gv-serif mt-2 text-[18px] text-[color:var(--gv-ink)]">
              Tính năng cần Cloud Run — chưa bật trên môi trường này.
            </p>
            <Link
              to="/app"
              className="gv-mono mt-4 inline-block text-[12px] text-[color:var(--gv-accent-deep)]"
            >
              Quay lại trang chính →
            </Link>
          </div>
        </main>
      </AppLayout>
    );
  }

  if (!urlA || !urlB) {
    return (
      <AppLayout enableMobileSidebar>
      <TopBar kicker="BÁO CÁO" title="So Sánh Hai Video" />
        <main className="container-app pb-12">
          <div className="rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6">
            <p className="gv-mono gv-uc text-[10px] tracking-[0.16em] text-[color:var(--gv-ink-4)]">
              So sánh hai video
            </p>
            <p className="gv-serif mt-2 text-[18px] text-[color:var(--gv-ink)]">
              Cần hai link TikTok để so sánh.
            </p>
            <p className="mt-3 text-sm text-[color:var(--gv-ink-3)]">
              Thử dán hai link liên tiếp trong ô tìm kiếm — ví dụ
              {" "}<code className="gv-mono text-[12px]">https://tiktok.com/@a/video/1 https://tiktok.com/@b/video/2</code>.
            </p>
            <Btn
              variant="ink"
              onClick={() => navigate("/app")}
              className="mt-5"
            >
              Quay lại trang chính
            </Btn>
          </div>
        </main>
      </AppLayout>
    );
  }

  // ── Loading / error / done ───────────────────────────────────────

  return (
    <AppLayout enableMobileSidebar>
      <TopBar kicker="BÁO CÁO" title="So Sánh Hai Video" />
      <main className="container-app pb-12">
        <header className="mb-5">
          <p className="gv-mono gv-uc text-[10px] tracking-[0.16em] text-[color:var(--gv-ink-4)]">
            So sánh hai video
          </p>
          <h1 className="gv-serif mt-1 text-[clamp(22px,3.4vw,30px)] leading-[1.2] text-[color:var(--gv-ink)]">
            Khác biệt giữa video A và video B
          </h1>
        </header>

        {status === "streaming" ? (
          <div
            role="status"
            aria-live="polite"
            className="flex items-center gap-3 rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5"
          >
            <Loader2 className="h-5 w-5 animate-spin text-[color:var(--gv-accent)]" />
            <span className="gv-mono text-[13px] text-[color:var(--gv-ink-3)]">
              Đang phân tích song song hai video...
            </span>
          </div>
        ) : null}

        {status === "error" && error ? (
          <div className="rounded-[18px] border border-[color:var(--gv-warn)] bg-[color:var(--gv-warn-soft)] p-5">
            <p className="gv-mono gv-uc text-[10px] tracking-[0.16em] text-[color:var(--gv-warn)]">
              Lỗi
            </p>
            <p className="mt-2 text-[14px] text-[color:var(--gv-ink-2)]">
              {error === "insufficient_credits"
                ? "Hết credit — nạp thêm để tiếp tục."
                : "Không tải được kết quả so sánh — thử lại sau."}
            </p>
            <Btn
              variant="ink"
              onClick={() => navigate(0)}
              className="mt-3"
            >
              Thử lại
            </Btn>
          </div>
        ) : null}

        {status === "done" && payload ? <CompareBody payload={payload} /> : null}
      </main>
    </AppLayout>
  );
}
