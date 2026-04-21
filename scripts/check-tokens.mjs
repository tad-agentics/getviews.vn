#!/usr/bin/env node
/**
 * check-tokens — Phase D.4.3 lint for legacy design-system tokens.
 *
 * After the D.4 sweep (commits b7187d4 .. 487f369), no source file
 * outside the two whitelisted paths below should reference `--purple`,
 * `--purple-light`, `--ink-soft`, `--border-active`, `--gv-purple`, or
 * the deprecated `variant="purple"` Badge value. This script scans the
 * tracked source tree and exits with code 1 if a new violator appears.
 *
 * Run via `npm run typecheck` (which chains this as its final step) or
 * directly: `node scripts/check-tokens.mjs`.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const SRC = join(ROOT, "src");

// Paths that intentionally reference legacy tokens (e.g. test fixtures
// that assert legacy tokens are *absent* from rendered className strings).
// Paths are matched as posix relative-to-repo-root strings.
const ALLOWLIST = new Set([
  // Badge.test.tsx asserts the shim renders without leaking the legacy
  // tokens — it has to mention the token names to check for them.
  "src/components/ui/Badge.test.tsx",
  // This file is the scanner itself.
  "scripts/check-tokens.mjs",
]);

const PATTERNS = [
  { id: "var(--purple)",        re: /var\(--purple\)/ },
  { id: "var(--purple-light)",  re: /var\(--purple-light\)/ },
  { id: "var(--purple-dark)",   re: /var\(--purple-dark\)/ },
  { id: "var(--ink-soft)",      re: /var\(--ink-soft\)/ },
  { id: "var(--border-active)", re: /var\(--border-active\)/ },
  { id: "--gv-purple",          re: /--gv-purple\b/ },
  { id: 'variant="purple"',     re: /variant="purple"/ },
];

const EXTENSIONS = new Set([".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".css"]);

/** @returns {string[]} */
function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    if (name === "node_modules" || name.startsWith(".")) continue;
    const full = join(dir, name);
    const st = statSync(full);
    if (st.isDirectory()) out.push(...walk(full));
    else if (EXTENSIONS.has(name.slice(name.lastIndexOf(".")))) out.push(full);
  }
  return out;
}

const violations = [];

for (const path of walk(SRC)) {
  const rel = relative(ROOT, path).split("\\").join("/");
  if (ALLOWLIST.has(rel)) continue;
  const text = readFileSync(path, "utf8");
  const lines = text.split("\n");
  for (let i = 0; i < lines.length; i++) {
    for (const { id, re } of PATTERNS) {
      if (re.test(lines[i])) {
        violations.push({ rel, line: i + 1, id, content: lines[i].trim() });
      }
    }
  }
}

if (violations.length === 0) {
  console.log("check-tokens: 0 legacy-token violations across src/ ✓");
  process.exit(0);
}

console.error(`check-tokens: ${violations.length} legacy-token violation(s) found:\n`);
for (const v of violations) {
  console.error(`  ${v.rel}:${v.line}  [${v.id}]`);
  console.error(`    ${v.content}`);
}
console.error(
  "\nPhase D.4 retired these tokens. Map to the gv-* namespace:\n" +
    "  var(--purple)        → var(--gv-accent)\n" +
    "  var(--purple-light)  → var(--gv-accent-soft)\n" +
    "  var(--ink-soft)      → var(--gv-ink-3)\n" +
    "  var(--border-active) → var(--gv-ink) (emphasised) or var(--gv-rule) (neutral)\n" +
    "  <Badge variant={purple}>  → <Badge variant={default}>\n" +
    "\nIf a reference is intentional (e.g. a shim regression test), add the path\n" +
    "to ALLOWLIST in scripts/check-tokens.mjs.",
);
process.exit(1);
