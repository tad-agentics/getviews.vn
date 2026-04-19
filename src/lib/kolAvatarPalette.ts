/**
 * KOL creator avatar backgrounds — cycle matches `kol.jsx` / `--gv-avatar-*` in `app.css`.
 */
export const kolAvatarBgClasses = [
  "bg-[color:var(--gv-avatar-1)]",
  "bg-[color:var(--gv-avatar-2)]",
  "bg-[color:var(--gv-avatar-3)]",
  "bg-[color:var(--gv-avatar-4)]",
  "bg-[color:var(--gv-avatar-5)]",
  "bg-[color:var(--gv-avatar-6)]",
] as const;

export function kolAvatarBgClassAt(rowIndex: number): string {
  const i = ((rowIndex % 6) + 6) % 6;
  return kolAvatarBgClasses[i] ?? kolAvatarBgClasses[0];
}
