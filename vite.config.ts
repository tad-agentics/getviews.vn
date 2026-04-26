import path from "node:path";
import { fileURLToPath } from "node:url";
import { reactRouter } from "@react-router/dev/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig, type Plugin } from "vitest/config";
import tsconfigPaths from "vite-tsconfig-paths";
import { VitePWA } from "vite-plugin-pwa";

/** App directory (e.g. getviews.vn-1); dependencies may be hoisted to the parent folder. */
const viteConfigDir = path.dirname(fileURLToPath(import.meta.url));

/**
 * Dev-only Vite plugin that proxies POST /api/chat to the Vercel Edge Function
 * handler (`api/chat.ts`) via ssrLoadModule. In production, Vercel routes
 * /api/* directly to the Edge Function before the SPA rewrite.
 */
function vercelEdgeDev(): Plugin {
  return {
    name: "vercel-edge-dev",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (req.url !== "/api/chat") return next();

        // Collect the request body from the Node.js stream.
        const body = await new Promise<Buffer>((resolve, reject) => {
          const chunks: Buffer[] = [];
          req.on("data", (chunk: Buffer) => chunks.push(chunk));
          req.on("end", () => resolve(Buffer.concat(chunks)));
          req.on("error", reject);
        });

        // Convert Node.js headers to a plain Record.
        const headers: Record<string, string> = {};
        for (const [key, value] of Object.entries(req.headers)) {
          if (typeof value === "string") headers[key] = value;
          else if (Array.isArray(value)) headers[key] = value.join(", ");
        }

        // Construct a Web API Request the handler expects (BodyInit, not Node Buffer).
        const webReq = new Request(`http://localhost${req.url}`, {
          method: req.method ?? "GET",
          headers,
          ...(body.length > 0 ? { body: new Uint8Array(body) } : {}),
        });

        try {
          // ssrLoadModule transforms TypeScript through Vite's pipeline.
          const mod = await server.ssrLoadModule("/api/chat.ts");
          const handler = mod.default as (req: Request) => Promise<Response>;
          const webRes = await handler(webReq);

          res.statusCode = webRes.status;
          webRes.headers.forEach((value: string, key: string) =>
            res.setHeader(key, value)
          );

          // Stream the SSE body back to the browser.
          if (webRes.body) {
            const reader = webRes.body.getReader();
            const pump = (): Promise<void> =>
              reader.read().then(({ done, value }) => {
                if (done) {
                  res.end();
                  return;
                }
                return new Promise<void>((resolve, reject) =>
                  res.write(value, (err) => (err ? reject(err) : resolve()))
                ).then(pump);
              });
            await pump();
          } else {
            res.end();
          }
        } catch (err) {
          console.error("[vercel-edge-dev] /api/chat error:", err);
          next(err);
        }
      });
    },
  };
}

/** Split heavy vendors so chunks cache independently and initial parse stays smaller on mobile. */
function manualChunks(id: string) {
  if (!id.includes("node_modules")) return;
  const n = id.replace(/\\/g, "/");
  if (n.includes("@radix-ui")) return "radix-ui";
  if (n.includes("@tanstack")) return "tanstack";
  if (n.includes("@supabase")) return "supabase";
  if (n.includes("lucide-react")) return "icons";
  if (n.includes("motion") || n.includes("framer-motion")) return "motion";
  if (n.includes("react-router") || n.includes("@remix-run")) return "react-router";
  // KNOWN: ``react-vendor`` does not currently emit as a separate chunk
  // under Rolldown — the matcher fires (verified via debug logging) and
  // returns "react-vendor", but Rolldown's chunk-merging pass folds it
  // into the generic ``vendor`` bundle anyway. Bundle audit 2026-04-25
  // confirmed the React/react-dom/scheduler bytes (~117 KB raw) ride
  // ``vendor-*.js``. Long-tail caching wins from a separate React chunk
  // are deferred until we either bisect a Rolldown option that respects
  // the return value here or migrate the chunking strategy to
  // ``output.advancedChunks``.
  if (
    n.includes("/react-dom/") ||
    n.includes("/scheduler/") ||
    /\/react\/[^/]/.test(n)
  )
    return "react-vendor";
  return "vendor";
}

export default defineConfig({
  server: {
    fs: {
      // Hoisted installs: @react-router/dev resolves from ../node_modules, which Vite
      // serves as /@fs/<parent>/... — outside the app root by default → 403 and a blank page.
      allow: [path.resolve(viteConfigDir, "..")],
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks,
      },
    },
  },
  plugins: [
    vercelEdgeDev(),
    tailwindcss(),
    reactRouter(),
    tsconfigPaths({ projects: ["./tsconfig.app.json"] }),

    VitePWA({
      registerType: "autoUpdate",
      manifest: false, // Use static public/manifest.json
      workbox: {
        // React Router v7 client build writes here (not Vite default ``dist/``).
        globDirectory: "build/client",
        globPatterns: ["**/*.{js,mjs,css,html,ico,png,svg,webp,woff2,json}"],
        navigateFallback: "/index.html",
        // Do not restrict fallback to /^\/app/ — that breaks /login, /signup, /auth/callback,
        // and / on hard refresh when the service worker handles navigation.
        navigateFallbackDenylist: [/^\/api\//],
        cleanupOutdatedCaches: true,
        // Ensures Workbox always has a runtime strategy even if globs miss (Rolldown edge cases).
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/fonts\.(?:googleapis|gstatic)\.com\/.*/i,
            handler: "CacheFirst",
            options: {
              cacheName: "google-fonts",
              expiration: { maxEntries: 16, maxAgeSeconds: 60 * 60 * 24 * 365 },
            },
          },
        ],
      },
    }),
  ],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
    env: {
      VITE_SUPABASE_URL: "https://test-project.supabase.co",
      VITE_SUPABASE_PUBLISHABLE_KEY: "vitest-publishable-key-placeholder",
    },
  },
});
