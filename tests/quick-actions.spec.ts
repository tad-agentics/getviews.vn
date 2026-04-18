import { test, expect, Page } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

/**
 * Live-site audit for the 6 quick-action cards on the empty chat screen.
 *
 * For each card the test:
 *   1. Navigates to /app
 *   2. Clicks the card by text
 *   3. Fills the modal field(s)
 *   4. Clicks "Tiếp tục"
 *   5. Waits for the SSE stream to land an assistant message
 *   6. Captures: request body, response text, credits before/after, latency
 *   7. Runs per-intent content assertions (soft — flagged, not failed)
 *
 * Output: artifacts/qa-reports/quick-actions-live-{date}.json
 *         + the default Playwright HTML report.
 *
 * EDIT INPUTS at the top of this file before running.
 */

// ── TEST INPUTS — edit these ────────────────────────────────────────────────
const INPUTS = {
  soiVideoUrl: "https://www.tiktok.com/@theretiredwife/video/7445420553103428910",
  soiKenhHandle: "@phuong.nga.beauty",
  xuHuongNiche: "skincare",
  kichBanTopic: "review son tint mới ra",
  timKolProduct: "mỹ phẩm Hàn Quốc cho da dầu",
  tuVanNiche: "review đồ skincare",
};

// ── 6 quick actions, in display order ───────────────────────────────────────
type ActionKey = "soi-video" | "soi-kenh" | "xu-huong" | "kich-ban" | "tim-kol" | "tu-van";

const ACTIONS: Array<{
  key: ActionKey;
  cardTitle: string;
  fillValue: string;
  expectedIntent: string;          // what detectIntent() should classify to
  expectedFree: boolean;           // what the card CLAIMS
  contentChecks: RegExp[];         // phrases the response should contain
}> = [
  {
    key: "soi-video",
    cardTitle: "Soi Video",
    fillValue: INPUTS.soiVideoUrl,
    expectedIntent: "video_diagnosis",
    expectedFree: false,
    contentChecks: [/hook/i, /(mở đầu|3 giây|giây đầu)/i, /(cải thiện|điểm yếu|điểm mạnh)/i],
  },
  {
    key: "soi-kenh",
    cardTitle: "Soi Kênh Đối Thủ",
    fillValue: INPUTS.soiKenhHandle,
    // NOTE: when user types @handle (not URL), detectIntent routes to own_channel
    // because the "soi kênh" keyword hits the ownChannelHandle branch. Flag this.
    expectedIntent: "competitor_profile",
    expectedFree: false,
    contentChecks: [/(công thức|công-thức|pattern|format)/i, /hook/i],
  },
  {
    key: "xu-huong",
    cardTitle: "Xu Hướng Tuần Này",
    fillValue: INPUTS.xuHuongNiche,
    expectedIntent: "trend_spike",
    expectedFree: true,
    contentChecks: [/(xu hướng|trend|đang hot|viral)/i, /hook/i],
  },
  {
    key: "kich-ban",
    cardTitle: "Lên Kịch Bản Quay",
    fillValue: INPUTS.kichBanTopic,
    expectedIntent: "shot_list",
    expectedFree: false,
    contentChecks: [/(cảnh|shot)/i, /hook/i, /cta/i],
  },
  {
    key: "tim-kol",
    cardTitle: "Tìm KOL / Creator",
    fillValue: INPUTS.timKolProduct,
    // NOTE: card claims free (isFree: true) but creator_search intent is paid in detectIntent.
    expectedIntent: "creator_search",
    expectedFree: true,
    contentChecks: [/(creator|kol|koc)/i, /(@[a-z0-9._]+|followers|follower)/i],
  },
  {
    key: "tu-van",
    cardTitle: "Tư Vấn Content",
    fillValue: INPUTS.tuVanNiche,
    expectedIntent: "content_directions",
    expectedFree: false,
    contentChecks: [/(format|hook)/i, /(nội dung|content)/i],
  },
];

type AuditRow = {
  key: ActionKey;
  cardTitle: string;
  input: string;
  ok: boolean;
  errors: string[];
  observedIntent: string | null;
  observedIsFree: boolean | null;
  creditsBefore: number | null;
  creditsAfter: number | null;
  creditDelta: number | null;
  latencyMs: number | null;
  responseLength: number;
  responseExcerpt: string;
  missingChecks: string[];
  requestUrl: string | null;
  requestBody: unknown;
};

const RESULTS: AuditRow[] = [];

test.afterAll(async () => {
  const date = new Date().toISOString().slice(0, 10);
  const outDir = "artifacts/qa-reports";
  mkdirSync(outDir, { recursive: true });
  const outFile = join(outDir, `quick-actions-live-${date}.json`);
  writeFileSync(
    outFile,
    JSON.stringify(
      {
        date: new Date().toISOString(),
        baseURL: process.env.GV_BASE_URL ?? "https://getviews.vn",
        results: RESULTS,
      },
      null,
      2,
    ),
  );
  console.log(`\n✓ Audit report: ${outFile}`);
});

async function readCredits(page: Page): Promise<number | null> {
  // CreditBar renders the deep credit count. We look for a number in a known
  // container. Fallback: any "x credits/credit" text in the header.
  const candidates = page.locator('[data-testid="credit-bar"], header, nav').locator("text=/\\b\\d+\\s*(deep|credit|video|phân tích)?/i");
  try {
    const txt = (await candidates.first().innerText({ timeout: 2_000 })).trim();
    const m = txt.match(/\b(\d+)\b/);
    return m ? Number(m[1]) : null;
  } catch {
    return null;
  }
}

async function runAction(page: Page, spec: (typeof ACTIONS)[number]) {
  const row: AuditRow = {
    key: spec.key,
    cardTitle: spec.cardTitle,
    input: spec.fillValue,
    ok: false,
    errors: [],
    observedIntent: null,
    observedIsFree: null,
    creditsBefore: null,
    creditsAfter: null,
    creditDelta: null,
    latencyMs: null,
    responseLength: 0,
    responseExcerpt: "",
    missingChecks: [],
    requestUrl: null,
    requestBody: null,
  };

  await page.goto("/app");
  await expect(page.getByText(/Thao tác nhanh/i).first()).toBeVisible();

  row.creditsBefore = await readCredits(page);

  // Intercept the chat POST to record intent + body.
  const requestPromise = page.waitForRequest(
    (req) => /\/api\/chat|\/stream/.test(req.url()) && req.method() === "POST",
    { timeout: 30_000 },
  );

  await page.getByRole("button", { name: new RegExp(`^${spec.cardTitle}$`, "i") }).click();
  await expect(page.getByRole("heading", { name: spec.cardTitle })).toBeVisible();

  // First visible input/textarea inside the modal.
  const field = page.locator('input[type="text"], textarea').first();
  await field.fill(spec.fillValue);

  const t0 = Date.now();
  await page.getByRole("button", { name: /Tiếp tục/i }).click();

  let req;
  try {
    req = await requestPromise;
    row.requestUrl = req.url();
    try {
      row.requestBody = req.postDataJSON();
      const body = row.requestBody as { intent_type?: string } | null;
      row.observedIntent = body?.intent_type ?? null;
    } catch {
      row.requestBody = req.postData();
    }
  } catch (e) {
    row.errors.push(`no chat request observed: ${(e as Error).message}`);
  }

  // Wait for assistant message to appear. The chat renders assistant turns
  // somewhere in the message list; we look for new content after submitting.
  // Heuristic: after the send, the send button re-enables and response text
  // appears. Wait up to 90s for streaming to finish.
  const deadline = Date.now() + 90_000;
  let lastLen = 0;
  let stableFor = 0;
  while (Date.now() < deadline) {
    const bodyText = await page.locator("main, [role='main'], body").first().innerText();
    if (bodyText.length > lastLen) {
      lastLen = bodyText.length;
      stableFor = 0;
    } else {
      stableFor += 500;
    }
    // Done when text has been stable 2.5s AND the card area is gone (we're in chat view).
    if (stableFor >= 2_500 && !(await page.getByText(/^Thao tác nhanh$/i).isVisible().catch(() => false))) {
      break;
    }
    await page.waitForTimeout(500);
  }
  row.latencyMs = Date.now() - t0;

  // Extract assistant response text — last assistant bubble.
  const assistant = page.locator('[data-role="assistant"], [data-message-role="assistant"]').last();
  let respText = "";
  if (await assistant.count()) {
    respText = await assistant.innerText();
  } else {
    // Fallback: take everything after the user's echoed prompt.
    const all = await page.locator("main, body").first().innerText();
    const idx = all.indexOf(spec.fillValue);
    respText = idx >= 0 ? all.slice(idx + spec.fillValue.length) : all.slice(-4_000);
  }
  row.responseLength = respText.length;
  row.responseExcerpt = respText.slice(0, 1_200);

  // Content assertions (soft).
  for (const re of spec.contentChecks) {
    if (!re.test(respText)) row.missingChecks.push(re.source);
  }

  row.creditsAfter = await readCredits(page);
  if (row.creditsBefore != null && row.creditsAfter != null) {
    row.creditDelta = row.creditsAfter - row.creditsBefore;
  }

  // Intent + free correctness (hard — recorded but won't fail the test).
  if (row.observedIntent && row.observedIntent !== spec.expectedIntent) {
    row.errors.push(`intent mismatch: expected ${spec.expectedIntent}, got ${row.observedIntent}`);
  }
  if (row.creditDelta != null) {
    if (spec.expectedFree && row.creditDelta < 0) {
      row.errors.push(`card claims free but credit decremented by ${-row.creditDelta}`);
    }
    if (!spec.expectedFree && row.creditDelta === 0) {
      row.errors.push(`card claims paid but no credit decremented`);
    }
  }

  row.ok = row.errors.length === 0 && row.responseLength > 40 && row.missingChecks.length === 0;
  RESULTS.push(row);
}

for (const spec of ACTIONS) {
  test(`quick-action: ${spec.cardTitle}`, async ({ page }) => {
    await runAction(page, spec);
    const row = RESULTS[RESULTS.length - 1];
    // Soft expectations — log but don't block the suite.
    expect.soft(row.errors, `errors for ${spec.key}`).toEqual([]);
    expect.soft(row.missingChecks, `missing content for ${spec.key}`).toEqual([]);
    expect(row.responseLength, `empty response for ${spec.key}`).toBeGreaterThan(40);
  });
}
