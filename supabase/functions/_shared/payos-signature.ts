/** PayOS HMAC helpers — shared by create-payment + payos-webhook. */

export async function hmacSha256Hex(secret: string, payload: string): Promise<string> {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(payload));
  const bytes = new Uint8Array(sig);
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** PayOS create-payment-link signature (field order is fixed by PayOS). */
export async function signPaymentLinkRequest(
  checksumKey: string,
  params: {
    orderCode: number;
    amount: number;
    description: string;
    cancelUrl: string;
    returnUrl: string;
  },
): Promise<string> {
  const dataStr =
    `amount=${params.amount}&cancelUrl=${params.cancelUrl}&description=${params.description}&orderCode=${params.orderCode}&returnUrl=${params.returnUrl}`;
  return hmacSha256Hex(checksumKey, dataStr);
}

/** PayOS ``description`` max length is 25 characters. */
export function payosOrderDescription(plan: string): string {
  return `GetViews ${plan}`.slice(0, 25);
}
