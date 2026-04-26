import { useNavigate } from "react-router";
import { ArrowLeft, Archive } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Btn } from "@/components/v2/Btn";
import { TopBar } from "@/components/v2/TopBar";

/**
 * Kho Douyin — placeholder screen (PR-T5).
 *
 * The TrendsDouyinCard on /app/trends links here. The full Douyin
 * surface (TQ pattern catalog with VN-subbed translations,
 * adaptability scoring, ETA timelines, translator notes) is a
 * separate wave; this screen ships now as the structural endpoint
 * so the link card on Trends has a real destination instead of a
 * 404. Replace this body when the Douyin pipeline + content land.
 */

export default function DouyinScreen() {
  const navigate = useNavigate();
  return (
    <AppLayout active="trends" enableMobileSidebar>
      <div className="min-h-full w-full bg-[color:var(--gv-canvas)] text-[color:var(--gv-ink)]">
        <TopBar
          kicker="THAM CHIẾU"
          title="Kho Douyin"
          right={
            <Btn variant="ghost" size="sm" type="button" onClick={() => navigate("/app/trends")}>
              <ArrowLeft className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
              Về Xu hướng
            </Btn>
          }
        />
        <main className="mx-auto w-full max-w-[760px] px-5 py-12 sm:px-7">
          <div
            className="rounded-[14px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-6 py-10 text-center sm:px-10 sm:py-14"
          >
            <div
              className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-[color:var(--gv-ink)] text-[color:var(--gv-accent)]"
              aria-hidden
            >
              <Archive className="h-5 w-5" strokeWidth={1.7} />
            </div>
            <p className="gv-mono mb-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-[color:var(--gv-accent-deep)]">
              <span aria-hidden>🇨🇳</span> TÍN HIỆU SỚM · DOUYIN → VN
            </p>
            <h1 className="gv-tight m-0 mb-3 text-[clamp(24px,3vw,32px)] font-semibold leading-[1.1] tracking-[-0.02em] text-[color:var(--gv-ink)]">
              Kho Douyin đang chuẩn bị
            </h1>
            <p
              className="m-0 mx-auto max-w-[480px] text-[14px] leading-[1.6] text-[color:var(--gv-ink-3)]"
              style={{ textWrap: "pretty" }}
            >
              Pattern Trung Quốc đã được dịch + chú thích văn hoá sẽ hiện ở đây trong bản ra mắt
              kế tiếp. Bạn sẽ thấy: video đã sub VN, mức độ hoá VN, ETA về VN, và ghi chú từ
              dịch giả.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              <Btn variant="ink" size="sm" type="button" onClick={() => navigate("/app/trends")}>
                Quay lại Xu hướng
              </Btn>
              <Btn variant="ghost" size="sm" type="button" onClick={() => navigate("/app")}>
                Về Studio
              </Btn>
            </div>
          </div>
        </main>
      </div>
    </AppLayout>
  );
}
