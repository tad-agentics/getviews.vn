/**
 * ShotListCard — one beat in a generated shot list (U2).
 */
export interface ShotItemData {
  beat: number;
  duration: string;
  action: string;
  overlay: string;
  note: string;
  type?: "shot_item";
}

interface Props {
  data: ShotItemData;
}

export function ShotListCard({ data }: Props) {
  return (
    <div className="mb-2 rounded-xl border border-gray-100 bg-white p-3">
      <div className="flex items-center gap-2">
        <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-purple-100 text-xs font-bold text-purple-700">
          {data.beat}
        </span>
        <span className="flex-1 text-xs text-gray-400">{data.duration}</span>
      </div>
      <p className="mt-2 text-sm font-medium text-gray-800">{data.action}</p>
      {data.overlay?.trim() ? (
        <div className="mt-1 rounded border-l-2 border-purple-400 bg-purple-50 px-3 py-1 text-sm font-semibold text-[var(--ink)]">
          {data.overlay}
        </div>
      ) : null}
      {data.note?.trim() ? <p className="mt-1 text-xs italic text-gray-400">{data.note}</p> : null}
    </div>
  );
}
