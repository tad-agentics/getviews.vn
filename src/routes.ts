import { type RouteConfig, index, layout, route } from "@react-router/dev/routes";

export default [
  // Landing page — pre-rendered for SEO
  index("routes/_index/route.tsx"),

  // Auth routes
  route("login", "routes/_auth/login/route.tsx"),
  route("signup", "routes/_auth/signup/route.tsx"),
  route("auth/callback", "routes/_auth/callback/route.tsx"),

  // Authenticated app routes — guarded by layout
  layout("routes/_app/layout.tsx", [
    route("app", "routes/_app/route.tsx"),
    route("app/chat", "routes/_app/chat/route.tsx"),
    route("app/onboarding", "routes/_app/onboarding/route.tsx"),
    route("app/history", "routes/_app/history/route.tsx"),
    route("app/trends", "routes/_app/trends/route.tsx"),
    route("app/video", "routes/_app/video/route.tsx"),
    route("app/kol", "routes/_app/kol/route.tsx"),
    route("app/settings", "routes/_app/settings/route.tsx"),
    route("app/learn-more", "routes/_app/learn-more/route.tsx"),
    route("app/pricing", "routes/_app/pricing/route.tsx"),
    route("app/checkout", "routes/_app/checkout/route.tsx"),
    route("app/payment-success", "routes/_app/payment-success/route.tsx"),
  ]),
] satisfies RouteConfig;
