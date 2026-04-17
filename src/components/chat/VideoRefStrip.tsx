/**
 * VideoRefStrip — video reference citations in chat.
 *
 * 1 ref  → w-36 card at intrinsic width (flex parent prevents stretching)
 * 2 refs → 2-col grid
 * 3 refs → 3-col grid
 * 4+ refs → horizontal scroll strip, w-36 fixed-width cards
 */
import { VideoRefCard, type VideoRefData } from "./VideoRefCard";

interface Props {
  refs: VideoRefData[];
}

export function VideoRefStrip({ refs }: Props) {
  if (!refs.length) return null;

  // Single card: flex parent keeps the w-36 card at intrinsic width.
  if (refs.length === 1) {
    return (
      <div className="my-3 flex">
        <VideoRefCard data={refs[0]} />
      </div>
    );
  }

  // 2–3 refs: CSS grid filling container width
  if (refs.length <= 3) {
    const cols = refs.length === 3 ? "grid-cols-3" : "grid-cols-2";
    return (
      <div className={`my-3 grid ${cols} gap-2`}>
        {refs.map((ref) => (
          <VideoRefCard key={ref.video_id} data={ref} />
        ))}
      </div>
    );
  }

  // 4+ refs: horizontal scroll strip — VideoRefCard is already w-36 flex-shrink-0
  return (
    <div className="my-3 -mx-4 lg:-mx-5">
      <div
        className="flex gap-2.5 overflow-x-auto px-4 pb-2 lg:px-5"
        style={{ scrollSnapType: "x mandatory", WebkitOverflowScrolling: "touch" }}
      >
        {refs.map((ref) => (
          <div key={ref.video_id} style={{ scrollSnapAlign: "start" }}>
            <VideoRefCard data={ref} />
          </div>
        ))}
        <div className="w-4 flex-shrink-0" aria-hidden />
      </div>
    </div>
  );
}
