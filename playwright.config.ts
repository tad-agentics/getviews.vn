import { defineConfig, devices } from "@playwright/test";
import { readFileSync } from "node:fs";

// Load .env.local manually so VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY are
// available to test helpers (resetProcessingFlag etc.) without a dotenv dep.
try {
  const lines = readFileSync(".env.local", "utf-8").split("\n");
  for (const line of lines) {
    const m = line.match(/^([A-Z0-9_]+)="?([^"]*)"?$/);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2];
  }
} catch { /* file absent in CI — env vars come from the environment */ }

const BASE_URL = process.env.GV_BASE_URL ?? "https://getviews.vn";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 10_000 },
  retries: 0,
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
    ["json", { outputFile: "playwright-report/results.json" }],
  ],
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    video: "retain-on-failure",
    screenshot: "only-on-failure",
    locale: "vi-VN",
    viewport: { width: 1280, height: 900 },
  },
  projects: [
    {
      name: "setup",
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: "quick-actions",
      testMatch: /quick-actions\.spec\.ts/,
      dependencies: ["setup"],
      use: { ...devices["Desktop Chrome"], storageState: ".auth/user.json" },
    },
  ],
});
