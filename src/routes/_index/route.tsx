import type { MetaFunction } from "react-router";
import LandingPage from "./LandingPage";

const PAGE_TITLE = "GetViews — Phân tích TikTok cho Creator Việt";
const PAGE_DESC =
  "Dán link video của bạn vào. 1 phút sau biết ngay lỗi ở đâu, nên fix gì, và hook nào đang chạy trong niche của bạn. Không guru. Không screenshot. Data thực từ video thực.";

export const meta: MetaFunction = () => [
  { title: PAGE_TITLE },
  { name: "description", content: PAGE_DESC },
  { property: "og:title", content: PAGE_TITLE },
  { property: "og:description", content: PAGE_DESC },
  { property: "og:type", content: "website" },
  { name: "twitter:card", content: "summary_large_image" },
];

export default LandingPage;
