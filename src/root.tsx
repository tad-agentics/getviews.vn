import {
  isRouteErrorResponse,
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";
import { QueryClientProvider } from "@tanstack/react-query";

import type { Route } from "./+types/root";
import { AuthProvider } from "@/lib/auth";
import { queryClient } from "@/lib/query-client";
import "./app.css";

export const links: Route.LinksFunction = () => [
  { rel: "preconnect", href: "https://fonts.googleapis.com" },
  {
    rel: "preconnect",
    href: "https://fonts.gstatic.com",
    crossOrigin: "anonymous",
  },
  // TikTok Sans for Vietnamese diacritic support (primary)
  // Self-hosted .woff2 in public/fonts/ — add @font-face in app.css
  // JetBrains Mono for data/numbers
  {
    rel: "stylesheet",
    href: "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500&display=swap",
  },
];

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
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
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Outlet />
      </AuthProvider>
    </QueryClientProvider>
  );
}

export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  let message = "Lỗi";
  let details = "Đã xảy ra lỗi không mong muốn.";
  let stack: string | undefined;

  if (isRouteErrorResponse(error)) {
    message = error.status === 404 ? "404" : "Lỗi";
    details =
      error.status === 404
        ? "Trang không tồn tại."
        : error.statusText || details;
  } else if (import.meta.env.DEV && error && error instanceof Error) {
    details = error.message;
    stack = error.stack;
  }

  return (
    <main className="pt-16 p-4 container mx-auto">
      <h1 className="text-xl font-bold">{message}</h1>
      <p className="text-[#71717A]">{details}</p>
      {stack && (
        <pre className="w-full p-4 overflow-x-auto text-sm">
          <code>{stack}</code>
        </pre>
      )}
    </main>
  );
}
