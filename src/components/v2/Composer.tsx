import { forwardRef, useRef, type KeyboardEvent, type TextareaHTMLAttributes } from "react";
import { ArrowUp } from "lucide-react";
import { Btn } from "./Btn";

/**
 * Neo-brutalist composer card — 2px ink border, 6px hard offset shadow,
 * pink "Gửi" submit button. Used on Home as the launcher into the research
 * session; also on FollowUpComposer in the answer screen (A3.3+).
 *
 * `layout="studio"` matches the UIUX ref: border between textarea and toolbar,
 * chips on the left, mic + Gửi (with arrow) on the right.
 *
 * Uncontrolled by default (internal ref-based read on submit) so the caller
 * doesn't need to store a message state just to render the button. Pass
 * `value` + `onChange` if you do need to control it externally.
 */
export type ComposerProps = {
  placeholder?: string;
  submitLabel?: string;
  onSubmit: (text: string) => void;
  disabled?: boolean;
  leftChips?: React.ReactNode;
  /** UIUX Home: bordered footer row, submit + arrow grouped on the right. */
  layout?: "default" | "studio";
  /** Shown before submit on the right in studio layout (e.g. mic). */
  toolbarEnd?: React.ReactNode;
} & Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "onSubmit">;

export const Composer = forwardRef<HTMLTextAreaElement, ComposerProps>(function Composer(
  {
    placeholder = "Hỏi mình bất kỳ điều gì về ngách của bạn…",
    submitLabel = "Gửi",
    onSubmit,
    disabled,
    leftChips,
    layout = "default",
    toolbarEnd,
    className,
    value,
    onChange,
    ...rest
  },
  ref,
) {
  const internalRef = useRef<HTMLTextAreaElement | null>(null);
  const resolved = (ref as React.RefObject<HTMLTextAreaElement>) ?? internalRef;

  const handleSubmit = () => {
    const text = (resolved.current?.value ?? "").trim();
    if (!text) return;
    onSubmit(text);
    if (value === undefined && resolved.current) {
      resolved.current.value = "";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const submitBtn = (
    <Btn
      type="button"
      variant="accent"
      size="md"
      onClick={handleSubmit}
      disabled={disabled}
    >
      <span>{submitLabel}</span>
      {layout === "studio" ? (
        <ArrowUp className="h-3 w-3" strokeWidth={2.5} aria-hidden />
      ) : null}
    </Btn>
  );

  return (
    <div className={["gv-surface-brutal p-4 md:p-5", className ?? ""].filter(Boolean).join(" ")}>
      <textarea
        ref={resolved}
        placeholder={placeholder}
        className={[
          "block w-full resize-none bg-transparent text-[color:var(--gv-ink)] placeholder:text-[color:var(--gv-ink-4)] focus:outline-none",
          /* UIUX composer: 17px / 1.5 on --sans; inherits Space Grotesk from .gv-studio-type on /app */
          layout === "studio" ? "text-[17px] leading-[1.5]" : "text-base leading-snug",
        ].join(" ")}
        rows={3}
        value={value}
        onChange={onChange}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        {...rest}
      />
      {layout === "studio" ? (
        <div className="mt-3 flex flex-col gap-3 border-t border-[color:var(--gv-rule)] pt-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">{leftChips}</div>
          <div className="flex shrink-0 items-center gap-2">
            {toolbarEnd}
            {submitBtn}
          </div>
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {leftChips}
          <div className="ml-auto">{submitBtn}</div>
        </div>
      )}
    </div>
  );
});
