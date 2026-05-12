import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { ANSWER_SESSION_FORMATS } from "./api-types";

function sorted(xs: Iterable<string>): string[] {
  return [...xs].sort();
}

function extractQuotedValues(input: string, quote: '"' | "'"): string[] {
  const re = quote === '"' ? /"([^"]+)"/g : /'([^']+)'/g;
  const out: string[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(input)) !== null) out.push(m[1]);
  return out;
}

describe("Answer session format contract parity", () => {
  it("keeps FE format list in sync with Cloud Run and DB constraint", () => {
    const root = process.cwd();
    const pyPath = path.join(root, "cloud-run/getviews_pipeline/routers/answer.py");
    const sqlPath = path.join(
      root,
      "supabase/migrations/20260512000003_answer_sessions_script_format.sql",
    );

    const py = readFileSync(pyPath, "utf8");
    const sql = readFileSync(sqlPath, "utf8");

    const pyMatch = py.match(/format:\s*Literal\[(?<inner>[\s\S]*?)\]\s*=/);
    expect(pyMatch?.groups?.inner, "AnswerSessionCreateBody.format Literal not found").toBeTruthy();
    const pyFormats = extractQuotedValues(pyMatch!.groups!.inner, '"');

    const sqlMatch = sql.match(/CHECK\s*\(format IN \((?<inner>[\s\S]*?)\)\)/);
    expect(sqlMatch?.groups?.inner, "answer_sessions format CHECK not found").toBeTruthy();
    const sqlFormats = extractQuotedValues(sqlMatch!.groups!.inner, "'");

    expect(sorted(ANSWER_SESSION_FORMATS)).toEqual(sorted(pyFormats));
    expect(sorted(ANSWER_SESSION_FORMATS)).toEqual(sorted(sqlFormats));
  });
});
