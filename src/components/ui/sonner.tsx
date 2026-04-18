"use client";

import type { ComponentProps } from "react";
import { Toaster as Sonner } from "sonner";

const Toaster = ({ ...props }: ComponentProps<typeof Sonner>) => {
  // Sonner portals to the document; gv-studio-type matches /app shell typography.
  return (
    <Sonner
      theme="light"
      className="toaster group gv-studio-type"
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
        } as React.CSSProperties
      }
      {...props}
    />
  );
};

export { Toaster };
