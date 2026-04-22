import { Camera, Film, MonitorSmartphone, Package, Play, Type, Zap } from "lucide-react";

import { sceneTypeVi } from "@/lib/constants/enum-labels-vi";

/**
 * BUG-17 (QA audit 2026-04-22): the shot timeline rendered every shot's
 * "thumbnail" as the same dark palette block regardless of scene type, so
 * CẬN MẶT, B-ROLL, POV, and CẬN TAY were visually indistinguishable. The
 * fix is deterministic per-type visuals (gradient + icon + label) so a
 * creator scanning the timeline can tell shots apart at a glance — no
 * image assets required.
 *
 * ``intelSceneType`` is the canonical scene enum
 * (``face_to_camera`` / ``product_shot`` / …); ``cam`` is the
 * creator-authored camera hint ("Cận mặt", "Cắt nhanh b-roll", …). When
 * ``intelSceneType`` is missing we fall back to normalised ``cam``.
 */

type VisualStyle = {
  bg: string;
  icon: typeof Camera;
  label: string;
};

const SHOT_VISUALS: Record<string, VisualStyle> = {
  face_to_camera: {
    bg: "bg-[linear-gradient(135deg,#3D2F4A_0%,#5A3F68_100%)]",
    icon: Camera,
    label: "Cận mặt",
  },
  product_shot: {
    bg: "bg-[linear-gradient(135deg,#5A3E1F_0%,#8A5E2F_100%)]",
    icon: Package,
    label: "Cận sản phẩm",
  },
  screen_recording: {
    bg: "bg-[linear-gradient(135deg,#1F3A5C_0%,#2F5A8E_100%)]",
    icon: MonitorSmartphone,
    label: "Quay màn hình",
  },
  broll: {
    bg: "bg-[linear-gradient(135deg,#2A3A5C_0%,#3E5A8A_100%)]",
    icon: Film,
    label: "B-roll",
  },
  text_card: {
    bg: "bg-[linear-gradient(135deg,#3A2F2F_0%,#5A4848_100%)]",
    icon: Type,
    label: "Thẻ chữ",
  },
  demo: {
    bg: "bg-[linear-gradient(135deg,#1F4A3C_0%,#2F6E56_100%)]",
    icon: Play,
    label: "Demo",
  },
  action: {
    bg: "bg-[linear-gradient(135deg,#4A2F2F_0%,#6E3F3F_100%)]",
    icon: Zap,
    label: "Hành động",
  },
  other: {
    bg: "bg-[linear-gradient(135deg,#333_0%,#555_100%)]",
    icon: Film,
    label: "Khác",
  },
};

// Fallback for free-form Vietnamese cam labels like "Cắt nhanh b-roll" that
// don't carry the canonical enum. Keyword-match to the closest scene type.
function inferSceneTypeFromCam(cam: string | null | undefined): string {
  if (!cam) return "other";
  const c = cam.toLowerCase();
  if (c.includes("mặt") || c.includes("pov")) return "face_to_camera";
  if (c.includes("sản phẩm") || c.includes("product")) return "product_shot";
  if (c.includes("màn hình") || c.includes("screen")) return "screen_recording";
  if (c.includes("b-roll") || c.includes("broll") || c.includes("b roll")) return "broll";
  if (c.includes("chữ") || c.includes("text")) return "text_card";
  if (c.includes("demo") || c.includes("thử")) return "demo";
  if (c.includes("hành động") || c.includes("action") || c.includes("cắt")) return "action";
  return "other";
}

export type ShotTypeVisualProps = {
  intelSceneType?: string | null;
  cam?: string | null;
  className?: string;
  /** Shown as a subline under the icon; defaults to ``cam``. */
  caption?: string | null;
};

export function ShotTypeVisual({ intelSceneType, cam, className = "", caption }: ShotTypeVisualProps) {
  const sceneKey = intelSceneType?.trim() || inferSceneTypeFromCam(cam);
  const style = SHOT_VISUALS[sceneKey] ?? SHOT_VISUALS.other!;
  const Icon = style.icon;
  const sub = caption ?? cam ?? sceneTypeVi(sceneKey, style.label);

  return (
    <div
      className={`relative flex h-full w-full flex-col items-center justify-center gap-1.5 p-2 text-[color:var(--gv-canvas)] ${style.bg} ${className}`.trim()}
      aria-label={`Scene type: ${style.label}`}
    >
      <Icon className="h-5 w-5 opacity-90" strokeWidth={1.75} aria-hidden />
      <span className="gv-mono text-center text-[9px] leading-[1.1] opacity-80 line-clamp-2">
        {sub}
      </span>
    </div>
  );
}
