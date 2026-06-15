import { describe, expect, it } from "vitest";

import {
  CONTEXT_AXIS_TITLES,
  VIDEO_CONTEXT_SECTION_TITLE,
  mergeVideoContextSections,
} from "./mergeVideoContextSections";

describe("mergeVideoContextSections", () => {
  it("merges all three sources into metadata with context_axes", () => {
    const input = [
      { section_id: "diagnosis", title_vi: "Chẩn đoán", text_vi: "D" },
      {
        section_id: "metadata",
        title_vi: "Phân tích bối cảnh & diễn biến",
        text_vi: "Ngách Làm đẹp, đăng tối.",
      },
      {
        section_id: "boost_attribution",
        title_vi: "Có dấu hiệu ads/seeding",
        text_vi: "355K view nhưng ER 2.1%.",
      },
      {
        section_id: "channel_pattern",
        title_vi: "Video này so với kênh bạn",
        text_vi: "Vượt median kênh 3.2×.",
      },
    ];
    const { sections, hasContextBlock, foldedSources } = mergeVideoContextSections(input);

    expect(hasContextBlock).toBe(true);
    expect(foldedSources).toEqual(
      new Set(["metadata", "boost_attribution", "channel_pattern"]),
    );
    expect(sections.map((s) => s.section_id)).toEqual(["diagnosis", "metadata"]);
    expect(sections[1].title_vi).toBe(VIDEO_CONTEXT_SECTION_TITLE);
    expect(sections[1].context_axes?.map((a) => a.axis_id)).toEqual([
      "context",
      "distribution",
      "channel",
    ]);
    expect(sections[1].context_axes?.[0]?.text_vi).toBe("Ngách Làm đẹp, đăng tối.");
    expect(sections[1].context_axes?.[1]?.title_vi).toBe(CONTEXT_AXIS_TITLES.distribution);
    expect(sections.find((s) => s.section_id === "boost_attribution")).toBeUndefined();
    expect(sections.find((s) => s.section_id === "channel_pattern")).toBeUndefined();
  });

  it("merges metadata + channel when boost is absent", () => {
    const input = [
      { section_id: "metadata", text_vi: "Bối cảnh prose." },
      { section_id: "channel_pattern", text_vi: "So với kênh prose." },
    ];
    const { sections, hasContextBlock } = mergeVideoContextSections(input);

    expect(hasContextBlock).toBe(true);
    expect(sections).toHaveLength(1);
    expect(sections[0].context_axes?.map((a) => a.axis_id)).toEqual(["context", "channel"]);
  });

  it("merges metadata + boost when channel is absent", () => {
    const input = [
      { section_id: "metadata", text_vi: "Bối cảnh prose." },
      { section_id: "boost_attribution", text_vi: "Ads/seeding prose." },
    ];
    const { sections, hasContextBlock } = mergeVideoContextSections(input);

    expect(hasContextBlock).toBe(true);
    expect(sections[0].context_axes?.map((a) => a.axis_id)).toEqual(["context", "distribution"]);
  });

  it("synthesizes a distribution axis when stats exist but boost section is absent", () => {
    const input = [
      { section_id: "metadata", text_vi: "Bối cảnh prose." },
      { section_id: "channel_pattern", text_vi: "So với kênh prose." },
    ];
    const { sections } = mergeVideoContextSections(input, { hasStatsHistory: true });

    expect(sections[0].context_axes?.map((a) => a.axis_id)).toEqual([
      "context",
      "distribution",
      "channel",
    ]);
    const dist = sections[0].context_axes?.find((a) => a.axis_id === "distribution");
    expect(dist?.title_vi).toBe(CONTEXT_AXIS_TITLES.distribution);
    expect(dist?.text_vi).toBe("");
  });

  it("does not synthesize a distribution axis without stats", () => {
    const input = [
      { section_id: "metadata", text_vi: "Bối cảnh prose." },
      { section_id: "channel_pattern", text_vi: "So với kênh prose." },
    ];
    const { sections } = mergeVideoContextSections(input, { hasStatsHistory: false });

    expect(sections[0].context_axes?.map((a) => a.axis_id)).toEqual(["context", "channel"]);
  });

  it("does not merge when only metadata is present", () => {
    const input = [{ section_id: "metadata", text_vi: "Chỉ metadata." }];
    const { sections, hasContextBlock } = mergeVideoContextSections(input);

    expect(hasContextBlock).toBe(false);
    expect(sections).toEqual(input);
  });

  it("does not merge when metadata is absent (boost + channel only)", () => {
    const input = [
      { section_id: "boost_attribution", text_vi: "Boost prose." },
      { section_id: "channel_pattern", text_vi: "Channel prose." },
    ];
    const { sections, hasContextBlock } = mergeVideoContextSections(input);

    expect(hasContextBlock).toBe(false);
    expect(sections).toEqual(input);
  });

  it("places merged block at earliest source position", () => {
    const input = [
      { section_id: "hook_analysis", text_vi: "Hook" },
      { section_id: "channel_pattern", text_vi: "Channel" },
      { section_id: "script_structure", text_vi: "Structure" },
      { section_id: "metadata", text_vi: "Metadata" },
      { section_id: "boost_attribution", text_vi: "Boost" },
    ];
    const { sections } = mergeVideoContextSections(input);

    expect(sections.map((s) => s.section_id)).toEqual([
      "hook_analysis",
      "metadata",
      "script_structure",
    ]);
  });

  it("returns unchanged when input is empty", () => {
    const { sections, hasContextBlock } = mergeVideoContextSections([]);
    expect(hasContextBlock).toBe(false);
    expect(sections).toEqual([]);
  });
});
