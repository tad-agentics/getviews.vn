import { useCallback, useEffect, useState } from "react";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

function isStandaloneDisplay(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(display-mode: standalone)").matches;
}

function isIOSDevice(): boolean {
  if (typeof navigator === "undefined") return false;
  return /iPhone|iPad|iPod/i.test(navigator.userAgent);
}

export function useInstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  // Start false on SSR; effect corrects to actual value after hydration
  const [isInstalled, setIsInstalled] = useState(false);
  const [isIOS, setIsIOS] = useState(false);

  useEffect(() => {
    // Resolve browser-only values after hydration to avoid SSR/client mismatch
    setIsIOS(isIOSDevice());
    setIsInstalled(isStandaloneDisplay());
    const onChange = () => setIsInstalled(isStandaloneDisplay());
    const mq = window.matchMedia("(display-mode: standalone)");
    mq.addEventListener("change", onChange);
    const onBip = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onBip);
    return () => {
      mq.removeEventListener("change", onChange);
      window.removeEventListener("beforeinstallprompt", onBip);
    };
  }, []);

  const canInstall = !!deferred && !isInstalled;

  const prompt = useCallback(async () => {
    if (!deferred) return;
    await deferred.prompt();
    setDeferred(null);
  }, [deferred]);

  return {
    canInstall,
    isIOS,
    isInstalled,
    prompt,
  };
}
