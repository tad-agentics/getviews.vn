/**
 * Quality gates that run BEFORE inserting a video into video_corpus.
 * Each gate returns { pass: boolean, reason?: string }.
 * If any gate fails, skip the video and log the reason.
 * Returns a transforms object with normalized values to merge into the row.
 */

import { type Analysis, detectLanguage, normalizeHandle, normalizeHookType } from './classifiers';

interface Metadata {
  createTime?: number;
  statistics?: {
    playCount?: number;
    collectCount?: number;
    [key: string]: unknown;
  };
  stats?: {
    playCount?: number;
    collectCount?: number;
    [key: string]: unknown;
  };
  author?: {
    username?: string;
    uniqueId?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface GateResult {
  pass: boolean;
  reason?: string;
}

export interface ValidationResult {
  valid: boolean;
  reason?: string;
  transforms: Record<string, unknown>;
}

// ── Individual gates ─────────────────────────────────────────────────────────

/** Gate 1: Language — must be Vietnamese */
function gateLanguage(analysis: Analysis): GateResult {
  const lang = detectLanguage(analysis);
  if (lang !== 'vi') {
    return { pass: false, reason: `language=${lang} (non-Vietnamese)` };
  }
  return { pass: true };
}

/** Gate 2: Views > 0 (unless video is <24h old) */
function gateViews(metadata: Metadata): GateResult {
  const views =
    metadata.statistics?.playCount ??
    metadata.stats?.playCount ??
    0;

  if (views === 0) {
    const createTime = metadata.createTime;
    if (createTime) {
      const hoursSincePost = (Date.now() - createTime * 1000) / (1000 * 60 * 60);
      if (hoursSincePost > 24) {
        return { pass: false, reason: 'views=0 after 24h — likely data issue' };
      }
    } else {
      return { pass: false, reason: 'views=0 and no createTime — cannot verify age' };
    }
  }

  return { pass: true };
}

/** Gate 3: ER sanity — clamp ER > 1.0 to 0 */
function gateER(
  views: number,
  likes: number,
  comments: number,
  shares: number,
): { pass: boolean; er: number } {
  const er = views > 0 ? (likes + comments + shares) / views : 0;
  if (er > 1) {
    return { pass: true, er: 0 };
  }
  return { pass: true, er };
}

/** Gate 6: Duration must be 3–600 seconds */
function gateDuration(analysis: Analysis): GateResult {
  const scenes = analysis.scenes ?? [];
  const duration = scenes.length > 0 ? (scenes[scenes.length - 1]?.end ?? 0) : 0;
  if (duration < 3 || duration > 600) {
    return {
      pass: false,
      reason: `duration=${duration}s outside 3-600s range`,
    };
  }
  return { pass: true };
}

/** Gate 7: Minimum analysis quality */
function gateAnalysisQuality(analysis: Analysis): GateResult {
  const hasHook = !!analysis.hook_analysis?.hook_type;
  const hasScenes = (analysis.scenes?.length ?? 0) > 0;
  const hasTranscript = (analysis.audio_transcript?.length ?? 0) > 10;

  if (!hasHook && !hasScenes && !hasTranscript) {
    return {
      pass: false,
      reason: 'analysis too thin (no hook, no scenes, no transcript)',
    };
  }
  return { pass: true };
}

// ── Main validation function ─────────────────────────────────────────────────

/**
 * Run all quality gates and return transforms to apply on the row.
 * Call this BEFORE building the full corpus row.
 *
 * Usage:
 *   const v = validateForCorpus(metadata, analysis, { handle, views, likes, comments, shares });
 *   if (!v.valid) { log.info(`Skipping: ${v.reason}`); continue; }
 *   const row = { ...existingFields, ...v.transforms, ... };
 */
export function validateForCorpus(
  metadata: Metadata,
  analysis: Analysis,
  stats: { handle: string; views: number; likes: number; comments: number; shares: number },
): ValidationResult {
  const { handle, views, likes, comments, shares } = stats;

  const gate1 = gateLanguage(analysis);
  if (!gate1.pass) return { valid: false, reason: gate1.reason, transforms: {} };

  const gate2 = gateViews(metadata);
  if (!gate2.pass) return { valid: false, reason: gate2.reason, transforms: {} };

  const gate6 = gateDuration(analysis);
  if (!gate6.pass) return { valid: false, reason: gate6.reason, transforms: {} };

  const gate7 = gateAnalysisQuality(analysis);
  if (!gate7.pass) return { valid: false, reason: gate7.reason, transforms: {} };

  const { er } = gateER(views, likes, comments, shares);

  const transforms: Record<string, unknown> = {
    creator_handle: normalizeHandle(handle),
    engagement_rate: er,
    hook_type: normalizeHookType(analysis.hook_analysis?.hook_type ?? 'other'),
    language: 'vi',
  };

  return { valid: true, transforms };
}
