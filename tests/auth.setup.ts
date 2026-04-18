import { test, expect } from "@playwright/test";
import { existsSync, mkdirSync, statSync } from "node:fs";

const AUTH_FILE = ".auth/user.json";
// Reuse saved auth for 12h before forcing another manual login.
const AUTH_TTL_MS = 12 * 60 * 60 * 1000;
// Set FORCE_AUTH=1 to ignore the cached state and re-login.
const FORCE_AUTH = process.env.FORCE_AUTH === "1";

/**
 * One-time auth bootstrap.
 *
 * getviews.vn only supports Facebook + Google OAuth, which can't be scripted
 * safely. On first run this test opens a real browser and waits for you to
 * log in; when the app lands on /app it saves storageState to .auth/user.json.
 *
 * On subsequent runs this test is a no-op (skips when the file exists and is
 * fresher than AUTH_TTL_MS). Set FORCE_AUTH=1 to re-authenticate.
 */
test("manual OAuth login → save storageState", async ({ page, context }) => {
  if (!FORCE_AUTH && existsSync(AUTH_FILE)) {
    const ageMs = Date.now() - statSync(AUTH_FILE).mtimeMs;
    if (ageMs < AUTH_TTL_MS) {
      test.info().annotations.push({
        type: "auth",
        description: `reusing .auth/user.json (age ${Math.round(ageMs / 60_000)}m)`,
      });
      return;
    }
  }

  test.setTimeout(5 * 60_000); // 5 minutes to log in
  mkdirSync(".auth", { recursive: true });

  await page.goto("/login");

  // Wait until we land on /app (auth guard passed). Any OAuth flow ends here.
  await page.waitForURL(/\/app(\/|$|\?)/, { timeout: 5 * 60_000 });

  await expect(page.getByText(/Sẵn sàng phân tích|Thao tác nhanh/i).first()).toBeVisible({
    timeout: 30_000,
  });

  await context.storageState({ path: AUTH_FILE });

  if (!existsSync(AUTH_FILE)) throw new Error(`Failed to write ${AUTH_FILE}`);
});
