/**
 * React Router prerenders `/` → `build/client/index.html` *after* the client
 * bundle + Workbox precache manifest are emitted, so `index.html` is missing
 * from precache and `createHandlerBoundToURL("/index.html")` throws
 * `non-precached-url`. Append a hashed entry once `index.html` exists.
 */
import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const indexPath = join(root, "build/client/index.html");
const swPath = join(root, "build/client/sw.js");

if (!existsSync(swPath)) {
  console.warn("[append-pwa-precache-index] skip: build/client/sw.js missing");
  process.exit(0);
}

if (!existsSync(indexPath)) {
  console.warn("[append-pwa-precache-index] skip: build/client/index.html missing");
  process.exit(0);
}

const revision = createHash("sha256").update(readFileSync(indexPath)).digest("hex").slice(0, 20);
const entry = `{url:"index.html",revision:"${revision}"}`;

let sw = readFileSync(swPath, "utf8");
if (sw.includes('"index.html"')) {
  console.info("[append-pwa-precache-index] index.html already listed — skipping");
  process.exit(0);
}

const marker = "precacheAndRoute([";
const idx = sw.indexOf(marker);
if (idx === -1) {
  console.error("[append-pwa-precache-index] precacheAndRoute([ not found in sw.js");
  process.exit(1);
}

const insertAt = idx + marker.length;
sw = `${sw.slice(0, insertAt)}${entry},${sw.slice(insertAt)}`;
writeFileSync(swPath, sw);
console.info("[append-pwa-precache-index] injected precache entry for index.html");
