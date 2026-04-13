/**
 * VideoRefStrip — horizontal scroll strip for 2+ VideoRefCards.
 * Shows 2.5 cards to signal scrollability on mobile (per EDS spec).
 */
import { VideoRefCard, type VideoRefData } from "./VideoRefCard";

interface Props {
  refs: VideoRefData[];
}

export function VideoRefStrip({ refs }: Props) {
  if (!refs.length) return null;

  // Single card: render inline without scroll container
  if (refs.length === 1) {
    return (
      <div className="my-3">
        <VideoRefCard data={refs[0]} />
      </div>
    );
  }

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
        {/* Peek spacer — signals more cards are scrollable */}
        <div className="flex-shrink-0" style={{ width: 16 }} aria-hidden />
      </div>
    </div>
  );
}
