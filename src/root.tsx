import { QueryClientProvider } from "@tanstack/react-query";
import {
  isRouteErrorResponse,
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
  useRouteError,
} from "react-router";
import { AuthProvider } from "@/lib/auth";
import { queryClient } from "@/lib/query-client";
import { PwaUpdatePrompt } from "@/components/PwaUpdatePrompt";
import "./app.css";

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <head>
        <meta charSet="utf-8" />
        {/* viewport-fit=cover lets the page draw under iOS notch / home
            indicator. Used together with ``env(safe-area-inset-*)`` in
            the mobile floating nav + global layout padding so content stays
            inside the safe area while the canvas extends edge-to-edge. */}
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, viewport-fit=cover"
        />
        {/* Favicon + PWA icons — magenta tile + white mark (Branding §07).
         * SVG for modern tabs; PNG/ICO fallbacks for Safari, iOS, Android. */}
        <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
        <link rel="icon" type="image/png" href="/icons/icon-32.png" sizes="32x32" />
        <link rel="icon" type="image/png" href="/icons/icon-16.png" sizes="16x16" />
        <link rel="icon" type="image/x-icon" href="/favicon.ico" />
        <link rel="apple-touch-icon" href="/icons/icon-180.png" sizes="180x180" />
        {/* PWA manifest + theme — magenta brand accent for the URL bar
         * on Android Chrome standalone PWA. */}
        <meta name="theme-color" content="#F72585" />
        <link rel="manifest" href="/manifest.json" />
        {/* Google Fonts: loaded via <link> tags (not CSS @import) so the
         * browser pre-parser discovers them in parallel with the main
         * stylesheet. With CSS @import the fetch was serialised behind
         * root-*.css parsing, leaving the prerendered landing blank on
         * slow networks until Google Fonts CSS finished. ``font-display:
         * swap`` (in the URL) lets the page paint with system fallbacks
         * the moment our own CSS is ready. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Instrument+Serif:ital@0;1&display=swap"
        />
        <Meta />
        <Links />
      </head>
      <body>
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

/**
 * Root catch-all for uncaught render/loader errors (audit 2026-06-10 M-8).
 * Without this, a render crash anywhere in the tree left users on a blank
 * white screen with no way forward. React Router renders the nearest
 * exported ``ErrorBoundary`` instead of unmounting the app.
 */
export function ErrorBoundary() {
  const error = useRouteError();
  const is404 = isRouteErrorResponse(error) && error.status === 404;
  if (import.meta.env.DEV) {
    console.error("[root ErrorBoundary]", error);
  }
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-background px-6 text-center text-foreground">
      <h1 className="text-2xl font-semibold">
        {is404 ? "Không tìm thấy trang này" : "Đã xảy ra lỗi"}
      </h1>
      <p className="max-w-md text-muted-foreground">
        {is404
          ? "Đường dẫn không tồn tại hoặc đã bị di chuyển."
          : "Ứng dụng gặp lỗi không mong muốn. Tải lại trang để tiếp tục — phiên phân tích của bạn vẫn được lưu trong Lịch sử."}
      </p>
      <div className="flex gap-3">
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="min-h-11 rounded-md bg-primary px-5 text-primary-foreground"
        >
          Tải lại trang
        </button>
        <a
          href="/app"
          className="flex min-h-11 items-center rounded-md border border-default px-5"
        >
          Về Sảnh Sáng Tạo
        </a>
      </div>
    </main>
  );
}

export default function App() {
  // QueryClientProvider MUST wrap AuthProvider: the global
  // SessionExpired listener in AuthProvider calls `useQueryClient()`
  // (it subscribes to the query + mutation caches to auto-signout on
  // 401s from Cloud Run). Without this order the prerender of `/`
  // throws during Vercel build, and client-side hydration breaks the
  // same way.
  return (
    // ``TooltipProvider`` lives in ``AppLayout`` (not here) so the
    // unauthenticated landing page doesn't init Radix tooltip
    // context — only authenticated /app/* screens use tooltips
    // (sidebar ``<UsageArc>``).
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Outlet />
        <PwaUpdatePrompt />
      </AuthProvider>
    </QueryClientProvider>
  );
}
