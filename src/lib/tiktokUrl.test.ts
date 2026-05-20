import { describe, expect, it } from "vitest";
import { extractTikTokVideoIdFromText } from "./tiktokUrl";

describe("extractTikTokVideoIdFromText", () => {
  it("parses standard video URL", () => {
    expect(
      extractTikTokVideoIdFromText(
        "https://www.tiktok.com/@curnon.official/video/7634391245737053447?lang=vi-VN",
      ),
    ).toBe("7634391245737053447");
  });

  it("parses URL without @handle", () => {
    expect(extractTikTokVideoIdFromText("https://www.tiktok.com/video/7634391245737053447")).toBe(
      "7634391245737053447",
    );
  });
});
