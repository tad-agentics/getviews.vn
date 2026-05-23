import { memo } from "react";
import { useNavigate } from "react-router";

import { Btn } from "@/components/v2/Btn";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

/**
 * Blocks Kho Douyin until the pipeline ships: no overlay dismiss, no Esc, no X.
 * Users leave only via in-app navigation (browser back also works).
 */
export const DouyinComingSoonModal = memo(function DouyinComingSoonModal() {
  const navigate = useNavigate();

  return (
    <Dialog open={true} onOpenChange={() => {}} modal>
      <DialogContent
        showCloseButton={false}
        className="max-w-md gap-5 border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] sm:max-w-md"
        onPointerDownOutside={(e) => e.preventDefault()}
        onInteractOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
      >
        <DialogHeader className="text-left">
          <p className="gv-mono mb-1 text-[11px] font-semibold gv-kicker tracking-[0.06em] text-[color:var(--gv-accent-deep)]">
            Tham chiếu
          </p>
          <DialogTitle className="gv-tight text-xl font-medium text-[color:var(--gv-ink)]">
            Kho Douyin — sắp ra mắt
          </DialogTitle>
          <DialogDescription className="text-[14px] leading-relaxed text-[color:var(--gv-ink-2)]">
            GetViews đang hoàn thiện pipeline nhập và làm tươi kho video Douyin (đàm
            thoại CTA, sub tiếng Việt, tín hiệu mẫu). Khu vực này tạm chưa mở —
            bạn có thể dùng{" "}
            <span className="font-medium text-[color:var(--gv-ink)]">Xu hướng</span>{" "}
            để xem format và ngách TikTok Việt trong lúc chờ.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
          <Btn
            variant="ink"
            size="md"
            type="button"
            className="w-full sm:w-auto sm:flex-1"
            onClick={() => void navigate("/app/trends")}
          >
            Về Xu hướng
          </Btn>
          <Btn
            variant="ghost"
            size="md"
            type="button"
            className="w-full sm:w-auto"
            onClick={() => void navigate("/app")}
          >
            Về Trang chủ
          </Btn>
        </div>
      </DialogContent>
    </Dialog>
  );
});
