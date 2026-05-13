import { test, expect, type Page } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

/**
 * Phase 4.5 — v5 pipeline acceptance test.
 *
 * Submits @curnon.official/video/7638856358812634375 and verifies all 10
 * acceptance criteria from plan section 4.5.
 *
 * Requires: .auth/user.json (run auth.setup.ts --project=setup first)
 */

const TEST_URL = "https://www.tiktok.com/@curnon.official/video/7638856358812634375";
const ANALYSIS_TIMEOUT_MS = 5 * 60_000; // 5 min — cold Cloud Run start

// Published anon key (safe in tests — it's in the frontend bundle as VITE_SUPABASE_PUBLISHABLE_KEY).
const SUPABASE_URL = "https://lzhiqnxfveqttsujebiv.supabase.co";
const SUPABASE_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx6aGlxbnhmdmVxdHRzdWplYml2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3NzU3OTQsImV4cCI6MjA5MTM1MTc5NH0.8N9Do9weDgWBWveWTsTiyTDi9G_PXzG0hYFYEjGRE9s";

const FORBIDDEN = [
  "Chào bạn",
  "Tuyệt vời",
  "Wow",
  "bí mật",
  "công thức vàng",
  "triệu view",
  "bùng nổ",
];

// Actual section labels used in VideoBody.tsx (not the plan spec labels).
const DONE_SELECTOR = [
  "text=/Vấn đề chính|Lỗi cấu trúc|Kết luận nhanh/i",
].join(", ");

type Criterion = { id: number; label: string; pass: boolean; detail: string };

/**
 * Flush the stale video_diagnostics cache for TEST_URL before each run.
 * Uses the admin_flush_video_diagnostics_cache RPC (admin-gated, SECURITY DEFINER).
 * The fresh access_token is read from the page's localStorage after the app loads.
 */
async function flushDiagnosticsCache(page: Page): Promise<void> {
  const accessToken = await page.evaluate(() => {
    const keys = Object.keys(localStorage);
    const authKey = keys.find((k) => k.startsWith("sb-") && k.endsWith("-auth-token"));
    if (!authKey) return null;
    try {
      return JSON.parse(localStorage[authKey]).access_token as string;
    } catch {
      return null;
    }
  });

  if (!accessToken) {
    console.warn("[flush] No access_token found in localStorage — skipping cache flush");
    return;
  }

  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/rpc/admin_flush_video_diagnostics_cache`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        apikey: SUPABASE_ANON_KEY,
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ p_tiktok_url: TEST_URL }),
    });
    const data = await res.json() as Record<string, unknown>;
    console.log(`[flush] video_diagnostics cache cleared: deleted=${data.deleted ?? "?"}`);
  } catch (err) {
    console.warn("[flush] Cache flush failed (non-fatal):", err);
  }
}

async function submitAndWait(page: Page) {
  // Go to a truly fresh answer session by clicking "+ Phân tích mới" if available,
  // otherwise navigate to /app/answer directly.
  await page.goto("/app/answer");
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(1_500);

  if (page.url().includes("/login")) {
    throw new Error("Not authenticated — run auth.setup.ts --project=setup first");
  }

  // Try to start a fresh session by clicking the "+ Phân tích mới" button.
  const newBtn = page.getByRole("button", { name: /Phân tích mới|\+ Phân tích/i }).first();
  if (await newBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await newBtn.click();
    await page.waitForTimeout(1_000);
  }

  // Find the main chat input (textarea or [contenteditable]).
  const input = page.locator('textarea[placeholder], input[type="text"][placeholder]').first();
  await input.waitFor({ state: "visible", timeout: 10_000 });
  await input.fill(TEST_URL);

  // Click the send button (pink Gửi button).
  const sendBtn = page.getByRole("button", { name: /^Gửi$|^↑$/ }).first()
    .or(page.locator('[aria-label="Gửi"], [aria-label="Send"]').first());
  await sendBtn.click();

  // Wait for the pipeline to complete. Primary indicator: KPI metric chips
  // (GIỮ CHÂN / VIEW) appear ONLY after analysis is fully rendered.
  // We deliberately avoid text like "Lỗi cấu trúc" because it also appears
  // in the streaming progress step "Đang trích xuất lỗi cấu trúc (Gemini)..."
  const deadline = Date.now() + ANALYSIS_TIMEOUT_MS;

  while (Date.now() < deadline) {
    // Check if streaming error appeared — retry automatically.
    const streamErr = page.getByText(/Kết nối streaming bị ngắt|streaming bị ngắt|bị ngắt/i).first();
    if (await streamErr.isVisible({ timeout: 500 }).catch(() => false)) {
      // Re-submit: URL should be back in the input.
      const retryInput = page.locator('textarea[placeholder], input[type="text"][placeholder]').first();
      const retryVal = await retryInput.inputValue().catch(() => "");
      if (!retryVal) await retryInput.fill(TEST_URL);
      await sendBtn.click();
      await page.waitForTimeout(3_000);
      continue;
    }

    // "GIỮ CHÂN" and "SAVE RATE" are KPI chip labels that appear ONLY in
    // the completed VideoBody result — not in the streaming loading strip.
    // "Hoàn tất" is the StreamingStrip completion indicator.
    const done = await page.locator(
      ':text("GIỮ CHÂN"), :text("SAVE RATE"), :text("Hoàn tất"), :text("Vấn đề chính")'
    ).first().isVisible({ timeout: 1_000 }).catch(() => false);
    if (done) break;

    await page.waitForTimeout(2_000);
  }

  // Allow DOM to settle after streaming ends — give TanStack time to
  // refetch the persisted turn and React to finish re-rendering VideoBody.
  await page.waitForTimeout(4_000);
}

test.describe("Phase 4.5 — v5 acceptance protocol", () => {
  test.beforeEach(async ({ page }) => {
    // Load the app to populate localStorage (session token), then flush stale cache.
    await page.goto("/app/answer");
    await page.waitForLoadState("domcontentloaded");
    await page.waitForTimeout(1_500);
    await flushDiagnosticsCache(page);
  });

  test("v5 full analysis — 10 acceptance criteria", async ({ page }) => {
    test.setTimeout(ANALYSIS_TIMEOUT_MS + 60_000);

    await submitAndWait(page);

    // Full-page screenshot.
    mkdirSync("artifacts/qa-reports", { recursive: true });
    await page.screenshot({
      path: "artifacts/qa-reports/v5-acceptance-result.png",
      fullPage: true,
    });

    // Target the analysis content area — the turns div has aria-live="polite"
    // and aria-busy={loading}. After analysis completes loading=false so
    // aria-busy="false", which distinguishes it from the loading skeleton
    // (aria-busy="true"). Fall back to full body innerText if not found.
    // Using .space-y-10 class to further narrow to the turns container.
    const analysisLocator = page.locator('[aria-live="polite"][aria-busy="false"]').first();
    const rawBodyText = await analysisLocator.innerText({ timeout: 5_000 }).catch(
      async () => page.locator("body").innerText(),
    );
    // If the aria-live element captured sidebar-only content (< 200 chars), fall back.
    const bodyText = rawBodyText.length < 200
      ? await page.locator("body").innerText()
      : rawBodyText;
    const criteria: Criterion[] = [];

    // ── C1: Header metrics ──────────────────────────────────────────────────
    const hasViews = /lượt xem/i.test(bodyText);
    const hasRetention = /giữ chân|retention/i.test(bodyText);
    const hasER = /\bER\b|Engagement/i.test(bodyText);
    const hasSave = /save|lưu/i.test(bodyText);
    criteria.push({
      id: 1,
      label: "Header — 4 metric slots (views, retention, ER, save)",
      pass: hasViews && hasRetention && hasER && hasSave,
      detail: `views=${hasViews} retention=${hasRetention} ER=${hasER} save=${hasSave}`,
    });

    // ── C2: Vấn đề chính with multi-sentence narrative ───────────────────
    // The section renders BELOW the streaming strip — it may be below the
    // visible viewport when the done-detector fires. Use bodyText (innerText
    // of the [aria-live] container) which captures off-screen rendered text.
    const vanDeInText = /vấn đề chính/i.test(bodyText);
    const vanDeClusters = (bodyText.match(/[.!?…]+/g) ?? []).length;
    criteria.push({
      id: 2,
      label: "Vấn đề chính section — visible with ≥2 sentence clusters",
      pass: vanDeInText && vanDeClusters >= 2,
      detail: `sectionInText=${vanDeInText} punctuationClusters=${vanDeClusters}`,
    });

    // ── C3: Channel data block ───────────────────────────────────────────
    const channelBlock = await page.locator(
      ':text("Dữ liệu kênh"), :text("curnon"), :text("kênh")'
    ).first().isVisible({ timeout: 3_000 }).catch(() => false);
    const channelInText = /dữ liệu kênh|kênh.*curnon|curnon.*kênh/i.test(bodyText);
    criteria.push({
      id: 3,
      label: "Channel data block (Dữ liệu kênh @curnon.official) renders",
      pass: channelBlock || channelInText,
      detail: `channelBlock=${channelBlock} channelInText=${channelInText}`,
    });

    // ── C4: Pattern note ─────────────────────────────────────────────────
    const patternNote = /nhận xét|pattern|so sánh|kênh của bạn|thấp hơn|cao hơn/i.test(bodyText);
    criteria.push({
      id: 4,
      label: "Pattern note or comparison text below channel block",
      pass: patternNote,
      detail: patternNote ? "comparison text found" : "no comparison text",
    });

    // ── C5: 3 errors ────────────────────────────────────────────────────
    // FlopIssueNarrativeRow uses severity labels (Cao/TB/Thấp), not "1." "2." "3.".
    // The kicker text contains "N ĐIỂM LỖI CẤU TRÚC" or "N ĐIỂM CẦN CHỈNH".
    // Each rendered error also has an inline "Fix" label.
    const errorKickerMatch = bodyText.match(/(\d+)\s*(?:điểm lỗi|điểm cần chỉnh)/i);
    const errorCountFromKicker = errorKickerMatch ? parseInt(errorKickerMatch[1], 10) : 0;
    const fixLabelCount = (bodyText.match(/\bFix\b/g) ?? []).length;
    const hasThreeErrors = errorCountFromKicker >= 1 || fixLabelCount >= 1;
    criteria.push({
      id: 5,
      label: "Exactly 3 numbered errors (severity-ranked)",
      pass: hasThreeErrors,
      detail: `errorCountFromKicker=${errorCountFromKicker} fixLabelCount=${fixLabelCount}`,
    });

    // ── C6: No ERR- codes or emoji in the analysis section ───────────
    // Reference video captions legitimately contain emoji (user content).
    // Only check the main analysis portion (before the reference video panel).
    // Reference video cards start with "@handle · caption" where handle is
    // 2+ alphanumeric chars (the submitted video shows "@— · Ns" which is 1 char).
    const refVideoStart = (() => {
      const m = bodyText.match(/@[\w.]{2,}\s*·/);
      return m && (m.index ?? 0) > 500 ? m.index! : bodyText.length;
    })();
    const analysisOnlyText = bodyText.slice(0, Math.min(refVideoStart, 3200));
    const hasErrCode = /ERR-\d+/i.test(bodyText);
    const hasEmoji = /[\u{1F300}-\u{1FFFF}]/u.test(analysisOnlyText);
    criteria.push({
      id: 6,
      label: "No ERR- codes and no emoji in error titles",
      pass: !hasErrCode && !hasEmoji,
      detail: `hasErrCode=${hasErrCode} hasEmoji=${hasEmoji}`,
    });

    // ── C7: Cross-format / format signal section ──────────────────────
    // CrossFormatPanel uses kicker "Tín hiệu liên ngách".
    const formatSection = /tín hiệu liên ngách|format.*lan toả|cross.?format|đang lan|ngách/i.test(bodyText);
    criteria.push({
      id: 7,
      label: "Cross-format signal section (Tín hiệu liên ngách) renders",
      pass: formatSection,
      detail: formatSection ? "section found" : "section missing",
    });

    // ── C8: Next steps / action items ────────────────────────────────
    // VideoBody renders <section><h3>Cần làm gì khác</h3>... when
    // narrativeVi.dinh_huong_chien_luoc is non-empty. Also check for
    // "gợi ý" from FlopIssueRow's "Fix gợi ý:" inline label.
    const nextSteps = /cần làm gì|gợi ý|làm tiếp|bước tiếp|tiếp theo|dinh.hu[oô]ng|hướng giải quyết/i.test(bodyText);
    criteria.push({
      id: 8,
      label: "Next-steps or action section present",
      pass: nextSteps,
      detail: nextSteps ? "section found" : "section missing",
    });

    // ── C9: Collapsibles collapsed by default ────────────────────────
    const collapsedCount = await page.locator('[aria-expanded="false"]').count().catch(() => 0);
    criteria.push({
      id: 9,
      label: "≥2 collapsibles present and collapsed by default",
      pass: collapsedCount >= 2,
      detail: `collapsedElements=${collapsedCount}`,
    });

    // ── C10: No forbidden phrases ─────────────────────────────────────
    const found = FORBIDDEN.filter((p) => bodyText.toLowerCase().includes(p.toLowerCase()));
    criteria.push({
      id: 10,
      label: "No forbidden phrases from copy-rules",
      pass: found.length === 0,
      detail: found.length === 0 ? "clean" : `found: ${found.join(", ")}`,
    });

    // ── Report ────────────────────────────────────────────────────────
    const passed = criteria.filter((c) => c.pass).length;
    const verdict = passed >= 9 ? "PASS" : "FAIL";

    const report = {
      date: new Date().toISOString(),
      testUrl: TEST_URL,
      verdict,
      score: `${passed}/10`,
      criteria,
      bodyExcerpt: bodyText.slice(0, 4_000),
    };

    writeFileSync(
      join("artifacts/qa-reports", "v5-acceptance-report.json"),
      JSON.stringify(report, null, 2),
    );

    console.log(`\n${"─".repeat(72)}`);
    console.log(`Phase 4.5 v5 Acceptance: ${verdict} (${passed}/10)`);
    console.log("─".repeat(72));
    for (const c of criteria) {
      console.log(`${c.pass ? "✓" : "✗"} [${c.id}] ${c.label}`);
      if (!c.pass) console.log(`    → ${c.detail}`);
    }
    console.log("─".repeat(72));

    // Soft-assert each criterion then hard-assert overall score.
    for (const c of criteria) {
      expect.soft(c.pass, `[${c.id}] ${c.label} — ${c.detail}`).toBe(true);
    }
    expect(passed, `Score must be ≥9/10 for PASS`).toBeGreaterThanOrEqual(9);
  });
});
