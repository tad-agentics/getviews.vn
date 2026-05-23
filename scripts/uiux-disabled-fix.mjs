#!/usr/bin/env node
/** Replace disabled:opacity-* with DS faint-surface pattern across src. */
import { readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const SRC = join(import.meta.dirname, "..", "src");

const FAINT_DISABLED =
  "disabled:pointer-events-none disabled:cursor-not-allowed disabled:border-[color:var(--gv-rule)] disabled:bg-[color:var(--gv-faint)] disabled:text-[color:var(--gv-ink-4)] disabled:opacity-100";

const ARIA_FAINT =
  "aria-disabled:pointer-events-none aria-disabled:cursor-not-allowed aria-disabled:border-[color:var(--gv-rule)] aria-disabled:bg-[color:var(--gv-faint)] aria-disabled:text-[color:var(--gv-ink-4)] aria-disabled:opacity-100";

function walk(dir, acc = []) {
  for (const ent of readdirSync(dir)) {
    const p = join(dir, ent);
    if (statSync(p).isDirectory()) {
      if (ent === "node_modules" || ent === "build") continue;
      walk(p, acc);
    } else if (/\.tsx$/.test(ent) && !/\.test\.tsx$/.test(ent)) acc.push(p);
  }
  return acc;
}

function fix(content) {
  let out = content;
  out = out.replace(/\bdisabled:opacity-50\b/g, FAINT_DISABLED);
  out = out.replace(/\bdisabled:opacity-40\b/g, FAINT_DISABLED);
  out = out.replace(/\bdisabled:opacity-60\b/g, FAINT_DISABLED);
  out = out.replace(/\baria-disabled:opacity-50\b/g, ARIA_FAINT);
  out = out.replace(/\bhas-disabled:opacity-50\b/g, "has-disabled:opacity-100");
  return out;
}

let n = 0;
for (const abs of walk(SRC)) {
  const before = readFileSync(abs, "utf8");
  const after = fix(before);
  if (after !== before) {
    writeFileSync(abs, after);
    n++;
  }
}
console.log(`Updated disabled styling in ${n} files`);
