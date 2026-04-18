import { test, expect, Page } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

/**
 * Live-site audit for the 6 quick-action cards on the empty chat screen.
 *
 * Captures per-stage pipeline timings so you can see where latency/errors
 * accumulate:
 *
 *   card_click → modal_open → submit_click → request_sent
 *     → ttfb (server accepted)
 *     → ttft (first SSE frame)
 *     → stream_done (done frame or error)
 *     → dom_settled (assistant bubble visible)
 *
 * Instruments via page.addInitScript: wraps window.fetch so the test sees
 * every POST to /api/chat or Cloud Run /stream and every SSE frame, with
 * timestamps and the raw delta/done/error payload. No source changes needed.
 *
 * Output:
 *   - playwright-report/index.html (traces + videos)
 *   - artifacts/qa-reports/quick-actions-live-YYYY-MM-DD.json (per-card audit)
 */

// ── TEST INPUTS — edit before running ───────────────────────────────────────
const INPUTS = {
  soiVideoUrl: "https://www.tiktok.com/@theretiredwife/video/7445420553103428910",
  soiKenhHandle: "@phuong.nga.beauty",
  xuHuongNiche: "skincare",
  kichBanTopic: "review son tint mới ra",
  timKolProduct: "mỹ phẩm Hàn Quốc cho da dầu",
  tuVanNiche: "review đồ skincare",
};

type ActionKey = "soi-video" | "soi-kenh" | "xu-huong" | "kich-ban" | "tim-kol" | "tu-van";

const ACTIONS: Array<{
  key: ActionKey;
  cardTitle: string;
  fillValue: string;
  expectedIntent: string;
  expectedFree: boolean;
  contentChecks: RegExp[];
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
    // KNOWN GAP: when user types @handle (not URL), detectIntent routes to
    // own_channel instead of competitor_profile because "soi kênh" matches
    // the ownChannelHandle regex (ChatScreen.tsx:76). Recorded, not failed.
    expectedIntent: "competitor_profile",
    expectedFree: false,
    contentChecks: [/(công thức|pattern|format)/i, /hook/i],
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
    // KNOWN GAP: card claims free (EmptyStates.tsx:63) but creator_search is
    // paid per detectIntent. Credit delta will reveal which side is authoritative.
    expectedIntent: "creator_search",
    expectedFree: true,
    contentChecks: [/(creator|kol|koc)/i, /(@[a-z0-9._]+|follower)/i],
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

// ── Window-side SSE interceptor ─────────────────────────────────────────────
// Injected BEFORE any page script runs. Wraps fetch so every POST to the chat
// endpoints is tee'd — we read the SSE stream character-by-character and
// append parsed frames (with timestamps) to window.__GV_EVENTS.

const INTERCEPTOR = `
(() => {
  if (window.__GV_INSTALLED) return;
  window.__GV_INSTALLED = true;
  window.__GV_EVENTS = [];
  const push = (e) => window.__GV_EVENTS.push({ t: performance.now(), ...e });
  const origFetch = window.fetch;
  window.fetch = async (input, init) => {
    const url = typeof input === "string" ? input : (input && input.url) || "";
    const isChat = /\\/api\\/chat|\\/stream(\\?|$)/.test(url);
    if (!isChat) return origFetch(input, init);
    push({ type: "request_sent", url, body: init && typeof init.body === "string" ? init.body : null });
    const resp = await origFetch(input, init);
    push({ type: "response_headers", url, status: resp.status, ok: resp.ok });
    if (!resp.body) {
      push({ type: "no_body", url });
      return resp;
    }
    const [a, b] = resp.body.tee();
    (async () => {
      const reader = a.getReader();
      const dec = new TextDecoder();
      let buf = "";
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          let idx;
          while ((idx = buf.indexOf("\\n\\n")) !== -1) {
            const frame = buf.slice(0, idx);
            buf = buf.slice(idx + 2);
            const line = frame.split("\\n").find((l) => l.startsWith("data:"));
            if (!line) continue;
            const payload = line.slice(5).trim();
            try {
              const obj = JSON.parse(payload);
              push({ type: "frame", url, payload: obj });
            } catch {
              push({ type: "frame_raw", url, payload });
            }
          }
        }
        push({ type: "stream_end", url });
      } catch (err) {
        push({ type: "stream_error", url, message: String(err) });
      }
    })();
    return new Response(b, { status: resp.status, statusText: resp.statusText, headers: resp.headers });
  };
})();
`;

type Event = {
  t: number;
  type: string;
  url?: string;
  status?: number;
  ok?: boolean;
  body?: string | null;
  payload?: unknown;
  message?: string;
};

type AuditRow = {
  key: ActionKey;
  cardTitle: string;
  input: string;
  ok: boolean;
  errors: string[];
  // Pipeline markers (ms from test start)
  t: {
    card_click?: number;
    modal_open?: number;
    submit_click?: number;
    request_sent?: number;
    response_headers?: number;
    first_frame?: number;
    done_frame?: number;
    stream_end?: number;
    dom_settled?: number;
  };
  // Stage latencies (ms)
  stages: {
    click_to_modal?: number;
    modal_to_submit?: number;
    submit_to_request?: number;
    request_to_headers?: number; // TTFB
    headers_to_first_frame?: number; // TTFT
    first_to_done?: number; // stream duration
    done_to_dom?: number;
    total?: number;
  };
  // Intent & billing
  observedIntent: string | null;
  observedIsFree: boolean | null;
  responseStatus: number | null;
  creditsBefore: number | null;
  creditsAfter: number | null;
  creditDelta: number | null;
  // Content
  frameCount: number;
  errorFrames: Array<{ error: string; at: number }>;
  responseText: string;
  responseExcerpt: string;
  missingChecks: string[];
  // Raw for manual inspection
  requestBody: unknown;
};

const RESULTS: AuditRow[] = [];

test.beforeEach(async ({ page }) => {
  await page.addInitScript(INTERCEPTOR);
});

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
        summary: summarize(RESULTS),
        results: RESULTS,
      },
      null,
      2,
    ),
  );
  console.log(`\n✓ Audit report: ${outFile}`);
  console.log(formatSummary(RESULTS));
});

function summarize(rows: AuditRow[]) {
  const pass = rows.filter((r) => r.ok).length;
  const stageAvg = (k: keyof AuditRow["stages"]) => {
    const vals = rows.map((r) => r.stages[k]).filter((v): v is number => typeof v === "number");
    if (!vals.length) return null;
    return Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
  };
  return {
    pass,
    total: rows.length,
    avg: {
      ttfb_ms: stageAvg("request_to_headers"),
      ttft_ms: stageAvg("headers_to_first_frame"),
      stream_ms: stageAvg("first_to_done"),
      total_ms: stageAvg("total"),
    },
  };
}

function formatSummary(rows: AuditRow[]) {
  const lines = ["", "PIPELINE STAGE LATENCIES (ms)", "".padEnd(88, "─")];
  lines.push(
    ["card".padEnd(22), "TTFB", "TTFT", "stream", "total", "intent", "credit", "status"]
      .map((s) => s.toString().padEnd(10))
      .join(""),
  );
  for (const r of rows) {
    lines.push(
      [
        r.cardTitle.padEnd(22),
        String(r.stages.request_to_headers ?? "-"),
        String(r.stages.headers_to_first_frame ?? "-"),
        String(r.stages.first_to_done ?? "-"),
        String(r.stages.total ?? "-"),
        String(r.observedIntent ?? "-"),
        String(r.creditDelta ?? "-"),
        r.ok ? "ok" : r.errors[0] ?? "fail",
      ]
        .map((s) => s.toString().padEnd(10))
        .join(""),
    );
  }
  return lines.join("\n");
}

async function readCredits(page: Page): Promise<number | null> {
  // CreditBar renders: <span class="font-mono ... font-extrabold">{N}</span><span>/ {cap}</span>
  // The "Phân tích" label sits just above. Scope via that label for robustness.
  try {
    const container = page.locator("div", { hasText: /^Phân tích$/ }).locator("..").first();
    const numSpan = container.locator("span.font-mono.font-extrabold").first();
    const txt = await numSpan.innerText({ timeout: 2_000 });
    const n = Number(txt.trim());
    return Number.isFinite(n) ? n : null;
  } catch {
    // Fallback: first "N / M" pattern in sidebar.
    try {
      const any = await page.getByText(/^\s*\d+\s*$/).first().innerText({ timeout: 1_000 });
      const n = Number(any.trim());
      return Number.isFinite(n) ? n : null;
    } catch {
      return null;
    }
  }
}

async function runAction(page: Page, spec: (typeof ACTIONS)[number]) {
  const row: AuditRow = {
    key: spec.key,
    cardTitle: spec.cardTitle,
    input: spec.fillValue,
    ok: false,
    errors: [],
    t: {},
    stages: {},
    observedIntent: null,
    observedIsFree: null,
    responseStatus: null,
    creditsBefore: null,
    creditsAfter: null,
    creditDelta: null,
    frameCount: 0,
    errorFrames: [],
    responseText: "",
    responseExcerpt: "",
    missingChecks: [],
    requestBody: null,
  };

  await page.goto("/app");
  await expect(page.getByText(/Thao tác nhanh/i).first()).toBeVisible();

  // ── Playwright-level network capture (authoritative) ────────────────────
  // Broader URL match than the fetch wrapper — catches anything that looks
  // like a chat POST regardless of host/path.
  const isChatUrl = (u: string) =>
    /\/api\/chat(\?|$)/.test(u) || /\/stream(\?|$)/.test(u) || /\/chat(\?|$)/.test(u);
  const netRequests: Array<{ t: number; url: string; body: string | null }> = [];
  const netResponses: Array<{ t: number; url: string; status: number }> = [];
  const allPosts: string[] = []; // diagnostic — every POST URL seen
  const onReq = (req: import("@playwright/test").Request) => {
    if (req.method() !== "POST") return;
    allPosts.push(req.url());
    if (!isChatUrl(req.url())) return;
    netRequests.push({ t: performance.now(), url: req.url(), body: req.postData() });
  };
  const onResp = (resp: import("@playwright/test").Response) => {
    if (!isChatUrl(resp.url())) return;
    netResponses.push({ t: performance.now(), url: resp.url(), status: resp.status() });
  };
  page.on("request", onReq);
  page.on("response", onResp);

  // Reset event log for this action (fetch-wrapper SSE frames, best-effort).
  await page.evaluate(() => {
    (window as unknown as { __GV_EVENTS: Event[] }).__GV_EVENTS = [];
  });

  row.creditsBefore = await readCredits(page);

  const cardButton = page
    .getByRole("button", { name: new RegExp(`^\\s*${spec.cardTitle}`, "i") })
    .first();
  await expect(cardButton).toBeVisible();

  const t0 = Date.now();
  await cardButton.click();
  row.t.card_click = Date.now() - t0;

  const heading = page.getByRole("heading", { name: spec.cardTitle });
  await expect(heading).toBeVisible();
  row.t.modal_open = Date.now() - t0;

  await page.locator('input[type="text"], textarea').first().fill(spec.fillValue);

  const submit = page.getByRole("button", { name: /^Tiếp tục$/i });
  await submit.click();
  row.t.submit_click = Date.now() - t0;

  // Wait for stream to end. Two signals, whichever fires first:
  //   (a) fetch-wrapper done/stream_end frame (best)
  //   (b) "Đang suy nghĩ…" / "Đang phân tích…" / "Đang tải video…" status
  //       text appears then disappears (DOM-level fallback)
  // Hard timeout 90s.
  const deadline = Date.now() + 90_000;
  const STATUS_RE = /Đang (suy nghĩ|phân tích|tải video|tạo)/i;
  let events: Event[] = [];
  let sawStatus = false;
  while (Date.now() < deadline) {
    events = await page.evaluate(
      () => (window as unknown as { __GV_EVENTS: Event[] }).__GV_EVENTS.slice(),
    );
    const wrapperDone = events.find(
      (e) =>
        e.type === "stream_end" ||
        e.type === "stream_error" ||
        (e.type === "frame" &&
          typeof e.payload === "object" &&
          e.payload !== null &&
          (e.payload as { done?: boolean }).done === true),
    );
    if (wrapperDone) break;
    const statusVisible = await page.getByText(STATUS_RE).first().isVisible().catch(() => false);
    if (statusVisible) sawStatus = true;
    // If we saw the streaming indicator at some point and it's now gone, stream is done.
    if (sawStatus && !statusVisible && netResponses.length > 0) break;
    await page.waitForTimeout(250);
  }
  const streamWallEnd = Date.now();

  // Interpret events from both sources. Playwright network layer is primary;
  // fetch wrapper provides SSE frame-level granularity when it fires.
  const firstBy = (pred: (e: Event) => boolean) => events.find(pred);
  const requestSent = firstBy((e) => e.type === "request_sent");
  const headers = firstBy((e) => e.type === "response_headers");
  const firstFrame = firstBy((e) => e.type === "frame");
  const doneFrame = firstBy(
    (e) =>
      e.type === "frame" &&
      typeof e.payload === "object" &&
      e.payload !== null &&
      (e.payload as { done?: boolean }).done === true,
  );
  const streamEnd = firstBy((e) => e.type === "stream_end" || e.type === "stream_error");

  // Primary source: Playwright network capture.
  const netReq = netRequests[0];
  const netResp = netResponses[0];

  if (netReq) {
    row.t.request_sent = Math.round(netReq.t);
    try {
      const parsed = netReq.body ? JSON.parse(netReq.body) : null;
      row.requestBody = parsed;
      row.observedIntent = (parsed as { intent_type?: string } | null)?.intent_type ?? null;
    } catch {
      row.requestBody = netReq.body;
    }
  } else if (requestSent) {
    row.t.request_sent = Math.round(requestSent.t);
    try {
      const parsed = requestSent.body ? JSON.parse(requestSent.body) : null;
      row.requestBody = parsed;
      row.observedIntent = (parsed as { intent_type?: string } | null)?.intent_type ?? null;
    } catch {
      row.requestBody = requestSent.body;
    }
  } else {
    row.errors.push(
      `no chat request seen. ${allPosts.length} POST(s) observed: ${allPosts.slice(0, 5).join(", ") || "none"}`,
    );
  }
  if (netResp) {
    row.t.response_headers = Math.round(netResp.t);
    row.responseStatus = netResp.status;
    if (netResp.status === 402) row.errors.push("402 insufficient_credits");
    else if (netResp.status >= 400) row.errors.push(`HTTP ${netResp.status}`);
  } else if (headers) {
    row.t.response_headers = Math.round(headers.t);
    row.responseStatus = headers.status ?? null;
    if (headers.status === 402) row.errors.push("402 insufficient_credits");
    else if (!headers.ok) row.errors.push(`HTTP ${headers.status}`);
  }
  if (firstFrame) row.t.first_frame = Math.round(firstFrame.t);
  if (doneFrame) row.t.done_frame = Math.round(doneFrame.t);
  if (streamEnd) row.t.stream_end = Math.round(streamEnd.t);

  row.frameCount = events.filter((e) => e.type === "frame").length;
  row.errorFrames = events
    .filter(
      (e) =>
        e.type === "frame" &&
        typeof e.payload === "object" &&
        e.payload !== null &&
        (e.payload as { error?: string }).error,
    )
    .map((e) => ({
      error: (e.payload as { error: string }).error,
      at: Math.round(e.t),
    }));

  // Compute stage latencies (relative within request timeline).
  const T = row.t;
  const diff = (a?: number, b?: number) =>
    typeof a === "number" && typeof b === "number" ? Math.round(b - a) : undefined;
  row.stages.click_to_modal = diff(T.card_click, T.modal_open);
  row.stages.modal_to_submit = diff(T.modal_open, T.submit_click);
  row.stages.submit_to_request = diff(T.submit_click, T.request_sent);
  row.stages.request_to_headers = diff(T.request_sent, T.response_headers);
  row.stages.headers_to_first_frame = diff(T.response_headers, T.first_frame);
  row.stages.first_to_done = diff(T.first_frame, T.done_frame ?? T.stream_end);

  // Wait for the assistant bubble to settle in the DOM.
  const bodyLocator = page.locator("main, body").first();
  let lastLen = 0;
  let stableFor = 0;
  const domDeadline = Date.now() + 10_000;
  while (Date.now() < domDeadline) {
    const txt = await bodyLocator.innerText();
    if (txt.length > lastLen) {
      lastLen = txt.length;
      stableFor = 0;
    } else {
      stableFor += 300;
      if (stableFor >= 1_500) break;
    }
    await page.waitForTimeout(300);
  }
  row.t.dom_settled = Date.now() - t0 + streamWallEnd - Date.now(); // approx
  row.stages.done_to_dom = diff(T.stream_end ?? T.done_frame, row.t.dom_settled);
  row.stages.total = diff(T.card_click, row.t.dom_settled);

  // Extract assistant response.
  const full = await bodyLocator.innerText();
  const idx = full.indexOf(spec.fillValue);
  row.responseText = idx >= 0 ? full.slice(idx + spec.fillValue.length).trim() : full.slice(-4_000);
  row.responseExcerpt = row.responseText.slice(0, 1_200);

  for (const re of spec.contentChecks) {
    if (!re.test(row.responseText)) row.missingChecks.push(re.source);
  }

  row.creditsAfter = await readCredits(page);
  if (row.creditsBefore != null && row.creditsAfter != null) {
    row.creditDelta = row.creditsAfter - row.creditsBefore;
  }

  if (row.observedIntent && row.observedIntent !== spec.expectedIntent) {
    row.errors.push(`intent mismatch: expected ${spec.expectedIntent}, got ${row.observedIntent}`);
  }
  if (row.creditDelta != null) {
    if (spec.expectedFree && row.creditDelta < 0) {
      row.errors.push(`card claims free but credit decremented by ${-row.creditDelta}`);
    }
    if (!spec.expectedFree && row.creditDelta === 0 && row.responseStatus !== 402) {
      row.errors.push("card claims paid but no credit decremented");
    }
  }

  row.ok =
    row.errors.length === 0 &&
    row.responseText.length > 40 &&
    row.missingChecks.length === 0 &&
    row.errorFrames.length === 0;

  page.off("request", onReq);
  page.off("response", onResp);

  RESULTS.push(row);
}

for (const spec of ACTIONS) {
  test(`quick-action: ${spec.cardTitle}`, async ({ page }) => {
    await runAction(page, spec);
    const row = RESULTS[RESULTS.length - 1];
    expect.soft(row.errors, `errors for ${spec.key}`).toEqual([]);
    expect.soft(row.missingChecks, `missing content for ${spec.key}`).toEqual([]);
    expect.soft(row.errorFrames, `SSE error frames for ${spec.key}`).toEqual([]);
    expect(row.responseText.length, `empty response for ${spec.key}`).toBeGreaterThan(40);
  });
}
