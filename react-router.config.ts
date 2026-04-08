import type { Config } from "@react-router/dev/config";

export default {
  // SPA mode — no runtime server, static files only
  ssr: false,

  // Pre-render the landing page at build time for SEO + OG tags
  // All other routes load as SPA (client-side routing)
  async prerender() {
    return ["/"];
  },
} satisfies Config;
