---
name: expo-native-reference
description: Official React Native and Expo documentation map, supplemental library docs, EAS/Router vocabulary, and performance investigation pointers (Callstack RN best-practices skill) for RAD mobile work (mobile/, shared/). Use when working on Expo, React Native, FlashList/Reanimated/jank, bundle size, TTI, EAS, or SDK alignment.
---

# Expo and React Native — official reference for RAD

Use this skill to **route questions to the right official docs** and to remember how native work fits the RAD pipeline. It does not replace repo-specific rules.

## Authority order (always)

1. **`.cursor/rules/mobile.mdc`** — prohibitions, NativeWind rules, Radix → @rn-primitives mapping, patterns for this codebase.
2. **`.cursor/agents/mobile-developer.md`** — Foundation vs Feature mode steps, commits, quality gates.
3. **This skill** — canonical URLs (platform + libraries), system requirements, and when to read which chapter.

If this skill and `mobile.mdc` disagree on **how to write code**, `mobile.mdc` wins. If the question is **which Expo SDK API or EAS command applies**, use the official links below for the SDK version in `mobile/package.json`. For **third-party** libraries, prefer the library’s current docs — versions must match `mobile/package.json` / lockfile.

---

## How native work runs in RAD (no `/mobile` command)

- **Shell + providers + auth + first dev build:** Mobile Developer via **`/foundation`** (after web foundation), see `.cursor/commands/foundation.md`.
- **Per-feature screens:** Mobile Developer via **`/feature [name]`** — **Step 2b — Mobile**, see `.cursor/commands/feature.md`.
- **`pwa-then-native` Phase B:** **`/native-init`** once (workspace + shared extraction + Expo scaffold), then **`/foundation` / `/feature`** as in `.cursor/commands/native-init.md`.
- **Web stays in `src/`**; **native stays in `mobile/`**; **`shared/`** holds cross-platform types, validation, Supabase factory, hooks consumed by both.

---

## React Native (Meta) — concepts and prerequisites

| Topic | URL |
| --- | --- |
| Introduction, prerequisites (JS; React helps), how the doc set works | [Introduction · React Native](https://reactnative.dev/docs/getting-started) |
| Why use a framework; Expo as recommended path | [Environment setup](https://reactnative.dev/docs/environment-setup) |
| Views, native components, core building blocks | [Core Components and Native Components](https://reactnative.dev/docs/intro-react-native-components) |

---

## Expo — hub, toolchain, routing, shipping

| Topic | URL | RAD note |
| --- | --- | --- |
| Documentation home | [Expo Documentation](https://docs.expo.dev/) | Primary doc set for `mobile/` |
| **Create project** — Node LTS, OS support (Windows: PowerShell / [WSL 2](https://expo.fyi/wsl)), `create-expo-app`, **SDK templates** (`--template default@sdk-*`) | [Create a project](https://docs.expo.dev/get-started/create-a-project/) | Align new scaffolds with `mobile/package.json` Expo SDK |
| Simulators, devices, Expo Go vs dev client | [Set up your environment](https://docs.expo.dev/get-started/set-up-your-environment/) | |
| File-based routes, deep links, `expo start` workflow | [Introduction to Expo Router](https://docs.expo.dev/router/introduction/) | Routes live under `mobile/src/app/` |
| Custom native code, beyond Expo Go | [Development builds](https://docs.expo.dev/develop/development-builds/introduction/) | Matches EAS **development** profiles in foundation flows |
| EAS overview | [Expo Application Services](https://docs.expo.dev/eas/) | Also [expo.dev/eas](https://expo.dev/eas) |
| Cloud compile + sign | [EAS Build](https://docs.expo.dev/build/introduction/) | |
| Store upload automation | [EAS Submit](https://docs.expo.dev/submit/introduction/) | |
| OTA JavaScript/asset updates | [EAS Update](https://docs.expo.dev/eas-update/introduction/) | |
| Browser playground (optional) | [Expo Snack](https://snack.expo.dev/) | |

---

## Supplemental docs — libraries RAD uses on native

Behavior is often defined by these packages; match **`mobile/package.json`** when reading migration notes.

| Area | Documentation | Typical questions |
| --- | --- | --- |
| **NativeWind** | [NativeWind](https://www.nativewind.dev/) · [Expo Router](https://www.nativewind.dev/getting-started/expo-router) | `className`, `cssInterop`, theme |
| **Expo Router** (deep) | [Router basics](https://docs.expo.dev/router/basics/core-concepts) · [Typed routes](https://docs.expo.dev/router/reference/typed-routes/) | Layouts, modals, linking |
| **React Navigation** | [Docs](https://reactnavigation.org/docs/getting-started/) | Headers, stack/tab under the hood |
| **FlashList** | [FlashList](https://shopify.github.io/flash-list/) | Recycling, `estimatedItemSize`, jank |
| **Reanimated** | [Reanimated](https://docs.swmansion.com/react-native-reanimated/) | Worklets, UI-thread animation |
| **expo-image** | [Expo Image](https://docs.expo.dev/versions/latest/sdk/image/) | `recyclingKey`, placeholders |
| **react-native-reusables** | [Site](https://reactnativereusables.com/) | Primitives |
| **TanStack Query** | [React](https://tanstack.com/query/latest/docs/framework/react/overview) | Same patterns as `shared/hooks/` |
| **RHF + Zod** | [RHF](https://react-hook-form.com/get-started) · [Zod](https://zod.dev) | Forms / `shared/validation/` |
| **Keyboard** | [keyboard-controller](https://kirillzyusko.github.io/react-native-keyboard-controller/) | Scroll + keyboard |
| **Supabase (device)** | [JS ref](https://supabase.com/docs/reference/javascript/introduction) · [Native deep linking](https://supabase.com/docs/guides/auth/native-mobile-deep-linking) | Session + auth with `shared/api` |

**Web parity (`src/`):** [React Router](https://reactrouter.com/home) · [Tailwind](https://tailwindcss.com/docs) — use when debugging web-vs-native behavior.

---

## Performance and profiling (Callstack)

The file you may have is the **index** for Callstack’s **react-native-best-practices** agent skill ([repo](https://github.com/callstackincubator/agent-skills), [skill folder](https://github.com/callstackincubator/agent-skills/tree/main/skills/react-native-best-practices), MIT). The **deep content** lives in that repo’s `references/*.md` files — install or copy the whole skill if you want those chapters; the index alone is a **routing table**.

**Workflow (from that skill):** *Measure → Optimize → Re-measure → Validate*. If the metric does not move, revert and try the next lever.

**Priority themes:** (1) FPS & re-renders (2) bundle size (3) TTI (4) native work (5) memory (6) animations.

**RAD alignment — do not “upgrade” stack from docs blindly:**

- Lists: **`mobile.mdc` already requires FlashList** for dynamic lists — prefer that over lazy ScrollView.
- Animations: **Reanimated only** — already in `mobile.mdc`.
- Data / re-renders: default is **TanStack Query in `shared/hooks/`** — not Jotai/Zustand unless Tech Lead approves.
- **React Compiler / Re.Pack / new state libraries:** optional; treat as architectural changes, not drive-by perf patches.

**Where to start (then open Callstack `references/` if the skill is installed):**

| Symptom | Direction |
| --- | --- |
| Janky UI / frame drops | RN DevTools / FPS → React profiler → list + re-render guides |
| List scroll stutter | FlashList docs + Callstack list references |
| Slow cold start | TTI markers + bundle analysis (Expo/EAS context) |
| Fat JS bundle | `source-map-explorer` / Expo bundle analysis; avoid barrel imports |
| Memory climbing | JS vs native leak chapters |
| TextInput lag | Uncontrolled input / RHF patterns |

**Security:** Treat **shell and bundle-analysis commands** from any external skill as *review before run*; pin tooling; don’t pipe remote scripts into a shell (per Callstack’s own skill notes).

*Attribution: priority/workflow/problem mapping is derived from Callstack’s **react-native-best-practices** skill (MIT); full text and code samples are in their repository.*

---

## When to open which doc

- **Metro errors, config plugins, specific `expo-*` module APIs** → versioned reference for the **same SDK** as `mobile/package.json`.
- **Navigation layouts, tabs, modals, typed routes** → [Expo Router](https://docs.expo.dev/router/introduction/) + [Router basics](https://docs.expo.dev/router/basics/core-concepts).
- **“Works in Expo Go but not in production”** → [Development builds](https://docs.expo.dev/develop/development-builds/introduction/).
- **TestFlight / Play Console / credentials** → [EAS Submit](https://docs.expo.dev/submit/introduction/) and store guides linked from EAS docs.

---

## Human onboarding (longer checklists)

Tables and account-level setup for Tech Leads also appear in **`RAD-GUIDE.md`** under **React Native and Expo** and **Expo documentation**.
