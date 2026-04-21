import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { Bookmark, Copy, Download, Film, Loader2, Plus, Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { AppLayout } from "@/components/AppLayout";
import { Btn } from "@/components/v2/Btn";
import { CardInput } from "@/components/v2/CardInput";
import { Chip } from "@/components/v2/Chip";
import { CitationTag } from "@/components/v2/CitationTag";
import { DurationInsight } from "@/components/v2/DurationInsight";
import { HookTimingMeter } from "@/components/v2/HookTimingMeter";
import { SceneIntelligencePanel, type ScriptReferenceClip } from "@/components/v2/SceneIntelligencePanel";
import { ScriptForecastBar } from "@/components/v2/ScriptForecastBar";
import { ScriptPacingRibbon } from "@/components/v2/ScriptPacingRibbon";
import { ScriptShotRow } from "@/components/v2/ScriptShotRow";
import { TopBar } from "@/components/v2/TopBar";
import { useHomePulse } from "@/hooks/useHomePulse";
import { useProfile } from "@/hooks/useProfile";
import { useScriptExport, useScriptSave } from "@/hooks/useScriptSave";
import { useScriptGenerate } from "@/hooks/useScriptGenerate";
import { useScriptHookPatterns } from "@/hooks/useScriptHookPatterns";
import { useScriptSceneIntelligence } from "@/hooks/useScriptSceneIntelligence";
import { analysisErrorCopy } from "@/lib/errorMessages";
import { env } from "@/lib/env";
import { logUsage } from "@/lib/logUsage";
import { formatRelativeSinceVi } from "@/lib/formatters";
import { apiShotsToEditorShots, mergeSceneIntelIntoShots, type ScriptEditorShot } from "@/lib/scriptEditorMerge";
import type { ScriptTone } from "@/lib/api-types";
import { supabase } from "@/lib/supabase";

const TONES: ScriptTone[] = ["Hài", "Chuyên gia", "Tâm sự", "Năng lượng", "Mỉa mai"];

const OVERLAY_PRESETS: Record<string, string[]> = {
  "BOLD CENTER": ["200K VS 2TR", "TEST THẬT", "BẠN CHỌN?"],
  "SUB-CAPTION": ['"khác biệt ngay đầu tiên"', '"chỉ sau 3 giây"', '"thật sự bất ngờ"'],
  "STAT BURST": ["+248% BASS", "2.4× THÊM CHI TIẾT", "72% PEOPLE"],
  LABEL: ["POV · test 3 thể loại", "Pop · Vocal · Rock", "Sample #1"],
  "QUESTION XL": ["BẠN CHỌN GÌ?", "200K HAY 2TR?", "COMMENT THỬ NÀO"],
};

const BASE_SHOTS: ScriptEditorShot[] = [
  {
    t0: 0,
    t1: 3,
    cam: "Cận mặt",
    voice: "Mình vừa test tai 2 triệu và thật sự…",
    viz: 'Tay cầm 2 tai nghe, chữ "200K vs 2TR" to',
    overlay: "BOLD CENTER",
    tip: "Hook lành trong 1.2s — ok. Không quá dài.",
    corpusAvg: 2.8,
    winnerAvg: 2.4,
    overlayWinner: "white sans 28pt · bottom-center",
    intelSceneType: "face_to_camera",
  },
  {
    t0: 3,
    t1: 8,
    cam: "Cắt nhanh b-roll",
    voice: "Khác biệt đầu tiên bạn nghe thấy ngay",
    viz: "Slow-mo unbox, đặt cạnh nhau",
    overlay: "SUB-CAPTION",
    tip: "Scene #2 nên có motion cut ≤ 0.4s",
    corpusAvg: 4.2,
    winnerAvg: 5.0,
    overlayWinner: "yellow outlined · mid-left",
    intelSceneType: "product_shot",
  },
  {
    t0: 8,
    t1: 16,
    cam: "Side-by-side",
    voice: "Bass 200k bị bí. 2 triệu mở ra như sân khấu.",
    viz: "Split-screen visualizer waveform",
    overlay: "STAT BURST",
    tip: "Split-screen cần hold ≥ 6s để người xem hiểu",
    corpusAvg: 7.8,
    winnerAvg: 8.0,
    overlayWinner: "number callout 72pt",
    intelSceneType: "demo",
  },
  {
    t0: 16,
    t1: 24,
    cam: "POV nghe",
    voice: "Mid-range khác hẳn — đây là test 3 thể loại",
    viz: "POV, đèn ấm, tai lớn",
    overlay: "LABEL",
    tip: "POV 8s là giới hạn — cắt trước khi mất attention",
    corpusAvg: 6.2,
    winnerAvg: 7.5,
    overlayWinner: "caption strip · bottom",
    intelSceneType: "face_to_camera",
  },
  {
    t0: 24,
    t1: 30,
    cam: "Cận tay + texture",
    voice: "Build cũng khác. Cảm giác cầm là khác hệ.",
    viz: "Xoay tai, ánh sáng bên",
    overlay: "NONE",
    tip: "Scene không text — để visual nói. Thuận ngách.",
    corpusAvg: 5.1,
    winnerAvg: 5.0,
    overlayWinner: "—",
    intelSceneType: "action",
  },
  {
    t0: 30,
    t1: 32,
    cam: "Cận mặt + câu hỏi",
    voice: "Bạn chọn cái nào? Comment cho mình biết.",
    viz: "Câu hỏi to trên màn",
    overlay: "QUESTION XL",
    tip: 'CTA câu hỏi ăn 3.4× "follow để xem thêm"',
    corpusAvg: 2.4,
    winnerAvg: 2.5,
    overlayWinner: "question mark · full bleed",
    intelSceneType: "face_to_camera",
  },
];

function parseNicheId(raw: string | null): number | null {
  if (!raw) return null;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) && n > 0 ? n : null;
}

export default function ScriptScreen() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { data: profile } = useProfile();
  const cloudConfigured = Boolean(env.VITE_CLOUD_RUN_API_URL);
  const { data: pulse } = useHomePulse(cloudConfigured);

  const asOf = useMemo(() => {
    if (!pulse?.as_of) return null;
    const d = new Date(pulse.as_of);
    return Number.isNaN(d.getTime()) ? null : d;
  }, [pulse?.as_of]);
  const asOfRelative = useMemo(() => formatRelativeSinceVi(new Date(), asOf), [asOf]);

  const paramNiche = parseNicheId(searchParams.get("niche_id"));
  const effectiveNicheId = paramNiche ?? profile?.primary_niche ?? null;

  const { data: sceneData, isPending: scenePending } = useScriptSceneIntelligence(effectiveNicheId);
  const { data: hookData, isPending: hookPending } = useScriptHookPatterns(effectiveNicheId);

  const [topic, setTopic] = useState("Review tai nghe 200k vs 2 triệu");
  const [hookPattern, setHookPattern] = useState("");
  const [duration, setDuration] = useState(32);
  const [activeShot, setActiveShot] = useState(0);
  const [hookDelayMs, setHookDelayMs] = useState(1200);
  const [toneIdx, setToneIdx] = useState(1);
  const [scriptNo] = useState(() => 14);
  const [shotsOverride, setShotsOverride] = useState<ScriptEditorShot[] | null>(null);
  const [savedDraftId, setSavedDraftId] = useState<string | null>(null);
  const [exportBanner, setExportBanner] = useState<string | null>(null);
  const [pdfAvailable, setPdfAvailable] = useState(true);

  const generate = useScriptGenerate();
  const save = useScriptSave();
  const exporter = useScriptExport();

  useEffect(() => {
    const t = searchParams.get("topic");
    if (t?.trim()) setTopic(t.trim());
  }, [searchParams]);

  useEffect(() => {
    const d = searchParams.get("duration");
    if (!d) return;
    const n = Number.parseInt(d, 10);
    if (Number.isFinite(n) && n >= 15 && n <= 90) setDuration(n);
  }, [searchParams]);

  useEffect(() => {
    const h = searchParams.get("hook");
    if (!h?.trim() || !hookData?.hook_patterns?.length) return;
    const decoded = decodeURIComponent(h.trim());
    const exact = hookData.hook_patterns.find((p) => p.pattern === decoded);
    if (exact) {
      setHookPattern(exact.pattern);
      return;
    }
    const partial = hookData.hook_patterns.find(
      (p) => decoded.includes(p.pattern) || p.pattern.includes(decoded),
    );
    if (partial) setHookPattern(partial.pattern);
  }, [searchParams, hookData]);

  useEffect(() => {
    if (cloudConfigured && effectiveNicheId != null) {
      logUsage("script_screen_load", { niche_id: effectiveNicheId });
    }
  }, [cloudConfigured, effectiveNicheId]);

  const mergedShots = useMemo(
    () => mergeSceneIntelIntoShots(shotsOverride ?? BASE_SHOTS, sceneData?.scenes),
    [shotsOverride, sceneData?.scenes],
  );

  const activeRow = mergedShots[activeShot] ?? mergedShots[0]!;
  const activeIntel = useMemo(
    () => sceneData?.scenes?.find((s) => s.scene_type === activeRow.intelSceneType),
    [sceneData?.scenes, activeRow.intelSceneType],
  );

  const refIds = activeIntel?.reference_video_ids ?? [];

  const { data: refCorpus } = useQuery({
    queryKey: ["script-ref-clips", refIds.join("|")],
    queryFn: async () => {
      if (!refIds.length) return [];
      const { data, error } = await supabase
        .from("video_corpus")
        .select("video_id, thumbnail_url, creator_handle, video_duration")
        .in("video_id", refIds.slice(0, 3));
      if (error) throw error;
      return data ?? [];
    },
    enabled: refIds.length > 0,
  });

  const referenceClips: ScriptReferenceClip[] = useMemo(() => {
    const rows = refCorpus ?? [];
    return rows.map((r) => ({
      video_id: r.video_id as string,
      thumbnail_url: (r.thumbnail_url as string | null) ?? null,
      creator_handle: String(r.creator_handle ?? ""),
      label: "Scene thắng",
      duration_sec: Number(r.video_duration) || 0,
    }));
  }, [refCorpus]);

  const overlaySamples = useMemo(() => {
    const fromApi = activeIntel?.overlay_samples;
    if (Array.isArray(fromApi) && fromApi.length) {
      return fromApi.filter((x): x is string => typeof x === "string" && x.trim().length > 0);
    }
    return OVERLAY_PRESETS[activeRow.overlay] ?? [];
  }, [activeIntel?.overlay_samples, activeRow.overlay]);

  const hookButtons = (hookData?.hook_patterns ?? []).slice(0, 4);
  const citation = hookData?.citation;
  const selectedHook = hookPattern || hookButtons[0]?.pattern || "";

  const handleRegenerate = () => {
    if (effectiveNicheId == null) return;
    const hookLine = selectedHook.trim() || topic.trim().slice(0, 120) || "Hook mở đầu";
    generate.mutate(
      {
        topic: topic.trim(),
        hook: hookLine,
        hook_delay_ms: hookDelayMs,
        duration,
        tone: TONES[toneIdx]!,
        niche_id: effectiveNicheId,
      },
      {
        onSuccess: (data) => {
          setShotsOverride(apiShotsToEditorShots(data.shots, BASE_SHOTS));
          setActiveShot(0);
          logUsage("script_generate", {
            niche_id: effectiveNicheId,
            duration,
            shots: data.shots.length,
          });
        },
      },
    );
  };

  const apiShotsForSave = useMemo(
     () =>
      mergedShots.map((s) => ({
        t0: s.t0,
        t1: s.t1,
        cam: s.cam,
        voice: s.voice,
        viz: s.viz,
        overlay: s.overlay,
        corpus_avg: s.corpusAvg,
        winner_avg: s.winnerAvg,
        intel_scene_type: s.intelSceneType,
        overlay_winner: s.overlayWinner,
      })),
    [mergedShots],
  );

  const ensureSavedDraft = async (): Promise<string | null> => {
    if (savedDraftId) return savedDraftId;
    if (effectiveNicheId == null) return null;
    try {
      const out = await save.mutateAsync({
        topic: topic.trim(),
        hook: (selectedHook.trim() || topic.trim().slice(0, 120) || "Hook mở đầu"),
        hook_delay_ms: hookDelayMs,
        duration_sec: duration,
        tone: TONES[toneIdx]!,
        shots: apiShotsForSave,
        niche_id: effectiveNicheId,
      });
      setSavedDraftId(out.draft_id);
      logUsage("script_save", {
        niche_id: effectiveNicheId,
        draft_id: out.draft_id,
        duration,
      });
      return out.draft_id;
    } catch (exc) {
      setExportBanner(exc instanceof Error ? exc.message : "Không lưu được kịch bản");
      return null;
    }
  };

  const handleSave = async () => {
    setExportBanner(null);
    const id = await ensureSavedDraft();
    if (id) {
      // Post-save landing was `/app/history?type=script` but the history
      // filter ribbon only knows "all" | "answer" | "chat" — the
      // ?type=script query fell through to "all" and the user couldn't
      // find their draft. Shoot mode is the natural next step anyway:
      // the saved draft is what you actually want to film against, and
      // the shoot screen renders the same draft rows in read-only mode.
      navigate(`/app/script/shoot/${encodeURIComponent(id)}`);
    }
  };

  const handleCopy = async () => {
    setExportBanner(null);
    const id = await ensureSavedDraft();
    if (!id) return;
    try {
      const res = await exporter.mutateAsync({ draftId: id, format: "copy" });
      if (res.format === "copy") {
        await navigator.clipboard.writeText(res.text);
        setExportBanner("Đã copy kịch bản vào clipboard.");
      }
    } catch (exc) {
      setExportBanner(exc instanceof Error ? exc.message : "Không copy được");
    }
  };

  const handlePdf = async () => {
    setExportBanner(null);
    const id = await ensureSavedDraft();
    if (!id) return;
    try {
      const res = await exporter.mutateAsync({
        draftId: id,
        format: "pdf",
        filenameHint: topic.trim().slice(0, 48) || "kich-ban",
      });
      if (res.format === "pdf") {
        const url = URL.createObjectURL(res.blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = res.filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      }
    } catch (exc) {
      if (exc instanceof Error && exc.name === "PdfUnavailable") {
        setPdfAvailable(false);
        setExportBanner("PDF tạm thời không khả dụng — dùng Copy để gửi Zalo.");
        return;
      }
      setExportBanner(exc instanceof Error ? exc.message : "Không tạo được PDF");
    }
  };

  const handleShootMode = async () => {
    setExportBanner(null);
    const id = await ensureSavedDraft();
    if (id) navigate(`/app/script/shoot/${id}`);
  };

  const loadingPanel = cloudConfigured && effectiveNicheId != null && (scenePending || hookPending);

  return (
    <AppLayout active="script" enableMobileSidebar>
      <TopBar
        kicker="XƯỞNG VIẾT"
        title="Kịch Bản"
        right={
          <>
            {pulse?.as_of ? (
              <span className="hide-narrow hidden items-center gap-2 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1 gv-mono text-[11px] uppercase tracking-[0.1em] text-[color:var(--gv-ink-3)] md:inline-flex">
                <span
                  className="inline-block h-1.5 w-1.5 rounded-full bg-[color:var(--gv-accent)]"
                  style={{ animation: "gv-pulse 1.6s ease-in-out infinite" }}
                />
                Dữ liệu cập nhật {asOfRelative}
              </span>
            ) : null}
            <Btn
              variant="ghost"
              size="sm"
              className="hidden sm:inline-flex"
              type="button"
              onClick={handleSave}
              disabled={save.isPending}
            >
              <Bookmark className="h-3.5 w-3.5" strokeWidth={1.7} aria-hidden />
              {save.isPending ? "Đang lưu…" : savedDraftId ? "Đã lưu" : "Lưu"}
            </Btn>
            <Btn variant="ink" size="sm" type="button" onClick={() => navigate("/app/answer")}>
              <Plus className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
              Phân tích mới
            </Btn>
          </>
        }
      />
      <main className="gv-route-main gv-route-main--1280">
        {!cloudConfigured ? (
          <div className="mx-auto w-full max-w-[1380px]">
            <p className="gv-mono text-[13px] leading-relaxed text-[color:var(--gv-ink-3)]">
              Cần <span className="font-[family-name:var(--gv-font-mono)]">VITE_CLOUD_RUN_API_URL</span> trong môi
              trường build.
            </p>
          </div>
        ) : effectiveNicheId == null ? (
          <div className="mx-auto w-full max-w-[1380px]">
            <p className="gv-mono text-[13px] leading-relaxed text-[color:var(--gv-ink-3)]">
              Chọn ngách trong onboarding hoặc Cài đặt để dùng Xưởng Viết.
            </p>
          </div>
        ) : (
          <div className="mx-auto w-full max-w-[1380px]">
            <header className="mb-5 flex flex-wrap items-center justify-between gap-4 border-b-2 border-[color:var(--gv-ink)] pb-4">
              <div className="min-w-0 flex-1">
                <div className="gv-mono gv-uc mb-1.5 text-[10px] font-semibold leading-none tracking-[0.18em] text-[color:var(--gv-accent)]">
                  XƯỞNG VIẾT · KỊCH BẢN SỐ {scriptNo}
                </div>
                <h1 className="gv-serif m-0 text-[clamp(26px,3vw,36px)] leading-[1.1] text-[color:var(--gv-ink)]">
                  {topic}
                </h1>
              </div>
              <div className="flex flex-wrap gap-2">
                <Btn
                  variant="ghost"
                  size="sm"
                  type="button"
                  onClick={handleCopy}
                  disabled={save.isPending || exporter.isPending}
                >
                  <Copy className="h-3 w-3" strokeWidth={2} aria-hidden />
                  Copy
                </Btn>
                <Btn
                  variant="ghost"
                  size="sm"
                  type="button"
                  onClick={handlePdf}
                  disabled={save.isPending || exporter.isPending || !pdfAvailable}
                  title={pdfAvailable ? undefined : "PDF tạm thời không khả dụng"}
                >
                  <Download className="h-3 w-3" strokeWidth={2} aria-hidden />
                  PDF
                </Btn>
                <Btn
                  variant="ink"
                  size="sm"
                  type="button"
                  onClick={handleShootMode}
                  disabled={save.isPending}
                >
                  <Film className="h-3 w-3" strokeWidth={2} aria-hidden />
                  Chế độ quay
                </Btn>
              </div>
            </header>
            {exportBanner ? (
              <div className="mb-4 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2 gv-mono text-[12px] text-[color:var(--gv-ink-3)]">
                {exportBanner}
              </div>
            ) : null}

            {loadingPanel ? (
              <div
                className="flex min-h-[30vh] items-center justify-center gv-mono text-[13px] text-[color:var(--gv-ink-3)]"
                role="status"
                aria-label="Đang tải dữ liệu ngách"
              >
                Đang tải dữ liệu ngách…
              </div>
            ) : (
              <div
                className={
                  "grid gap-6 " +
                  "max-[880px]:grid-cols-1 " +
                  "min-[881px]:max-[1240px]:grid-cols-[minmax(0,280px)_minmax(0,1fr)] " +
                  "min-[1241px]:grid-cols-[300px_minmax(0,1fr)_300px]"
                }
              >
                <aside className="flex min-w-0 flex-col gap-3.5">
                  <CardInput label="CHỦ ĐỀ">
                    <textarea
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      rows={2}
                      className="gv-serif m-0 w-full resize-none border-0 bg-transparent p-0 text-[16px] leading-[1.3] text-[color:var(--gv-ink)] outline-none"
                    />
                  </CardInput>

                  <CardInput label="MẪU HOOK · XẾP THEO RETENTION">
                    <div className="flex flex-col gap-1.5">
                      {hookButtons.length ? (
                        hookButtons.map((h) => {
                          const active = selectedHook === h.pattern;
                          return (
                            <button
                              key={h.pattern}
                              type="button"
                              onClick={() => setHookPattern(h.pattern)}
                              className={`flex cursor-pointer items-center justify-between rounded-[4px] px-2.5 py-2 text-left text-xs ${
                                active
                                  ? "border border-[color:var(--gv-ink)] bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
                                  : "border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-2)]"
                              }`}
                            >
                              <span className="gv-tight text-[13px]">{`"${h.pattern}"`}</span>
                              <span className="gv-mono text-[10px] text-[color:var(--gv-chart-benchmark)]">
                                ▲{h.delta}
                              </span>
                            </button>
                          );
                        })
                      ) : (
                        <p className="gv-mono text-[11px] text-[color:var(--gv-ink-4)]">Chưa có dữ liệu hook cho ngách.</p>
                      )}
                    </div>
                  </CardInput>

                  <CardInput
                    label={
                      <span>
                        HOOK RƠI LÚC{" "}
                        <span
                          className={`gv-mono ${hookDelayMs > 1400 ? "text-[color:var(--gv-accent)]" : "text-[rgb(0,159,250)]"}`}
                        >
                          {(hookDelayMs / 1000).toFixed(1)}s
                        </span>
                      </span>
                    }
                  >
                    <input
                      type="range"
                      min={400}
                      max={3000}
                      step={100}
                      value={hookDelayMs}
                      onChange={(e) => setHookDelayMs(Number(e.target.value))}
                      className="w-full accent-[color:var(--gv-accent)]"
                    />
                    <HookTimingMeter delayMs={hookDelayMs} />
                    <p className="gv-mono mt-3 text-[11px] leading-[1.45] text-[color:var(--gv-ink-4)]">
                      Video thắng trong ngách Tech rơi hook tại{" "}
                      <span className="text-[color:var(--gv-ink-2)]">0.8–1.4s</span>. Sau 1.4s, retention giảm{" "}
                      <span className="text-[color:var(--gv-accent)]">38%</span>.
                    </p>
                  </CardInput>

                  <CardInput
                    label={
                      <span>
                        ĐỘ DÀI · <span className="gv-mono">{duration}s</span>
                      </span>
                    }
                  >
                    <input
                      type="range"
                      min={15}
                      max={90}
                      value={duration}
                      onChange={(e) => setDuration(Number(e.target.value))}
                      className="w-full accent-[color:var(--gv-accent)]"
                    />
                    <DurationInsight durationSec={duration} />
                  </CardInput>

                  <CardInput label="GIỌNG ĐIỆU">
                    <div className="flex flex-wrap gap-1.5">
                      {TONES.map((t, i) => (
                        <Chip
                          key={t}
                          type="button"
                          size="md"
                          variant={toneIdx === i ? "accent" : "default"}
                          onClick={() => setToneIdx(i)}
                        >
                          {t}
                        </Chip>
                      ))}
                    </div>
                  </CardInput>

                  <Btn
                    variant="accent"
                    type="button"
                    className="w-full justify-center"
                    disabled={!topic.trim() || generate.isPending}
                    onClick={handleRegenerate}
                  >
                    {generate.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={2} aria-hidden />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
                    )}
                    Tạo lại với AI
                  </Btn>
                  {generate.isError ? (
                    <p className="gv-mono text-[11px] text-[color:var(--gv-neg-deep)]">
                      {analysisErrorCopy(generate.error)}
                    </p>
                  ) : null}

                  {citation && citation.sample_size > 0 ? (
                    <CitationTag
                      sampleSize={citation.sample_size}
                      nicheLabel={citation.niche_label}
                      windowDays={citation.window_days}
                    />
                  ) : null}
                </aside>

                <div className="min-w-0 min-[881px]:max-[1240px]:col-span-2 min-[1241px]:col-span-1">
                  <ScriptPacingRibbon
                    shots={mergedShots}
                    activeShot={activeShot}
                    onSelectShot={setActiveShot}
                  />
                  <div className="mt-3.5 flex flex-col gap-2.5">
                    {mergedShots.map((s, i) => (
                      <ScriptShotRow
                        key={`${s.t0}-${s.t1}-${i}`}
                        shot={s}
                        idx={i}
                        active={activeShot === i}
                        onClick={() => setActiveShot(i)}
                      />
                    ))}
                  </div>
                  <ScriptForecastBar durationSec={duration} hookDelayMs={hookDelayMs} />
                </div>

                <aside
                  className={
                    "flex min-w-0 flex-col gap-3.5 " +
                    "min-[881px]:max-[1240px]:col-span-2 min-[881px]:max-[1240px]:flex-row min-[881px]:max-[1240px]:overflow-x-auto " +
                    "min-[1241px]:col-span-1 min-[1241px]:flex-col"
                  }
                >
                  <div className="min-[881px]:max-[1240px]:min-w-[280px] min-[881px]:max-[1240px]:flex-1">
                    <SceneIntelligencePanel
                      shot={activeRow}
                      shotIndex={activeShot}
                      overlaySamples={overlaySamples}
                      referenceClips={referenceClips}
                      sceneSampleSize={activeIntel?.sample_size ?? null}
                      overlayCorpusCount={activeIntel?.sample_size ?? null}
                    />
                  </div>
                </aside>
              </div>
            )}
          </div>
        )}
      </main>
    </AppLayout>
  );
}
