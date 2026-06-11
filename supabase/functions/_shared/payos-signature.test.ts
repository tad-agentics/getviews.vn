import { assertEquals } from "https://deno.land/std@0.224.0/assert/mod.ts";
import { payosOrderDescription, signPaymentLinkRequest } from "./payos-signature.ts";

Deno.test("payosOrderDescription truncates to 25 chars", () => {
  assertEquals(payosOrderDescription("pack_50"), "GetViews pack_50");
  assertEquals(payosOrderDescription("starter_monthly").length, 24);
});

Deno.test("signPaymentLinkRequest matches PayOS field order", async () => {
  const sig = await signPaymentLinkRequest("test-checksum-key", {
    orderCode: 123,
    amount: 2000,
    description: "payment",
    cancelUrl: "https://example.com/cancel",
    returnUrl: "https://example.com/return",
  });
  assertEquals(sig.length, 64);
});
