import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, Shield } from "lucide-react";

import { useUpdateProfile } from "@/hooks/useUpdateProfile";

/**
 * Studio Home — inline ConnectChannelCard (PR-cleanup-D).
 *
 * Replaces the "go to Settings" detour with the design pack's paste-
 * link card (home.jsx:512-668): user pastes a TikTok URL or @handle
 * directly on Studio Home, the card runs a 4-step progress animation,
 * and the profile is updated in the background. Once the mutation
 * lands, the parent re-renders to ConnectedCard which fetches the
 * channel data via useChannelAnalyze.
 *
 * The 4 animation steps are intentionally fake — they're visual
 * padding while the (~100-500ms) profile-update mutation completes.
 * The real channel/analyze BE call (5-15s) renders its own pending
 * skeleton on ConnectedCard after this component unmounts.
 *
 * Source of truth for the layout + copy:
 * ``cloud-run/getviews_pipeline/...`` <- no, this is FE-only.
 * Reference: ``screens/home.jsx::ConnectChannelCard``.
 */

const HANDLE_REGEX = /(?:tiktok\.com\/@|^@)([A-Za-z0-9._]+)/;

/** Strict parse — accepts ``tiktok.com/@x``, ``@x``, or just ``x`` (loose form). */
function parseHandle(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const match = trimmed.match(HANDLE_REGEX);
  if (match) return `@${match[1]}`;
  if (trimmed.startsWith("@")) return trimmed;
  // Loose form: bare username (no @, no tiktok.com prefix). Accept if the
  // string is alphanumeric/dots/underscores only — same character set
  // TikTok allows.
  if (/^[A-Za-z0-9._]+$/.test(trimmed)) return `@${trimmed}`;
  return null;
}

const STEPS: ReadonlyArray<string> = [
  "Đang tìm kênh trên TikTok…",
  "Đọc 60 video gần nhất…",
  "So sánh với corpus ngách…",
  "Tìm 3 việc nên làm tuần này…",
];

const STEP_INTERVAL_MS = 480;
const STEP_HANDOFF_DELAY_MS = 350;

const EXAMPLE_HANDLES: ReadonlyArray<string> = ["@an.tech", "@chinasecrets", "@aifreelance"];

type Phase = "idle" | "analyzing" | "error";

export const ConnectChannelCard = memo(function ConnectChannelCard() {
  const [url, setUrl] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [step, setStep] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string>("");
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const handoffRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const updateProfile = useUpdateProfile();

  const validHandle = useMemo(() => parseHandle(url), [url]);

  // Cleanup outstanding timers when unmounting (parent flips to
  // ConnectedCard mid-animation once the profile mutation lands).
  useEffect(() => {
    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
      if (handoffRef.current) clearTimeout(handoffRef.current);
    };
  }, []);

  const submit = useCallback(() => {
    if (!validHandle || phase === "analyzing") return;

    setPhase("analyzing");
    setStep(0);
    setErrorMsg("");

    // Fire the profile mutation immediately. The optimistic update in
    // ``useUpdateProfile`` flips ``profile.tiktok_handle`` in the
    // React Query cache — the parent will re-render to ConnectedCard
    // as soon as that lands (typically before the animation finishes).
    const handleClean = validHandle.replace(/^@/, "");
    updateProfile.mutate(
      { tiktok_handle: handleClean },
      {
        onError: (err) => {
          if (tickRef.current) clearInterval(tickRef.current);
          if (handoffRef.current) clearTimeout(handoffRef.current);
          setPhase("error");
          setErrorMsg((err as Error)?.message || "Không thể lưu kênh — thử lại sau.");
        },
      },
    );

    // Run the 4-step animation in parallel as visual feedback.
    let s = 0;
    tickRef.current = setInterval(() => {
      s += 1;
      if (s >= STEPS.length) {
        if (tickRef.current) clearInterval(tickRef.current);
        tickRef.current = null;
        setStep(s);
        // Brief hold on the final "✓" then the parent unmounts us.
        handoffRef.current = setTimeout(() => {
          handoffRef.current = null;
        }, STEP_HANDOFF_DELAY_MS);
      } else {
        setStep(s);
      }
    }, STEP_INTERVAL_MS);
  }, [phase, updateProfile, validHandle]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        e.preventDefault();
        submit();
      }
    },
    [submit],
  );

  return (
    <div className="overflow-hidden rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]">
      <div
        className="border-b border-[color:var(--gv-rule)] px-7 py-7 sm:px-8"
        style={{
          background:
            "linear-gradient(135deg, color-mix(in srgb, var(--gv-accent) 4%, transparent) 0%, color-mix(in srgb, var(--gv-accent-2) 4%, transparent) 100%)",
        }}
      >
        <div className="mb-5 flex items-center gap-3.5">
          <div
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[14px] text-[22px] font-bold text-[color:var(--gv-canvas)]"
            style={{ background: "var(--gv-ink)" }}
            aria-hidden
          >
            ♪
          </div>
          <div>
            <p className="gv-mono mb-1 text-[9px] font-bold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
              BƯỚC 1 / 1
            </p>
            <p className="m-0 text-[18px] font-semibold tracking-[-0.02em] text-[color:var(--gv-ink)]">
              Dán link kênh TikTok của bạn
            </p>
          </div>
        </div>

        {phase === "idle" || phase === "error" ? (
          <>
            <div
              className="flex items-stretch overflow-hidden rounded-[12px] border-[1.5px] border-[color:var(--gv-ink)] bg-[color:var(--gv-canvas)]"
              style={{ boxShadow: "3px 3px 0 var(--gv-ink)" }}
            >
              <span
                className="gv-mono flex shrink-0 items-center border-r border-[color:var(--gv-rule)] px-3.5 text-[13px] text-[color:var(--gv-ink-3)]"
                aria-hidden
              >
                tiktok.com/
              </span>
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="@an.tech  hoặc dán link đầy đủ"
                aria-label="Handle hoặc URL kênh TikTok"
                className="min-w-0 flex-1 border-0 bg-transparent px-4 py-3.5 text-[15px] font-medium text-[color:var(--gv-ink)] outline-none placeholder:text-[color:var(--gv-ink-4)]"
              />
              <button
                type="button"
                onClick={submit}
                disabled={!validHandle}
                className={
                  "flex shrink-0 items-center gap-1.5 border-l border-[color:var(--gv-rule)] px-5 text-[13px] font-semibold text-[color:var(--gv-canvas)] transition-colors " +
                  (validHandle
                    ? "bg-[color:var(--gv-ink)] hover:bg-[color:var(--gv-ink-2)]"
                    : "cursor-not-allowed bg-[color:var(--gv-ink-2)] opacity-60")
                }
              >
                Phân tích
                <ArrowRight className="h-3 w-3" strokeWidth={2.4} aria-hidden />
              </button>
            </div>
            <div className="mt-3.5 flex flex-wrap items-center gap-2 text-[11px] text-[color:var(--gv-ink-3)]">
              <span>Ví dụ:</span>
              {EXAMPLE_HANDLES.map((h) => (
                <button
                  key={h}
                  type="button"
                  onClick={() => setUrl(h)}
                  className="gv-mono rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-2.5 py-1 text-[11px] text-[color:var(--gv-ink-2)] hover:border-[color:var(--gv-ink)]"
                >
                  {h}
                </button>
              ))}
            </div>
            {phase === "error" && errorMsg ? (
              <p className="mt-3 text-[12px] text-[color:var(--gv-neg-deep)]">
                {errorMsg}
              </p>
            ) : null}
          </>
        ) : (
          <div
            className="rounded-[12px] border-[1.5px] border-[color:var(--gv-ink)] bg-[color:var(--gv-canvas)] px-6 py-5"
            style={{ boxShadow: "3px 3px 0 var(--gv-ink)" }}
          >
            <div className="mb-4 flex items-center gap-3">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full bg-[color:var(--gv-accent)]"
                style={{ animation: "gv-pulse 1.2s ease-in-out infinite" }}
                aria-hidden
              />
              <p className="m-0 text-[14px] font-semibold text-[color:var(--gv-ink)]">
                Đang phân tích {validHandle}
              </p>
            </div>
            <ul className="flex flex-col gap-2">
              {STEPS.map((label, i) => {
                const symbol = i < step ? "✓" : i === step ? "→" : "○";
                const isCurrent = i === step;
                const isDone = i < step;
                return (
                  <li
                    key={label}
                    className={
                      "flex items-center gap-2.5 text-[12px] transition-all " +
                      (i <= step
                        ? "text-[color:var(--gv-ink)] opacity-100"
                        : "text-[color:var(--gv-ink-4)] opacity-50")
                    }
                  >
                    <span
                      className={
                        "inline-flex h-3.5 w-3.5 items-center justify-center text-[10px] font-bold " +
                        (isDone
                          ? "text-[color:var(--gv-pos)]"
                          : isCurrent
                            ? "text-[color:var(--gv-ink-3)]"
                            : "text-[color:var(--gv-ink-3)]")
                      }
                      aria-hidden
                    >
                      {symbol}
                    </span>
                    {label}
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5 text-[11px] text-[color:var(--gv-ink-3)] sm:px-6">
        <div className="flex items-center gap-1.5">
          <Shield className="h-3 w-3" strokeWidth={1.6} aria-hidden />
          <span>Chỉ đọc dữ liệu công khai. Không cần đăng nhập.</span>
        </div>
        <span className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">~6 giây</span>
      </div>
    </div>
  );
});
