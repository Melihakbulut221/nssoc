#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Exercise the real Ibex/ROM/flash path, including geometry rejection.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
export PATH="$ROOT/.venv/bin:$PATH"
OUT="$ROOT/hw/soc/out/boot-regression"
mkdir -p "$OUT"
if [ "$#" = 0 ]; then set -- none entry0 length0; fi
for mode in "$@"; do
    case "$mode" in none|entry0|length0) ;; *) echo "unknown boot case: $mode" >&2; exit 2 ;; esac
    if ! BOOT_CORRUPT="$mode" bash "$ROOT/hw/soc/flow/sim_soc.sh" "$OUT/$mode" >"$OUT/$mode.log" 2>&1; then
        tail -25 "$OUT/$mode.log" >&2
        exit 1
    fi
    log="$OUT/$mode/sim.log"
    grep -q 'checks run: 0x0000001c  fail mask: 0x00000000' "$log"
    grep -q '^\[TB\] PASS' "$log"
    if [ "$mode" != none ]; then
        grep -q 'image 0x00000000 rejected, cause 0x00000004' "$log"
        grep -q 'image 0x00000001 at 0x0001c000' "$log"
    fi
    printf '%s: PASS (28 application checks%s)\n' "$mode" "$(if [ "$mode" != none ]; then printf ', secondary image selected'; fi)"
done
