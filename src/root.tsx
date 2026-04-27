import { QueryClientProvider } from "@tanstack/react-query";
import {
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";
import { AuthProvider } from "@/lib/auth";
import { queryClient } from "@/lib/query-client";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./app.css";

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <head>
        <meta charSet="utf-8" />
        {/* viewport-fit=cover lets the page draw under iOS notch / home
            indicator. Used together with ``env(safe-area-inset-*)`` in
            BottomTabBar.tsx + global layout padding so content stays
            inside the safe area while the canvas extends edge-to-edge. */}
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, viewport-fit=cover"
        />
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

export default function App() {
  // QueryClientProvider MUST wrap AuthProvider: the global
  // SessionExpired listener in AuthProvider calls `useQueryClient()`
  // (it subscribes to the query + mutation caches to auto-signout on
  // 401s from Cloud Run). Without this order the prerender of `/`
  // throws during Vercel build, and client-side hydration breaks the
  // same way.
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TooltipProvider delayDuration={200}>
          <Outlet />
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
