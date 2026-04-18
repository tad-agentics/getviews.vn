import { test, expect } from "@playwright/test";
import { existsSync } from "node:fs";
import { mkdirSync } from "node:fs";

const AUTH_FILE = ".auth/user.json";

/**
 * One-time auth bootstrap.
 *
 * getviews.vn only supports Facebook + Google OAuth, which can't be scripted
 * safely. So this test opens a real browser and waits for YOU to log in
 * manually. When it detects `/app` (the post-login route) it saves
 * storageState to `.auth/user.json`. Subsequent test runs reuse that file.
 *
 * Run once with a headed browser:
 *   npx playwright test auth.setup.ts --headed --project=setup
 *
 * Re-run whenever the session expires.
 */
test("manual OAuth login → save storageState", async ({ page, context }) => {
  test.setTimeout(5 * 60_000); // 5 minutes to log in

  mkdirSync(".auth", { recursive: true });

  await page.goto("/login");

  // Wait until we land on /app (auth guard passed). Any OAuth flow ends here.
  await page.waitForURL(/\/app(\/|$|\?)/, { timeout: 5 * 60_000 });

  // Sanity-check: a chat-screen marker is visible.
  await expect(page.getByText(/Sẵn sàng phân tích|Thao tác nhanh/i).first()).toBeVisible({
    timeout: 30_000,
  });

  await context.storageState({ path: AUTH_FILE });

  if (!existsSync(AUTH_FILE)) throw new Error(`Failed to write ${AUTH_FILE}`);
});
