# Phase C.1 — Design audit: `/app/answer` shell

**Date:** 2026-04-20  
**Scope:** `src/routes/_app/answer/**`, `src/components/v2/QueryComposer.tsx`, `src/components/v2/answer/**`

## Token grep gate

Run from repo root (expect **0** matches in new files):

```bash
rg '#[0-9a-fA-F]{3,8}|--purple|--ink-soft|--border-active|--gv-purple-|Badge variant="purple"' \
  src/routes/_app/answer src/components/v2/answer src/components/v2/QueryComposer.tsx || true
```

## Status

- **Brutalist shell** uses `--gv-*` tokens and `gv-route-main--1280`.
- **Pattern body** uses `PatternBody` + `ConfidenceStrip` + `WhatStalledRow` (`--gv-danger` for empty WhatStalled label).

## Manual QA

Breakpoints 1100 / 900 / 720 / 640 / 560 — pending device pass.
