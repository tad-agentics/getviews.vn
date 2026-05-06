/**
 * Studio Home paste-template guard tests.
 *
 * Pre-L1.5 audit, the "Dán @handle" chip filled the composer with a
 * literal ``@handle`` token. Submitting unchanged routed users to
 * /app/channel?handle=handle (404). The fix here is two-pronged:
 *   1. Switch the placeholder to ``@…`` (Vietnamese ellipsis) which
 *      breaks the FE classifier handle regex.
 *   2. Block submission via ``unfilledPasteTemplateHint`` when the
 *      placeholder hasn't been replaced with a real URL/handle.
 */

import { describe, expect, it } from "vitest";
import {
  PASTE_HANDLE_TEMPLATE,
  PASTE_VIDEO_TEMPLATE,
  unfilledPasteTemplateHint,
} from "./pasteTemplates";

describe("pasteTemplates", () => {
  it("PASTE_HANDLE_TEMPLATE uses @… ellipsis, never a literal @handle", () => {
    // The FE classifier regex /@([a-zA-Z0-9_.]+)/ must NOT match the
    // template — that was the root cause of the 404 false-positive.
    expect(PASTE_HANDLE_TEMPLATE).not.toMatch(/@[a-zA-Z0-9_.]+/);
    expect(PASTE_HANDLE_TEMPLATE).toContain("@…");
  });

  it("PASTE_VIDEO_TEMPLATE contains no embedded URL the regex would parse", () => {
    expect(PASTE_VIDEO_TEMPLATE).not.toMatch(/https?:\/\//i);
  });

  it("returns hint when video template submitted without a real URL", () => {
    expect(unfilledPasteTemplateHint(PASTE_VIDEO_TEMPLATE)).toContain("link TikTok");
  });

  it("returns hint when handle template submitted without a real @handle", () => {
    expect(unfilledPasteTemplateHint(PASTE_HANDLE_TEMPLATE)).toContain("@handle");
  });

  it("clears hint when a real TikTok URL is appended", () => {
    const filled = `${PASTE_VIDEO_TEMPLATE}https://www.tiktok.com/@user/video/123`;
    expect(unfilledPasteTemplateHint(filled)).toBeNull();
  });

  it("clears hint when a real @username is appended", () => {
    const filled = `${PASTE_HANDLE_TEMPLATE}@nguyenvana`;
    expect(unfilledPasteTemplateHint(filled)).toBeNull();
  });

  it("returns null for unrelated free-form queries", () => {
    expect(unfilledPasteTemplateHint("Xu hướng tuần này trong ngách Beauty?")).toBeNull();
    expect(unfilledPasteTemplateHint("")).toBeNull();
    expect(unfilledPasteTemplateHint("   ")).toBeNull();
  });

  it("does NOT trigger on a custom flop question that doesn't start with the template", () => {
    // A user typing their own question should pass through cleanly even
    // if the wording overlaps — only the literal template prefix counts.
    const custom = "Tôi nghĩ video này flop vì hook chưa bắt — đúng không?";
    expect(unfilledPasteTemplateHint(custom)).toBeNull();
  });
});
