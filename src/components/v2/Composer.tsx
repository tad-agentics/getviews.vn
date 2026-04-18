import { forwardRef, useRef, type KeyboardEvent, type TextareaHTMLAttributes } from "react";
import { Btn } from "./Btn";

/**
 * Neo-brutalist composer card — 2px ink border, 6px hard offset shadow,
 * pink "Gửi" submit button. Used on Home as the launcher into the research
 * session; also on FollowUpComposer in the answer screen (A3.3+).
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
} & Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "onSubmit">;

export const Composer = forwardRef<HTMLTextAreaElement, ComposerProps>(function Composer(
  {
    placeholder = "Hỏi mình bất kỳ điều gì về ngách của bạn…",
    submitLabel = "Gửi",
    onSubmit,
    disabled,
    leftChips,
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

  return (
    <div className={["gv-surface-brutal p-4 md:p-5", className ?? ""].filter(Boolean).join(" ")}>
      <textarea
        ref={resolved}
        placeholder={placeholder}
        className="block w-full resize-none bg-transparent text-base leading-snug text-[color:var(--gv-ink)] placeholder:text-[color:var(--gv-ink-4)] focus:outline-none"
        rows={3}
        value={value}
        onChange={onChange}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        {...rest}
      />
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {leftChips}
        <div className="ml-auto">
          <Btn
            type="button"
            variant="accent"
            size="md"
            onClick={handleSubmit}
            disabled={disabled}
          >
            {submitLabel}
          </Btn>
        </div>
      </div>
    </div>
  );
});
