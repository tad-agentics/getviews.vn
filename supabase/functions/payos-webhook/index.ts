import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { handlePayOSWebhook } from "./handler.ts";

// Thin runtime binding — all logic (and its tests) live in handler.ts.
Deno.serve((req) => {
  const url = Deno.env.get("SUPABASE_URL")!;
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  return handlePayOSWebhook(req, {
    checksumKey: Deno.env.get("PAYOS_CHECKSUM_KEY"),
    supabaseUrl: url,
    serviceKey,
    supabase: createClient(url, serviceKey),
    fetchFn: fetch,
  });
});
