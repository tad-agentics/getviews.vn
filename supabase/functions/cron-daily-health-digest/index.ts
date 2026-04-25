// Wave 5+ — daily health digest. Vietnamese-language ops summary
// emailed once per day to OPS_DIGEST_RECIPIENTS, covering the last
// 24h of pipeline activity. Pairs naturally with the existing
// alert-rule-cron-failures (Wave 1) — that fires on incidents; this
// surfaces ambient health so we notice silent degradation (slow
// growth, climbing Gemini cost, drifting failure rate) BEFORE it
// trips an alert.
//
// Three info layers, top → bottom:
//   1. Pipeline runs — batch_job_runs counts per job_name + p50
//      duration + failure tally (last 24h).
//   2. Corpus growth — rows added to video_corpus + per-niche delta
//      (ranked DESC; top 5 only to keep email scannable).
//   3. Cost — gemini_calls cost_usd sum + failure count (last 24h).
//      Includes the most-recent ingest run's thin_niche_allocations
//      so dogfood can see the Phase 2 distribution at a glance.
//
// Auth: service-role bearer (mirror cron-monday-email pattern).
// Send: invokes the existing send-email function with the new
// "daily_health_digest" template.
// Recipients: OPS_DIGEST_RECIPIENTS env var, comma-separated emails.
//   When unset the function returns 200 + skipped:true rather than
//   erroring so the cron schedule can land before recipients are
//   configured.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { corsHeaders } from "../_shared/cors.ts";

type JobRunRow = {
  job_name: string;
  status: string;
  duration_ms: number | null;
};

type NicheGrowthRow = {
  niche_id: number;
  niche_name: string | null;
  delta_24h: number;
};

type GeminiCostRow = {
  total_calls: number;
  failures: number;
  cost_usd: number;
};

type ThinNicheAllocation = {
  niche_id: number;
  niche_name: string;
  current_count: number;
  multiplier: number;
  allocated_vpn: number;
};

function requireService(req: Request): Response | null {
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const auth = req.headers.get("Authorization") ?? "";
  const token = auth.replace(/^Bearer\s+/i, "").trim();
  if (token !== serviceKey) {
    return new Response(JSON.stringify({ error: "Không được phép" }), {
      status: 401,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
  return null;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function p50(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return Math.round((sorted[mid - 1] + sorted[mid]) / 2);
  }
  return sorted[mid];
}

function aggregateRuns(rows: JobRunRow[]): Map<string, {
  ok: number;
  failed: number;
  running: number;
  p50_ms: number;
}> {
  const byJob = new Map<string, JobRunRow[]>();
  for (const r of rows) {
    if (!byJob.has(r.job_name)) byJob.set(r.job_name, []);
    byJob.get(r.job_name)!.push(r);
  }
  const out = new Map<string, {
    ok: number;
    failed: number;
    running: number;
    p50_ms: number;
  }>();
  for (const [job, jobRows] of byJob) {
    const ok = jobRows.filter((r) => r.status === "ok").length;
    const failed = jobRows.filter((r) => r.status === "failed").length;
    const running = jobRows.filter((r) => r.status === "running").length;
    const durations = jobRows
      .filter((r) => r.duration_ms != null && r.status === "ok")
      .map((r) => r.duration_ms!);
    out.set(job, { ok, failed, running, p50_ms: p50(durations) });
  }
  return out;
}

function fmtDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60_000).toFixed(1)}m`;
}

async function invokeSendDigest(
  functionsUrl: string,
  serviceKey: string,
  to: string,
  subject: string,
  html: string,
): Promise<boolean> {
  const res = await fetch(`${functionsUrl}/functions/v1/send-email`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${serviceKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      template: "daily_health_digest",
      to,
      subject,
      data: { html },
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    console.error("Gửi digest thất bại", res.status, text);
    return false;
  }
  return true;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  const auth = requireService(req);
  if (auth) return auth;

  try {
    const url = Deno.env.get("SUPABASE_URL")!;
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const functionsUrl = Deno.env.get("SUPABASE_FUNCTIONS_URL") ?? url;
    const recipientsRaw = Deno.env.get("OPS_DIGEST_RECIPIENTS") ?? "";
    const supabase = createClient(url, serviceKey);

    if (!recipientsRaw.trim()) {
      // Land the cron schedule before recipients are configured —
      // skip cleanly instead of erroring so the cron history stays
      // green.
      return new Response(
        JSON.stringify({
          ok: true,
          skipped: true,
          reason: "chưa cấu hình OPS_DIGEST_RECIPIENTS",
        }),
        { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();

    // ── 1. Pipeline runs ─────────────────────────────────────────────
    const runsResp = await supabase
      .from("batch_job_runs")
      .select("job_name,status,duration_ms")
      .gte("started_at", since);
    if (runsResp.error) throw runsResp.error;
    const runRows = (runsResp.data ?? []) as JobRunRow[];
    const runStats = aggregateRuns(runRows);

    const totalOk = Array.from(runStats.values()).reduce((s, x) => s + x.ok, 0);
    const totalFailed = Array.from(runStats.values()).reduce((s, x) => s + x.failed, 0);
    const totalRunning = Array.from(runStats.values()).reduce((s, x) => s + x.running, 0);

    const runsTableRows = Array.from(runStats.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([job, s]) => {
        const failedCell = s.failed > 0
          ? `<td style="color:#c82828"><strong>${s.failed}</strong></td>`
          : `<td>${s.failed}</td>`;
        return `<tr><td>${escapeHtml(job)}</td><td>${s.ok}</td>${failedCell}<td>${s.running}</td><td>${fmtDuration(s.p50_ms)}</td></tr>`;
      })
      .join("");

    // ── 2. Corpus growth (top 5 niches by 24h delta) ─────────────────
    // Inline query: COUNT(*) per niche from video_corpus rows added
    // in the last 24h, joined to niche_taxonomy for the label.
    const { data: growthData, error: growthErr } = await supabase.rpc(
      "daily_corpus_growth_by_niche",
      { p_since: since },
    );
    let growthRows: NicheGrowthRow[];
    if (growthErr) {
      // RPC may not exist yet on first deploy — fail-open with empty
      // growth section rather than blocking the whole digest.
      console.warn("daily_corpus_growth_by_niche RPC missing — skipping growth section", growthErr);
      growthRows = [];
    } else {
      growthRows = (growthData ?? []) as NicheGrowthRow[];
    }
    const growthTotal = growthRows.reduce((s, r) => s + r.delta_24h, 0);
    const growthTableRows = growthRows
      .sort((a, b) => b.delta_24h - a.delta_24h)
      .slice(0, 5)
      .map(
        (r) =>
          `<tr><td>${escapeHtml(r.niche_name ?? String(r.niche_id))}</td><td>+${r.delta_24h}</td></tr>`,
      )
      .join("");

    // ── 3. Cost (gemini_calls last 24h) ──────────────────────────────
    const costResp = await supabase
      .from("gemini_calls")
      .select("cost_usd,success")
      .gte("created_at", since);
    let costStats: GeminiCostRow = { total_calls: 0, failures: 0, cost_usd: 0 };
    if (costResp.error) {
      console.warn("gemini_calls fetch failed — cost section will be blank", costResp.error);
    } else {
      const rows = (costResp.data ?? []) as Array<{ cost_usd: number | null; success: boolean }>;
      costStats = {
        total_calls: rows.length,
        failures: rows.filter((r) => !r.success).length,
        cost_usd: rows.reduce((s, r) => s + (r.cost_usd ?? 0), 0),
      };
    }

    // ── 4. Phase 2 thin-niche allocation snapshot ────────────────────
    // Pull the most recent batch/ingest run's summary; surface its
    // thin_niche_allocations[] so dogfood can verify the Wave 5+
    // prioritization is doing what it claimed in the implementation
    // plan. Fail-open: any error → empty section.
    let thinNicheRows: ThinNicheAllocation[] = [];
    try {
      const { data: ingestRows } = await supabase
        .from("batch_job_runs")
        .select("summary")
        .eq("job_name", "batch/ingest")
        .eq("status", "ok")
        .order("started_at", { ascending: false })
        .limit(1);
      const summary = (ingestRows?.[0] as { summary?: { thin_niche_allocations?: ThinNicheAllocation[] } } | undefined)?.summary;
      thinNicheRows = summary?.thin_niche_allocations ?? [];
    } catch (e) {
      console.warn("thin-niche allocation fetch failed", e);
    }
    const thinNicheTopBottom = (() => {
      if (thinNicheRows.length === 0) return null;
      const sorted = [...thinNicheRows].sort((a, b) => b.allocated_vpn - a.allocated_vpn);
      return {
        top: sorted.slice(0, 3),
        bottom: sorted.slice(-3).reverse(),
      };
    })();

    // ── Render HTML ──────────────────────────────────────────────────
    const todayVi = new Date().toLocaleDateString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });
    const headlineColor = totalFailed > 0 ? "#c82828" : "#2a8a2a";
    const headlineText = totalFailed > 0
      ? `${totalFailed} job thất bại trong 24h qua`
      : `Không có job thất bại trong 24h qua`;

    const runsSection = `<h3>Pipeline · 24h qua</h3>
<p style="color:${headlineColor}"><strong>${escapeHtml(headlineText)}</strong> — tổng ${totalOk} ok, ${totalFailed} fail, ${totalRunning} đang chạy.</p>
${runsTableRows
        ? `<table border="1" cellpadding="6" cellspacing="0"><thead><tr><th>Job</th><th>OK</th><th>Fail</th><th>Đang chạy</th><th>p50</th></tr></thead><tbody>${runsTableRows}</tbody></table>`
        : "<p>(không có job nào chạy trong 24h)</p>"}`;

    const growthSection = `<h3>Corpus · 24h qua</h3>
<p>Tổng cộng <strong>+${growthTotal}</strong> video mới.</p>
${growthTableRows
        ? `<table border="1" cellpadding="6" cellspacing="0"><thead><tr><th>Top niche (theo lượng mới)</th><th>+24h</th></tr></thead><tbody>${growthTableRows}</tbody></table>`
        : "<p>(không có data tăng trưởng — RPC daily_corpus_growth_by_niche chưa cài hoặc lỗi)</p>"}`;

    const costSection = `<h3>Gemini · 24h qua</h3>
<p><strong>$${costStats.cost_usd.toFixed(4)}</strong> · ${costStats.total_calls} call · ${costStats.failures} lỗi.</p>`;

    const thinNicheSection = (() => {
      if (!thinNicheTopBottom) return "";
      const topRows = thinNicheTopBottom.top
        .map(
          (a) =>
            `<tr><td>${escapeHtml(a.niche_name)}</td><td>${a.current_count}</td><td>${a.multiplier.toFixed(2)}×</td><td>${a.allocated_vpn}</td></tr>`,
        )
        .join("");
      const botRows = thinNicheTopBottom.bottom
        .map(
          (a) =>
            `<tr><td>${escapeHtml(a.niche_name)}</td><td>${a.current_count}</td><td>${a.multiplier.toFixed(2)}×</td><td>${a.allocated_vpn}</td></tr>`,
        )
        .join("");
      return `<h3>Phase 2 · phân bổ ngách (lần ingest gần nhất)</h3>
<p><em>3 ngách được ưu tiên cao nhất:</em></p>
<table border="1" cellpadding="6" cellspacing="0"><thead><tr><th>Niche</th><th>Hiện có</th><th>Mult</th><th>Cấp phát</th></tr></thead><tbody>${topRows}</tbody></table>
<p><em>3 ngách được cấp phát ít nhất:</em></p>
<table border="1" cellpadding="6" cellspacing="0"><thead><tr><th>Niche</th><th>Hiện có</th><th>Mult</th><th>Cấp phát</th></tr></thead><tbody>${botRows}</tbody></table>`;
    })();

    const html = `<h2>GetViews — Sức khỏe pipeline ${escapeHtml(todayVi)}</h2>
${runsSection}
${growthSection}
${costSection}
${thinNicheSection}
<p style="color:#888;font-size:11px;margin-top:24px">Digest tự động hàng ngày — sửa người nhận qua env var <code>OPS_DIGEST_RECIPIENTS</code>.</p>`;

    const subjPrefix = totalFailed > 0 ? `⚠ ${totalFailed} fail` : "OK";
    const subject = `[GV] ${subjPrefix} · +${growthTotal} video · $${costStats.cost_usd.toFixed(2)}`;

    const emails = recipientsRaw.split(",").map((s) => s.trim()).filter(Boolean);
    let sent = 0;
    for (const to of emails) {
      const ok = await invokeSendDigest(functionsUrl, serviceKey, to, subject, html);
      if (ok) sent += 1;
    }

    return new Response(
      JSON.stringify({
        ok: true,
        sent,
        recipients_total: emails.length,
        runs_24h: runRows.length,
        videos_24h: growthTotal,
        cost_24h_usd: costStats.cost_usd,
        failures_24h: totalFailed,
      }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  } catch (e) {
    console.error(e);
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
