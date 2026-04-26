/**
 * PR-cleanup-D Studio Home — ConnectChannelCard render-test.
 *
 * Reference: design pack ``screens/home.jsx::ConnectChannelCard``
 * (lines 512-668).
 */
import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockMutate = vi.fn();
const mockUseUpdateProfile = vi.fn();
vi.mock("@/hooks/useUpdateProfile", () => ({
  useUpdateProfile: () => mockUseUpdateProfile(),
}));

const { ConnectChannelCard } = await import("./ConnectChannelCard");

beforeEach(() => {
  mockMutate.mockReset();
  mockUseUpdateProfile.mockReset();
  mockUseUpdateProfile.mockReturnValue({
    mutate: mockMutate,
    isPending: false,
    isError: false,
    isSuccess: false,
  });
  vi.useFakeTimers({ shouldAdvanceTime: false });
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("ConnectChannelCard — idle state", () => {
  it("renders the BƯỚC 1 / 1 kicker and paste-input UI", () => {
    const { getByText, getByPlaceholderText } = render(<ConnectChannelCard />);
    expect(getByText("BƯỚC 1 / 1")).toBeTruthy();
    expect(getByText(/Dán link kênh TikTok của bạn/)).toBeTruthy();
    expect(getByPlaceholderText(/@an\.tech/)).toBeTruthy();
    expect(getByText("Phân tích")).toBeTruthy();
  });

  it("renders the example handle chips", () => {
    const { getByText } = render(<ConnectChannelCard />);
    expect(getByText("@an.tech")).toBeTruthy();
    expect(getByText("@chinasecrets")).toBeTruthy();
    expect(getByText("@aifreelance")).toBeTruthy();
  });

  it("renders the trust footer line + ~6 giây timing hint", () => {
    const { getByText } = render(<ConnectChannelCard />);
    expect(getByText(/Chỉ đọc dữ liệu công khai/)).toBeTruthy();
    expect(getByText("~6 giây")).toBeTruthy();
  });

  it("disables Phân tích until a valid handle is entered", () => {
    const { getByPlaceholderText, getByText } = render(<ConnectChannelCard />);
    const input = getByPlaceholderText(/@an\.tech/) as HTMLInputElement;
    const button = getByText("Phân tích").closest("button") as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    fireEvent.change(input, { target: { value: "@valid.user" } });
    expect(button.disabled).toBe(false);
  });

  it("clicking an example chip fills the input", () => {
    const { getByPlaceholderText, getByText } = render(<ConnectChannelCard />);
    const input = getByPlaceholderText(/@an\.tech/) as HTMLInputElement;
    fireEvent.click(getByText("@an.tech"));
    expect(input.value).toBe("@an.tech");
  });
});

describe("ConnectChannelCard — submit & analyze flow", () => {
  it("strips @ prefix when calling updateProfile.mutate", () => {
    const { getByPlaceholderText, getByText } = render(<ConnectChannelCard />);
    const input = getByPlaceholderText(/@an\.tech/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "@an.tech" } });
    fireEvent.click(getByText("Phân tích"));
    expect(mockMutate).toHaveBeenCalledWith(
      { tiktok_handle: "an.tech" },
      expect.any(Object),
    );
  });

  it("parses tiktok.com/@x style URLs", () => {
    const { getByPlaceholderText, getByText } = render(<ConnectChannelCard />);
    const input = getByPlaceholderText(/@an\.tech/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "https://www.tiktok.com/@chinasecrets" } });
    fireEvent.click(getByText("Phân tích"));
    expect(mockMutate).toHaveBeenCalledWith(
      { tiktok_handle: "chinasecrets" },
      expect.any(Object),
    );
  });

  it("accepts bare username (no @ prefix) as a loose form", () => {
    const { getByPlaceholderText, getByText } = render(<ConnectChannelCard />);
    const input = getByPlaceholderText(/@an\.tech/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "an.tech" } });
    fireEvent.click(getByText("Phân tích"));
    expect(mockMutate).toHaveBeenCalledWith(
      { tiktok_handle: "an.tech" },
      expect.any(Object),
    );
  });

  it("submits via Enter key", () => {
    const { getByPlaceholderText } = render(<ConnectChannelCard />);
    const input = getByPlaceholderText(/@an\.tech/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "@x" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(mockMutate).toHaveBeenCalled();
  });

  it("renders the 4-step progress list during analyzing phase", () => {
    const { getByPlaceholderText, getByText } = render(<ConnectChannelCard />);
    const input = getByPlaceholderText(/@an\.tech/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "@x" } });
    fireEvent.click(getByText("Phân tích"));
    // After click, the analyzing card is rendered.
    expect(getByText(/Đang phân tích/)).toBeTruthy();
    expect(getByText(/Đang tìm kênh trên TikTok/)).toBeTruthy();
    expect(getByText(/Đọc 60 video gần nhất/)).toBeTruthy();
    expect(getByText(/So sánh với corpus ngách/)).toBeTruthy();
    expect(getByText(/Tìm 3 việc nên làm tuần này/)).toBeTruthy();
  });

  it("surfaces the error message + restores idle UI when the mutation errors", () => {
    mockMutate.mockImplementation((_patch, opts) => {
      // Synchronously trigger the onError callback.
      opts?.onError?.(new Error("Mạng yếu"));
    });
    const { getByPlaceholderText, getByText, queryByText } = render(<ConnectChannelCard />);
    const input = getByPlaceholderText(/@an\.tech/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "@x" } });
    fireEvent.click(getByText("Phân tích"));
    expect(getByText(/Mạng yếu/)).toBeTruthy();
    // Idle UI returned (input + Phân tích button visible again).
    expect(queryByText(/Đang phân tích/)).toBeNull();
    expect(getByText("Phân tích")).toBeTruthy();
  });

  it("ignores click while already in analyzing phase", () => {
    const { getByPlaceholderText, getByText } = render(<ConnectChannelCard />);
    const input = getByPlaceholderText(/@an\.tech/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "@x" } });
    const button = getByText("Phân tích");
    fireEvent.click(button);
    fireEvent.click(button);
    // Even with two clicks while idle could fire twice in theory; the
    // analyzing state hides the button so re-clicks become impossible.
    // Assertion: the mutation was called exactly once.
    expect(mockMutate).toHaveBeenCalledTimes(1);
  });
});
