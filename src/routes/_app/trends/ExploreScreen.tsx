import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router";
import { motion, AnimatePresence } from "motion/react";
import {
  ChevronRight,
  Search,
  X,
  ChevronDown,
  VolumeX,
  Volume2,
  Heart,
  MessageCircle,
  Share2,
  Eye,
  Loader2,
} from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { useVideoCorpus } from "@/hooks/useVideoCorpus";
import { formatDate, formatViews } from "@/lib/formatters";

/* --- Mock data ---------------------------------------------------- */

const trendingCards = [
  {
    id: 1,
    title: "Fruit-cutting or food-prep as a visual anchor while delivering the hook",
    description:
      "Creators who slice fruit, peel oranges, or chop food while speaking their hook to camera dramatically outperform static talking heads...",
    images: [
      "https://images.unsplash.com/photo-1598358532244-6480b5c5ea1a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=300",
      "https://images.unsplash.com/photo-1758273706007-f1524d2d963f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=300",
      "https://images.unsplash.com/photo-1759215524472-1b0686fdbd87?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=300",
    ],
    platforms: ["tiktok", "ig", "yt"],
    videos: [
      {
        handle: "@bephanoi_official",
        title: "Cat dua hau kieu nay viral ngay",
        views: "1.2M",
        time: "2d ago",
        img: "https://images.unsplash.com/photo-1598358532244-6480b5c5ea1a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400",
        caption: "Hook cat trai cay + noi thang vao cam",
        likes: "89.4K",
        comments: "2.1K",
        shares: "12.3K",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
      },
      {
        handle: "@cookwithlinh",
        title: "Got tao 1 phut = 500K view??",
        views: "523K",
        time: "3d ago",
        img: "https://images.unsplash.com/photo-1758273706007-f1524d2d963f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400",
        caption: "Khong can studio xin, can tay nghe",
        likes: "42.1K",
        comments: "918",
        shares: "5.7K",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
      },
      {
        handle: "@foodhacksvn",
        title: "Thai hanh kieu nay khong chay nuoc mat",
        views: "341K",
        time: "4d ago",
        img: "https://images.unsplash.com/photo-1759215524472-1b0686fdbd87?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400",
        caption: "Meo bep nuc ma ai cung can",
        likes: "28.6K",
        comments: "640",
        shares: "9.2K",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
      },
      {
        handle: "@minhbep",
        title: "POV: ban cat xoai dung cach",
        views: "198K",
        time: "5d ago",
        img: "https://images.unsplash.com/photo-1598358532244-6480b5c5ea1a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400",
        caption: "Cai nay ai cung lam sai het",
        likes: "17.2K",
        comments: "430",
        shares: "3.1K",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
      },
      {
        handle: "@vegankitchen.vn",
        title: "Luoc rau kieu nay moi giu mau xanh",
        views: "89K",
        time: "6d ago",
        img: "https://images.unsplash.com/photo-1759215524472-1b0686fdbd87?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400",
        caption: "Bi quyet tu dau bep 5 sao",
        likes: "7.8K",
        comments: "201",
        shares: "1.4K",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4",
      },
    ],
  },
  {
    id: 2,
    title: "Panic-countdown hook: 'We literally leave in X hours and I see THIS'",
    description:
      "A formulaic hook structure where the creator feigns panic about an imminent departure and then reveals an app got them breakout ratios of...",
    images: [
      "https://images.unsplash.com/photo-1758272422000-07f4bdc8a9fd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=300",
      "https://images.unsplash.com/photo-1645118286859-0cf9c5c784b2?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=300",
      "https://images.unsplash.com/photo-1758272422309-070322449526?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=300",
    ],
    platforms: ["tiktok", "ig", "yt"],
    videos: [
      {
        handle: "@dulichviet365",
        title: "Bay sau 3 tieng ma con chua pack!!",
        views: "892K",
        time: "1d ago",
        img: "https://images.unsplash.com/photo-1758272422000-07f4bdc8a9fd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400",
        caption: "Panic packing vlog kieu nay moi viral",
        likes: "67.3K",
        comments: "3.4K",
        shares: "18.9K",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
      },
      {
        handle: "@travelwithkhanh",
        title: "2 tieng nua check-in ma con ngoi day",
        views: "445K",
        time: "2d ago",
        img: "https://images.unsplash.com/photo-1645118286859-0cf9c5c784b2?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400",
        caption: "Hook countdown = cong thuc trieu view",
        likes: "38.9K",
        comments: "1.2K",
        shares: "7.3K",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
      },
      {
        handle: "@bacpacker.vn",
        title: "Con 1 tieng ma vali van rong",
        views: "267K",
        time: "3d ago",
        img: "https://images.unsplash.com/photo-1758272422309-070322449526?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400",
        caption: "Cai cam giac nay ai cung tung trai",
        likes: "22.1K",
        comments: "876",
        shares: "4.5K",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
      },
      {
        handle: "@minhtravel",
        title: "Quen passport luc ra san bay",
        views: "134K",
        time: "4d ago",
        img: "https://images.unsplash.com/photo-1758272422000-07f4bdc8a9fd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400",
        caption: "Khoanh khac panic ma ai cung so",
        likes: "11.2K",
        comments: "540",
        shares: "2.8K",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
      },
    ],
  },
  {
    id: 3,
    title: "AI-generated fake photo sent as text prank with real reaction recording",
    description:
      "Creators use AI photo editors to generate a fake disaster image, text it to a family member or partner, then screen-record the panicked text...",
    images: [
      "https://images.unsplash.com/photo-1759215524472-1b0686fdbd87?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=300",
      "https://images.unsplash.com/photo-1758273706007-f1524d2d963f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=300",
      "https://images.unsplash.com/photo-1598358532244-6480b5c5ea1a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=300",
    ],
    platforms: ["tiktok", "ig"],
    videos: [
      {
        handle: "@haihuocvn",
        title: "Gui anh AI cho me roi nhan cai ket",
        views: "2.1M",
        time: "1d ago",
        img: "https://images.unsplash.com/photo-1759215524472-1b0686fdbd87?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400",
        caption: "Phan ung cua me moi la highlight",
        likes: "198K",
        comments: "12.4K",
        shares: "67.8K",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4",
      },
      {
        handle: "@prankviet",
        title: "Ban trai tuong minh dam xe",
        views: "876K",
        time: "2d ago",
        img: "https://images.unsplash.com/photo-1758273706007-f1524d2d963f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400",
        caption: "AI prank + real reaction = cong thuc viral",
        likes: "74.2K",
        comments: "5.6K",
        shares: "23.1K",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
      },
      {
        handle: "@comedyvn",
        title: "Prank em gai bang anh AI nha bi lu",
        views: "412K",
        time: "3d ago",
        img: "https://images.unsplash.com/photo-1598358532244-6480b5c5ea1a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400",
        caption: "Man phan ung khong ai ngo toi",
        likes: "35.8K",
        comments: "2.3K",
        shares: "9.7K",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
      },
    ],
  },
  {
    id: 4,
    title: "Alarm-won't-stop scavenger hunt filmed first-person",
    description:
      "First-person POV videos of creators searching their house to photograph object so their alarm app stops scr...",
    images: [
      "https://images.unsplash.com/photo-1760551937732-a86cccd851e7?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=300",
      "https://images.unsplash.com/photo-1758272422309-070322449526?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=300",
      "https://images.unsplash.com/photo-1645118286859-0cf9c5c784b2?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=300",
    ],
    platforms: ["tiktok", "yt"],
    videos: [
      {
        handle: "@lazyvn",
        title: "App bao thuc bat chup anh giay",
        views: "1.5M",
        time: "1d ago",
        img: "https://images.unsplash.com/photo-1760551937732-a86cccd851e7?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400",
        caption: "Tim cai giay luc 5am ma khong ngu them duoc",
        likes: "142K",
        comments: "8.9K",
        shares: "44.2K",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
      },
      {
        handle: "@morningroutine.vn",
        title: "POV: chay khap nha luc 6am de tat alarm",
        views: "634K",
        time: "2d ago",
        img: "https://images.unsplash.com/photo-1758272422309-070322449526?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400",
        caption: "First-person chaos = engagement cao nhat",
        likes: "54.7K",
        comments: "3.2K",
        shares: "15.6K",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
      },
      {
        handle: "@sleepaddict",
        title: "Bi bat chup cau thang luc 5:30am",
        views: "289K",
        time: "3d ago",
        img: "https://images.unsplash.com/photo-1645118286859-0cf9c5c784b2?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400",
        caption: "Cai app nay ac nhan that su",
        likes: "23.4K",
        comments: "1.1K",
        shares: "5.8K",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4",
      },
      {
        handle: "@wakeupchallenge",
        title: "Ngay 7 dung alarm chup anh: ket qua?",
        views: "178K",
        time: "4d ago",
        img: "https://images.unsplash.com/photo-1760551937732-a86cccd851e7?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400",
        caption: "Review sau 1 tuan dung that su",
        likes: "15.1K",
        comments: "780",
        shares: "3.3K",
        videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
      },
    ],
  },
];

const breakoutHits = [
  { rank: 1, title: "Solicit Opinion On Celebrity Drama", views: "109.4K", handle: "@bc_drama", time: "4d ago", img: "https://images.unsplash.com/photo-1758272422000-07f4bdc8a9fd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=80" },
  { rank: 2, title: "Mock Unrealistic Instant Results Hook", views: "45K", handle: "@jinnablogg3", time: "4d ago", img: "https://images.unsplash.com/photo-1760551937732-a86cccd851e7?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=80" },
  { rank: 3, title: "Tease Scandalous App Content", views: "25.1K", handle: "@theappdotcomm", time: "4d ago", img: "https://images.unsplash.com/photo-1759215524472-1b0686fdbd87?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=80" },
  { rank: 4, title: "Call Out Specific Dating Ick", views: "5.3K", handle: "@datingwithkatie", time: "5d ago", img: "https://images.unsplash.com/photo-1645118286859-0cf9c5c784b2?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=80" },
  { rank: 5, title: "Pitch Hypothetical Marketing Strategy", views: "2.8K", handle: "@thequestion", time: "3d ago", img: "https://images.unsplash.com/photo-1758273706007-f1524d2d963f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=80" },
  { rank: 6, title: "Confusing Duo Introduction Hook", views: "340.8K", handle: "@duosetug_official", time: "2d ago", img: "https://images.unsplash.com/photo-1598358532244-6480b5c5ea1a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=80" },
  { rank: 7, title: "Solo Activity Vulnerability Hook", views: "27.3K", handle: "@jodelosb", time: "13d ago", img: "https://images.unsplash.com/photo-1758272422309-070322449526?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=80" },
  { rank: 8, title: "Partner Jealousy Warning Hook", views: "8.7K", handle: "@jyounglikelee", time: "9d ago", img: "https://images.unsplash.com/photo-1758272422000-07f4bdc8a9fd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=80" },
  { rank: 9, title: "Stereotype Competitor App Hook", views: "8.9K", handle: "@daniel.dates", time: "8d ago", img: "https://images.unsplash.com/photo-1760551937732-a86cccd851e7?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=80" },
];

const viralNow = [
  { title: "Why Is X Hard Template", views: "540.2K", handle: "@mercy_german", time: "2d ago", img: "https://images.unsplash.com/photo-1758273706007-f1524d2d963f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=80" },
  { title: "Toxic Romantic Rival Comparison Hook", views: "491K", handle: "@silyat", time: "2d ago", img: "https://images.unsplash.com/photo-1645118286859-0cf9c5c784b2?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=80" },
];

const PLACEHOLDER_THUMB = "/placeholder.svg";

type CorpusRow = {
  id: string;
  tiktok_url: string | null;
  video_url: string | null;
  thumbnail_url: string | null;
  creator_handle: string | null;
  views: number | null;
  indexed_at: string | null;
  likes: number | null;
  shares: number | null;
  comments: number | null;
};

/** Shape expected by VideoCard / VideoPlayerModal (replaces Make exploreVideos items). */
type ExploreGridVideo = {
  id: string;
  views: string;
  time: string;
  img: string;
  text: string;
  handle: string;
  caption: string;
  likes: string;
  comments: string;
  shares: string;
  videoUrl: string;
  tiktok_url: string | null;
};

function corpusRowToExploreVideo(row: CorpusRow): ExploreGridVideo {
  const v = row.views ?? 0;
  return {
    id: row.id,
    views: v === 0 ? "—" : formatViews(v),
    time: row.indexed_at ? formatDate(row.indexed_at) : "—",
    img: row.thumbnail_url || PLACEHOLDER_THUMB,
    text: "",
    handle: row.creator_handle ? `@${row.creator_handle}` : "@—",
    caption: row.creator_handle ? `Video @${row.creator_handle}` : "Video",
    likes: row.likes != null ? formatViews(row.likes) : "—",
    comments: row.comments != null ? formatViews(row.comments) : "—",
    shares: row.shares != null ? formatViews(row.shares) : "—",
    videoUrl: row.video_url ?? "",
    tiktok_url: row.tiktok_url,
  };
}

/* --- Platform Icon SVGs ------------------------------------------ */
function TikTokIcon({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path
        fill="#69C9D0"
        d="M10.06 13.28a2.89 2.89 0 0 0-2.89 2.89 2.89 2.89 0 0 0 2.89 2.89 2.89 2.89 0 0 0 2.88-2.5V2h3.45c.09.78.4 1.5.88 2.08a4.83 4.83 0 0 0 2.9 2.17v3.44a8.18 8.18 0 0 1-4.78-1.52v6.5a6.34 6.34 0 0 1-6.33 6.33 6.34 6.34 0 0 1-6.34-6.34 6.34 6.34 0 0 1 6.34-6.34c.27 0 .53.02.79.05v3.48a2.89 2.89 0 0 0-.79-.1z"
      />
      <path
        fill="#EE1D52"
        d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V8.69a8.18 8.18 0 0 0 4.78 1.52V6.76a4.85 4.85 0 0 1-1.01-.07z"
      />
      <path
        fill="#ffffff"
        d="M18.58 6.09a4.83 4.83 0 0 1-3.77-4.25V1.36h-3.45v13.31a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V7.97a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V7.9a8.18 8.18 0 0 0 4.78 1.52V6.05a4.85 4.85 0 0 1-1.01.04z"
      />
    </svg>
  );
}

function IGIcon({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <defs>
        <linearGradient id="ig-grad" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#f09433" />
          <stop offset="25%" stopColor="#e6683c" />
          <stop offset="50%" stopColor="#dc2743" />
          <stop offset="75%" stopColor="#cc2366" />
          <stop offset="100%" stopColor="#bc1888" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="20" height="20" rx="5" ry="5" fill="url(#ig-grad)" />
      <circle cx="12" cy="12" r="4.5" fill="none" stroke="white" strokeWidth="1.8" />
      <circle cx="17.5" cy="6.5" r="1.2" fill="white" />
    </svg>
  );
}

function YTIcon({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect x="1" y="5" width="22" height="14" rx="4" fill="#FF0000" />
      <polygon points="9.5,8.5 16,12 9.5,15.5" fill="white" />
    </svg>
  );
}

/* --- Shared VideoPlayerPanel --------------------------------------- */
function EngagementSidebar({
  img,
  likes,
  comments,
  shares,
  views,
}: {
  img: string;
  likes: string;
  comments: string;
  shares: string;
  views: string;
}) {
  return (
    <div className="hidden md:flex absolute right-3 bottom-24 z-20 flex-col items-center gap-4">
      <div className="w-9 h-9 rounded-full bg-[var(--surface)] border-2 border-white overflow-hidden">
        <img src={img} alt="" className="w-full h-full object-cover" />
      </div>
      <div className="flex flex-col items-center gap-0.5">
        <Heart className="w-6 h-6 text-white" strokeWidth={2} />
        <span className="text-white text-[11px] font-semibold">{likes}</span>
      </div>
      <div className="flex flex-col items-center gap-0.5">
        <MessageCircle className="w-6 h-6 text-white" strokeWidth={2} />
        <span className="text-white text-[11px] font-semibold">{comments}</span>
      </div>
      <div className="flex flex-col items-center gap-0.5">
        <Share2 className="w-6 h-6 text-white" strokeWidth={2} />
        <span className="text-white text-[11px] font-semibold">{shares}</span>
      </div>
      <div className="flex flex-col items-center gap-0.5">
        <Eye className="w-6 h-6 text-white" strokeWidth={2} />
        <span className="text-white text-[11px] font-semibold">{views}</span>
      </div>
    </div>
  );
}

/* --- Trending Card Modal ------------------------------------------ */
type VideoEntry = (typeof trendingCards)[0]["videos"][0];

function TrendingCardModal({ card, onClose }: { card: (typeof trendingCards)[0]; onClose: () => void }) {
  const [selectedVideo, setSelectedVideo] = useState<VideoEntry>(card.videos[0]);
  const [muted, setMuted] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.load();
      videoRef.current.play().catch(() => {});
    }
  }, [selectedVideo]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.18 }}
        className="fixed inset-0 z-50 flex items-end md:items-center justify-center md:p-4"
        style={{ background: "rgba(0,0,0,0.65)", backdropFilter: "blur(8px)" }}
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 48 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 48 }}
          transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          className="relative flex flex-col md:flex-row bg-[var(--surface)] w-full md:rounded-2xl overflow-hidden"
          style={{
            maxWidth: 960,
            height: "95dvh",
            maxHeight: "95dvh",
            borderRadius: "20px 20px 0 0",
            boxShadow: "0 32px 80px rgba(0,0,0,0.4)",
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="relative bg-black overflow-hidden order-1 md:order-2 md:flex-1" style={{ minHeight: "55%" }}>
            <video
              ref={videoRef}
              key={selectedVideo.videoUrl}
              src={selectedVideo.videoUrl}
              autoPlay
              loop
              playsInline
              muted={muted}
              className="absolute inset-0 w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/20 pointer-events-none" />

            <button
              onClick={onClose}
              className="absolute top-3 right-3 z-20 w-9 h-9 flex items-center justify-center rounded-full bg-black/40 text-white hover:bg-black/60 transition-colors duration-[120ms] backdrop-blur-sm"
            >
              <X className="w-4 h-4" strokeWidth={2} />
            </button>
            <button
              onClick={() => setMuted((v) => !v)}
              className="absolute top-3 left-3 z-20 w-9 h-9 flex items-center justify-center rounded-full bg-black/40 text-white hover:bg-black/60 transition-colors duration-[120ms] backdrop-blur-sm"
            >
              {muted ? <VolumeX className="w-4 h-4" strokeWidth={2} /> : <Volume2 className="w-4 h-4" strokeWidth={2} />}
            </button>

            <EngagementSidebar
              img={selectedVideo.img}
              likes={selectedVideo.likes}
              comments={selectedVideo.comments}
              shares={selectedVideo.shares}
              views={selectedVideo.views}
            />

            <div className="absolute bottom-0 inset-x-0 z-20 px-4 pb-4">
              <p className="text-white font-semibold text-sm mb-0.5">
                {selectedVideo.handle} · {selectedVideo.time}
              </p>
              <p className="text-white/85 text-xs leading-snug">{selectedVideo.caption}</p>
            </div>
          </div>

          <div
            className="order-2 md:order-1 flex flex-col md:w-[340px] md:flex-shrink-0 border-t md:border-t-0 md:border-r border-[var(--border)] bg-[var(--surface)] overflow-hidden"
            style={{ flex: "0 0 auto", maxHeight: "45%", minHeight: 0 }}
          >
            <div className="hidden md:block px-4 pt-4 pb-3 border-b border-[var(--border)]">
              <p className="font-bold text-[var(--ink)] text-sm leading-snug mb-1 line-clamp-2">{card.title}</p>
              <p className="text-[11px] text-[var(--muted)] leading-relaxed line-clamp-3">{card.description}</p>
            </div>

            <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border)] flex-shrink-0">
              <p className="text-[11px] font-bold uppercase tracking-widest text-[var(--faint)]">Videos</p>
              <div className="flex md:hidden items-center gap-3">
                <span className="flex items-center gap-1 text-[11px] text-[var(--muted)]">
                  <Heart className="w-3.5 h-3.5" strokeWidth={2} />
                  {selectedVideo.likes}
                </span>
                <span className="flex items-center gap-1 text-[11px] text-[var(--muted)]">
                  <Eye className="w-3.5 h-3.5" strokeWidth={2} />
                  {selectedVideo.views}
                </span>
              </div>
            </div>

            <div className="flex md:hidden flex-1 overflow-x-auto" style={{ scrollbarWidth: "none" }}>
              <div className="flex flex-row gap-2 px-3 py-2.5" style={{ width: "max-content" }}>
                {card.videos.map((video, idx) => {
                  const isSelected = video.handle === selectedVideo.handle && video.title === selectedVideo.title;
                  return (
                    <button
                      key={idx}
                      onClick={() => setSelectedVideo(video)}
                      className={`flex flex-col items-start gap-1 p-1.5 rounded-xl border transition-colors duration-[120ms] ${isSelected ? "border-[var(--purple)] bg-[var(--purple-light)]" : "border-[var(--border)]"}`}
                      style={{ width: 80, flexShrink: 0 }}
                    >
                      <div className="w-full rounded-lg overflow-hidden relative" style={{ height: 100 }}>
                        <img src={video.img} alt="" className="w-full h-full object-cover" />
                        {isSelected && (
                          <div className="absolute inset-0 bg-[var(--purple)]/20 flex items-center justify-center">
                            <div className="w-3 h-3 rounded-full bg-white/90" />
                          </div>
                        )}
                      </div>
                      <p
                        className={`text-[10px] font-semibold leading-snug line-clamp-2 w-full text-left ${isSelected ? "text-[var(--purple)]" : "text-[var(--ink)]"}`}
                      >
                        {video.title}
                      </p>
                      <p className="text-[10px] font-mono text-[var(--muted)]">{video.views}</p>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="hidden md:block flex-1 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
              {card.videos.map((video, idx) => {
                const isSelected = video.handle === selectedVideo.handle && video.title === selectedVideo.title;
                return (
                  <button
                    key={idx}
                    onClick={() => setSelectedVideo(video)}
                    className={`w-full flex items-start gap-2.5 px-3 py-2.5 text-left transition-colors duration-[120ms] border-b border-[var(--border)] last:border-0 ${isSelected ? "bg-[var(--purple-light)]" : "hover:bg-[var(--surface-alt)]"}`}
                  >
                    <div className="flex-shrink-0 rounded-md overflow-hidden border border-[var(--border)] relative" style={{ width: 40, height: 52 }}>
                      <img src={video.img} alt="" className="w-full h-full object-cover" />
                      {isSelected && (
                        <div className="absolute inset-0 bg-[var(--purple)]/20 flex items-center justify-center">
                          <div className="w-3 h-3 rounded-full bg-white/90" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p
                        className={`text-[12px] font-semibold leading-snug line-clamp-2 mb-0.5 ${isSelected ? "text-[var(--purple)]" : "text-[var(--ink)]"}`}
                      >
                        {video.title}
                      </p>
                      <p className="text-[11px] font-mono font-semibold text-[var(--ink)]">{video.views}</p>
                      <p className="text-[10px] text-[var(--faint)]">
                        {video.handle} · {video.time}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

/* --- Trending Card ------------------------------------------------ */
function TrendingCard({ card }: { card: (typeof trendingCards)[0] }) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      {modalOpen && <TrendingCardModal card={card} onClose={() => setModalOpen(false)} />}
      <div
        onClick={() => setModalOpen(true)}
        className="flex-shrink-0 w-[220px] flex flex-col rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden hover:border-[var(--border-active)] transition-colors duration-[150ms] cursor-pointer"
      >
        <div className="relative h-[130px] bg-[var(--surface-alt)]">
          {card.images.slice(0, 3).map((img, i) => (
            <div
              key={i}
              className="absolute rounded-lg overflow-hidden border border-[var(--border)] shadow-sm"
              style={{ width: 72, height: 96, top: 12 + i * 8, left: 16 + i * 36, zIndex: 3 - i }}
            >
              <img src={img} alt="" className="w-full h-full object-cover" />
            </div>
          ))}
        </div>
        <div className="flex flex-col gap-1.5 p-3 flex-1">
          <p className="text-xs font-semibold text-[var(--ink)] leading-snug line-clamp-2">{card.title}</p>
          <p className="text-[11px] text-[var(--muted)] leading-relaxed line-clamp-3">{card.description}</p>
          <div className="flex items-center justify-between mt-auto pt-1.5">
            <div className="flex items-center gap-1">
              {card.platforms.includes("tiktok") && <TikTokIcon size={13} />}
              {card.platforms.includes("ig") && <IGIcon size={13} />}
              {card.platforms.includes("yt") && <YTIcon size={13} />}
            </div>
            <button className="text-[11px] text-[var(--purple)] font-medium hover:underline">See more &rsaquo;</button>
          </div>
        </div>
      </div>
    </>
  );
}

/* --- Video Player Modal ------------------------------------------- */
function VideoPlayerModal({
  video,
  allVideos,
  onClose,
}: {
  video: ExploreGridVideo;
  allVideos: ExploreGridVideo[];
  onClose: () => void;
}) {
  const [selected, setSelected] = useState(video);
  const [muted, setMuted] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.load();
      videoRef.current.play().catch(() => {});
    }
  }, [selected]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.18 }}
        className="fixed inset-0 z-50 flex items-end md:items-center justify-center md:p-4"
        style={{ background: "rgba(0,0,0,0.65)", backdropFilter: "blur(8px)" }}
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 48 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 48 }}
          transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          className="relative flex flex-col md:flex-row bg-[var(--surface)] w-full md:rounded-2xl overflow-hidden"
          style={{
            maxWidth: 960,
            height: "95dvh",
            maxHeight: "95dvh",
            borderRadius: "20px 20px 0 0",
            boxShadow: "0 32px 80px rgba(0,0,0,0.4)",
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="relative bg-black overflow-hidden order-1 md:order-2 md:flex-1" style={{ minHeight: "55%" }}>
            <video
              ref={videoRef}
              key={selected.videoUrl}
              src={selected.videoUrl}
              autoPlay
              loop
              playsInline
              muted={muted}
              className="absolute inset-0 w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/20 pointer-events-none" />

            <button
              onClick={onClose}
              className="absolute top-3 right-3 z-20 w-9 h-9 flex items-center justify-center rounded-full bg-black/40 text-white hover:bg-black/60 transition-colors duration-[120ms] backdrop-blur-sm"
            >
              <X className="w-4 h-4" strokeWidth={2} />
            </button>
            <button
              onClick={() => setMuted((v) => !v)}
              className="absolute top-3 left-3 z-20 w-9 h-9 flex items-center justify-center rounded-full bg-black/40 text-white hover:bg-black/60 transition-colors duration-[120ms] backdrop-blur-sm"
            >
              {muted ? <VolumeX className="w-4 h-4" strokeWidth={2} /> : <Volume2 className="w-4 h-4" strokeWidth={2} />}
            </button>

            <EngagementSidebar
              img={selected.img}
              likes={selected.likes}
              comments={selected.comments}
              shares={selected.shares}
              views={selected.views}
            />

            <div className="absolute bottom-0 inset-x-0 z-20 px-4 pb-4">
              <p className="text-white font-semibold text-sm mb-0.5">
                {selected.handle} · {selected.time}
              </p>
              <p className="text-white/85 text-xs leading-snug">{selected.caption}</p>
            </div>
          </div>

          <div
            className="order-2 md:order-1 flex flex-col md:w-[320px] md:flex-shrink-0 border-t md:border-t-0 md:border-r border-[var(--border)] bg-[var(--surface)] overflow-hidden"
            style={{ flex: "0 0 auto", maxHeight: "45%", minHeight: 0 }}
          >
            <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border)] flex-shrink-0">
              <p className="text-[11px] font-bold uppercase tracking-widest text-[var(--faint)]">Kham pha video</p>
              <div className="flex md:hidden items-center gap-3">
                <span className="flex items-center gap-1 text-[11px] text-[var(--muted)]">
                  <Heart className="w-3.5 h-3.5" strokeWidth={2} />
                  {selected.likes}
                </span>
                <span className="flex items-center gap-1 text-[11px] text-[var(--muted)]">
                  <Eye className="w-3.5 h-3.5" strokeWidth={2} />
                  {selected.views}
                </span>
              </div>
            </div>

            <div className="flex md:hidden flex-1 overflow-x-auto" style={{ scrollbarWidth: "none" }}>
              <div className="flex flex-row gap-2 px-3 py-2.5" style={{ width: "max-content" }}>
                {allVideos.map((v) => {
                  const isSel = v.id === selected.id;
                  return (
                    <button
                      key={v.id}
                      onClick={() => setSelected(v)}
                      className={`flex flex-col items-start gap-1 p-1.5 rounded-xl border transition-colors duration-[120ms] ${isSel ? "border-[var(--purple)] bg-[var(--purple-light)]" : "border-[var(--border)]"}`}
                      style={{ width: 80, flexShrink: 0 }}
                    >
                      <div className="w-full rounded-lg overflow-hidden relative" style={{ height: 100 }}>
                        <img src={v.img} alt="" className="w-full h-full object-cover" />
                        {isSel && (
                          <div className="absolute inset-0 bg-[var(--purple)]/20 flex items-center justify-center">
                            <div className="w-3 h-3 rounded-full bg-white/90" />
                          </div>
                        )}
                      </div>
                      {v.text && (
                        <p
                          className={`text-[10px] font-semibold leading-snug line-clamp-2 w-full text-left ${isSel ? "text-[var(--purple)]" : "text-[var(--ink)]"}`}
                        >
                          {v.text}
                        </p>
                      )}
                      <p className="text-[10px] font-mono text-[var(--muted)]">{v.views}</p>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="hidden md:block flex-1 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
              {allVideos.map((v) => {
                const isSel = v.id === selected.id;
                return (
                  <button
                    key={v.id}
                    onClick={() => setSelected(v)}
                    className={`w-full flex items-start gap-2.5 px-3 py-2.5 text-left transition-colors duration-[120ms] border-b border-[var(--border)] last:border-0 ${isSel ? "bg-[var(--purple-light)]" : "hover:bg-[var(--surface-alt)]"}`}
                  >
                    <div className="flex-shrink-0 rounded-md overflow-hidden border border-[var(--border)] relative" style={{ width: 36, height: 50 }}>
                      <img src={v.img} alt="" className="w-full h-full object-cover" />
                      {isSel && (
                        <div className="absolute inset-0 bg-[var(--purple)]/25 flex items-center justify-center">
                          <div className="w-2.5 h-2.5 rounded-full bg-white/90" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      {v.text && (
                        <p
                          className={`text-[11px] font-semibold leading-snug line-clamp-2 mb-0.5 ${isSel ? "text-[var(--purple)]" : "text-[var(--ink)]"}`}
                        >
                          {v.text}
                        </p>
                      )}
                      <p
                        className={`text-[11px] ${v.text ? "text-[var(--faint)]" : isSel ? "text-[var(--purple)] font-semibold" : "text-[var(--ink)] font-semibold"} leading-snug line-clamp-1`}
                      >
                        {v.handle}
                      </p>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[11px] font-mono font-semibold text-[var(--ink)]">{v.views}</span>
                        <span className="text-[10px] text-[var(--faint)]">{v.time}</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

/* --- Video Thumbnail Card ----------------------------------------- */
function VideoCard({
  video,
  allVideos,
  onNavigate,
}: {
  video: ExploreGridVideo;
  allVideos: ExploreGridVideo[];
  onNavigate?: () => void;
}) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      {modalOpen && <VideoPlayerModal video={video} allVideos={allVideos} onClose={() => setModalOpen(false)} />}
      <div
        onClick={() => setModalOpen(true)}
        className="relative rounded-xl overflow-hidden bg-[var(--surface-alt)] border border-[var(--border)] cursor-pointer hover:border-[var(--border-active)] transition-colors duration-[120ms]"
        style={{ aspectRatio: "9/14" }}
      >
        <img src={video.img} alt="" className="w-full h-full object-cover" />
        {video.text && (
          <div className="absolute top-2 left-2 right-2">
            <p className="text-white text-[11px] font-semibold drop-shadow leading-snug line-clamp-2">{video.text}</p>
          </div>
        )}
        <div className="absolute bottom-0 inset-x-0 px-2 py-2 bg-gradient-to-t from-black/80 to-transparent flex flex-col gap-1.5">
          <div className="flex items-end justify-between w-full">
            <span className="text-white text-[11px] font-semibold">{video.views} views</span>
            <span className="text-white/70 text-[10px]">{video.time}</span>
          </div>
          {onNavigate ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onNavigate();
              }}
              className="w-full min-h-[36px] rounded-md bg-white/20 py-1.5 text-center text-[10px] font-semibold text-white backdrop-blur-sm"
            >
              Phân tích video này
            </button>
          ) : null}
        </div>
      </div>
    </>
  );
}

/* --- Sidebar Video Row -------------------------------------------- */
function SidebarVideoRow({
  item,
  rank,
}: {
  item: { title: string; views: string; handle: string; time: string; img: string };
  rank?: number;
}) {
  return (
    <div className="flex items-start gap-2.5 py-2.5 border-b border-[var(--border)] last:border-0 cursor-pointer group">
      {rank !== undefined && (
        <span className="text-xs font-mono text-[var(--faint)] w-4 flex-shrink-0 pt-0.5 text-right">{rank}</span>
      )}
      <div className="w-9 h-12 flex-shrink-0 rounded-md overflow-hidden bg-[var(--surface-alt)] border border-[var(--border)]">
        <img src={item.img} alt="" className="w-full h-full object-cover" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[12px] font-semibold text-[var(--ink)] leading-snug line-clamp-2 group-hover:text-[var(--purple)] transition-colors duration-[120ms]">
          {item.title}
        </p>
        <div className="flex items-center gap-1.5 mt-0.5">
          <span className="text-[11px] font-mono font-semibold text-[var(--ink)]">{item.views}</span>
          <span className="text-[10px] text-[var(--muted)]">{item.handle}</span>
        </div>
        <span className="text-[10px] text-[var(--faint)]">{item.time}</span>
      </div>
    </div>
  );
}

/* --- Filter Chip -------------------------------------------------- */
function FilterChip({
  label,
  active = false,
  onRemove,
  hasArrow = false,
}: {
  label: string;
  active?: boolean;
  onRemove?: () => void;
  hasArrow?: boolean;
}) {
  return (
    <button
      className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs border transition-all duration-[120ms] whitespace-nowrap ${
        active
          ? "border-[var(--ink)] text-[var(--ink)] bg-[var(--surface)]"
          : "border-[var(--border)] text-[var(--muted)] bg-[var(--surface)] hover:border-[var(--border-active)] hover:text-[var(--ink)]"
      }`}
    >
      {label === "App" && (
        <span className="flex items-center mr-0.5">
          <TikTokIcon size={11} />
        </span>
      )}
      <span>{label}</span>
      {onRemove ? (
        <X
          className="w-3 h-3 opacity-60"
          strokeWidth={2}
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
        />
      ) : hasArrow ? (
        <ChevronDown className="w-3 h-3 opacity-60" strokeWidth={2} />
      ) : null}
    </button>
  );
}

function ExploreGridSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5">
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className="rounded-xl overflow-hidden border border-[var(--border)] bg-[var(--surface-alt)] animate-pulse"
          style={{ aspectRatio: "9/14" }}
        />
      ))}
    </div>
  );
}

/* --- ExploreScreen (Make TrendScreen + corpus) -------------------- */
export default function ExploreScreen() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [activeViewFilter, setActiveViewFilter] = useState("100K+");
  const loaderRef = useRef<HTMLDivElement>(null);

  const { data, isPending, isError, refetch, hasNextPage, isFetchingNextPage, fetchNextPage } = useVideoCorpus({});

  const corpusRows = useMemo(() => (data?.pages ?? []).flat() as CorpusRow[], [data?.pages]);
  const videos = useMemo(() => corpusRows.map(corpusRowToExploreVideo), [corpusRows]);

  const exploreTitle = isPending
    ? "Khám phá video"
    : `Khám phá ${videos.length}${hasNextPage ? "+" : ""} video`;

  const fetchNextPageStable = useCallback(() => {
    void fetchNextPage();
  }, [fetchNextPage]);

  useEffect(() => {
    const el = loaderRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPageStable();
        }
      },
      { threshold: 0.1 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPageStable, isPending, isError]);

  return (
    <AppLayout active="trends" enableMobileSidebar>
      <div className="flex-1 overflow-hidden flex min-h-0">
        <div className="flex-1 overflow-y-auto min-w-0" style={{ scrollbarWidth: "thin" }}>
          <section className="px-5 lg:px-7 pt-14 lg:pt-6 pb-4">
            <button type="button" className="flex items-center gap-1 mb-4 group">
              <h2 className="font-extrabold text-[var(--ink)] group-hover:text-[var(--purple)] transition-colors duration-[120ms]">Xu huong tuan nay</h2>
              <ChevronRight
                className="w-4 h-4 text-[var(--ink)] group-hover:text-[var(--purple)] transition-colors duration-[120ms]"
                strokeWidth={2.5}
              />
            </button>
            <div className="overflow-x-auto -mx-5 lg:-mx-7 px-5 lg:px-7" style={{ scrollbarWidth: "none" }}>
              <div className="flex gap-3 pb-2" style={{ width: "max-content" }}>
                {trendingCards.map((card) => (
                  <TrendingCard key={card.id} card={card} />
                ))}
              </div>
            </div>
          </section>

          <section className="px-5 lg:px-7 pb-8">
            <button type="button" className="flex items-center gap-1 mb-4 group">
              <h2 className="font-extrabold text-[var(--ink)] group-hover:text-[var(--purple)] transition-colors duration-[120ms]">{exploreTitle}</h2>
              <ChevronRight
                className="w-4 h-4 text-[var(--ink)] group-hover:text-[var(--purple)] transition-colors duration-[120ms]"
                strokeWidth={2.5}
              />
            </button>

            <div className="flex items-center gap-2 mb-4 flex-wrap">
              <div className="flex-1 min-w-[200px] flex items-center gap-2 px-3 py-2 rounded-full border border-[var(--border)] bg-[var(--surface)] hover:border-[var(--border-active)] transition-colors duration-[120ms]">
                <Search className="w-3.5 h-3.5 text-[var(--faint)] flex-shrink-0" strokeWidth={1.8} />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="flex-1 text-xs bg-transparent border-none outline-none text-[var(--ink)] placeholder:text-[var(--faint)]"
                  placeholder="Tim video..."
                />
              </div>
              <FilterChip label="Nen tang" hasArrow />
              <FilterChip label="Sap xep" hasArrow />
              <FilterChip label="Ngay" hasArrow />
              <FilterChip label={activeViewFilter} active onRemove={() => setActiveViewFilter("")} />
              <FilterChip label="The loai" hasArrow />
            </div>

            {isPending ? <ExploreGridSkeleton /> : null}

            {isError ? (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 text-center">
                <p className="mb-4 text-sm text-[var(--ink)]">Không thể tải video — thử lại</p>
                <button
                  type="button"
                  onClick={() => void refetch()}
                  className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-xs font-semibold text-[var(--ink)] hover:border-[var(--border-active)] transition-colors duration-[120ms]"
                >
                  Thử lại
                </button>
              </div>
            ) : null}

            {!isPending && !isError && videos.length === 0 ? (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-8 text-center">
                <p className="text-sm text-[var(--ink-soft)]">Chưa có video trong khoảng này — thử lại sau.</p>
              </div>
            ) : null}

            {!isPending && !isError && videos.length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5">
                {videos.map((video, idx) => (
                  <motion.div
                    key={video.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.18, delay: idx * 0.04, ease: "easeOut" }}
                  >
                    <VideoCard
                      video={video}
                      allVideos={videos}
                      onNavigate={() =>
                        navigate("/app", {
                          state: video.tiktok_url ? { prefillUrl: video.tiktok_url } : undefined,
                        })
                      }
                    />
                  </motion.div>
                ))}
              </div>
            ) : null}

            {!isPending && !isError ? (
              <div ref={loaderRef} className="flex min-h-[48px] items-center justify-center py-4" aria-hidden>
                {isFetchingNextPage ? <Loader2 className="h-6 w-6 animate-spin text-[var(--purple)]" /> : null}
              </div>
            ) : null}
          </section>
        </div>

        <aside
          className="hidden lg:flex flex-col w-[290px] flex-shrink-0 border-l border-[var(--border)] bg-[var(--surface)] overflow-y-auto"
          style={{ scrollbarWidth: "thin" }}
        >
          <div className="px-4 pt-5 pb-3 border-b border-[var(--border)]">
            <button type="button" className="flex items-center gap-1 group">
              <h2 className="font-extrabold text-[var(--ink)] group-hover:text-[var(--purple)] transition-colors duration-[120ms]">Video nen xem</h2>
              <ChevronRight
                className="w-4 h-4 text-[var(--ink)] group-hover:text-[var(--purple)] transition-colors duration-[120ms]"
                strokeWidth={2.5}
              />
            </button>
            <p className="text-xs text-[var(--faint)] mt-0.5">Cap nhat 2 gio truoc</p>
          </div>

          <div className="flex-1 px-4 pb-6">
            <div className="mt-4 mb-1">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-2 h-2 rounded-full bg-orange-500 flex-shrink-0" />
                <span className="text-xs font-bold text-[var(--ink)]">Breakout tuan nay</span>
              </div>
            </div>
            <div>
              {breakoutHits.map((item) => (
                <SidebarVideoRow key={item.rank} item={item} rank={item.rank} />
              ))}
            </div>

            <div className="mt-5 mb-1">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-2 h-2 rounded-full bg-orange-500 flex-shrink-0" />
                <span className="text-xs font-bold text-[var(--ink)]">Dang viral</span>
              </div>
            </div>
            <div>
              {viralNow.map((item, idx) => (
                <SidebarVideoRow key={`${item.title}-${idx}`} item={item} />
              ))}
            </div>
          </div>
        </aside>
      </div>
    </AppLayout>
  );
}
