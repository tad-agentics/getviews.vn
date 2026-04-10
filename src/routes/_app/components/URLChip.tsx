export function URLChip({ url }: { url: string }) {
  const isValid = url.includes("tiktok.com");
  const handle = url.match(/@[\w.]+/)?.[0] || url.substring(0, 30);
  return (
    <div
      className={`mb-2 flex items-center gap-2 rounded-lg border-l-2 px-3 py-2 text-xs font-medium ${
        isValid
          ? "border-l-[var(--purple)] bg-[var(--purple-light)] text-[var(--purple)]"
          : "border-l-[var(--danger)] bg-[var(--danger)]/5 text-[var(--danger)]"
      }`}
    >
      {isValid ? `Video TikTok — ${handle}` : "Link không hợp lệ — cần link TikTok"}
    </div>
  );
}
