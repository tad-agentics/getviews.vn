#!/usr/bin/env node
/**
 * UIUX compliance scan — Design System v1.0 + uiux-improvement-plan V/T registries.
 * Usage: node scripts/uiux-compliance-scan.mjs [--phase 1|2|3]
 */
import { readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = join(import.meta.dirname, "..");
const SRC = join(ROOT, "src");

const phaseIdx = process.argv.indexOf("--phase");
const phaseFilter =
  phaseIdx >= 0 && process.argv[phaseIdx + 1] != null
    ? Number(process.argv[phaseIdx + 1])
    : null;

const PHASE_IDS = {
  1: new Set(["V-01", "V-02", "V-03", "V-04", "V-17", "T-01", "T-04", "T-05", "T-07"]),
  2: new Set(["V-05", "V-06", "V-07", "V-10", "V-11", "V-12", "V-16", "V-18", "T-02", "T-03", "T-06", "T-08", "T-09", "T-10"]),
  3: new Set(["V-08", "V-09", "V-14", "V-15", "V-19", "V-20", "T-11", "T-12"]),
};

const ALLOWED_TYPE_PX = new Set([11, 12, 14, 17, 22, 24, 32, 42, 48, 56, 72]);

const ROUTES = [
  { name: "Landing", file: "src/routes/_index/LandingPage.tsx" },
  { name: "Login", file: "src/routes/_auth/login/route.tsx" },
  { name: "Signup", file: "src/routes/_auth/signup/route.tsx" },
  { name: "Studio Home", file: "src/routes/_app/home/HomeScreen.tsx" },
  { name: "Trends grid", file: "src/routes/_app/trends/TrendsPatternGrid.tsx" },
  { name: "Trends Explore", file: "src/routes/_app/trends/ExploreScreen.tsx" },
  { name: "Channel", file: "src/routes/_app/channel/ChannelScreen.tsx" },
  { name: "Answer shell", file: "src/routes/_app/answer/AnswerScreen.tsx" },
  { name: "History", file: "src/routes/_app/history/HistoryScreen.tsx" },
  { name: "Settings", file: "src/routes/_app/settings/SettingsScreen.tsx" },
  { name: "Pricing", file: "src/routes/_app/pricing/PricingScreen.tsx" },
  { name: "Checkout", file: "src/routes/_app/checkout/CheckoutScreen.tsx" },
  { name: "Payment success", file: "src/routes/_app/payment-success/PaymentSuccessScreen.tsx" },
  { name: "Onboarding", file: "src/routes/_app/onboarding/OnboardingScreen.tsx" },
  { name: "Learn more", file: "src/routes/_app/learn-more/LearnMoreScreen.tsx" },
  { name: "Compare", file: "src/routes/_app/compare/CompareScreen.tsx" },
  { name: "Douyin", file: "src/routes/_app/douyin/DouyinScreen.tsx" },
  { name: "Admin", file: "src/routes/_app/admin/AdminScreen.tsx" },
];

const PRIMITIVES = [
  "src/components/v2/Btn.tsx",
  "src/components/ui/Button.tsx",
  "src/components/v2/Chip.tsx",
  "src/components/v2/QueryComposer.tsx",
  "src/components/ui/Input.tsx",
  "src/components/ui/textarea.tsx",
  "src/components/v2/SectionHeader.tsx",
  "src/components/ui/sheet.tsx",
  "src/components/ui/dialog.tsx",
  "src/components/v2/answer/pattern/HookFindingCard.tsx",
];

/** Strip // comments and trim — keeps line numbers aligned with source. */
function codeOnly(line) {
  return line.replace(/\/\/.*$/, "").trim();
}

function walk(dir, acc = []) {
  for (const ent of readdirSync(dir)) {
    const p = join(dir, ent);
    if (statSync(p).isDirectory()) {
      if (ent === "node_modules" || ent === "build") continue;
      walk(p, acc);
    } else if (/\.tsx$/.test(ent) && !/\.test\.tsx$/.test(ent)) {
      acc.push(p);
    }
  }
  return acc;
}

function scanFile(relPath, content) {
  const hits = [];
  const add = (id, severity, line, snippet) =>
    hits.push({ id, severity, line, snippet: snippet.trim().slice(0, 120) });

  const lines = content.split("\n");
  lines.forEach((line, i) => {
    const ln = i + 1;
    const code = codeOnly(line);
    if (!code || code.startsWith("*")) return;

    // V-01 motion
    if (/0\.(4[5-9]|[5-9]\d)s|duration-500|duration-\[0\.[5-9]/.test(code)) {
      add("V-01", "BLOCKING", ln, line);
    }

    // V-05 left border accent
    if (/border-l-[24].*accent|border-l-[24].*gv-accent/.test(code)) {
      add("V-05", "HIGH", ln, line);
    }

    // V-06 toLocaleString on view counts (line-level)
    if (
      /\.toLocaleString\(/.test(code) &&
      /(?:play_count|playCount|\.views\b|avg_views|median_views|creator_median_views)/.test(code) &&
      !relPath.includes("admin/")
    ) {
      add("V-06", "HIGH", ln, line);
    }

    // V-07 viral user-facing copy (skip API field identifiers)
    if (/viral/i.test(code) && !relPath.includes("intent-router")) {
      const isUserFacing =
        /["'`][^"'`]*viral[^"'`]*["'`]/i.test(code) ||
        />\s*[^<{]*viral/i.test(code);
      const isApiFieldOnly =
        /\b(virals?|virality|viral_score|is_viral|viralScore)\b/i.test(code) && !isUserFacing;
      if (isUserFacing && !isApiFieldOnly) {
        add("V-07", "HIGH", ln, line);
      }
    }

    // V-08 emoji (excl. allowed ✓/✕ diagnosis glyphs in ternary)
    if (/[🔥✨🎵💰★⚠✻]/.test(code)) {
      add("V-08", "HIGH", ln, line);
    }

    // V-10 hex (except FB)
    if (/bg-\[#(?!1877F2)/i.test(code) || /text-\[#/i.test(code)) {
      add("V-10", "HIGH", ln, line);
    }

    // V-15 gray
    if (/text-gray-\d+/.test(code)) {
      add("V-15", "LOW", ln, line);
    }

    // V-17 disabled opacity (loading-state opacity ternaries excluded)
    if (/disabled:opacity-(40|50|60)/.test(code) && !/regenerating \? "opacity/.test(line)) {
      add("V-17", "HIGH", ln, line);
    }
    if (/disabled:opacity-50/.test(code) && /accent|primary|gv-accent/.test(code)) {
      add("V-17", "HIGH", ln, line);
    }

    // V-18 shadows
    if (/shadow-lg|shadow-xl/.test(code)) {
      add("V-18", "HIGH", ln, line);
    }

    // T-01 arbitrary text size off scale
    const pxMatch = code.matchAll(/text-\[(\d+(?:\.\d+)?)px\]/g);
    for (const m of pxMatch) {
      const px = parseFloat(m[1]);
      if (!ALLOWED_TYPE_PX.has(px)) {
        add("T-01", "HIGH", ln, line);
      }
    }

    // T-04 kicker without utility
    if (
      /text-\[(9|10)px\].*uppercase|uppercase.*text-\[(9|10)px\]/.test(code) &&
      !/gv-kicker|gv-uc/.test(code)
    ) {
      add("T-04", "HIGH", ln, line);
    }

    // T-07 body in ink-4
    if (/text-\[color:var\(--gv-ink-4\)\]/.test(code) && /<p[^>]*>/.test(code)) {
      add("T-07", "MEDIUM", ln, line);
    }
  });

  return hits;
}

function scanCss(content) {
  const hits = [];
  if (/gv-fade-up[\s\S]*?0\.45s/.test(content))
    hits.push({
      id: "V-01",
      severity: "BLOCKING",
      file: "src/app.css",
      snippet: "gv-fade-up 0.45s",
    });
  if (
    /animate-scroll-ticker/.test(content) &&
    !/prefers-reduced-motion[\s\S]*animate-scroll-ticker/.test(content)
  ) {
    hits.push({
      id: "V-02",
      severity: "BLOCKING",
      file: "src/app.css",
      snippet: "scroll ticker missing PRM",
    });
  }
  if (/\.gv-kicker[\s\S]*?font-size:\s*10px/.test(content)) {
    hits.push({
      id: "T-04",
      severity: "HIGH",
      file: "src/app.css",
      snippet: "gv-kicker 10px drift",
    });
  }
  return hits;
}

function applyPhaseFilter(hits) {
  if (phaseFilter == null || Number.isNaN(phaseFilter)) return hits;
  const allowed = PHASE_IDS[phaseFilter];
  if (!allowed) {
    console.warn(`Unknown --phase ${phaseFilter}; valid: 1, 2, 3`);
    return hits;
  }
  return hits.filter((h) => allowed.has(h.id));
}

const files = walk(SRC);
const fileResults = {};
let allHits = [];

for (const abs of files) {
  const rel = relative(ROOT, abs);
  const content = readFileSync(abs, "utf8");
  const hits = scanFile(rel, content);
  if (hits.length) fileResults[rel] = hits;
  allHits = allHits.concat(hits.map((h) => ({ ...h, file: rel })));
}

try {
  const css = readFileSync(join(ROOT, "src/app.css"), "utf8");
  allHits = allHits.concat(scanCss(css));
} catch {
  /* app.css optional in partial workspaces */
}

allHits = applyPhaseFilter(allHits);

const filteredFileResults = {};
for (const h of allHits) {
  if (!h.file) continue;
  filteredFileResults[h.file] = filteredFileResults[h.file] ?? [];
  filteredFileResults[h.file].push(h);
}

const byId = {};
for (const h of allHits) {
  byId[h.id] = byId[h.id] ?? { count: 0, severity: h.severity };
  byId[h.id].count++;
}

const routeScores = ROUTES.map(({ name, file }) => {
  const hits = filteredFileResults[file] ?? [];
  const typeHits = hits.filter((h) => h.id.startsWith("T-"));
  const blocking = hits.filter((h) => h.severity === "BLOCKING").length;
  const high = hits.filter((h) => h.severity === "HIGH").length;
  let verdict = "PASS";
  if (blocking > 0 || high > 3) verdict = "FAIL";
  else if (hits.length > 0) verdict = "CONCERNS";
  return { name, file, verdict, hits: hits.length, typeHits: typeHits.length };
});

const summary = {
  scannedAt: new Date().toISOString(),
  filesScanned: files.length,
  totalHits: allHits.length,
  byViolationId: byId,
  routeScores,
  primitiveFiles: PRIMITIVES.map((f) => ({
    file: f,
    hits: (filteredFileResults[f] ?? []).length,
  })),
  phaseFilter: phaseFilter ?? "all",
};

const outPath = join(ROOT, "artifacts/qa-reports/uiux-ds-audit-2026-05-23.json");
writeFileSync(
  outPath,
  JSON.stringify(
    {
      summary,
      fileResults: filteredFileResults,
      topFiles: Object.entries(filteredFileResults)
        .sort((a, b) => b[1].length - a[1].length)
        .slice(0, 30),
    },
    null,
    2,
  ),
);

console.log(JSON.stringify(summary, null, 2));
console.log(`\nWrote ${outPath}`);
