import { useEffect, useState } from "react";

const LG_QUERY = "(min-width: 1024px)";

/** Matches Tailwind ``lg:`` — desktop sidebar visible. */
export function useMediaMinLg(): boolean {
  const [matches, setMatches] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.matchMedia(LG_QUERY).matches;
  });

  useEffect(() => {
    const mq = window.matchMedia(LG_QUERY);
    const onChange = () => setMatches(mq.matches);
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return matches;
}
