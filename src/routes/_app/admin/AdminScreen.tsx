/**
 * /app/admin operator dashboard.
 *
 * Editorial layout mirrors `artifacts/uiux-reference/screens/home.jsx`:
 * sticky TopBar, 1320px main wrap, SectionHeader with kicker dot + tight
 * 28px title for each panel, `<hr>` rules between sections, and
 * `gv-fade-up` staggered entries. Each panel handles its own data + visual
 * density; this file is purely the routing + section rhythm.
 *
 * Scope is deliberately tight — four sections answer the only questions an
 * operator acts on: is the pipeline growing the corpus (Corpus health), are
 * we under the cost ceiling (EnsembleData), what's broken right now (Logs),
 * and a manual re-kick when a nightly cron fails (Triggers). Product/growth
 * funnels and one-off backfills were removed; backfills live in the CLI.
 *
 * Gate: the SPA checks `useIsAdmin()` and bounces non-admins to /app.
 * The server-side `require_admin` dep on every /admin/* endpoint is the
 * authoritative boundary — this screen only decides what the SPA
 * bothers to render.
 */
import { useEffect } from "react";
import { useNavigate } from "react-router";
import { AppLayout } from "@/components/AppLayout";
import { SectionHeader } from "@/components/v2/SectionHeader";
import { TopBar } from "@/components/v2/TopBar";
import { useIsAdmin } from "@/hooks/useIsAdmin";
import { CorpusHealthPanel } from "./CorpusHealthPanel";
import { CorpusClassHealthPanel } from "./CorpusClassHealthPanel";
import { Hi13BatchHealthPanel } from "./Hi13BatchHealthPanel";
import { EnsembleCreditsPanel } from "./EnsembleCreditsPanel";
import { LogsPanel } from "./LogsPanel";
import { TriggersPanel } from "./TriggersPanel";

export default function AdminScreen() {
  const { isAdmin, isLoading } = useIsAdmin();
  const navigate = useNavigate();

  useEffect(() => {
    // Bounce non-admins to Studio. The server's require_admin dep will
    // also 403 any /admin/* fetch; routing away keeps the URL honest and
    // prevents flashes of panel chrome before the first query fails.
    if (!isLoading && !isAdmin) navigate("/app", { replace: true });
  }, [isAdmin, isLoading, navigate]);

  if (isLoading) {
    return (
      <AppLayout active="admin" enableMobileSidebar>
        <div
          role="status"
          aria-label="Đang tải"
          className="min-h-[40vh] flex-1 animate-pulse rounded-[var(--gv-radius-lg)] bg-[color:var(--gv-canvas-2)]"
        />
      </AppLayout>
    );
  }
  if (!isAdmin) {
    // Keep the redirect-effect tick quiet — render the empty shell so the
    // layout doesn't reflow between "loading" and "bounce".
    return <AppLayout active="admin" enableMobileSidebar>{null}</AppLayout>;
  }

  return (
    <AppLayout active="admin" enableMobileSidebar>
      <div className="min-h-full w-full bg-[color:var(--gv-canvas)] text-[color:var(--gv-ink)]">
        <TopBar kicker="ADMIN · OPS CONSOLE" title="Sức khỏe hệ thống" />

        <main className="gv-home-wrap mx-auto w-full max-w-[1320px]">
          <section className="gv-fade-up">
            <SectionHeader
              kicker="CORPUS · TAXONOMY + CLAIM TIERS"
              title="Sức khỏe thư viện nội dung (Corpus)"
              caption="Theo từng mảng nội dung (niche_taxonomy). Số lượng video mới trong 7/30/90 ngày, phân hạng dữ liệu (claim tier) và số lượng lỗi tải ảnh thu nhỏ (thumbnail) trong 7 ngày qua — phản ánh nhịp hoạt động của quy trình chạy đêm (nightly pipeline)."
            />
            <CorpusHealthPanel />
          </section>

          <hr className="my-9 border-0 border-t border-[color:var(--gv-rule)]" />

          <section className="gv-fade-up gv-fade-up-delay-1">
            <SectionHeader
              kicker="CORPUS · CONTENT CLASS + JUNCTION"
              title="Sức khỏe phân loại nội dung (Content Class)"
              caption="Theo từng nhóm phân loại nội dung (content_class - trục xoay pivot). Số lượng video trong 7/30/90 ngày, mức độ khả thi ACQE, biểu đồ phân hạng và tỷ lệ bỏ lỡ liên kết (junction miss giữa mảng nội dung và phân loại)."
            />
            <CorpusClassHealthPanel />
          </section>

          <hr className="my-9 border-0 border-t border-[color:var(--gv-rule)]" />

          <section className="gv-fade-up gv-fade-up-delay-2">
            <SectionHeader
              kicker="CORPUS · HI-13 BATCH API"
              title="Trích xuất dữ liệu Gemini Batch"
              caption="Theo dõi tiến trình thu thập dữ liệu hàng đêm qua Batch API: tỷ lệ thành công/thất bại, cơ chế đồng bộ dự phòng (sync fallback), tối ưu chi phí (~50%) và lịch sử các đợt chạy thử nghiệm gần nhất."
            />
            <Hi13BatchHealthPanel />
          </section>

          <hr className="my-9 border-0 border-t border-[color:var(--gv-rule)]" />

          <section className="gv-fade-up gv-fade-up-delay-3">
            <SectionHeader
              kicker="ENSEMBLEDATA · USED UNITS"
              title="Hạn mức API EnsembleData"
              caption="Số lượt (Units) đã dùng theo ngày (giờ UTC) và dự báo trong 30 ngày — kiểm soát để không vượt trần ngân sách ~$80–90/tháng."
            />
            <EnsembleCreditsPanel />
          </section>

          <hr className="my-9 border-0 border-t border-[color:var(--gv-rule)]" />

          <section className="gv-fade-up gv-fade-up-delay-4">
            <SectionHeader
              kicker="CLOUD RUN · STDOUT TAIL"
              title="Nhật ký hệ thống (Logs)"
              caption="Lọc theo mức độ nghiêm trọng (severity) và khoảng thời gian; nhấp chọn để xem chi tiết thông tin lỗi (payload)."
              kickerTone="muted"
            />
            <LogsPanel />
          </section>

          <hr className="my-9 border-0 border-t border-[color:var(--gv-rule)]" />

          <section className="gv-fade-up gv-fade-up-delay-5">
            <SectionHeader
              kicker="MANUAL RUN · NIGHTLY PIPELINE"
              title="Kích hoạt thủ công"
              caption="Chạy lại các bước trong quy trình hàng đêm khi cron gặp lỗi: thu thập (ingest) · xử lý hậu kỳ (post-processing) · làm mới dữ liệu (refresh) · đồng bộ layer 0. Cần xác nhận trước khi khởi chạy mỗi tác vụ."
            />
            <TriggersPanel />
          </section>
        </main>
      </div>
    </AppLayout>
  );
}
