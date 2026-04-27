import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { ArrowLeft, Download, Film, Loader2, Plus, Sparkles } from "lucide-react";
import type { ScriptExportFormat } from "@/lib/api-types";
import { useQuery } from "@tanstack/react-query";
import { AppLayout } from "@/components/AppLayout";
import { IdeaWorkspace } from "./IdeaWorkspace";
import { IdeaRefStrip } from "./IdeaRefStrip";
import { ScriptExportModal } from "./ScriptExportModal";
import { ScriptExitModal } from "./ScriptExitModal";
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
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
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
    references: [],
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
    references: [],
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
    references: [],
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
    references: [],
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
    references: [],
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
    references: [],
  },
];

function parseNicheId(raw: string | null): number | null {
  if (!raw) return null;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) && n > 0 ? n : null;
}

/**
 * Mode gate (per design pack ``screens/script.jsx`` lines 24-46): when
 * /app/script is opened with no prefill deeplink, render the IdeaWorkspace
 * step-1 surface instead of dropping the user into the editor with stale
 * defaults. Any of ``?topic=``, ``?hook=``, ``?duration=`` (the existing
 * prefill scheme used by Trends/Channel/Video handoffs) routes to the
 * detail editor below.
 */
export default function ScriptScreen() {
  const [searchParams] = useSearchParams();
  const isWorkspaceMode =
    !searchParams.has("topic") &&
    !searchParams.has("hook") &&
    !searchParams.has("duration");
  if (isWorkspaceMode) {
    return (
      <AppLayout>
        <IdeaWorkspace />
      </AppLayout>
    );
  }
  return <ScriptDetailScreen />;
}

function ScriptDetailScreen() {
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

  const { data: niches } = useNicheTaxonomy();
  const {
    data: sceneData,
    isPending: scenePending,
    isError: sceneIsError,
    refetch: refetchScene,
  } = useScriptSceneIntelligence(effectiveNicheId);
  const {
    data: hookData,
    isPending: hookPending,
    isError: hookIsError,
    refetch: refetchHook,
  } = useScriptHookPatterns(effectiveNicheId);

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

  // S4 — modal + dirty-tracking state. ``dirty`` flips ``true`` on the
  // first edit after the editor settles (firstEditPassed ref skips the
  // initial render's state-restore from URL params + sessionStorage).
  // Cleared after a successful save.
  const [exportOpen, setExportOpen] = useState(false);
  const [exportDone, setExportDone] = useState(false);
  const [exitOpen, setExitOpen] = useState(false);
  const [dirty, setDirty] = useState(false);
  const firstEditPassed = useRef(false);

  // Draft preservation across reloads + 401 auto-signout bounces.
  // Snapshot the four most-expensive-to-re-type fields (topic, hook,
  // duration, tone, hook-delay) to sessionStorage on every change,
  // restore on mount if URL params aren't already driving initial
  // state, and clear after a successful save (once savedDraftId is
  // set, the source of truth lives on the server).
  //
  // sessionStorage — not localStorage — because drafts are tab-scoped
  // and we don't want to leak half-edited content across browser
  // profiles or tabs opened weeks later. 401 recovery completes on
  // the same tab so the snapshot survives the /login round-trip.
  const SCRIPT_DRAFT_STORAGE_KEY = "gv:script-draft-v1";

  useEffect(() => {
    // URL params win over the snapshot — dedicated prefill links
    // (e.g. from /video handoff) should reset the editor deliberately.
    if (searchParams.has("topic") || searchParams.has("hook") || searchParams.has("duration")) {
      return;
    }
    try {
      const raw = sessionStorage.getItem(SCRIPT_DRAFT_STORAGE_KEY);
      if (!raw) return;
      const snap = JSON.parse(raw) as {
        topic?: string;
        hookPattern?: string;
        duration?: number;
        toneIdx?: number;
        hookDelayMs?: number;
      };
      if (typeof snap.topic === "string" && snap.topic.length > 0) setTopic(snap.topic);
      if (typeof snap.hookPattern === "string") setHookPattern(snap.hookPattern);
      if (typeof snap.duration === "number" && snap.duration >= 15 && snap.duration <= 90) setDuration(snap.duration);
      if (typeof snap.toneIdx === "number" && snap.toneIdx >= 0 && snap.toneIdx < 10) setToneIdx(snap.toneIdx);
      if (typeof snap.hookDelayMs === "number" && snap.hookDelayMs >= 0 && snap.hookDelayMs <= 5000) setHookDelayMs(snap.hookDelayMs);
    } catch {
      /* stale or malformed — ignore */
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- restore runs once per mount
  }, []);

  useEffect(() => {
    // Debounced write. Skip once a draft is saved — the server row is
    // the source of truth and keeping a stale client snapshot around
    // would confuse a subsequent edit session.
    if (savedDraftId) return;
    const id = setTimeout(() => {
      try {
        sessionStorage.setItem(
          SCRIPT_DRAFT_STORAGE_KEY,
          JSON.stringify({ topic, hookPattern, duration, toneIdx, hookDelayMs }),
        );
      } catch {
        /* quota exceeded or SSR — ignore */
      }
    }, 400);
    return () => clearTimeout(id);
  }, [topic, hookPattern, duration, toneIdx, hookDelayMs, savedDraftId]);

  useEffect(() => {
    if (!savedDraftId) return;
    try {
      sessionStorage.removeItem(SCRIPT_DRAFT_STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }, [savedDraftId]);

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

  const nicheDisplayName = useMemo(() => {
    const fromTax = niches?.find((n) => n.id === effectiveNicheId)?.name?.trim();
    if (fromTax) return fromTax;
    const fromCitation = hookData?.citation?.niche_label?.trim();
    if (fromCitation) return fromCitation;
    return null;
  }, [niches, effectiveNicheId, hookData?.citation?.niche_label]);

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

  // S6 — per-shot regenerate. The BE returns ``{ shots: [oneShot] }``
  // when ``shot_index`` is set; we splice it back into the existing
  // shot array (using the user's current override base when present).
  // ``regeneratingShot`` tracks the in-flight index so the row can
  // dim its meta + show a spinner without blocking the rest of the
  // editor.
  const [regeneratingShot, setRegeneratingShot] = useState<number | null>(null);

  const handleRegenerateShot = (idx: number) => {
    if (effectiveNicheId == null) return;
    const hookLine = selectedHook.trim() || topic.trim().slice(0, 120) || "Hook mở đầu";
    setRegeneratingShot(idx);
    generate.mutate(
      {
        topic: topic.trim(),
        hook: hookLine,
        hook_delay_ms: hookDelayMs,
        duration,
        tone: TONES[toneIdx]!,
        niche_id: effectiveNicheId,
        shot_index: idx,
      },
      {
        onSuccess: (data) => {
          if (!data.shots || data.shots.length === 0) {
            setRegeneratingShot(null);
            return;
          }
          // BE ALWAYS returns the regenerated shot as ``data.shots[0]``.
          // Splice it into the merged-editor shape; fall back to BASE_SHOTS
          // if the user hadn't yet generated the full script.
          const baseShots = shotsOverride ?? mergedShots;
          const next = [...baseShots];
          if (idx >= 0 && idx < next.length) {
            const merged = apiShotsToEditorShots(
              [data.shots[0]],
              [BASE_SHOTS[idx] ?? BASE_SHOTS[0]!],
            );
            next[idx] = merged[0]!;
          }
          setShotsOverride(next);
          setRegeneratingShot(null);
          logUsage("script_generate_shot", {
            niche_id: effectiveNicheId,
            shot_index: idx,
          });
        },
        onError: () => {
          setRegeneratingShot(null);
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

  // S4 — flip into the export modal. Save is deferred until the user
  // picks a format inside the modal so we don't leave a stale draft on
  // the server if they cancel out.
  const handleOpenExport = () => {
    setExportBanner(null);
    setExportDone(false);
    setExportOpen(true);
  };

  // Handle the modal's "Tải file" — save (if needed), call the export
  // endpoint with the chosen format, and trigger a Blob download. Brief
  // ``Đã tải`` confirmation in the modal CTA before it auto-closes.
  const handleExport = async (format: ScriptExportFormat) => {
    setExportBanner(null);
    const id = await ensureSavedDraft();
    if (!id) return;
    try {
      const res = await exporter.mutateAsync({ draftId: id, format });
      const safeBase =
        topic.trim().slice(0, 40).replace(/[^\w\s-]/g, "").trim().replace(/\s+/g, "-") ||
        "kich-ban";
      const blob = new Blob([res.text], { type: res.mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${safeBase}${res.fileExt}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setExportDone(true);
      window.setTimeout(() => {
        setExportOpen(false);
        setExportDone(false);
      }, 900);
    } catch (exc) {
      setExportBanner(exc instanceof Error ? exc.message : "Không xuất được");
    }
  };

  const handleShootMode = async () => {
    setExportBanner(null);
    const id = await ensureSavedDraft();
    if (id) navigate(`/app/script/shoot/${id}`);
  };

  // S4 — dirty tracking. First effect skips the initial state restore
  // from URL params + sessionStorage; subsequent edits flip dirty=true.
  // Saving the draft (or successfully exiting via "Lưu & thoát") clears it.
  useEffect(() => {
    if (!firstEditPassed.current) {
      firstEditPassed.current = true;
      return;
    }
    setDirty(true);
  }, [topic, hookPattern, duration, toneIdx, hookDelayMs]);

  useEffect(() => {
    if (savedDraftId) setDirty(false);
  }, [savedDraftId]);

  // Header "Quay lại Xưởng Viết" — opens the exit modal when dirty,
  // otherwise navigates straight to the workspace (no params → mode
  // gate at the top of ScriptScreen renders IdeaWorkspace).
  const handleBack = () => {
    if (dirty) {
      setExitOpen(true);
      return;
    }
    navigate("/app/script");
  };

  const handleSaveAndExit = async () => {
    const id = await ensureSavedDraft();
    if (id) {
      setExitOpen(false);
      navigate(`/app/script/shoot/${encodeURIComponent(id)}`);
    }
  };

  const handleDiscardAndExit = () => {
    try {
      sessionStorage.removeItem(SCRIPT_DRAFT_STORAGE_KEY);
    } catch {
      /* ignore */
    }
    setExitOpen(false);
    navigate("/app/script");
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
            {/* S4 — back link to IdeaWorkspace. Triggers exit modal when
                ``dirty`` (unsaved edits); otherwise navigates straight to
                /app/script which renders the workspace via the mode gate. */}
            <button
              type="button"
              onClick={handleBack}
              className="mb-3 inline-flex items-center gap-1.5 text-[12px] text-[color:var(--gv-ink-3)] hover:text-[color:var(--gv-ink)] transition-colors"
            >
              <ArrowLeft className="h-3 w-3" strokeWidth={1.7} />
              Quay lại Xưởng Viết
            </button>
            <header className="mb-5 flex flex-wrap items-center justify-between gap-4 border-b-2 border-[color:var(--gv-ink)] pb-4">
              <div className="min-w-0 flex-1">
                <div className="gv-mono gv-uc mb-1.5 text-[10px] font-semibold leading-none tracking-[0.18em] text-[color:var(--gv-accent)]">
                  XƯỞNG VIẾT · KỊCH BẢN SỐ {scriptNo}
                </div>
                {/* S6 — topic header is a single-line auto-resize textarea
                    (per design pack ``screens/script.jsx`` lines 663-686).
                    Font-size scales DOWN as length grows so the H1 keeps
                    its prominence without overflowing. The sidebar CHỦ ĐỀ
                    field remains for the multi-line edit affordance and
                    stays in sync via shared ``topic`` state. */}
                <textarea
                  aria-label="Chủ đề kịch bản"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  rows={1}
                  ref={(el) => {
                    if (!el) return;
                    el.style.height = "auto";
                    el.style.height = `${el.scrollHeight}px`;
                  }}
                  className="gv-serif m-0 w-full resize-none border-0 bg-transparent p-0 leading-[1.15] text-[color:var(--gv-ink)] outline-none"
                  style={{
                    fontSize:
                      topic.length > 80
                        ? "clamp(18px, 2.0vw, 22px)"
                        : topic.length > 60
                          ? "clamp(20px, 2.4vw, 26px)"
                          : topic.length > 40
                            ? "clamp(24px, 2.8vw, 32px)"
                            : "clamp(28px, 3.4vw, 40px)",
                    letterSpacing: "-0.025em",
                    fontWeight: 500,
                  }}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <Btn
                  variant="ghost"
                  size="sm"
                  type="button"
                  onClick={handleOpenExport}
                  disabled={save.isPending || exporter.isPending}
                >
                  <Download className="h-3 w-3" strokeWidth={2} aria-hidden />
                  Xuất kịch bản
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

            {hookIsError || sceneIsError ? (
              <div
                role="status"
                className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2"
              >
                <p className="m-0 gv-mono text-[12px] text-[color:var(--gv-ink-3)]">
                  Không tải được dữ liệu ngách.
                </p>
                <Btn
                  variant="ghost"
                  size="sm"
                  type="button"
                  onClick={() => {
                    void refetchHook();
                    void refetchScene();
                  }}
                >
                  Thử lại
                </Btn>
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
                      Hầu hết video thắng rơi hook trong{" "}
                      <span className="text-[color:var(--gv-ink-2)]">0.8–1.4s</span>. Sau 1.4s, retention giảm rõ
                      rệt.
                      {nicheDisplayName ? (
                        <span className="mt-1 block">Tham chiếu cho {nicheDisplayName}.</span>
                      ) : null}
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
                  {/* IdeaRefStrip — 5 viral videos in this niche matching
                      the chosen hook. Sits above the storyboard so creators
                      can scan reference cadence/overlay before reading
                      their own shot list. Hook is the in-app selection
                      (``selectedHook``), which already accepts both the VN
                      pattern label and the raw enum. */}
                  <IdeaRefStrip
                    nicheId={effectiveNicheId}
                    hookType={selectedHook || null}
                    ideaAngle={selectedHook || topic}
                  />
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
                        onRegenerate={() => handleRegenerateShot(i)}
                        regenerating={regeneratingShot === i}
                      />
                    ))}
                  </div>
                  <ScriptForecastBar
                    durationSec={duration}
                    hookDelayMs={hookDelayMs}
                    onSaveDraft={handleSave}
                    savePending={save.isPending}
                    saved={Boolean(savedDraftId)}
                  />
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
      <ScriptExportModal
        open={exportOpen}
        busy={save.isPending || exporter.isPending}
        exported={exportDone}
        onClose={() => setExportOpen(false)}
        onExport={(fmt) => void handleExport(fmt)}
      />
      <ScriptExitModal
        open={exitOpen}
        busy={save.isPending}
        onCancel={() => setExitOpen(false)}
        onDiscard={handleDiscardAndExit}
        onSaveAndExit={() => void handleSaveAndExit()}
      />
    </AppLayout>
  );
}
