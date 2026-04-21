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
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="manifest" href="/manifest.json" />
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
