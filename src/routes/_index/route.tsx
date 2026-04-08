import type { MetaFunction } from "react-router";

export const meta: MetaFunction = () => [
  { title: "GetViews.vn — Phân tích TikTok cho creator Việt Nam" },
  {
    name: "description",
    content:
      "Bạn lướt TikTok cả ngày để tìm ý tưởng. GetViews làm việc đó thay bạn. Không guru. Không screenshot. Data thực từ video thực.",
  },
];

export default function LandingPage() {
  return (
    <main>
      {/* Landing page — built in /foundation by Frontend Developer */}
      <p>GetViews.vn</p>
    </main>
  );
}
