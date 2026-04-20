#!/usr/bin/env bash
# Phase C.2.6 — WhatStalled invariant (pytest).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/cloud-run"
python3 -m pytest tests/test_report_pattern.py -q
