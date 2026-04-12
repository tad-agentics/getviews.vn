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
  }[];
  buildPrompt: (values: Record<string, string>) => string;
}

const MODAL_CONFIGS: Record<string, ModalConfig> = {
  marketing: {
    title: "Chiến lược Marketing",
    fields: [
      { label: "Tên sản phẩm của bạn là gì?", placeholder: "VD: FitTrack", type: "input", key: "product" },
      {
        label: "Mô tả sản phẩm",
        placeholder: "VD: Ứng dụng fitness AI tạo kế hoạch tập luyện cá nhân hóa",
        type: "textarea",
        key: "description",
      },
    ],
    buildPrompt: (v) => `Tư vấn chiến lược marketing TikTok cho sản phẩm "${v.product}": ${v.description}`,
  },
  "tiktok-page": {
    title: "Phân tích trang TikTok",
    fields: [
      { label: "TikTok profile URL", placeholder: "https://www.tiktok.com/@username", type: "input", key: "url" },
    ],
    buildPrompt: (v) => `Phân tích trang TikTok: ${v.url}`,
  },
  trends: {
    title: "Tìm xu hướng mới nhất",
    fields: [
      { label: "Xu hướng trong lĩnh vực nào?", placeholder: "VD: fitness, skincare, AI tools", type: "input", key: "niche" },
    ],
    buildPrompt: (v) => `Tìm xu hướng TikTok mới nhất trong lĩnh vực: ${v.niche}`,
  },
  video: {
    title: "Chẩn đoán video",
    fields: [
      { label: "TikTok video URL", placeholder: "https://www.tiktok.com/@username/video/...", type: "input", key: "url" },
    ],
    buildPrompt: (v) => `Chẩn đoán video TikTok: ${v.url}`,
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
    () => Object.fromEntries(config.fields.map((f) => [f.key, ""])),
  );

  if (!config) return null;

  const allFilled = config.fields.every((f) => values[f.key]?.trim());

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
