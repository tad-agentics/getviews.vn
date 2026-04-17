import type { MetaFunction } from "react-router";
import type { Route } from "./+types/route";
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

export async function loader(_: Route.LoaderArgs) {
  try {
    const res = await fetch("/api/landing-stats");
    if (!res.ok) throw new Error("stats unavailable");
    return (await res.json()) as {
      hooks: { hook_type: string; avg_views: number; sample_size: number }[];
      thumb_ids: string[];
    };
  } catch {
    return { hooks: [], thumb_ids: [] };
  }
}

export default function Route({ loaderData }: Route.ComponentProps) {
  return <LandingPage stats={loaderData} />;
}
