import { reactRouter } from "@react-router/dev/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";
import { VitePWA } from "vite-plugin-pwa";

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
  if (
    n.includes("node_modules/react-dom") ||
    n.includes("node_modules/scheduler/") ||
    n.includes("node_modules/react/")
  )
    return "react-vendor";
  return "vendor";
}

import { VitePWA } from "vite-plugin-pwa";

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

    VitePWA({
      registerType: "autoUpdate",
      manifest: false, // Use static public/manifest.json
      workbox: {
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
        navigateFallback: "/index.html",
        navigateFallbackAllowlist: [/^\/app/],
      },
    }),
  ],
});
