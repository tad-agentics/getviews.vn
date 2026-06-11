import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react-swc";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [tsconfigPaths({ projects: ["./tsconfig.app.json"] }), react()],
  test: {
    environment: "jsdom",
    // Playwright lives under /tests and uses its own runner; Supabase Edge
    // Function tests are Deno (run via `deno test` in CI's edge-functions job).
    exclude: ["**/node_modules/**", "**/dist/**", "**/.{idea,git,cache,output,temp}/**", "tests/**", "supabase/**"],
  },
});
