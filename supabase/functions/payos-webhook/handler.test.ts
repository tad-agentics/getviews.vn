// Tests for the PayOS webhook (audit 2026-06-10 H-2): signature
// verification, idempotency semantics, and the RPC-before-marker ordering
// invariant documented in handler.ts. Run with:
//   deno test supabase/functions/payos-webhook/handler.test.ts
import { handlePayOSWebhook, hmacSha256Hex, timingSafeEqual, type WebhookDeps } from "./handler.ts";

// Local assert — keeps the test hermetic (no jsr/esm fetch at test time).
function assertEquals<T>(actual: T, expected: T): void {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a !== e) throw new Error(`assertEquals failed: ${a} !== ${e}`);
}

const CHECKSUM_KEY = "test-checksum-key";

function paidPayload(orderCode = "12345"): string {
  return JSON.stringify({
    code: "00",
    data: { orderCode, paymentLinkId: "pl-1", desc: "success", amount: 99000 },
  });
}

async function signedRequest(body: string, sigOverride?: string): Promise<Request> {
  const sig = sigOverride ?? (await hmacSha256Hex(CHECKSUM_KEY, body));
  return new Request("https://x.test/payos-webhook", {
    method: "POST",
    headers: { "x-payos-signature": sig },
    body,
  });
}

type Call = { kind: "rpc" | "insert"; name: string; args: Record<string, unknown> };

function makeDeps(opts?: {
  rpcError?: unknown;
  insertErrorCode?: string;
  grantUserId?: string;
}): { deps: WebhookDeps; calls: Call[]; emails: string[] } {
  const calls: Call[] = [];
  const emails: string[] = [];
  const deps: WebhookDeps = {
    checksumKey: CHECKSUM_KEY,
    supabaseUrl: "https://sb.test",
    serviceKey: "service-key",
    fetchFn: ((input: RequestInfo | URL) => {
      emails.push(String(input));
      return Promise.resolve(new Response("{}", { status: 200 }));
    }) as typeof fetch,
    supabase: {
      rpc: (name, args) => {
        calls.push({ kind: "rpc", name, args });
        return Promise.resolve({
          data: opts?.rpcError ? null : { user_id: opts?.grantUserId ?? null },
          error: opts?.rpcError ?? null,
        });
      },
      from: (table) => ({
        insert: (row) => {
          calls.push({ kind: "insert", name: table, args: row });
          return Promise.resolve({
            error: opts?.insertErrorCode ? { code: opts.insertErrorCode } : null,
          });
        },
        select: () => ({
          eq: () => ({
            single: () =>
              Promise.resolve({
                data:
                  table === "profiles"
                    ? { display_name: "A", email: "a@b.vn" }
                    : { tier: "starter", credits_granted: 10, expires_at: null, amount_vnd: 99000 },
              }),
          }),
        }),
      }),
    },
  };
  return { deps, calls, emails };
}

Deno.test("rejects a request with an invalid signature — no RPC runs", async () => {
  const { deps, calls } = makeDeps();
  const req = await signedRequest(paidPayload(), "deadbeef".repeat(8));
  const res = await handlePayOSWebhook(req, deps);
  assertEquals(res.status, 401);
  assertEquals(calls.length, 0);
});

Deno.test("rejects a request with a missing signature", async () => {
  const { deps, calls } = makeDeps();
  const req = new Request("https://x.test/payos-webhook", { method: "POST", body: paidPayload() });
  const res = await handlePayOSWebhook(req, deps);
  assertEquals(res.status, 401);
  assertEquals(calls.length, 0);
});

Deno.test("accepts a correctly signed PAID event and grants once", async () => {
  const { deps, calls } = makeDeps({ grantUserId: "u-1" });
  const res = await handlePayOSWebhook(await signedRequest(paidPayload("777")), deps);
  assertEquals(res.status, 200);
  const rpc = calls.find((c) => c.kind === "rpc")!;
  assertEquals(rpc.name, "decrement_and_grant_credits");
  assertEquals(rpc.args.p_payos_order_code, "777");
  assertEquals(rpc.args.p_event_type, "PAID");
});

Deno.test("signature comparison is case-insensitive on the header", async () => {
  const body = paidPayload();
  const sig = (await hmacSha256Hex(CHECKSUM_KEY, body)).toUpperCase();
  const { deps } = makeDeps();
  const res = await handlePayOSWebhook(await signedRequest(body, sig), deps);
  assertEquals(res.status, 200);
});

Deno.test("INVARIANT: grant RPC runs BEFORE the idempotency marker insert", async () => {
  // Marker-first + RPC crash = PayOS retries short-circuit on the marker
  // and the customer is never granted. This ordering must never flip.
  const { deps, calls } = makeDeps();
  await handlePayOSWebhook(await signedRequest(paidPayload()), deps);
  const rpcIdx = calls.findIndex((c) => c.kind === "rpc");
  const insIdx = calls.findIndex(
    (c) => c.kind === "insert" && c.name === "processed_webhook_events",
  );
  assertEquals(rpcIdx >= 0 && insIdx >= 0, true);
  assertEquals(rpcIdx < insIdx, true);
});

Deno.test("duplicate delivery (marker 23505) returns 200 duplicate, not error", async () => {
  const { deps } = makeDeps({ insertErrorCode: "23505" });
  const res = await handlePayOSWebhook(await signedRequest(paidPayload()), deps);
  assertEquals(res.status, 200);
  const body = await res.json();
  assertEquals(body.duplicate, true);
});

Deno.test("RPC failure returns 500 and does NOT write the marker (retry can re-grant)", async () => {
  const { deps, calls } = makeDeps({ rpcError: new Error("db down") });
  const res = await handlePayOSWebhook(await signedRequest(paidPayload()), deps);
  assertEquals(res.status, 500);
  const markerWritten = calls.some(
    (c) => c.kind === "insert" && c.name === "processed_webhook_events",
  );
  assertEquals(markerWritten, false);
});

Deno.test("missing orderCode is a 400 before any DB work", async () => {
  const { deps, calls } = makeDeps();
  const body = JSON.stringify({ code: "00", data: { desc: "success" } });
  const res = await handlePayOSWebhook(await signedRequest(body), deps);
  assertEquals(res.status, 400);
  assertEquals(calls.length, 0);
});

Deno.test("non-success payload maps to CANCELLED and sends no receipt email", async () => {
  const { deps, calls, emails } = makeDeps({ grantUserId: "u-1" });
  const body = JSON.stringify({ code: "01", data: { orderCode: "9", desc: "cancelled" } });
  const res = await handlePayOSWebhook(await signedRequest(body), deps);
  assertEquals(res.status, 200);
  const rpc = calls.find((c) => c.kind === "rpc")!;
  assertEquals(rpc.args.p_event_type, "CANCELLED");
  assertEquals(emails.length, 0);
});

Deno.test("missing PAYOS_CHECKSUM_KEY is a hard 500", async () => {
  const { deps } = makeDeps();
  deps.checksumKey = undefined;
  const res = await handlePayOSWebhook(await signedRequest(paidPayload()), deps);
  assertEquals(res.status, 500);
});

Deno.test("timingSafeEqual basic properties", () => {
  assertEquals(timingSafeEqual("abc", "abc"), true);
  assertEquals(timingSafeEqual("abc", "abd"), false);
  assertEquals(timingSafeEqual("abc", "ab"), false);
  assertEquals(timingSafeEqual("", ""), true);
});
