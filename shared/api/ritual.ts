import type { DailyRitual, RitualEmptyReason, RitualErrorBody, RitualResult } from "../types/ritual";

export type FetchDailyRitualParams = {
  baseUrl: string;
  accessToken: string;
  /** Niche row to load (must be one of the user’s ``niche_ids``). */
  expectedNicheId: number;
};

/**
 * GET /home/daily-ritual?niche_id= — parses 200/404 and enforces niche_id match on success.
 * Uses global `fetch` (browser or React Native).
 */
export async function fetchDailyRitual(params: FetchDailyRitualParams): Promise<RitualResult> {
  const { baseUrl, accessToken, expectedNicheId } = params;
  const root = baseUrl.replace(/\/$/, "");
  const q = `?niche_id=${encodeURIComponent(String(expectedNicheId))}`;
  const res = await fetch(`${root}/home/daily-ritual${q}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (res.status === 404) {
    let code: RitualEmptyReason = "ritual_no_row";
    try {
      const body = (await res.json()) as Partial<RitualErrorBody>;
      if (body.code === "ritual_niche_stale" || body.code === "ritual_no_row") {
        code = body.code;
      }
    } catch {
      /* malformed body — default no_row */
    }
    return { data: null, emptyReason: code };
  }

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const data = (await res.json()) as DailyRitual;
  if (Number(data.niche_id) !== Number(expectedNicheId)) {
    return { data: null, emptyReason: "ritual_niche_stale" };
  }
  return { data, emptyReason: null };
}
