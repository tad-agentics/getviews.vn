import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { X } from "lucide-react";

interface ModalConfig {
  title: string;
  fields: {
    label: string;
    placeholder: string;
    type: "input" | "textarea";
    key: string;
    optional?: boolean;
  }[];
  buildPrompt: (values: Record<string, string>) => string;
}

const MODAL_CONFIGS: Record<string, ModalConfig> = {
  "soi-video": {
    title: "Soi Video",
    fields: [
      {
        label: "Dán link TikTok video",
        placeholder: "https://vm.tiktok.com/... hoặc https://www.tiktok.com/@user/video/...",
        type: "input",
        key: "url",
      },
    ],
    buildPrompt: (v) =>
      `Phân tích video TikTok này, chỉ ra hook, điểm mạnh, điểm yếu, và cách cải thiện: ${v.url}`,
  },
  "soi-kenh": {
    title: "Soi Kênh Đối Thủ",
    fields: [
      {
        label: "@handle hoặc link trang TikTok",
        placeholder: "@username hoặc https://www.tiktok.com/@username",
        type: "input",
        key: "handle",
      },
    ],
    buildPrompt: (v) => {
      const h = v.handle.trim();
      const handle = h.startsWith("http") ? h : h.startsWith("@") ? h : `@${h}`;
      return `Soi kênh đối thủ ${handle} — phân tích công thức content, hook, format của họ`;
    },
  },
  "xu-huong": {
    title: "Xu Hướng Tuần Này",
    fields: [
      {
        label: "Lĩnh vực / ngách (tùy chọn)",
        placeholder: "VD: skincare, fitness, AI tools — hoặc để trống dùng ngách mặc định",
        type: "input",
        key: "niche",
        optional: true,
      },
    ],
    buildPrompt: (v) => {
      const niche = v.niche.trim();
      return niche
        ? `Xu hướng TikTok đang hot tuần này trong lĩnh vực ${niche} — hook nào đang chạy, format nào đang lên?`
        : "Xu hướng TikTok đang hot tuần này — hook nào đang chạy, format nào đang lên?";
    },
  },
  "kich-ban": {
    title: "Lên Kịch Bản Quay",
    fields: [
      {
        label: "Chủ đề video",
        placeholder: "VD: review son mới, so sánh điện thoại, recipe nấu ăn nhanh",
        type: "input",
        key: "topic",
      },
    ],
    buildPrompt: (v) =>
      `Lên kịch bản quay video TikTok cho chủ đề: ${v.topic} — bao gồm hook, danh sách cảnh quay, CTA`,
  },
  "tim-kol": {
    title: "Tìm KOL / Creator",
    fields: [
      {
        label: "Mô tả sản phẩm hoặc lĩnh vực",
        placeholder: "VD: ứng dụng fitness AI, mỹ phẩm Hàn Quốc, đồ gia dụng thông minh",
        type: "input",
        key: "product",
      },
    ],
    buildPrompt: (v) =>
      `Tìm creator TikTok phù hợp để marketing sản phẩm: ${v.product} — gợi ý KOL và lý do`,
  },
  "tu-van": {
    title: "Tư Vấn Content",
    fields: [
      {
        label: "Bạn đang làm content về gì?",
        placeholder: "VD: review đồ skincare, chia sẻ kinh nghiệm đầu tư, dạy nấu ăn",
        type: "input",
        key: "niche",
      },
    ],
    buildPrompt: (v) =>
      `Hướng nội dung TikTok cho ngách ${v.niche} — nên làm video gì, format nào đang hiệu quả, hook mẫu`,
  },
  // Legacy keys for backward compatibility
  marketing: {
    title: "Chiến lược Marketing",
    fields: [
      { label: "Tên sản phẩm của bạn là gì?", placeholder: "VD: FitTrack", type: "input", key: "product" },
      { label: "Mô tả sản phẩm", placeholder: "VD: Ứng dụng fitness AI", type: "textarea", key: "description" },
    ],
    buildPrompt: (v) => `Tư vấn chiến lược marketing TikTok cho sản phẩm "${v.product}": ${v.description}`,
  },
  "tiktok-page": {
    title: "Phân tích trang TikTok",
    fields: [
      { label: "TikTok profile URL", placeholder: "https://www.tiktok.com/@username", type: "input", key: "url" },
    ],
    buildPrompt: (v) => `Soi kênh đối thủ ${v.url} — phân tích công thức content của họ`,
  },
  trends: {
    title: "Tìm xu hướng mới nhất",
    fields: [
      { label: "Xu hướng trong lĩnh vực nào?", placeholder: "VD: fitness, skincare", type: "input", key: "niche" },
    ],
    buildPrompt: (v) => `Xu hướng TikTok đang hot tuần này trong lĩnh vực: ${v.niche}`,
  },
  video: {
    title: "Chẩn đoán video",
    fields: [
      { label: "TikTok video URL", placeholder: "https://www.tiktok.com/@username/video/...", type: "input", key: "url" },
    ],
    buildPrompt: (v) => `Phân tích video TikTok này: ${v.url}`,
  },
};

export function QuickActionModal({
  modalKey,
  onClose,
  onContinue,
}: {
  modalKey: string;
  onClose: () => void;
  onContinue: (prompt: string) => void;
}) {
  const config = MODAL_CONFIGS[modalKey];
  const [values, setValues] = useState<Record<string, string>>(
    () => Object.fromEntries((config?.fields ?? []).map((f) => [f.key, ""])),
  );

  if (!config) return null;

  const allFilled = config.fields.every((f) => f.optional || values[f.key]?.trim());

  const handleContinue = () => {
    if (!allFilled) return;
    onContinue(config.buildPrompt(values));
  };

  return (
    <AnimatePresence>
      <motion.div
        key="backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        style={{ background: "rgba(0,0,0,0.45)", backdropFilter: "blur(4px)" }}
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
      >
        <motion.div
          key="modal"
          initial={{ opacity: 0, scale: 0.95, y: 8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 8 }}
          transition={{ duration: 0.18, ease: "easeOut" }}
          className="relative flex w-full max-w-[420px] flex-col gap-5 rounded-2xl p-6"
          style={{
            background: "var(--surface)",
            boxShadow: "0 24px 64px rgba(0,0,0,0.18)",
          }}
        >
          <button
            type="button"
            onClick={onClose}
            className="absolute right-4 top-4 flex h-8 w-8 items-center justify-center rounded-full text-[var(--muted)] transition-colors duration-[120ms] hover:bg-[var(--surface-alt)] hover:text-[var(--ink)]"
          >
            <X className="h-4 w-4" strokeWidth={2} />
          </button>

          <h2 className="pr-8 text-[var(--ink)]" style={{ fontSize: "1.35rem", fontWeight: 800, lineHeight: 1.2 }}>
            {config.title}
          </h2>

          <div className="flex flex-col gap-4">
            {config.fields.map((field) => (
              <div key={field.key} className="flex flex-col gap-1.5">
                <label className="text-sm font-semibold text-[var(--ink)]">{field.label}</label>
                {field.type === "input" ? (
                  <input
                    type="text"
                    placeholder={field.placeholder}
                    value={values[field.key]}
                    onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleContinue();
                    }}
                    className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-4 py-3 text-sm text-[var(--ink)] transition-all duration-[120ms] placeholder:text-[var(--faint)] focus:border-[var(--purple)] focus:outline-none focus:ring-1 focus:ring-[var(--purple)]"
                    autoFocus={field.key === config.fields[0].key}
                  />
                ) : (
                  <textarea
                    placeholder={field.placeholder}
                    value={values[field.key]}
                    onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
                    rows={3}
                    className="w-full resize-none rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-4 py-3 text-sm text-[var(--ink)] transition-all duration-[120ms] placeholder:text-[var(--faint)] focus:border-[var(--purple)] focus:outline-none focus:ring-1 focus:ring-[var(--purple)]"
                  />
                )}
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={handleContinue}
            disabled={!allFilled}
            className="h-12 w-full rounded-xl text-sm font-semibold text-white transition-all duration-[120ms] active:scale-[0.98]"
            style={{
              background: allFilled ? "var(--gradient-primary)" : "var(--faint)",
              cursor: allFilled ? "pointer" : "not-allowed",
            }}
          >
            Tiếp tục
          </button>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
