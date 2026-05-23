#!/usr/bin/env node
/**
 * Bulk typography compliance fix — maps off-scale text-[Npx] to DS-allowed sizes/utilities.
 * Usage: node scripts/uiux-typography-fix.mjs [--dry-run]
 */
import { readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(import.meta.dirname, "..");
const SRC = join(ROOT, "src");
const dryRun = process.argv.includes("--dry-run");

const PX_REPLACEMENTS = [
  [/text-\[40px\]/g, "text-[42px]"],
  [/text-\[36px\]/g, "text-[32px]"],
  [/text-\[30px\]/g, "text-[32px]"],
  [/text-\[28px\]/g, "text-[24px]"],
  [/text-\[26px\]/g, "text-[24px]"],
  [/text-\[20px\]/g, "text-[22px]"],
  [/text-\[19px\]/g, "text-[17px]"],
  [/text-\[18px\]/g, "text-[17px]"],
  [/text-\[16px\]/g, "text-[17px]"],
  [/text-\[15px\]/g, "text-[17px]"],
  [/text-\[13\.5px\]/g, "text-sm"],
  [/text-\[13px\]/g, "text-sm"],
  [/text-\[12\.5px\]/g, "text-xs"],
  [/text-\[11\.5px\]/g, "text-xs"],
  [/text-\[10\.5px\]/g, "text-[11px]"],
  [/text-\[9\.5px\]/g, "text-[11px]"],
  [/text-\[10px\]/g, "text-[11px]"],
  [/text-\[9px\]/g, "text-[11px]"],
  [/text-\[8px\]/g, "text-[11px]"],
  [/text-\[7px\]/g, "text-[11px]"],
];

/** Collapse redundant mono + uppercase kicker stacks into gv-kicker. */
function fixKickers(content) {
  let out = content;
  const patterns = [
    [
      /\bgv-mono\s+text-\[11px\](?:\s+font-(?:semibold|medium|bold))?(?:\s+uppercase)?(?:\s+tracking-\[[^\]]+\])?(?:\s+tracking-wider)?(?:\s+tracking-wide)?/g,
      "gv-kicker",
    ],
    [
      /\bfont-mono\s+text-\[11px\](?:\s+font-(?:semibold|medium|bold))?(?:\s+uppercase)?(?:\s+tracking-\[[^\]]+\])?(?:\s+tracking-wider)?(?:\s+tracking-wide)?/g,
      "gv-kicker",
    ],
    [
      /\btext-\[11px\]\s+font-mono(?:\s+font-(?:semibold|medium|bold))?(?:\s+uppercase)?(?:\s+tracking-\[[^\]]+\])?(?:\s+tracking-wider)?(?:\s+tracking-wide)?/g,
      "gv-kicker",
    ],
    [
      /\btext-\[11px\]\s+gv-mono(?:\s+font-(?:semibold|medium|bold))?(?:\s+uppercase)?(?:\s+tracking-\[[^\]]+\])?(?:\s+tracking-wider)?(?:\s+tracking-wide)?/g,
      "gv-kicker",
    ],
  ];
  for (const [re, rep] of patterns) {
    out = out.replace(re, rep);
  }
  // uppercase label on allowed 11px without utility
  out = out.replace(
    /className="([^"]*)\buppercase\b([^"]*text-\[11px\][^"]*)"/g,
    (m, a, b) => {
      if (/gv-kicker|gv-uc/.test(m)) return m;
      return `className="${a}gv-kicker ${b.replace(/\buppercase\b/g, "").replace(/\s+/g, " ").trim()}"`;
    },
  );
  out = out.replace(
    /className="([^"]*text-\[11px\][^"]*)\buppercase\b([^"]*)"/g,
    (m, a, b) => {
      if (/gv-kicker|gv-uc/.test(m)) return m;
      return `className="${a}gv-kicker ${b.replace(/\buppercase\b/g, "").replace(/\s+/g, " ").trim()}"`;
    },
  );
  return out;
}

function fixBodyInk4(content) {
  return content.replace(
    /(<p[^>]*className="[^"]*)text-\[color:var\(--gv-ink-4\)\]/g,
    "$1text-[color:var(--gv-ink-3)]",
  );
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

let changed = 0;
for (const abs of walk(SRC)) {
  let content = readFileSync(abs, "utf8");
  const before = content;
  for (const [re, rep] of PX_REPLACEMENTS) {
    content = content.replace(re, rep);
  }
  content = fixKickers(content);
  content = fixBodyInk4(content);
  if (content !== before) {
    changed++;
    if (!dryRun) writeFileSync(abs, content);
  }
}

console.log(`${dryRun ? "[dry-run] " : ""}Updated ${changed} files`);
