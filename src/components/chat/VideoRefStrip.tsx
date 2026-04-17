/**
 * VideoRefStrip — video reference citations in chat.
 *
 * 1 ref  → w-36 card at intrinsic width (flex parent prevents stretching)
 * 2 refs → 2-col grid filling container width
 * 3 refs → 3-col grid filling container width
 * 4+ refs → horizontal scroll strip, w-36 fixed-width cards
 *
 * Width is controlled by the caller via VideoRefCard's className prop —
 * grid cells receive w-full, scroll-strip cards receive w-36 flex-shrink-0.
 */
import { VideoRefCard, type VideoRefData } from "./VideoRefCard";

interface Props {
  refs: VideoRefData[];
}

export function VideoRefStrip({ refs }: Props) {
  if (!refs.length) return null;

  // Single card: flex parent keeps card at intrinsic width.
  if (refs.length === 1) {
    return (
      <div className="my-3 flex">
        <VideoRefCard data={refs[0]} className="w-36 flex-shrink-0" />
      </div>
    );
  }

  // 2–3 refs: CSS grid — cards fill their column, w-36 / flex-shrink-0 not needed.
  if (refs.length <= 3) {
    const cols = refs.length === 3 ? "grid-cols-3" : "grid-cols-2";
    return (
      <div className={`my-3 grid ${cols} gap-2`}>
        {refs.map((ref) => (
          <VideoRefCard key={ref.video_id} data={ref} className="w-full" />
        ))}
      </div>
    );
  }

  // 4+ refs: horizontal scroll strip — fixed card width via className.
  return (
    <div className="my-3 -mx-4 lg:-mx-5">
      <div
        className="flex gap-2.5 overflow-x-auto px-4 pb-2 lg:px-5"
        style={{ scrollSnapType: "x mandatory", WebkitOverflowScrolling: "touch" }}
      >
        {refs.map((ref) => (
          <div key={ref.video_id} style={{ scrollSnapAlign: "start" }}>
            <VideoRefCard data={ref} className="w-36 flex-shrink-0" />
          </div>
        ))}
        <div className="w-4 flex-shrink-0" aria-hidden />
      </div>
    </div>
  );
}
