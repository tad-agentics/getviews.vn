import { reactRouter } from "@react-router/dev/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

/** Split heavy vendors so chunks cache independently and initial parse stays smaller on mobile. */
function manualChunks(id: string) {
  if (!id.includes("node_modules")) return;
  // Rollup IDs may use backslashes on Windows — normalize before segment checks.
  const n = id.replace(/\\/g, "/");
  if (n.includes("@radix-ui")) return "radix-ui";
  if (n.includes("@tanstack")) return "tanstack";
  if (n.includes("@supabase")) return "supabase";
  if (n.includes("lucide-react")) return "icons";
  if (n.includes("motion") || n.includes("framer-motion")) return "motion";
  if (n.includes("react-router") || n.includes("@remix-run")) return "react-router";
  // Match the real `react` package only (`.../node_modules/react/...`), not loose `/react/`
  // (avoids odd substring matches). `react-dom` is a different folder: `react-dom/...`.
  if (
    n.includes("node_modules/react-dom") ||
    n.includes("node_modules/scheduler/") ||
    n.includes("node_modules/react/")
  )
    return "react-vendor";
  return "vendor";
}

// PWA — uncomment ONE of these after evaluating during /init:
// Option A: vite-plugin-pwa (Workbox — more battle-tested for Vite)
// import { VitePWA } from "vite-plugin-pwa";
// Option B: @serwist/vite (if Serwist Vite plugin is mature enough at build time)
// import { serwist } from "@serwist/vite";

export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks,
      },
    },
  },
  plugins: [
    tailwindcss(),
    reactRouter(),
    tsconfigPaths(),

    // PWA plugin goes here — configured during /init based on evaluation
    // VitePWA({
    //   registerType: "autoUpdate",
    //   manifest: false, // Use static public/manifest.json
    //   workbox: {
    //     globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
    //     navigateFallback: "/index.html",
    //     navigateFallbackAllowlist: [/^\/app/],
    //   },
    // }),
  ],
});
