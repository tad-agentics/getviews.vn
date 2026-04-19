# Design system spec — GetViews.vn (Foundation)

**Source:** Studio UI/UX reference in **`artifacts/uiux-reference/`** (shell + screens + `styles.css`); Radix primitives in `src/components/ui/`. Legacy Figma Make dumps may still land in gitignored `src/make-import/` during porting. Tokens live in `src/app.css` (`@theme inline` + `:root` + Phase A `--gv-*`).

## Tokens

Semantic colors: `--purple`, `--ink`, `--surface`, `--border`, `--danger`, `--success`, `--brand-red`, gradients (`--gradient-cta`). Typography: TikTok Sans (`public/fonts/`). Use Tailwind utilities mapped in `@theme` (e.g. `bg-primary`, `text-foreground`) where available; Make screens often use `bg-[var(--surface)]` — keep parity when porting screens.

## UI primitives (`src/components/ui/`)

| Component file | Role |
|----------------|------|
| `Button.tsx` | Primary CTA — variants `primary` \| `secondary` \| `outlined` \| `danger`, `fullWidth` |
| `Input.tsx` | Text input — matches Make form fields |
| `Badge.tsx` | Small labels |
| `Card.tsx` | Card container |
| `accordion.tsx` | Radix Accordion — FAQ, collapsible sections |
| `alert.tsx` / `alert-dialog.tsx` | Status + modal alerts |
| `avatar.tsx` | User avatar |
| `breadcrumb.tsx` | Nav breadcrumbs |
| `calendar.tsx` | Date picker (react-day-picker) |
| `carousel.tsx` | Embla carousel wrapper |
| `chart.tsx` | Recharts wrapper |
| `checkbox.tsx` | Checkbox |
| `collapsible.tsx` | Collapsible |
| `command.tsx` | cmdk command palette |
| `context-menu.tsx` | Right-click menu |
| `dialog.tsx` | Modal dialog (Radix) |
| `drawer.tsx` | Vaul drawer |
| `dropdown-menu.tsx` | Dropdown |
| `form.tsx` | react-hook-form helpers |
| `hover-card.tsx` | Hover card |
| `input-otp.tsx` | OTP input |
| `label.tsx` | Form label |
| `menubar.tsx` | Menubar |
| `navigation-menu.tsx` | Navigation menu |
| `pagination.tsx` | Pagination |
| `popover.tsx` | Popover |
| `progress.tsx` | Progress bar |
| `radio-group.tsx` | Radio group |
| `resizable.tsx` | Resizable panels |
| `scroll-area.tsx` | Scroll area |
| `select.tsx` | Select |
| `separator.tsx` | Separator |
| `sheet.tsx` | Side sheet |
| `sidebar.tsx` | Sidebar shell |
| `skeleton.tsx` | Skeleton placeholder |
| `slider.tsx` | Slider |
| `sonner.tsx` | Toasts (theme fixed to `light`; no `next-themes`) |
| `switch.tsx` | Switch |
| `table.tsx` | Table |
| `tabs.tsx` | Tabs |
| `textarea.tsx` | Textarea |
| `toggle.tsx` / `toggle-group.tsx` | Toggle |
| `tooltip.tsx` | Tooltip |
| `aspect-ratio.tsx` | Aspect ratio wrapper |
| `utils.ts` | `cn()` helper |
| `use-mobile.ts` | Breakpoint hook |

## Shared layout / chrome (`src/components/`)

| Component | Purpose |
|-----------|---------|
| `AppLayout.tsx` | Authenticated app shell from Make — sidebar, sessions (still on mock data until features wire Supabase) |
| `BottomNav.tsx` | 3 tabs: Chat `/app`, Xu hướng `/app/trends`, Lịch sử `/app/history` |
| `EmptyState.tsx` | Icon + title + body + optional CTA |
| `ErrorBanner.tsx` | Error message + retry |
| `SkeletonCard.tsx` | Pulsing placeholder card |

## Gaps addressed in Foundation

- Loading / error / empty: `EmptyState`, `ErrorBanner`, `SkeletonCard` for feature routes.
- Install UX: `useInstallPrompt` for PWA CTA on landing.

## Rules for feature agents

- Prefer Make primitives from `src/components/ui/` before adding new libraries.
- Port screens: **copy Make TSX**, then `str_replace` imports, data, and `/app` paths only — preserve Tailwind classes.
- Credits: use `useCredits()` for balance; `useAuth()` for session (from `@/lib/auth`).
